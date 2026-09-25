# core/metrics.py
"""
Utilidades de red. Solo se usa `ping()` en el resto de la app.
"""
import logging
import platform
import re
import subprocess

log = logging.getLogger(__name__)


def ping(host: str, timeout_ms: int = 1000) -> tuple:
    """
    Hace un ping ICMP a `host`.
    Devuelve (ok: bool, latency_ms: float | None).

    Usa el comando nativo del SO (ping en Windows / Linux).
    """
    if not host:
        return False, None

    system = platform.system().lower()
    try:
        if system == "windows":
            cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host]
        else:
            cmd = ["ping", "-c", "1",
                   "-W", str(max(1, timeout_ms // 1000)), host]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000) + 0.5,
        )

        if result.returncode != 0:
            return False, None

        lat = _parse_latency(result.stdout)
        return True, lat

    except subprocess.TimeoutExpired:
        return False, None
    except Exception as e:
        log.debug(f"Ping a {host} falló: {e}")
        return False, None


def _parse_latency(output: str) -> float | None:
    """Extrae 'time=XXms' o 'tiempo=XXms' del output de ping."""
    if not output:
        return None
    m = re.search(r"(?:tiempo|time)[=<]\s*(\d+(?:[.,]\d+)?)\s*ms",
                  output, re.IGNORECASE)
    if m:
        return float(m.group(1).replace(",", "."))
    return None