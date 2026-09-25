# ui/tabs/dashboard_tab.py
"""
Dashboard principal con KPIs de uptime, MTBF/MTTR/SLA y estado de red.
"""
import logging

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.analytics import (
    compute_availability, compute_mtbf, compute_mttr, net_status_last,
)

log = logging.getLogger(__name__)


class KPICard(QFrame):

    def __init__(self, title: str, value: str = "-", subtitle: str = ""):
        super().__init__()
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            KPICard {
                background-color: rgba(31, 78, 120, 0.12);
                border: 1px solid rgba(31, 78, 120, 0.4);
                border-radius: 8px;
            }
        """)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)

        self.lbl_title = QLabel(title)
        self.lbl_title.setStyleSheet("color: #888; font-size: 11px;")
        lay.addWidget(self.lbl_title)

        self.lbl_value = QLabel(value)
        f = QFont()
        f.setPointSize(18)
        f.setBold(True)
        self.lbl_value.setFont(f)
        lay.addWidget(self.lbl_value)

        self.lbl_sub = QLabel(subtitle)
        self.lbl_sub.setStyleSheet("color: #aaa; font-size: 10px;")
        lay.addWidget(self.lbl_sub)

    def set(self, value: str, subtitle: str = None):
        self.lbl_value.setText(value)
        if subtitle is not None:
            self.lbl_sub.setText(subtitle)

    def set_value_color(self, color: str):
        self.lbl_value.setStyleSheet(
            f"color: {color}; font-weight: bold; font-size: 18px;"
        )

    def reset_color(self):
        self.lbl_value.setStyleSheet("")


class DashboardTab(QWidget):

    def __init__(self):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        # --- Fila 1: Uptime ---
        row1 = QHBoxLayout()
        self.card_uptime30 = KPICard("Uptime 30 dias", "-")
        self.card_uptime7  = KPICard("Uptime 7 dias", "-")
        self.card_today    = KPICard("Uptime hoy", "-")
        row1.addWidget(self.card_uptime30)
        row1.addWidget(self.card_uptime7)
        row1.addWidget(self.card_today)
        lay.addLayout(row1)

        # --- Fila 2: Fallos ---
        row2 = QHBoxLayout()
        self.card_mtbf = KPICard("MTBF (30 d)", "-",
                                 "tiempo medio entre fallos")
        self.card_mttr = KPICard("MTTR (30 d)", "-",
                                 "tiempo medio de recuperacion")
        self.card_cuts = KPICard("Cortes electricos (30 d)", "-")
        row2.addWidget(self.card_mtbf)
        row2.addWidget(self.card_mttr)
        row2.addWidget(self.card_cuts)
        lay.addLayout(row2)

        # --- Fila 3: SLA ---
        row3 = QHBoxLayout()
        self.card_sla995 = KPICard("SLA 99.5 %", "-", "comprometido")
        self.card_sla999 = KPICard("SLA 99.9 %", "-", "comprometido")
        row3.addWidget(self.card_sla995)
        row3.addWidget(self.card_sla999)
        lay.addLayout(row3)

        # --- Fila 4: Red ---
        row4 = QHBoxLayout()
        self.card_net_status = KPICard("Estado de red", "-")
        self.card_net_uptime = KPICard("Uptime red (30 d)", "-")
        self.card_net_downs  = KPICard("Caidas de red (30 d)", "-")
        row4.addWidget(self.card_net_status)
        row4.addWidget(self.card_net_uptime)
        row4.addWidget(self.card_net_downs)
        lay.addLayout(row4)

        lay.addStretch()
        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self):
        try:
            self._refresh_uptime()
        except Exception as e:
            log.warning(f"Error refrescando uptime: {e}")

        try:
            self._refresh_red()
        except Exception as e:
            log.warning(f"Error refrescando red: {e}")

    # ------------------------------------------------------------------
    def _refresh_uptime(self):
        r30 = compute_availability(30)
        r7  = compute_availability(7)
        r1  = compute_availability(1)

        self.card_uptime30.set(
            f"{r30['availability_pct']:.2f} %",
            f"{r30['cuts']} cortes - {r30['reboots']} reinicios",
        )
        self.card_uptime7.set(
            f"{r7['availability_pct']:.2f} %",
            f"{r7['cuts']} cortes - {r7['reboots']} reinicios",
        )
        self.card_today.set(
            f"{r1['availability_pct']:.2f} %",
            f"{r1['cuts']} cortes hoy",
        )

        mtbf = compute_mtbf(30)
        mttr = compute_mttr(30)
        self.card_mtbf.set(f"{mtbf:.1f} h" if mtbf else "-")
        self.card_mttr.set(f"{mttr:.1f} min" if mttr else "-")
        self.card_cuts.set(str(r30["cuts"]))

        self.card_sla995.set(
            "Cumplido" if r30["sla_995_ok"] else "No cumplido",
            "99.5 %",
        )
        self.card_sla995.set_value_color(
            "#2E7D32" if r30["sla_995_ok"] else "#C62828"
        )
        self.card_sla999.set(
            "Cumplido" if r30["sla_999_ok"] else "No cumplido",
            "99.9 %",
        )
        self.card_sla999.set_value_color(
            "#2E7D32" if r30["sla_999_ok"] else "#C62828"
        )

    # ------------------------------------------------------------------
    def _refresh_red(self):
        net = net_status_last(days=30)

        if net["ok"]:
            ping_txt = "sin latencia"
            if net["last_ping_ms"] is not None:
                ping_txt = f"ultimo ping: {net['last_ping_ms']:.0f} ms"
            self.card_net_status.set("En linea", ping_txt)
            self.card_net_status.set_value_color("#2E7D32")
        else:
            self.card_net_status.set(
                "Sin conexion",
                f"ultimo intento: {net['last_time']}",
            )
            self.card_net_status.set_value_color("#C62828")

        self.card_net_uptime.set(
            f"{net['uptime_pct']:.2f} %",
            "de lecturas con ping OK",
        )
        self.card_net_downs.set(
            str(net["downs"]),
            "eventos NET_DOWN",
        )