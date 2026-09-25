# ui/tray.py
from pathlib import Path

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QBrush, QPen
from PyQt6.QtCore import Qt, QPoint


def _fallback_icon() -> QIcon:
    """Ícono generado en memoria. Nunca es nulo."""
    size = 64
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)

    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QBrush(QColor("#1F4E78")))
    p.drawEllipse(2, 2, size - 4, size - 4)

    pen = QPen(QColor("white"))
    pen.setWidth(max(2, int(size * 0.09)))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)

    cy = size // 2
    pts = [
        QPoint(int(size * 0.10), cy),
        QPoint(int(size * 0.35), cy),
        QPoint(int(size * 0.44), cy - int(size * 0.22)),
        QPoint(int(size * 0.54), cy + int(size * 0.22)),
        QPoint(int(size * 0.64), cy - int(size * 0.18)),
        QPoint(int(size * 0.72), cy),
        QPoint(int(size * 0.90), cy),
    ]
    for i in range(len(pts) - 1):
        p.drawLine(pts[i], pts[i + 1])

    p.end()
    return QIcon(pm)


def _load_icon() -> QIcon:
    """Intenta cargar assets/icon.*, si falla devuelve el fallback en memoria."""
    base = Path(__file__).resolve().parent.parent
    for name in ("icon.ico", "icon.png"):
        path = base / "assets" / name
        if path.exists():
            icon = QIcon(str(path))
            if not icon.isNull():
                return icon
    return _fallback_icon()


class TrayIcon(QSystemTrayIcon):

    def __init__(self, window, parent=None):
        super().__init__(_load_icon(), parent)
        self._window = window

        menu = QMenu()
        act_show = QAction("Mostrar", self)
        act_show.triggered.connect(self._show_window)
        menu.addAction(act_show)

        act_report = QAction("Exportar mes actual…", self)
        act_report.triggered.connect(window.export_current_month)
        menu.addAction(act_report)

        menu.addSeparator()

        act_quit = QAction("Salir", self)
        act_quit.triggered.connect(window.quit_app)
        menu.addAction(act_quit)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)
        self.setToolTip("HeartbeatMonitor — activo")

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self):
        self._window.showNormal()
        self._window.raise_()
        self._window.activateWindow()