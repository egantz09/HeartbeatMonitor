# core/config.py
import json
from pathlib import Path

from core.constants import (
    BASE_DIR, THEME_DARK,
    DEFAULT_PING_HOSTS, DEFAULT_PING_INTERVAL,
    DEFAULT_DISK_THRESHOLD, DEFAULT_RAM_THRESHOLD, DEFAULT_CPU_THRESHOLD,
)

CONFIG_FILE = BASE_DIR / "data" / "settings.json"

DEFAULTS = {
    "theme": THEME_DARK,
    "ping_enabled": True,
    "ping_hosts": list(DEFAULT_PING_HOSTS),
    "ping_interval": DEFAULT_PING_INTERVAL,
    "disk_threshold": DEFAULT_DISK_THRESHOLD,
    "ram_threshold": DEFAULT_RAM_THRESHOLD,
    "cpu_threshold": DEFAULT_CPU_THRESHOLD,
    "notifications_enabled": True,
    "read_event_log": True,
}


class Config:

    _cache = None
    _cache_mtime = None

    # ------------------------------------------------------------------
    @classmethod
    def load(cls) -> dict:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

        try:
            mtime = CONFIG_FILE.stat().st_mtime if CONFIG_FILE.exists() else 0
        except OSError:
            mtime = 0

        # Cache válida solo si el archivo no cambió
        if cls._cache is not None and cls._cache_mtime == mtime:
            return cls._cache

        # Leer del disco
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                data = {}
        else:
            data = {}

        # Migración de versiones previas
        if "ping_host" in data and "ping_hosts" not in data:
            data["ping_hosts"] = [data.pop("ping_host")]
        else:
            data.pop("ping_host", None)

        merged = {**DEFAULTS, **data}

        # Asegurar que ping_hosts es lista no vacía
        if isinstance(merged.get("ping_hosts"), str):
            merged["ping_hosts"] = [merged["ping_hosts"]]
        if not merged.get("ping_hosts"):
            merged["ping_hosts"] = list(DEFAULT_PING_HOSTS)

        cls._cache = merged
        cls._cache_mtime = mtime
        return merged

    # ------------------------------------------------------------------
    @classmethod
    def save(cls, data: dict | None = None):
        if data is not None:
            cls._cache = {**DEFAULTS, **data}
        if cls._cache is None:
            cls._cache = dict(DEFAULTS)

        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cls._cache, f, indent=2, ensure_ascii=False)

        # Actualizar mtime tras escribir
        try:
            cls._cache_mtime = CONFIG_FILE.stat().st_mtime
        except OSError:
            cls._cache_mtime = None

    # ------------------------------------------------------------------
    @classmethod
    def get(cls, key: str, default=None):
        return cls.load().get(key, default)

    # ------------------------------------------------------------------
    @classmethod
    def set(cls, key: str, value):
        cfg = cls.load()
        cfg[key] = value
        cls.save(cfg)