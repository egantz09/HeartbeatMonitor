# core/config.py
import json
from pathlib import Path

from core.constants import (
    BASE_DIR, THEME_DARK,
    DEFAULT_PING_HOSTS, DEFAULT_PING_INTERVAL,
    DEFAULT_METRICS_INTERVAL, DEFAULT_DISK_THRESHOLD,
    DEFAULT_RAM_THRESHOLD, DEFAULT_CPU_THRESHOLD,
)

CONFIG_FILE = BASE_DIR / "data" / "settings.json"

DEFAULTS = {
    "theme": THEME_DARK,
    "ping_hosts": list(DEFAULT_PING_HOSTS),
    "ping_interval": DEFAULT_PING_INTERVAL,
    "metrics_interval": DEFAULT_METRICS_INTERVAL,
    "disk_threshold": DEFAULT_DISK_THRESHOLD,
    "ram_threshold": DEFAULT_RAM_THRESHOLD,
    "cpu_threshold": DEFAULT_CPU_THRESHOLD,
    "notifications_enabled": True,
    "read_event_log": True,
    "ping_enabled": True,          # ← NUEVO
}

class Config:

    _cache = None

    @classmethod
    def load(cls) -> dict:
        if cls._cache is not None:
            return cls._cache

        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                data = {}
        else:
            data = {}

        # Migración: si venimos de la versión con `ping_host` único
        if "ping_host" in data and "ping_hosts" not in data:
            data["ping_hosts"] = [data.pop("ping_host")]
        else:
            data.pop("ping_host", None)

        merged = {**DEFAULTS, **data}

        # Asegurar tipo lista
        if isinstance(merged.get("ping_hosts"), str):
            merged["ping_hosts"] = [merged["ping_hosts"]]
        if not merged.get("ping_hosts"):
            merged["ping_hosts"] = list(DEFAULT_PING_HOSTS)

        cls._cache = merged
        cls.save()
        return merged

    @classmethod
    def save(cls, data: dict | None = None):
        if data is not None:
            cls._cache = {**DEFAULTS, **data}
        if cls._cache is None:
            cls._cache = dict(DEFAULTS)

        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cls._cache, f, indent=2, ensure_ascii=False)

    @classmethod
    def get(cls, key: str, default=None):
        return cls.load().get(key, default)

    @classmethod
    def set(cls, key: str, value):
        cfg = cls.load()
        cfg[key] = value
        cls.save(cfg)