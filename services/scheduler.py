# services/scheduler.py
import logging
from datetime import datetime, timedelta, date

from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from core.summary import build_summary
from core.excel_manager import ExcelManager
from core.database import Database
from core.metrics import ping
from core.config import Config
from core.constants import EVENT_NET_DOWN, EVENT_NET_UP
from services.notifier import notifier

log = logging.getLogger(__name__)


class BackgroundWorker(QObject):
    """
    Worker de fondo que corre en el hilo principal de Qt.
    - Hace ping a múltiples hosts.
    - Detecta cambios de estado por host.
    - Ejecuta el resumen diario a medianoche.
    """

    summary_ready = pyqtSignal(dict)
    ping_ready    = pyqtSignal(dict)   # {host: {...}}

    def __init__(self, parent=None):
        super().__init__(parent)

        self._last_run_day = None
        self._net_state = {}   # {host: bool}

        # --- Timer medianoche ---
        self.timer_midnight = QTimer(self)
        self.timer_midnight.timeout.connect(self._tick_midnight)
        self.timer_midnight.start(30_000)

        # --- Timer pings ---
        self.timer_ping = QTimer(self)
        self.timer_ping.timeout.connect(self._collect_pings)
        self._reschedule_ping()

    # ------------------------------------------------------------------
    # Reprogramar según config
    # ------------------------------------------------------------------
    def _reschedule_ping(self):
        interval = max(10, int(Config.get("ping_interval", 60)))
        self.timer_ping.start(interval * 1000)
        log.info(f"Ping cada {interval} s")

    # ------------------------------------------------------------------
    # Pings
    # ------------------------------------------------------------------
    def _collect_pings(self):
        try:
            # Si el monitoreo de red está desactivado, no hacemos nada
            if not Config.get("ping_enabled", True):
                return

            hosts = Config.get("ping_hosts", []) or []
            resultados = {}

            hosts = Config.get("ping_hosts", []) or []
            resultados = {}

            for host in hosts:
                ok, latency = ping(host)
                Database.add_ping(host, latency, ok)

                prev = self._net_state.get(host)
                if prev is None:
                    # Primera lectura: sin evento, pero notificamos si falla
                    self._net_state[host] = ok
                    if not ok:
                        Database.add_event(
                            EVENT_NET_DOWN, host
                        )
                        notifier.notify_net(False, host)
                elif prev != ok:
                    if ok:
                        Database.add_event(EVENT_NET_UP, host)
                        notifier.notify_net(True, host)
                    else:
                        Database.add_event(EVENT_NET_DOWN, host)
                        notifier.notify_net(False, host)
                    self._net_state[host] = ok

                resultados[host] = {
                    "host": host,
                    "ok": ok,
                    "ping_ms": latency,
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }

            self.ping_ready.emit(resultados)

        except Exception as e:
            log.warning(f"Error en _collect_pings: {e}")

    # ------------------------------------------------------------------
    # Resumen a medianoche
    # ------------------------------------------------------------------
    def _tick_midnight(self):
        now = datetime.now()
        if now.hour == 0 and now.minute < 1:
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
            ExcelManager.export_month(day)
        except Exception as e:
            log.warning(f"Error en resumen medianoche: {e}")


# Alias retro-compatible
MidnightScheduler = BackgroundWorker