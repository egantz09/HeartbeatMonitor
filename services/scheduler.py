# services/scheduler.py
"""
Worker de fondo (QObject con QTimers) que se ejecuta en el hilo principal
de Qt. Se encarga de:

  - Hacer ping a múltiples hosts EN PARALELO en un hilo de fondo
    (la UI nunca se bloquea esperando respuestas).
  - Detectar cambios de estado por host y notificar (hilo principal).
  - Ejecutar el resumen diario a medianoche + mantenimiento (purga).

Cada QTimer dispara señales que la GUI consume para refrescarse.
"""
import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, date

from PyQt6.QtCore import QObject, QTimer, QThread, pyqtSignal, pyqtSlot

from core.summary import build_summary
from core.excel_manager import ExcelManager
from core.database import Database
from core.metrics import ping
from core.config import Config
from core.constants import (
    EVENT_NET_DOWN, EVENT_NET_UP,
    EVENT_HW_ALERT,
)
from services.notifier import notifier

log = logging.getLogger(__name__)


class _PingWorker(QObject):
    """
    Vive en un hilo de fondo (QThread dedicado). Lanza un ping por host
    en paralelo y emite el resultado; no toca la base de datos ni la UI.
    """

    pings_done = pyqtSignal(dict)   # {host: {"ok", "ping_ms", "timestamp"}}

    @pyqtSlot()
    def collect(self):
        try:
            if not Config.get("ping_enabled", True):
                return

            hosts = Config.get("ping_hosts", []) or []
            hosts = [h.strip() for h in hosts if h and h.strip()]
            if not hosts:
                return

            resultados = {}
            with ThreadPoolExecutor(max_workers=len(hosts)) as ex:
                futures = {h: ex.submit(ping, h) for h in hosts}
                for host, fut in futures.items():
                    try:
                        ok, latency = fut.result()
                    except Exception as e:
                        # Aislamiento: si un host falla, los demás siguen
                        log.debug(f"Ping a {host} lanzó excepción: {e}")
                        ok, latency = False, None
                    resultados[host] = {
                        "ok": ok,
                        "ping_ms": latency,
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                    }

            if resultados:
                self.pings_done.emit(resultados)

        except Exception as e:
            log.warning(f"Error en _PingWorker.collect: {e}")


class BackgroundWorker(QObject):

    summary_ready = pyqtSignal(dict)
    ping_ready    = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._last_run_day = None
        self._net_state = {}   # {host: bool}
        self._last_alert = {}  # {metric: timestamp}

        # Hilo dedicado a los pings
        self._ping_thread = QThread(self)
        self._ping_worker = _PingWorker()
        self._ping_worker.moveToThread(self._ping_thread)
        # El resultado vuelve al hilo principal (conexión queued automática)
        self._ping_worker.pings_done.connect(self._on_pings_done)
        self._ping_thread.start()

        # Timer de medianoche (chequea cada 30 s)
        self.timer_midnight = QTimer(self)
        self.timer_midnight.timeout.connect(self._tick_midnight)
        self.timer_midnight.start(30_000)

        # Timer de pings: dispara el slot del worker vía conexión queued
        self.timer_ping = QTimer(self)
        self.timer_ping.timeout.connect(self._ping_worker.collect)
        self._reschedule_ping()

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def shutdown(self):
        """Detiene timers y el hilo de pings (llamar desde aboutToQuit)."""
        self.timer_ping.stop()
        self.timer_midnight.stop()
        if self._ping_thread.isRunning():
            self._ping_thread.quit()
            self._ping_thread.wait(3000)

    # ------------------------------------------------------------------
    # Reprogramar según config
    # ------------------------------------------------------------------
    def _reschedule_ping(self):
        interval = max(10, int(Config.get("ping_interval", 60)))
        self.timer_ping.start(interval * 1000)
        log.info(f"Timer de pings cada {interval} s")

    # ------------------------------------------------------------------
    # Recepción de resultados de ping (hilo principal)
    # ------------------------------------------------------------------
    def _on_pings_done(self, resultados: dict):
        """Persiste lecturas, detecta cambios de estado y notifica."""
        for host, r in resultados.items():
            try:
                Database.add_ping(host, r["ping_ms"], r["ok"])
            except Exception as e:
                log.warning(f"No se pudo guardar ping de {host}: {e}")

            self._detect_state_change(host, r["ok"])

        self.ping_ready.emit(resultados)

    def _detect_state_change(self, host: str, ok: bool):
        """Registra eventos NET_DOWN / NET_UP cuando cambia el estado."""
        prev = self._net_state.get(host)

        if prev is None:
            # Primera lectura: guardar estado, solo notificar si falla
            self._net_state[host] = ok
            if not ok:
                try:
                    Database.add_event(EVENT_NET_DOWN, host)
                    notifier.notify_net(False, host)
                except Exception:
                    pass
            return

        if prev == ok:
            return

        # Cambio de estado
        try:
            if ok:
                Database.add_event(EVENT_NET_UP, host)
                notifier.notify_net(True, host)
            else:
                Database.add_event(EVENT_NET_DOWN, host)
                notifier.notify_net(False, host)
        except Exception as e:
            log.warning(f"Error registrando cambio de red para {host}: {e}")

        self._net_state[host] = ok

    # ------------------------------------------------------------------
    # Resumen a medianoche
    # ------------------------------------------------------------------
    def _tick_midnight(self):
        now = datetime.now()
        # Ventana: 00:00 a 00:00:59
        if now.hour != 0 or now.minute >= 1:
            return

        target = now.date() - timedelta(days=1)
        if self._last_run_day == target:
            return

        self._last_run_day = target
        self._run_midnight(target)

    def _run_midnight(self, day: date):
        try:
            result = build_summary(day)
            self.summary_ready.emit(result)
            log.info(f"Resumen de {day} generado: {result}")

            # Export + purga en un hilo de fondo: no bloquear la UI
            threading.Thread(
                target=self._maintenance_task, args=(day,), daemon=True
            ).start()
        except Exception as e:
            log.warning(f"Error en resumen medianoche: {e}")

    def _maintenance_task(self, day: date):
        try:
            ExcelManager.export_month(day)
        except Exception as e:
            log.warning(f"Error exportando Excel en medianoche: {e}")

        try:
            # Evita que events/ping_metrics crezcan sin límite
            deleted = Database.purge_old_data(days=365)
            if deleted:
                log.info(f"Purga: {deleted} filas eliminadas")
        except Exception as e:
            log.warning(f"Error purgando datos antiguos: {e}")

    # ------------------------------------------------------------------
    # Umbrales de hardware (opcional, por si en el futuro se reactiva)
    # ------------------------------------------------------------------
    def _check_threshold(self, name: str, value: float,
                         cfg_key: str, min_minutes: int = 10):
        """Alerta solo si supera umbral y no alertó en los últimos N minutos."""
        if value is None:
            return

        threshold = float(Config.get(cfg_key, 90.0))
        if value < threshold:
            return

        now = datetime.now().timestamp()
        last = self._last_alert.get(name, 0.0)
        if now - last < min_minutes * 60:
            return
        self._last_alert[name] = now

        try:
            Database.add_event(
                EVENT_HW_ALERT,
                f"{name}={value:.1f}% (límite {threshold:.0f}%)",
            )
            notifier.notify_hw_alert(name, value, threshold)
            log.warning(f"Alerta de {name}: {value:.1f}%")
        except Exception as e:
            log.warning(f"Error notificando alerta de {name}: {e}")


# Alias retro-compatible con el nombre anterior
MidnightScheduler = BackgroundWorker
