# ui/tabs/metrics_tab.py
from datetime import datetime, timedelta, time as dtime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QFrame, QScrollArea,
)
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QFont

from core.database import Database
from core.config import Config
from core.analytics import net_status_per_host
from ui.charts import SingleMetricChart


# Modos del combo:  (etiqueta, horas_atras | "today")
RANGOS = [
    ("Hoy (00:00 → ahora)", "today"),
    ("Últimas 6 h",        6),
    ("Últimas 24 h",       24),
    ("Últimos 7 días",     24 * 7),
    ("Últimos 30 días",    24 * 30),
]


class HostCard(QFrame):

    def __init__(self, host: str):
        super().__init__()
        self.host = host
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            HostCard {
                background-color: rgba(31, 78, 120, 0.10);
                border: 1px solid rgba(31, 78, 120, 0.30);
                border-radius: 6px;
            }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(2)

        self.lbl_host = QLabel(host)
        self.lbl_host.setStyleSheet("color: #888; font-size: 10px;")
        lay.addWidget(self.lbl_host)

        self.lbl_status = QLabel("—")
        f = QFont()
        f.setPointSize(14)
        f.setBold(True)
        self.lbl_status.setFont(f)
        lay.addWidget(self.lbl_status)

        self.lbl_sub = QLabel("")
        self.lbl_sub.setStyleSheet("color: #aaa; font-size: 9px;")
        lay.addWidget(self.lbl_sub)

    def update_data(self, info: dict):
        if info["ok"]:
            ms = info.get("ping_ms")
            self.lbl_status.setText(
                f"{ms:.0f} ms" if ms is not None else "En línea"
            )
            self.lbl_status.setStyleSheet(
                "color: #2E7D32; font-weight: bold; font-size: 14px;"
            )
        else:
            self.lbl_status.setText("Sin conexión")
            self.lbl_status.setStyleSheet(
                "color: #C62828; font-weight: bold; font-size: 14px;"
            )

        t = info.get("time", "")
        t_str = t[11:19] if len(t) >= 19 else t
        self.lbl_sub.setText(
            f"Uptime {info['uptime_pct']:.1f} % · "
            f"{info['downs']} caídas · "
            f"{t_str}"
        )


