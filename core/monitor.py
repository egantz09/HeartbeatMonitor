# core/monitor.py
from datetime import datetime, timedelta
from core.state_manager import StateManager
from core.database import Database
from core.constants import (
    EVENT_BOOT, EVENT_POWER_LOSS, EVENT_KERNEL_PWR,
    POWER_LOSS_THRESHOLD,
)
from core import event_log

from services.notifier import notifier


class HeartbeatMonitor:

    def __init__(self):
        Database.init()
        self._first_boot_seen = False

    # ------------------------------------------------------------------
    # Chequeo al arranque
    # ------------------------------------------------------------------
    def startup_check(self):
        power_loss = False
        offline_str = ""

        # --- Fuente 1: delta de heartbeat ---
        state = StateManager.load()
        if state and "last_heartbeat" in state:
            try:
                last = datetime.fromisoformat(state["last_heartbeat"])
                delta = datetime.now() - last
                if delta.total_seconds() > POWER_LOSS_THRESHOLD:
                    power_loss = True
                    offline_str = str(delta)
            except ValueError:
                pass

        # --- Fuente 2: Event Log de Windows ---
        kernel_event = None
        if event_log.is_available():
            kernel_event = event_log.detect_power_loss_since_last_boot()
            if kernel_event and not power_loss:
                # Si Windows lo registró, es un corte seguro
                power_loss = True
                offline_str = (
                    f"Event Log ID {kernel_event['event_id']} "
                    f"a las {kernel_event['time']:%H:%M:%S}"
                )

        # --- Registro ---
        if power_loss:
            Database.add_event(EVENT_POWER_LOSS, f"Offline {offline_str}")

        if kernel_event:
            Database.add_event(
                EVENT_KERNEL_PWR,
                f"ID {kernel_event['event_id']} — {kernel_event['source']}",
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
        except Exception:
            pass

        StateManager.save_heartbeat()
        self._first_boot_seen = True

    # ------------------------------------------------------------------
    # Heartbeat periódico
    # ------------------------------------------------------------------
    def heartbeat(self):
        StateManager.save_heartbeat()