# core/startup.py
import logging
import os
import sys
import winreg

log = logging.getLogger(__name__)

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "HeartbeatMonitor"


def _exe_command() -> str:
    """Devuelve el comando correcto en modo .py o .exe."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    script = os.path.abspath(sys.argv[0])
    return f'"{sys.executable}" "{script}"'


def enable_startup() -> bool:
    """Registra la app para que arranque al iniciar sesión."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _exe_command())
        winreg.CloseKey(key)
        log.info("Autoarranque activado")
        return True
    except OSError as e:
        log.warning(f"No se pudo activar autoarranque: {e}")
        return False


def disable_startup() -> bool:
    """Elimina el registro de autoarranque."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        log.info("Autoarranque desactivado")
        return True
    except FileNotFoundError:
        return False
    except OSError as e:
        log.warning(f"No se pudo desactivar autoarranque: {e}")
        return False


def is_startup_enabled() -> bool:
    """Consulta si el autoarranque está activo."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ
        )
        try:
            winreg.QueryValueEx(key, APP_NAME)
            return True
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except OSError:
        return False