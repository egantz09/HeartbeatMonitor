# services/scheduler.py
"""
Worker de fondo (QObject con QTimers) que se ejecuta en el hilo principal
de Qt. Se encarga de:

  - Hacer ping a múltiples hosts y registrar eventos NET_DOWN / NET_UP.
  - Detectar cambios de estado por host.
  - Ejecutar el resumen diario a medianoche.
  - (Opcional) Chequear umbrales de hardware.

Cada QTimer dispara señales que la GUI consume para refrescarse.
"""
import logging
from datetime import datetime, timedelta, date

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

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


class BackgroundWorker(QObject):

    summary_ready = pyqtSignal(dict)
    ping_ready    = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._last_run_day = None
        self._net_state = {}   # {host: bool}
        self._last_alert = {}  # {metric: timestamp}

        # Timer de medianoche (chequea cada 30 s)
        self.timer_midnight = QTimer(self)
        self.timer_midnight.timeout.connect(self._tick_midnight)
        self.timer_midnight.start(30_000)

        # Timer de pings
        self.timer_ping = QTimer(self)
        self.timer_ping.timeout.connect(self._collect_pings)
        self._reschedule_ping()

    # ------------------------------------------------------------------
    # Reprogramar según config
    # ------------------------------------------------------------------
    def _reschedule_ping(self):
        interval = max(10, int(Config.get("ping_interval", 60)))
        self.timer_ping.start(interval * 1000)
        log.info(f"Timer de pings cada {interval} s")

    # ------------------------------------------------------------------
    # Pings multi-host
    # ------------------------------------------------------------------
    def _collect_pings(self):
        try:
            if not Config.get("ping_enabled", True):
                # Monitoreo desactivado
                return

            hosts = Config.get("ping_hosts", []) or []
            hosts = [h.strip() for h in hosts if h and h.strip()]

            # Limpiar hosts eliminados del estado interno
            for h in list(self._net_state.keys()):
                if h not in hosts:
                    del self._net_state[h]

            if not hosts:
                return

            resultados = {}

            for host in hosts:
                # Aislamiento: si un host falla, los demás siguen
                try:
                    ok, latency = ping(host)
                except Exception as e:
                    log.debug(f"Ping a {host} lanzó excepción: {e}")
                    ok, latency = False, None

                try:
                    Database.add_ping(host, latency, ok)
                except Exception as e:
                    log.warning(f"No se pudo guardar ping de {host}: {e}")

                self._detect_state_change(host, ok)

                resultados[host] = {
                    "host": host,
                    "ok": ok,
                    "ping_ms": latency,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }

            self.ping_ready.emit(resultados)

        except Exception as e:
            log.warning(f"Error en _collect_pings: {e}")

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

            # Exportar el mes al que pertenece el día
            ExcelManager.export_month(day)
        except Exception as e:
            log.warning(f"Error en resumen medianoche: {e}")

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