class MetricsTab(QWidget):

    def __init__(self):
        super().__init__()
        self._host_charts = {}   # {host: SingleMetricChart}
        self._host_cards = {}    # {host: HostCard}
        self._current_hosts = []
        self._disabled_lbl = None

        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # --- Cabecera ---
        header = QHBoxLayout()
        header.addWidget(QLabel("Rango:"))
        self.cmb_range = QComboBox()
        for label, _ in RANGOS:
            self.cmb_range.addItem(label)
        self.cmb_range.setCurrentIndex(0)   # "Hoy" por defecto
        self.cmb_range.currentIndexChanged.connect(self.refresh)
        header.addWidget(self.cmb_range)
        header.addStretch()

        self.lbl_last = QLabel("—")
        self.lbl_last.setStyleSheet("color: #888; font-size: 10px;")
        header.addWidget(self.lbl_last)
        root.addLayout(header)

        # --- Scroll vertical ---
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(14)

        self._cards_row = QHBoxLayout()
        self._content_layout.addLayout(self._cards_row)
        self._content_layout.addStretch()

        self.scroll.setWidget(self._content)
        root.addWidget(self.scroll)

        # Timer de refresco
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh)
        self._timer.start(30_000)

        self._rebuild_if_needed()
        self.refresh()

    # ------------------------------------------------------------------
    def _clear_hosts(self):
        """Limpia tarjetas y gráficas."""
        while self._cards_row.count():
            item = self._cards_row.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)

        for chart in self._host_charts.values():
            chart.setParent(None)
            chart.deleteLater()
        self._host_charts.clear()
        self._host_cards.clear()

    # ------------------------------------------------------------------
    def _show_disabled_message(self):
        """Vacía la vista y muestra el mensaje de desactivado."""
        self._clear_hosts()
        self._current_hosts = []

        if self._disabled_lbl is None:
            self._disabled_lbl = QLabel(
                "El monitoreo de red está desactivado.\n\n"
                "Puedes activarlo en Configuración → "
                "'Activar monitoreo de red (ping)'."
            )
            self._disabled_lbl.setStyleSheet(
                "color: #888; padding: 40px; font-size: 13px;"
            )
            self._disabled_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.insertWidget(0, self._disabled_lbl)
        else:
            self._disabled_lbl.show()

        # Deshabilitar el combo de rango (no tiene sentido sin datos)
        self.cmb_range.setEnabled(False)
        self.lbl_last.setText("Monitoreo desactivado")

    # ------------------------------------------------------------------
    def _rebuild_if_needed(self) -> bool:
        # Ocultar el mensaje de desactivado si existe
        if self._disabled_lbl is not None:
            self._disabled_lbl.hide()

        self.cmb_range.setEnabled(True)

        hosts = Config.get("ping_hosts", []) or []
        hosts = [h.strip() for h in hosts if h and h.strip()]

        if hosts == self._current_hosts and self._host_charts:
            return False

        self._clear_hosts()
        self._current_hosts = list(hosts)

        if not hosts:
            lbl = QLabel(
                "No hay hosts configurados.\n"
                "Ve a Configuración y añade al menos un host para hacer ping."
            )
            lbl.setStyleSheet("color: #888; padding: 20px;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.insertWidget(0, lbl)
            return True

        # --- Tarjetas ---
        for h in hosts:
            card = HostCard(h)
            self._host_cards[h] = card
            self._cards_row.addWidget(card)

        # --- Gráficas ---
        for h in hosts:
            chart = SingleMetricChart(
                f"Ping a {h} (ms)",
                color="#FFB74D",
                unidad=" ms",
                y_max=500,
            )
            chart.setMinimumHeight(180)
            self._host_charts[h] = chart
            self._content_layout.insertWidget(
                self._content_layout.count() - 1, chart
            )

        return True

    # ------------------------------------------------------------------
    def _get_range(self):
        """Devuelve (start_dt, end_dt) según el combo."""
        idx = self.cmb_range.currentIndex()
        _, mode = RANGOS[idx]

        now = datetime.now()

        if mode == "today":
            start = datetime.combine(now.date(), dtime.min)
            return start, now

        start = now - timedelta(hours=int(mode))
        return start, now

    # ------------------------------------------------------------------
    def refresh(self):
        # Si el monitoreo está desactivado, mostrar mensaje y salir
        if not Config.get("ping_enabled", True):
            self._show_disabled_message()
            return

        self._rebuild_if_needed()

        if not self._host_charts:
            self.lbl_last.setText("Sin hosts configurados")
            return

        start_dt, end_dt = self._get_range()

        # --- Tarjetas (resumen últimas 24 h) ---
        info = net_status_per_host(hours=24)
        for host, card in self._host_cards.items():
            data = info.get(host)
            if data:
                card.update_data(data)
            else:
                card.lbl_status.setText("Sin datos")
                card.lbl_status.setStyleSheet(
                    "color: #888; font-weight: bold; font-size: 14px;"
                )
                card.lbl_sub.setText("")

        # --- Gráficas ---
        last_time = None
        for host, chart in self._host_charts.items():
            metrics = Database.pings_for_host(host, hours=24 * 30, limit=100_000)

            filtrados = [
                m for m in metrics
                if start_dt <= datetime.fromisoformat(m["timestamp"]) <= end_dt
            ]

            if not filtrados:
                chart.plot([], [])
                continue

            cron = list(reversed(filtrados))
            xs = [datetime.fromisoformat(m["timestamp"]) for m in cron]
            ys = [m["ping_ms"] if m["ping_ms"] is not None else 0 for m in cron]
            fails = [xs[i] for i, m in enumerate(cron) if not m["ping_ok"]]

            max_ping = max(ys) if ys else 0
            chart.y_max = max(200, int(max_ping * 1.2))
            chart.plot(xs, ys, ping_fail_xs=fails)

            if filtrados:
                last_time = filtrados[0]["timestamp"]

        if last_time:
            self.lbl_last.setText(f"Última lectura: {last_time}")