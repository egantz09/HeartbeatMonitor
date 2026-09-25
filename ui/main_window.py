# ui/main_window.py
from datetime import date, datetime, timedelta

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QStatusBar, QTabWidget,
)

from core.database import Database
from core.excel_manager import ExcelManager
from core.constants import HEARTBEAT_INTERVAL, APP_TITLE
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.events_tab import EventsTab
from ui.tabs.analytics_tab import AnalyticsTab
from ui.tabs.metrics_tab import MetricsTab
from ui.tabs.config_tab import ConfigTab


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        try:
            from ui.tray import _load_icon
            self.setWindowIcon(_load_icon())
        except Exception:
            pass

        self.resize(1100, 760)
        self.showMaximized()

        self._build_ui()
        self._start_timers()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)

        # Cabecera superior
        header = QHBoxLayout()
        self.lbl_status = QLabel("● Activo")
        self.lbl_status.setStyleSheet(
            "color: #2E7D32; font-weight: bold; font-size: 13px;"
        )
        header.addWidget(self.lbl_status)
        header.addStretch()

        btn_export = QPushButton("Exportar Excel del mes")
        btn_export.clicked.connect(self.export_current_month)
        header.addWidget(btn_export)

        btn_about = QPushButton("Acerca de")
        btn_about.clicked.connect(self.show_about)
        header.addWidget(btn_about)

        root.addLayout(header)

        # Pestañas
        self.tabs = QTabWidget()
        self.tab_dashboard = DashboardTab()
        self.tab_events = EventsTab()
        self.tab_analytics = AnalyticsTab()
        self.tab_metrics = MetricsTab()
        self.tab_config = ConfigTab()

        self.tabs.addTab(self.tab_dashboard, "Dashboard")
        self.tabs.addTab(self.tab_events, "Eventos")
        self.tabs.addTab(self.tab_analytics, "Analítica")
        self.tabs.addTab(self.tab_metrics, "Métricas")
        self.tabs.addTab(self.tab_config, "Configuración")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self.tabs)

        # Status bar
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            f"Intervalo heartbeat: {HEARTBEAT_INTERVAL} s  |  "
            f"Umbral corte: {int(HEARTBEAT_INTERVAL * 2.5)} s"
        )

    def _start_timers(self):
        self._timer_refresh = QTimer(self)
        self._timer_refresh.timeout.connect(self._refresh_current_tab)
        self._timer_refresh.start(30_000)

    def _refresh_current_tab(self):
        idx = self.tabs.currentIndex()
        widget = self.tabs.widget(idx)
        if hasattr(widget, "refresh"):
            try:
                widget.refresh()
            except Exception:
                pass

    def _on_tab_changed(self, idx):
        widget = self.tabs.widget(idx)
        if hasattr(widget, "refresh"):
            try:
                widget.refresh()
            except Exception:
                pass

    # Acciones globales
    def export_current_month(self):
        try:
            path = ExcelManager.export_month(date.today())
            QMessageBox.information(self, "Exportado", str(path))
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    def show_about(self):
        from core.constants import APP_NAME, APP_AUTHOR, APP_EMAIL, APP_VERSION
        QMessageBox.about(
            self,
            f"Acerca de {APP_NAME}",
            f"<h3>{APP_NAME} v{APP_VERSION}</h3>"
            f"<p>Monitor de uptime y disponibilidad.</p>"
            f"<p><b>Creada por {APP_AUTHOR}</b><br>"
            f"<a href='mailto:{APP_EMAIL}'>{APP_EMAIL}</a></p>"
        )

    def quit_app(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        if hasattr(self, "tray") and self.tray is not None:
            try:
                self.tray.showMessage(
                    "HeartbeatMonitor",
                    "Sigue en ejecución en la bandeja.",
                )
            except Exception:
                pass