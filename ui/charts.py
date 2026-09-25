# ui/charts.py
"""
Gráficas embebidas en Qt con matplotlib.

Clases:
  - UptimeChart         → barras de uptime diario con tooltip
  - CutsByHourChart     → cortes por hora (barras horizontales)
  - CutsByWeekdayChart  → cortes por día de la semana
  - SingleMetricChart   → serie única (ping por host)
"""
from datetime import date, datetime, timedelta

import matplotlib.dates as mdates
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle

from core.database import Database
from core.summary import build_summary


# ----------------------------------------------------------------------
# Colores compartidos
# ----------------------------------------------------------------------
COLOR_OK      = "#2E7D32"   # verde
COLOR_WARN    = "#F9A825"   # amarillo
COLOR_BAD     = "#C62828"   # rojo
COLOR_EMPTY   = "#BDBDBD"   # gris (sin datos)
COLOR_GOAL    = "#1F4E78"   # azul corporativo
COLOR_TODAY   = "#1565C0"   # azul hoy

DIAS_ES = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]


def _color_for(pct: float, has_data: bool) -> str:
    if not has_data:
        return COLOR_EMPTY
    if pct >= 95:
        return COLOR_OK
    if pct >= 80:
        return COLOR_WARN
    return COLOR_BAD


# =====================================================================
# Uptime diario
# =====================================================================
class UptimeChart(FigureCanvasQTAgg):
    """Gráfica de uptime diario con colores semánticos y tooltip."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(8, 3.6), tight_layout=True)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self._data = []
        self._annot = None

        self.mpl_connect("motion_notify_event", self._on_hover)
        self.mpl_connect("figure_leave_event", self._on_leave)
        self._render_empty()

    # ------------------------------------------------------------------
    def plot_days(self, days: int = 14):
        today = date.today()
        now_hours = self._elapsed_hours_today()
        start = today - timedelta(days=days - 1)

        # Una sola consulta para todo el rango (en vez de una por día)
        existing = {s["day"]: s for s in Database.summaries_between(start, today)}

        data = []
        for i in range(days - 1, -1, -1):
            d = today - timedelta(days=i)

            if d == today:
                # El resumen de hoy se recalcula hasta la hora actual
                s = build_summary(d)
                if s and now_hours > 0.05:
                    pct = min(100.0, (s["hours_on"] / now_hours) * 100)
                else:
                    pct = 0.0
                has_data = s is not None and s["hours_on"] > 0
            else:
                s = existing.get(d.isoformat())
                if s:
                    pct = max(0.0, min(100.0, (s["hours_on"] / 24) * 100))
                    has_data = True
                else:
                    pct = 0.0
                    has_data = False

            data.append({
                "date": d,
                "pct": pct,
                "has_data": has_data,
                "hours_on": s["hours_on"] if s else 0.0,
                "hours_off": s["hours_off"] if s else 0.0,
                "reboots": s["reboots"] if s else 0,
                "cuts": s["cuts"] if s else 0,
                "is_today": d == today,
            })

        self._data = data
        self._render()

    # ------------------------------------------------------------------
    def _render_empty(self):
        self.ax.clear()
        self.ax.set_ylim(0, 105)
        self.ax.set_yticks([0, 25, 50, 75, 100])
        self.ax.set_yticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
        self.ax.set_title("Uptime diario", fontsize=11, fontweight="bold")
        self.ax.grid(axis="y", linestyle="--", alpha=0.3)
        self.draw()

    def _render(self):
        self.ax.clear()

        if not self._data:
            self._render_empty()
            return

        n = len(self._data)
        xs = list(range(n))
        ys = [d["pct"] for d in self._data]
        colors = [_color_for(d["pct"], d["has_data"]) for d in self._data]

        bars = self.ax.bar(
            xs, ys, color=colors, edgecolor="white",
            linewidth=0.8, width=0.72, zorder=3,
        )

        for i, d in enumerate(self._data):
            if d["is_today"]:
                bars[i].set_edgecolor(COLOR_TODAY)
                bars[i].set_linewidth(2.0)
                bars[i].set_linestyle("--")

        self.ax.axhline(
            95, color=COLOR_GOAL, linewidth=1.0,
            linestyle=":", alpha=0.7, zorder=2,
        )
        self.ax.text(
            n - 0.4, 95.5, "Objetivo 95 %",
            color=COLOR_GOAL, fontsize=8, ha="right", va="bottom",
        )

        labels = []
        for d in self._data:
            dow = DIAS_ES[d["date"].weekday()]
            labels.append(f"{dow}\n{d['date'].day}")
        self.ax.set_xticks(xs)
        self.ax.set_xticklabels(labels, fontsize=8)

        self.ax.set_ylim(0, 108)
        self.ax.set_yticks([0, 25, 50, 75, 100])
        self.ax.set_yticklabels(["0 %", "25 %", "50 %", "75 %", "100 %"])
        self.ax.grid(axis="y", linestyle="--", alpha=0.3, zorder=0)
        for spine in ("top", "right"):
            self.ax.spines[spine].set_visible(False)

        valid = [d["pct"] for d in self._data if d["has_data"]]
        avg = sum(valid) / len(valid) if valid else 0.0
        self.ax.set_title(
            f"Uptime - ultimos {n} dias        Promedio: {avg:.1f} %",
            fontsize=11, fontweight="bold", loc="left",
        )

        handles = [
            Rectangle((0, 0), 1, 1, color=COLOR_OK,    label=">=95 %"),
            Rectangle((0, 0), 1, 1, color=COLOR_WARN,  label="80-95 %"),
            Rectangle((0, 0), 1, 1, color=COLOR_BAD,   label="<80 %"),
            Rectangle((0, 0), 1, 1, color=COLOR_EMPTY, label="Sin datos"),
        ]
        self.ax.legend(
            handles=handles, loc="lower right",
            fontsize=8, framealpha=0.9, ncol=4,
        )

        self._annot = self.ax.annotate(
            "", xy=(0, 0), xytext=(8, 8),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.4",
                      fc="white", ec="#888", alpha=0.95),
            fontsize=8, zorder=10,
        )
        self._annot.set_visible(False)
        self.draw()

    # ------------------------------------------------------------------
    def _on_hover(self, event):
        if self._annot is None or event.inaxes != self.ax:
            return
        if event.xdata is None:
            return

        idx = int(round(event.xdata))
        if idx < 0 or idx >= len(self._data):
            self._annot.set_visible(False)
            self.draw_idle()
            return

        d = self._data[idx]
        estado = "HOY" if d["is_today"] else d["date"].strftime("%d/%m")
        if not d["has_data"]:
            texto = f"{estado}\nSin datos"
        else:
            texto = (
                f"{estado}  -  {d['pct']:.1f} %\n"
                f"ON:  {d['hours_on']:.2f} h\n"
                f"OFF: {d['hours_off']:.2f} h\n"
                f"Reinicios: {d['reboots']}\n"
                f"Cortes: {d['cuts']}"
            )
        self._annot.xy = (idx, d["pct"])
        self._annot.set_text(texto)
        self._annot.set_visible(True)
        self.draw_idle()

    def _on_leave(self, event):
        if self._annot is not None:
            self._annot.set_visible(False)
            self.draw_idle()

    @staticmethod
    def _elapsed_hours_today() -> float:
        now = datetime.now()
        return now.hour + now.minute / 60 + now.second / 3600


# =====================================================================
# Cortes por hora
# =====================================================================
class CutsByHourChart(FigureCanvasQTAgg):
    """Barras horizontales: cortes por hora del día."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 4.5), tight_layout=True)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self._render_empty()

    def _render_empty(self):
        self.ax.clear()
        self.ax.set_title("Sin datos", fontsize=11)
        self.draw()

    def plot(self, grid: dict):
        totals = [sum(grid.get(h, [0] * 7)) for h in range(24)]
        self.ax.clear()

        if max(totals) == 0:
            self.ax.set_title("Sin cortes registrados", fontsize=11)
            self.ax.set_xlim(0, 1)
            self.draw()
            return

        pares = sorted(
            [(h, c) for h, c in enumerate(totals) if c > 0],
            key=lambda x: x[1],
        )
        horas = [f"{h:02d}:00" for h, _ in pares]
        counts = [c for _, c in pares]
        max_c = max(counts)

        colores = [
            "#C62828" if c == max_c else
            "#F9A825" if c >= max_c * 0.6 else
            "#81C784"
            for c in counts
        ]

        bars = self.ax.barh(horas, counts, color=colores, edgecolor="white")

        for bar, c in zip(bars, counts):
            self.ax.text(
                bar.get_width() + max_c * 0.02,
                bar.get_y() + bar.get_height() / 2,
                str(c), va="center", fontsize=9, fontweight="bold",
            )

        self.ax.set_xlabel("Numero de cortes")
        self.ax.set_title("Horas del dia con mas cortes",
                          fontsize=11, fontweight="bold")
        self.ax.set_xlim(0, max_c * 1.15)
        self.ax.grid(axis="x", linestyle="--", alpha=0.3)
        for s in ("top", "right"):
            self.ax.spines[s].set_visible(False)
        self.draw()


