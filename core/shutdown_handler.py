# core/shutdown_handler.py
import logging

from PyQt6.QtWidgets import QApplication

from core.database import Database
from core.state_manager import StateManager
from core.constants import EVENT_SHUTDOWN

log = logging.getLogger(__name__)

_installed = False


def _on_about_to_quit():
    """Se ejecuta cuando la app se cierra limpiamente."""
    try:
        Database.add_event(EVENT_SHUTDOWN, "clean")
        log.info("Cierre limpio registrado")
    except Exception as e:
        log.warning(f"Error registrando shutdown: {e}")

    try:
        StateManager.clear()
    except Exception as e:
        log.warning(f"Error limpiando state: {e}")


def install():
    """Registra el handler de cierre limpio (una sola vez)."""
    global _installed
    if _installed:
        return
    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(_on_about_to_quit)
        _installed = True
        log.debug("Shutdown handler instalado")