# services/notifier.py
"""
Wrapper sobre QSystemTrayIcon para enviar notificaciones.
Respeta los toggles de configuración:
  - notifications_enabled → global
  - ping_enabled → solo para notificaciones de red
"""
import logging

from PyQt6.QtWidgets import QSystemTrayIcon

from core.config import Config

log = logging.getLogger(__name__)


class Notifier:

    def __init__(self, tray: QSystemTrayIcon = None):
        self.tray = tray

    # ------------------------------------------------------------------
    def set_tray(self, tray: QSystemTrayIcon):
        self.tray = tray

    # ------------------------------------------------------------------
    def _notifications_enabled(self) -> bool:
        return bool(Config.get("notifications_enabled", True))

    def _ping_enabled(self) -> bool:
        return bool(Config.get("ping_enabled", True))

    def _show(self, title: str, message: str,
              icon=None, ms: int = 5000):
        """Envía una notificación respetando el toggle global."""
        if not self._notifications_enabled():
            return
        if self.tray is None:
            return
        if icon is None:
            icon = QSystemTrayIcon.MessageIcon.Information
        try:
            self.tray.showMessage(title, message, icon, ms)
        except Exception as e:
            log.debug(f"No se pudo mostrar notificación: {e}")

    # ------------------------------------------------------------------
    # Corte eléctrico
    # ------------------------------------------------------------------
    def notify_power_loss(self, offline: str):
        self._show(
            "Corte eléctrico detectado",
            f"El equipo estuvo apagado {offline}.",
            QSystemTrayIcon.MessageIcon.Critical,
            8000,
        )

    # ------------------------------------------------------------------
    # Arranque
    # ------------------------------------------------------------------
    def notify_boot(self, after_power_loss: bool):
        if after_power_loss:
            self._show(
                "Reinicio tras corte",
                "El equipo volvió a estar en línea.",
                QSystemTrayIcon.MessageIcon.Warning,
                6000,
            )
        else:
            self._show(
                "Inicio del sistema",
                "HeartbeatMonitor está activo.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )

    # ------------------------------------------------------------------
    # Hardware
    # ------------------------------------------------------------------
    def notify_hw_alert(self, metric: str,
                        value: float, threshold: float):
        self._show(
            f"Alerta de {metric}",
            f"Uso actual: {value:.1f} %  (límite {threshold:.0f} %)",
            QSystemTrayIcon.MessageIcon.Warning,
            6000,
        )

    # ------------------------------------------------------------------
    # Red (solo si el monitoreo está activo)
    # ------------------------------------------------------------------
    def notify_net(self, up: bool, host: str):
        if not self._ping_enabled():
            return

        if up:
            self._show(
                "Red restablecida",
                f"Conexión con {host} recuperada.",
                QSystemTrayIcon.MessageIcon.Information,
                4000,
            )
        else:
            self._show(
                "Red caída",
                f"Sin respuesta de {host}.",
                QSystemTrayIcon.MessageIcon.Warning,
                6000,
            )


# Instancia global (se conecta al tray desde main.py)
notifier = Notifier()