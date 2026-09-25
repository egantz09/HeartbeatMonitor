# core/monitor.py
import logging
from datetime import datetime

from core.state_manager import StateManager
from core.database import Database
from core.config import Config
from core.constants import (
    EVENT_BOOT, EVENT_POWER_LOSS, EVENT_KERNEL_POWER,
    POWER_LOSS_THRESHOLD,
)
from core import event_log
from services.notifier import notifier

log = logging.getLogger(__name__)


class HeartbeatMonitor:

    def __init__(self):
        Database.init()
        Database.init_ping()

    # ------------------------------------------------------------------
    def startup_check(self):
        """
        Se ejecuta al arrancar la app. Detecta si hubo un corte eléctrico
        combinando dos fuentes:
          1. Delta de heartbeat (state.json)
          2. Windows Event Log ID 41 (Kernel-Power)
        """
        power_loss = False
        offline_str = ""

        # --- Fuente 1: delta de heartbeat ---
        offline_secs = StateManager.offline_seconds()
        if offline_secs is not None and offline_secs > POWER_LOSS_THRESHOLD:
            power_loss = True
            offline_str = self._fmt_seconds(offline_secs)

        # --- Fuente 2: Event Log de Windows (si el usuario lo activó) ---
        kernel_event = None
        if Config.get("read_event_log", True) and event_log.is_available():
            try:
                kernel_event = event_log.detect_power_loss_since_last_boot()
            except Exception as e:
                log.warning(f"Error consultando Event Log: {e}")

            if kernel_event and not power_loss:
                power_loss = True
                offline_str = (
                    f"Event Log ID {kernel_event['event_id']} "
                    f"a las {kernel_event['time']:%H:%M:%S}"
                )

        # --- Registro en DB ---
        if power_loss:
            Database.add_event(EVENT_POWER_LOSS, f"Offline {offline_str}")
            log.warning(f"Corte detectado: {offline_str}")

        if kernel_event:
            Database.add_event(
                EVENT_KERNEL_POWER,
                f"ID {kernel_event['event_id']} - {kernel_event['source']}",
            )

        Database.add_event(
            EVENT_BOOT,
            "power_loss" if power_loss else "normal",
        )

        # --- Notificación ---
        try:
            if power_loss:
                notifier.notify_power_loss(offline_str)
            else:
                notifier.notify_boot(after_power_loss=False)
        except Exception as e:
            log.debug(f"No se pudo notificar: {e}")

        # Guarda heartbeat inicial
        StateManager.save_heartbeat()

    # ------------------------------------------------------------------
    def heartbeat(self):
        """
        Se ejecuta cada HEARTBEAT_INTERVAL segundos.
        Solo actualiza state.json. No persiste en DB para no llenarla.
        """
        StateManager.save_heartbeat()

    # ------------------------------------------------------------------
    @staticmethod
    def _fmt_seconds(secs: float) -> str:
        """Convierte segundos a 'HH:MM:SS' legible."""
        total = int(secs)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h > 0:
            return f"{h:02d}:{m:02d}:{s:02d}"
        return f"{m:02d}:{s:02d}"