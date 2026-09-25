# core/metrics.py
import logging
import platform
import subprocess
from datetime import datetime

import psutil

log = logging.getLogger(__name__)


def cpu_percent() -> float:
    try:
        return float(psutil.cpu_percent(interval=None))
    except Exception:
        return 0.0


def ram_percent() -> float:
    try:
        return float(psutil.virtual_memory().percent)
    except Exception:
        return 0.0


def disk_percent(path: str = None) -> float:
    """Uso del disco en el que está instalada la app (o el indicado)."""
    try:
        if path is None:
            # En Windows usamos la unidad donde está la app
            from core.constants import BASE_DIR
            path = BASE_DIR.anchor or "C:\\"
        return float(psutil.disk_usage(path).percent)
    except Exception:
        return 0.0


def ping(host: str, timeout_ms: int = 1500) -> tuple[bool, float | None]:
    """
    Devuelve (ok, latency_ms). Si falla, latency_ms = None.
    Usa el ping nativo del SO. Sin dependencias externas.
    """
    if not host:
        return False, None

    system = platform.system().lower()
    try:
        if system == "windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(max(1, timeout_ms // 1000)), host]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000) + 1.0,
        )
        if result.returncode != 0:
            return False, None

        # Extraer latencia del texto
        lat = _parse_ping_latency(result.stdout)
        return True, lat
    except Exception as e:
        log.debug(f"Ping a {host} falló: {e}")
        return False, None


def _parse_ping_latency(output: str) -> float | None:
    """Extrae el tiempo en ms de la salida del ping."""
    import re
    # Windows: "tiempo=23ms" o "time=23ms"
    m = re.search(r"(?:tiempo|time)[=<](\d+)\s*ms", output, re.IGNORECASE)
    if m:
        return float(m.group(1))
    return None


def collect(ping_host: str) -> dict:
    """Recolecta todas las métricas de una sola vez."""
    ok, latency = ping(ping_host)
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "cpu": cpu_percent(),
        "ram": ram_percent(),
        "disk": disk_percent(),
        "ping_ms": latency,
        "ping_ok": ok,
    }