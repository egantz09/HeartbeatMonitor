# ui/tabs/analytics_tab.py
"""
Analitica de cortes:
  - Barras horizontales por hora
  - Barras verticales por dia de la semana
  - Top 5 cortes mas largos
  - KPIs resumen
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.analytics import cuts_heatmap, top_longest_cuts
from ui.charts import CutsByHourChart, CutsByWeekdayChart

log = logging.getLogger(__name__)


class MiniKPI(QFrame):

    def __init__(self, title: str, value: str = "-", subtitle: str = ""):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            MiniKPI {
                background-color: rgba(31, 78, 120, 0.10);
                border: 1px solid rgba(31, 78, 120, 0.30);
                border-radius: 6px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(2)

        lbl_t = QLabel(title)
        lbl_t.setStyleSheet("color: #888; font-size: 10px;")
        lay.addWidget(lbl_t)

        self.lbl_v = QLabel(value)
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        self.lbl_v.setFont(f)
        lay.addWidget(self.lbl_v)

        self.lbl_s = QLabel(subtitle)
        self.lbl_s.setStyleSheet("color: #aaa; font-size: 9px;")
        lay.addWidget(self.lbl_s)

    def set(self, value: str, subtitle: str = None):
        self.lbl_v.setText(value)
        if subtitle is not None:
            self.lbl_s.setText(subtitle)


class AnalyticsTab(QWidget):

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        # --- Cabecera ---
        header = QHBoxLayout()
        header.addWidget(QLabel("Rango:"))
        self.cmb_range = QComboBox()
        self.cmb_range.addItems(["7 dias", "30 dias", "90 dias"])
        self.cmb_range.setCurrentIndex(1)
        self.cmb_range.currentIndexChanged.connect(self.refresh)
        header.addWidget(self.cmb_range)
        header.addStretch()
        lay.addLayout(header)

        # --- KPIs ---
        kpis = QHBoxLayout()
        self.kpi_total = MiniKPI("Total de cortes")
        self.kpi_avg   = MiniKPI("Duracion media")
        self.kpi_worst = MiniKPI("Peor corte")
        self.kpi_peak  = MiniKPI("Hora mas critica")
        kpis.addWidget(self.kpi_total)
        kpis.addWidget(self.kpi_avg)
        kpis.addWidget(self.kpi_worst)
        kpis.addWidget(self.kpi_peak)
        lay.addLayout(kpis)

        # --- Graficas ---
        charts = QHBoxLayout()
        self.chart_hours = CutsByHourChart()
        self.chart_hours.setMinimumHeight(300)
        self.chart_weekday = CutsByWeekdayChart()
        self.chart_weekday.setMinimumHeight(300)
        charts.addWidget(self.chart_hours)
        charts.addWidget(self.chart_weekday)
        lay.addLayout(charts)

        # --- Top 5 ---
        lbl_top = QLabel("Top 5 cortes mas largos")
        lbl_top.setStyleSheet("font-weight: bold; margin-top: 4px;")
        lay.addWidget(lbl_top)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(
            ["Inicio", "Fin", "Duracion", "Horas"]
        )
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.table.setMaximumHeight(180)
        lay.addWidget(self.table)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        days = [7, 30, 90][self.cmb_range.currentIndex()]

        try:
            grid = cuts_heatmap(days)
            top  = top_longest_cuts(days, top=5)
        except Exception as e:
            log.warning(f"Error cargando datos de analitica: {e}")
            grid = {h: [0] * 7 for h in range(24)}
            top = []

        self.chart_hours.plot(grid)
        self.chart_weekday.plot(grid)

        # KPIs
        total_cortes = sum(sum(grid.get(h, [0] * 7)) for h in range(24))

        if top:
            duraciones = [c["duracion_min"] for c in top]
            dur_media = sum(duraciones) / len(duraciones)
            peor = top[0]["duracion_min"]

            horas_tot = [(h, sum(grid.get(h, [0] * 7))) for h in range(24)]
            horas_tot = [x for x in horas_tot if x[1] > 0]
            if horas_tot:
                hora_pico, count_pico = max(horas_tot, key=lambda x: x[1])
                self.kpi_peak.set(f"{hora_pico:02d}:00", f"{count_pico} cortes")
            else:
                self.kpi_peak.set("-")

            self.kpi_total.set(str(total_cortes))
            self.kpi_avg.set(f"{dur_media:.0f} min")
            if peor < 120:
                self.kpi_worst.set(f"{peor:.0f} min")
            else:
                self.kpi_worst.set(f"{peor/60:.1f} h")
        else:
            self.kpi_total.set("0")
            self.kpi_avg.set("-")
            self.kpi_worst.set("-")
            self.kpi_peak.set("-")

        # Tabla
        self.table.setRowCount(len(top))
        for row, c in enumerate(top):
            dur = c["duracion_min"]
            dur_txt = f"{dur:.1f} min" if dur < 120 else f"{dur/60:.2f} h"

            i0 = QTableWidgetItem(c["inicio"].strftime("%d/%m %H:%M:%S"))
            i1 = QTableWidgetItem(c["fin"].strftime("%d/%m %H:%M:%S"))
            i2 = QTableWidgetItem(dur_txt)
            i3 = QTableWidgetItem(f"{dur/60:.2f}")

            if dur >= 60:
                i2.setForeground(Qt.GlobalColor.red)
            elif dur >= 15:
                i2.setForeground(Qt.GlobalColor.darkYellow)

            self.table.setItem(row, 0, i0)
            self.table.setItem(row, 1, i1)
            self.table.setItem(row, 2, i2)
            self.table.setItem(row, 3, i3)