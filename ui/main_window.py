# ui/main_window.py
"""
Ventana principal con pestañas.
"""
import logging
from datetime import date, datetime, timedelta

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QMessageBox, QStatusBar, QTabWidget,
)

from core.database import Database
from core.excel_manager import ExcelManager
from core.constants import (
    HEARTBEAT_INTERVAL, POWER_LOSS_THRESHOLD,
    APP_NAME, APP_AUTHOR, APP_EMAIL, APP_VERSION, APP_TITLE,
)
from services.pdf_export import export_month_pdf
from ui.tabs.dashboard_tab import DashboardTab
from ui.tabs.events_tab import EventsTab
from ui.tabs.analytics_tab import AnalyticsTab
from ui.tabs.metrics_tab import MetricsTab
from ui.tabs.config_tab import ConfigTab

log = logging.getLogger(__name__)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)

        # Ícono
        try:
            from ui.tray import _load_icon
            self.setWindowIcon(_load_icon())
        except Exception as e:
            log.debug(f"No se pudo cargar el ícono: {e}")

        self.resize(1100, 760)

        self._build_ui()
        self._start_timers()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        # ---------- Cabecera ----------
        header = QHBoxLayout()

        self.lbl_status = QLabel("\u25cf Activo")
        self.lbl_status.setStyleSheet(
            "color: #2E7D32; font-weight: bold; font-size: 13px;"
        )
        header.addWidget(self.lbl_status)
        header.addStretch()

        btn_export = QPushButton("Exportar Excel del mes")
        btn_export.clicked.connect(self.export_current_month)
        header.addWidget(btn_export)

        btn_pdf = QPushButton("Exportar PDF del mes")
        btn_pdf.clicked.connect(self.export_pdf_month)
        header.addWidget(btn_pdf)

        btn_about = QPushButton("Acerca de")
        btn_about.clicked.connect(self.show_about)
        header.addWidget(btn_about)

        root.addLayout(header)

        # ---------- Pestañas ----------
        self.tabs = QTabWidget()

        self.tab_dashboard = DashboardTab()
        self.tab_events = EventsTab()
        self.tab_analytics = AnalyticsTab()
        self.tab_metrics = MetricsTab()
        self.tab_config = ConfigTab()

        self.tabs.addTab(self.tab_dashboard, "Dashboard")
        self.tabs.addTab(self.tab_events, "Eventos")
        self.tabs.addTab(self.tab_analytics, "Analitica")
        self.tabs.addTab(self.tab_metrics, "Metricas")
        self.tabs.addTab(self.tab_config, "Configuracion")

        self.tabs.currentChanged.connect(self._on_tab_changed)
        root.addWidget(self.tabs)

        # ---------- Status bar ----------
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage(
            f"Intervalo heartbeat: {HEARTBEAT_INTERVAL} s  |  "
            f"Umbral corte: {int(POWER_LOSS_THRESHOLD)} s"
        )

    # ------------------------------------------------------------------
    def _start_timers(self):
        """Refresco periódico del tab activo."""
        self._timer_refresh = QTimer(self)
        self._timer_refresh.timeout.connect(self._refresh_current_tab)
        self._timer_refresh.start(30_000)

    def _refresh_current_tab(self):
        idx = self.tabs.currentIndex()
        widget = self.tabs.widget(idx)
        if hasattr(widget, "refresh"):
            try:
                widget.refresh()
            except Exception as e:
                log.debug(f"Error refrescando tab {idx}: {e}")

    def _on_tab_changed(self, idx):
        widget = self.tabs.widget(idx)
        if hasattr(widget, "refresh"):
            try:
                widget.refresh()
            except Exception as e:
                log.debug(f"Error al cambiar a tab {idx}: {e}")

    # ------------------------------------------------------------------
    # Acciones
    # ------------------------------------------------------------------
    def export_current_month(self):
        try:
            path = ExcelManager.export_month(date.today())
            QMessageBox.information(
                self, "Exportado",
                f"Archivo generado:\n\n{path}"
            )
        except PermissionError:
            QMessageBox.critical(
                self, "Error",
                "El archivo está abierto en otro programa. "
                "Cierra Excel e inténtalo de nuevo."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al exportar", str(e))

    def export_pdf_month(self):
        try:
            path = export_month_pdf(date.today())
            QMessageBox.information(
                self, "PDF generado",
                f"Archivo generado:\n\n{path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error al generar PDF", str(e))

    def show_about(self):
        QMessageBox.about(
            self,
            f"Acerca de {APP_NAME}",
            f"<h3>{APP_NAME} v{APP_VERSION}</h3>"
            f"<p>Monitor de uptime y disponibilidad para Windows.</p>"
            f"<p><b>Creada por {APP_AUTHOR}</b><br>"
            f"<a href='mailto:{APP_EMAIL}'>{APP_EMAIL}</a></p>"
            f"<p style='color:#888;font-size:10px;'>"
            f"\u00a9 2026 {APP_AUTHOR}. Todos los derechos reservados."
            f"</p>"
        )

    def quit_app(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.quit()

    # ------------------------------------------------------------------
    # Cierre a bandeja
    # ------------------------------------------------------------------
    def closeEvent(self, event):
        event.ignore()
        self.hide()
        tray = getattr(self, "tray", None)
        if tray is not None:
            try:
                tray.showMessage(
                    APP_NAME,
                    "Sigue en ejecucion en la bandeja.",
                )
            except Exception:
                pass