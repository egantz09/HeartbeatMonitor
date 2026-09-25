# core/event_log.py
"""
Lectura del Event Log de Windows para detectar apagados inesperados.

- Event ID 41 (Kernel-Power) → apagado brusco / corte eléctrico
- Event ID 6008 → apagado inesperado
- Event ID 1074 → apagado iniciado por proceso (Windows Update, etc.)
- Event ID 6005 → inicio del servicio Event Log (= sistema arrancó)
"""
import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

try:
    import win32evtlog
    import win32evtlogutil
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False
    log.warning("pywin32 no disponible — lectura de Event Log deshabilitada")


# Códigos de interés
EVENT_ID_KERNEL_POWER   = 41     # apagado brusco
EVENT_ID_UNEXPECTED     = 6008   # apagado inesperado
EVENT_ID_SHUTDOWN_INIT  = 1074   # apagado iniciado
EVENT_ID_BOOT           = 6005   # inicio del log (= arranque)


def is_available() -> bool:
    return _HAS_WIN32


def read_recent_kernel_power(hours: int = 24) -> list[dict]:
    """
    Devuelve lista de eventos Kernel-Power (ID 41) recientes.
    Cada item: {"time": datetime, "event_id": int, "source": str}
    """
    if not _HAS_WIN32:
        return []

    eventos = []
    cutoff = datetime.now() - timedelta(hours=hours)

    try:
        hand = win32evtlog.OpenEventLog(None, "System")
        flags = (
            win32evtlog.EVENTLOG_BACKWARDS_READ
            | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        )

        total = 0
        while True:
            records = win32evtlog.ReadEventLog(hand, flags, 0)
            if not records:
                break
            for rec in records:
                ts = rec.TimeGenerated  # datetime
                if ts < cutoff:
                    break
                if rec.EventID in (EVENT_ID_KERNEL_POWER,
                                   EVENT_ID_UNEXPECTED,
                                   EVENT_ID_SHUTDOWN_INIT):
                    eventos.append({
                        "time": ts,
                        "event_id": rec.EventID,
                        "source": rec.SourceName,
                    })
            total += len(records)
            if total > 5000:   # límite de seguridad
                break

        win32evtlog.CloseEventLog(hand)
    except Exception as e:
        log.warning(f"Error leyendo Event Log: {e}")

    return eventos


def detect_power_loss_since_last_boot() -> dict | None:
    """
    Busca un Event ID 41 o 6008 en las últimas 24 h.
    Si encuentra, devuelve el más reciente.
    """
    eventos = read_recent_kernel_power(hours=24)
    if not eventos:
        return None
    return max(eventos, key=lambda e: e["time"])