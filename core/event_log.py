# core/event_log.py
"""
Lectura del Event Log de Windows para detectar apagados inesperados.

IDs de interés:
  41   (Kernel-Power)   → apagado brusco / corte eléctrico
  6008 (EventLog)       → apagado inesperado
  1074 (User32)         → apagado iniciado por un proceso (Windows Update, etc.)
  6005 (EventLog)       → inicio del servicio Event Log (= sistema arrancó)
"""
import logging
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

try:
    import win32evtlog
    _HAS_WIN32 = True
except ImportError:
    _HAS_WIN32 = False
    log.warning("pywin32 no disponible — lectura de Event Log deshabilitada")


# Códigos de interés
EVENT_ID_KERNEL_POWER = 41
EVENT_ID_UNEXPECTED   = 6008
EVENT_ID_SHUTDOWN_INIT = 1074
EVENT_ID_BOOT         = 6005


def is_available() -> bool:
    return _HAS_WIN32


def read_recent_events(hours: int = 24, event_ids: tuple = None) -> list:
    """
    Devuelve una lista de eventos recientes del log "System".
    Cada item: {"time": datetime, "event_id": int, "source": str}

    Si `event_ids` es None, usa los IDs por defecto (41, 6008, 1074).
    """
    if not _HAS_WIN32:
        return []

    if event_ids is None:
        event_ids = (EVENT_ID_KERNEL_POWER,
                     EVENT_ID_UNEXPECTED,
                     EVENT_ID_SHUTDOWN_INIT)

    eventos = []
    cutoff = datetime.now() - timedelta(hours=hours)

    try:
        hand = win32evtlog.OpenEventLog(None, "System")
        flags = (
            win32evtlog.EVENTLOG_BACKWARDS_READ
            | win32evtlog.EVENTLOG_SEQUENTIAL_READ
        )

        max_records = 5000
        processed = 0
        stop = False

        while not stop:
            records = win32evtlog.ReadEventLog(hand, flags, 0)
            if not records:
                break

            for rec in records:
                processed += 1
                ts = rec.TimeGenerated
                if ts < cutoff:
                    stop = True
                    break

                if rec.EventID in event_ids:
                    eventos.append({
                        "time": ts,
                        "event_id": rec.EventID,
                        "source": rec.SourceName or "",
                    })

                if processed >= max_records:
                    stop = True
                    break

        win32evtlog.CloseEventLog(hand)

    except Exception as e:
        log.warning(f"Error leyendo Event Log: {e}")

    return eventos


def detect_power_loss_since_last_boot(hours: int = 24) -> dict | None:
    """
    Busca un evento 41 (Kernel-Power) o 6008 (apagado inesperado)
    en las últimas `hours` horas.
    Devuelve el más reciente, o None.
    """
    eventos = read_recent_events(
        hours=hours,
        event_ids=(EVENT_ID_KERNEL_POWER, EVENT_ID_UNEXPECTED),
    )
    if not eventos:
        return None
    return max(eventos, key=lambda e: e["time"])