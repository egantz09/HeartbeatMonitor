# core/power_filter.py
"""
Detecta eventos de suspensión / reanudación en Windows.
"""
import ctypes
import logging
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter

from core.database import Database
from core.constants import EVENT_SUSPEND, EVENT_RESUME

log = logging.getLogger(__name__)

WM_POWERBROADCAST      = 0x0218
PBT_APMSUSPEND         = 0x0004
PBT_APMRESUMEAUTOMATIC = 0x0012
PBT_APMRESUMESUSPEND   = 0x0007


class _MSG(ctypes.Structure):
    _fields_ = [
        ("hWnd",     wintypes.HWND),
        ("message",  wintypes.UINT),
        ("wParam",   wintypes.WPARAM),
        ("lParam",   wintypes.LPARAM),
        ("time",     wintypes.DWORD),
        ("pt",       wintypes.POINT),
    ]


class PowerEventFilter(QAbstractNativeEventFilter):

    def nativeEventFilter(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            try:
                msg = _MSG.from_address(int(message))
            except Exception:
                return False, 0

            if msg.message == WM_POWERBROADCAST:
                if msg.wParam == PBT_APMSUSPEND:
                    try:
                        Database.add_event(EVENT_SUSPEND, "system")
                        log.info("Suspensión detectada")
                    except Exception as e:
                        log.warning(f"Error registrando SUSPEND: {e}")
                elif msg.wParam in (PBT_APMRESUMEAUTOMATIC,
                                    PBT_APMRESUMESUSPEND):
                    try:
                        Database.add_event(EVENT_RESUME, "system")
                        log.info("Reanudación detectada")
                    except Exception as e:
                        log.warning(f"Error registrando RESUME: {e}")
        return False, 0


def install(app):
    """Instala el filtro de eventos nativos."""
    try:
        app.installNativeEventFilter(PowerEventFilter())
        log.info("Power event filter instalado")
    except Exception as e:
        log.warning(f"No se pudo instalar power_filter: {e}")