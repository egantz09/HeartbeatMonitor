import json
from datetime import datetime
from core.constants import STATE_FILE


class StateManager:

    @staticmethod
    def save_heartbeat():
        data = {"last_heartbeat": datetime.now().isoformat()}
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

    @staticmethod
    def load():
        if not STATE_FILE.exists():
            return None
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    @staticmethod
    def clear():
        if STATE_FILE.exists():
            STATE_FILE.unlink()