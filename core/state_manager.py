# core/state_manager.py
import json
from datetime import datetime
from pathlib import Path

from core.constants import STATE_FILE, POWER_LOSS_THRESHOLD


class StateManager:

    @staticmethod
    def save_heartbeat():
        """Guarda el último heartbeat en state.json."""
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        data = {"last_heartbeat": datetime.now().isoformat()}
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except OSError:
            pass

    @staticmethod
    def load():
        """Devuelve el dict con last_heartbeat o None."""
        if not STATE_FILE.exists():
            return None
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def clear():
        """Borra state.json (llamado en cierre limpio)."""
        try:
            if STATE_FILE.exists():
                STATE_FILE.unlink()
        except OSError:
            pass

    @classmethod
    def offline_seconds(cls) -> float | None:
        """
        Devuelve cuántos segundos pasaron desde el último heartbeat,
        o None si no hay estado previo.
        """
        state = cls.load()
        if not state or "last_heartbeat" not in state:
            return None
        try:
            last = datetime.fromisoformat(state["last_heartbeat"])
        except ValueError:
            return None
        return (datetime.now() - last).total_seconds()

    @classmethod
    def had_power_loss(cls) -> bool:
        """True si el último heartbeat fue hace más del umbral."""
        secs = cls.offline_seconds()
        return secs is not None and secs > POWER_LOSS_THRESHOLD