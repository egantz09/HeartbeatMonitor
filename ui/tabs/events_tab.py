# ui/tabs/events_tab.py
"""
Tabla de eventos con filtro por tipo, rango de fechas y columna de duracion.
"""
import logging
from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton,
    QDateEdit, QMessageBox,
)

from core.database import Database
from services.pdf_export import export_range_pdf

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
def _fmt_duration(seconds) -> str:
    """Convierte segundos a '3d 04h 12m', '4h 20m', '12m 05s'."""
    if seconds is None:
        return "-"
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        return "-"
    if seconds < 0:
        return "-"

    d, rem = divmod(seconds, 86400)
    h, rem = divmod(rem, 3600)
    m, s = divmod(rem, 60)

    if d > 0:
        return f"{d}d {h:02d}h {m:02d}m"
    if h > 0:
        return f"{h}h {m:02d}m"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"


class EventsTab(QWidget):

    def __init__(self):
        super().__init__()
        self._cache = []
        self._build_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)

        header = QHBoxLayout()

        header.addWidget(QLabel("Filtrar:"))
        self.cmb_filter = QComboBox()
        self.cmb_filter.addItems([
            "Todos", "BOOT", "SHUTDOWN", "POWER_LOSS",
            "SUSPEND", "RESUME", "KERNEL_POWER",
            "HW_ALERT", "NET_DOWN", "NET_UP",
        ])
        self.cmb_filter.currentIndexChanged.connect(self._apply_filter)
        header.addWidget(self.cmb_filter)

        header.addStretch()

        header.addWidget(QLabel("Desde:"))
        self.dt_from = QDateEdit(QDate.currentDate().addDays(-7))
        self.dt_from.setCalendarPopup(True)
        header.addWidget(self.dt_from)

        header.addWidget(QLabel("Hasta:"))
        self.dt_to = QDateEdit(QDate.currentDate())
        self.dt_to.setCalendarPopup(True)
        header.addWidget(self.dt_to)

        btn_range = QPushButton("Aplicar")
        btn_range.clicked.connect(self.refresh)
        header.addWidget(btn_range)

        btn_pdf = QPushButton("Exportar rango a PDF")
        btn_pdf.clicked.connect(self._export_range_pdf)
        header.addWidget(btn_pdf)

        root.addLayout(header)

        # Tabla
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["FechaHora", "Evento", "Duracion", "Detalle"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        root.addWidget(self.table)

    # ------------------------------------------------------------------
    def refresh(self):
        start = datetime.combine(
            self.dt_from.date().toPyDate(), datetime.min.time()
        )
        end = datetime.combine(
            self.dt_to.date().toPyDate(), datetime.max.time()
        )
        try:
            events = Database.events_with_duration(start, end)
        except Exception as e:
            log.warning(f"Error cargando eventos: {e}")
            events = []

        self._cache = list(reversed(events))
        self._apply_filter()

    # ------------------------------------------------------------------
    def _apply_filter(self):
        events = self._cache
        selected = self.cmb_filter.currentText()
        if selected != "Todos":
            events = [e for e in events if e["event"] == selected]

        self.table.setRowCount(len(events))

        color_map = {
            "POWER_LOSS":   Qt.GlobalColor.red,
            "KERNEL_POWER": Qt.GlobalColor.darkRed,
            "BOOT":         Qt.GlobalColor.darkGreen,
            "SHUTDOWN":     Qt.GlobalColor.darkGray,
            "SUSPEND":      Qt.GlobalColor.darkYellow,
            "RESUME":       Qt.GlobalColor.darkBlue,
            "HW_ALERT":     Qt.GlobalColor.darkMagenta,
            "NET_DOWN":     Qt.GlobalColor.red,
            "NET_UP":       Qt.GlobalColor.darkGreen,
        }
        bg_critical = QBrush(QColor(198, 40, 40, 40))

        for row, ev in enumerate(events):
            i0 = QTableWidgetItem(ev["timestamp"].replace("T", " "))
            i1 = QTableWidgetItem(ev["event"])
            i2 = QTableWidgetItem(_fmt_duration(ev.get("duration_seconds")))
            i3 = QTableWidgetItem(ev["detail"] or "")

            if ev["event"] in color_map:
                i1.setForeground(color_map[ev["event"]])

            dur = ev.get("duration_seconds")
            if dur is not None:
                if dur >= 3600 * 6:
                    i2.setForeground(Qt.GlobalColor.darkGreen)
                elif dur >= 3600:
                    i2.setForeground(Qt.GlobalColor.darkBlue)

            if ev["event"] in ("POWER_LOSS", "KERNEL_POWER", "NET_DOWN"):
                i0.setBackground(bg_critical)
                i1.setBackground(bg_critical)
                i2.setBackground(bg_critical)
                i3.setBackground(bg_critical)

            self.table.setItem(row, 0, i0)
            self.table.setItem(row, 1, i1)
            self.table.setItem(row, 2, i2)
            self.table.setItem(row, 3, i3)

    # ------------------------------------------------------------------
    def _export_range_pdf(self):
        start = self.dt_from.date().toPyDate()
        end = self.dt_to.date().toPyDate()
        if start > end:
            QMessageBox.warning(
                self, "Rango invalido",
                "La fecha 'Desde' es posterior a 'Hasta'."
            )
            return
        try:
            path = export_range_pdf(start, end)
            QMessageBox.information(self, "PDF generado", str(path))
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))