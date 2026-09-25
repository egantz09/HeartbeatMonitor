import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QAbstractNativeEventFilter
from PyQt6.QtWidgets import QApplication

from core.database import Database
from core.constants import EVENT_SUSPEND, EVENT_RESUME

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
                    Database.add_event(EVENT_SUSPEND, "system")
                elif msg.wParam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                    Database.add_event(EVENT_RESUME, "system")
        return False, 0


def install(app: QApplication):
    app.installNativeEventFilter(PowerEventFilter())