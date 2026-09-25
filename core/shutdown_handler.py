from PyQt6.QtWidgets import QApplication
from core.database import Database
from core.constants import EVENT_SHUTDOWN
from core.state_manager import StateManager

_installed = False


def _on_about_to_quit():
    Database.add_event(EVENT_SHUTDOWN, "clean")
    StateManager.clear()


def install():
    """Registra el handler de apagado limpio (una sola vez)."""
    global _installed
    if _installed:
        return
    app = QApplication.instance()
    if app is not None:
        app.aboutToQuit.connect(_on_about_to_quit)
        _installed = True