# =====================================================================
# Cortes por día de la semana
# =====================================================================
class CutsByWeekdayChart(FigureCanvasQTAgg):
    """Barras verticales: cortes por día de la semana."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(6, 4.5), tight_layout=True)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)
        self._render_empty()

    def _render_empty(self):
        self.ax.clear()
        self.ax.set_title("Sin datos", fontsize=11)
        self.draw()

    def plot(self, grid: dict):
        totals = [0] * 7
        for h in range(24):
            for d in range(7):
                totals[d] += grid.get(h, [0] * 7)[d]

        self.ax.clear()

        if max(totals) == 0:
            self.ax.set_title("Sin cortes registrados", fontsize=11)
            self.ax.set_ylim(0, 1)
            self.draw()
            return

        max_c = max(totals)
        colores = [
            "#C62828" if c == max_c and c > 0 else
            "#F9A825" if c >= max_c * 0.6 else
            "#81C784"
            for c in totals
        ]

        bars = self.ax.bar(DIAS_ES, totals, color=colores, edgecolor="white")

        for bar, c in zip(bars, totals):
            if c > 0:
                self.ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max_c * 0.02,
                    str(c), ha="center", fontsize=9, fontweight="bold",
                )

        self.ax.set_ylabel("Numero de cortes")
        self.ax.set_title("Cortes por dia de la semana",
                          fontsize=11, fontweight="bold")
        self.ax.set_ylim(0, max_c * 1.15)
        self.ax.grid(axis="y", linestyle="--", alpha=0.3)
        for s in ("top", "right"):
            self.ax.spines[s].set_visible(False)
        self.draw()


# =====================================================================
# Serie única (ping por host)
# =====================================================================
class SingleMetricChart(FigureCanvasQTAgg):
    """Gráfica de una sola serie (ping)."""

    def __init__(self, titulo: str = "", color: str = "#64B5F6",
                 unidad: str = "%", y_max: float = 100,
                 umbral: float = None, parent=None):
        self.fig = Figure(figsize=(8, 2.0), tight_layout=True)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111)

        self.titulo = titulo
        self.color = color
        self.unidad = unidad
        self.y_max = y_max
        self.umbral = umbral
        self._render_empty()

    def _render_empty(self):
        self.ax.clear()
        self.ax.set_title(self.titulo, fontsize=10,
                          fontweight="bold", loc="left")
        self.ax.set_ylim(0, self.y_max)
        self.ax.grid(alpha=0.3, linestyle="--")
        self.draw()

    def plot(self, xs: list, ys: list, fail_indices: list = None):
        self.ax.clear()

        if not xs or not ys:
            self._render_empty()
            return

        self.ax.fill_between(xs, ys, 0, color=self.color,
                             alpha=0.18, zorder=1)
        self.ax.plot(xs, ys, color=self.color,
                     linewidth=1.4, zorder=2)

        if self.umbral is not None:
            self.ax.axhline(self.umbral, color="#C62828",
                            linestyle=":", alpha=0.7, zorder=3)
            self.ax.text(
                xs[-1], self.umbral,
                f"  limite {self.umbral:.0f}{self.unidad}",
                color="#C62828", fontsize=7,
                va="bottom", ha="right",
            )

        if fail_indices:
            # Agrupar fallos consecutivos en un solo span por caída
            spans = []
            a = b = fail_indices[0]
            for i in fail_indices[1:]:
                if i == b + 1:
                    b = i
                else:
                    spans.append((a, b))
                    a = b = i
            spans.append((a, b))

            for a, b in spans:
                self.ax.axvspan(
                    xs[a] - timedelta(seconds=30),
                    xs[b] + timedelta(seconds=30),
                    color="#C62828", alpha=0.20, zorder=0,
                )

        ultimo = ys[-1]
        self.ax.scatter([xs[-1]], [ultimo], color=self.color,
                        edgecolor="white", s=40, zorder=4)
        self.ax.text(
            xs[-1], ultimo,
            f"  {ultimo:.0f}{self.unidad}",
            fontsize=9, fontweight="bold",
            va="center", ha="left", color=self.color,
        )

        self.ax.set_title(self.titulo, fontsize=10,
                          fontweight="bold", loc="left")
        self.ax.set_ylim(0, self.y_max)
        self.ax.grid(alpha=0.3, linestyle="--")
        for s in ("top", "right"):
            self.ax.spines[s].set_visible(False)

        # Marcas horarias limpias
        locator = mdates.AutoDateLocator(minticks=4, maxticks=10)
        formatter = mdates.DateFormatter("%H:%M")
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)

        self.fig.autofmt_xdate(rotation=0, ha="center")
        self.draw()