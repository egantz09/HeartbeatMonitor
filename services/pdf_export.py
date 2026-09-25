# services/pdf_export.py
"""
Generación de PDFs de reportes de disponibilidad.

Dos funciones públicas:
  - export_month_pdf(month)      → PDF del mes completo
  - export_range_pdf(start, end) → PDF de un rango de fechas
"""
import logging
from datetime import datetime, date, timedelta

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak,
)

from core.database import Database
from core.constants import (
    REPORTS_DIR, APP_NAME, APP_AUTHOR, APP_EMAIL,
)

log = logging.getLogger(__name__)


# =====================================================================
# Estilos compartidos
# =====================================================================
_styles = getSampleStyleSheet()

STYLE_TITLE = ParagraphStyle(
    "HMTitle", parent=_styles["Title"],
    textColor=colors.HexColor("#1F4E78"),
    fontSize=22, spaceAfter=6,
)
STYLE_SUBTITLE = ParagraphStyle(
    "HMSubtitle", parent=_styles["Normal"],
    textColor=colors.HexColor("#555555"),
    fontSize=11, spaceAfter=18,
)
STYLE_H2 = ParagraphStyle(
    "HMH2", parent=_styles["Heading2"],
    textColor=colors.HexColor("#1F4E78"),
    fontSize=14, spaceBefore=14, spaceAfter=8,
)
STYLE_BODY = _styles["Normal"]

HEADER_BG  = colors.HexColor("#1F4E78")
HEADER_FG  = colors.white
ROW_ALT_BG = colors.HexColor("#F2F2F2")
GRID_COLOR = colors.HexColor("#CCCCCC")


# =====================================================================
# Helpers
# =====================================================================
def _table_style(extra=None):
    """Estilo base compartido por las tablas."""
    base = [
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 9),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRID_COLOR),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if extra:
        base.extend(extra)
    return TableStyle(base)


def _month_bounds(month: date):
    """Devuelve (start_dt, end_dt, nombre_mes) para el mes dado."""
    first = month.replace(day=1)
    if month.month == 12:
        next_first = month.replace(year=month.year + 1, month=1, day=1)
    else:
        next_first = month.replace(month=month.month + 1, day=1)

    start = datetime.combine(first, datetime.min.time())
    end   = datetime.combine(next_first, datetime.min.time())

    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
             "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    nombre = f"{meses[month.month - 1]} {month.year}"
    return start, end, nombre


def _range_bounds(start: date, end: date):
    """Devuelve (start_dt, end_dt) inclusivo."""
    return (
        datetime.combine(start, datetime.min.time()),
        datetime.combine(end + timedelta(days=1), datetime.min.time()),
    )


def _build_daily_rows(start_dt: datetime, end_dt: datetime):
    """Filas de la tabla resumen día a día."""
    rows = []
    d = start_dt.date()
    last = (end_dt - timedelta(seconds=1)).date()

    while d <= last:
        s = Database.get_summary(d)
        if s:
            hours_on = s["hours_on"] or 0
            hours_off = s["hours_off"] or 0
            pct = (hours_on / 24 * 100) if hours_on else 0.0
            rows.append([
                d.strftime("%d/%m/%Y"),
                d.strftime("%a"),
                f"{hours_on:.2f}",
                f"{hours_off:.2f}",
                f"{pct:.1f} %",
                str(s["reboots"] or 0),
                str(s["cuts"] or 0),
            ])
        else:
            rows.append([
                d.strftime("%d/%m/%Y"), d.strftime("%a"),
                "-", "-", "-", "-", "-",
            ])
        d += timedelta(days=1)
    return rows


def _compute_totals(start_dt: datetime, end_dt: datetime):
    """Totales agregados del rango."""
    total_on = 0.0
    total_off = 0.0
    reboots = 0
    cuts = 0
    dias = 0

    d = start_dt.date()
    last = (end_dt - timedelta(seconds=1)).date()
    while d <= last:
        s = Database.get_summary(d)
        if s:
            dias += 1
            total_on  += s["hours_on"] or 0
            total_off += s["hours_off"] or 0
            reboots   += s["reboots"] or 0
            cuts      += s["cuts"] or 0
        d += timedelta(days=1)

    horas = total_on + total_off or 1
    uptime = (total_on / horas * 100) if dias else 0.0

    return {
        "dias": dias,
        "total_on": total_on,
        "total_off": total_off,
        "uptime": uptime,
        "reboots": reboots,
        "cuts": cuts,
    }


def _build_pdf(filename, title, subtitle, start_dt, end_dt, footer_range=""):
    """
    Genera el PDF (portada + detalle por día + eventos).
    `footer_range` es solo texto para el pie de página.
    """
    doc = SimpleDocTemplate(
        str(filename),
        pagesize=landscape(A4),
        leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
        title=title, author=APP_AUTHOR,
    )

    story = []

    # --- Portada ---
    story.append(Paragraph(APP_NAME, STYLE_TITLE))
    story.append(Paragraph(subtitle, STYLE_SUBTITLE))
    story.append(Paragraph(
        f"<para align='right'><font color='#666666' size='9'>"
        f"Creada por <b>{APP_AUTHOR}</b><br/>{APP_EMAIL}"
        f"</font></para>",
        STYLE_BODY,
    ))
    story.append(Spacer(1, 6))

    totals = _compute_totals(start_dt, end_dt)

    resumen_data = [
        ["Métrica", "Valor"],
        ["Días con datos", f"{totals['dias']}"],
        ["Horas ON",  f"{totals['total_on']:.2f} h"],
        ["Horas OFF", f"{totals['total_off']:.2f} h"],
        ["Uptime",    f"{totals['uptime']:.2f} %"],
        ["Reinicios", f"{totals['reboots']}"],
        ["Cortes",    f"{totals['cuts']}"],
    ]
    t = Table(resumen_data, colWidths=[80 * mm, 60 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRID_COLOR),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ("ALIGN",         (1, 1), (1, -1), "RIGHT"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(t)
    story.append(PageBreak())

    # --- Detalle por día ---
    story.append(Paragraph("Detalle por día", STYLE_H2))
    rows = _build_daily_rows(start_dt, end_dt)
    header = ["Fecha", "Día", "ON (h)", "OFF (h)",
              "Uptime", "Reinicios", "Cortes"]
    day_table = Table(
        [header] + rows,
        colWidths=[28*mm, 15*mm, 25*mm, 25*mm, 25*mm, 25*mm, 22*mm],
        repeatRows=1,
    )
    day_table.setStyle(_table_style([
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN",    (2, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(day_table)
    story.append(PageBreak())

    # --- Eventos ---
    story.append(Paragraph("Eventos del rango", STYLE_H2))
    events = Database.events_between(start_dt, end_dt)

    if not events:
        story.append(Paragraph("Sin eventos en el rango.", STYLE_BODY))
    else:
        ev_data = [["Fecha y hora", "Evento", "Detalle"]]
        for e in events:
            ev_data.append([
                e["timestamp"].replace("T", " "),
                e["event"],
                (e["detail"] or "")[:80],
            ])
        ev_table = Table(
            ev_data,
            colWidths=[45*mm, 35*mm, 160*mm],
            repeatRows=1,
        )
        ev_table.setStyle(_table_style([
            ("FONTSIZE", (0, 0), (-1, -1), 7),
        ]))
        story.append(ev_table)

    # --- Footer en cada página ---
    def _on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        footer = (
            f"{APP_NAME} - {footer_range}    |    "
            f"Creada por {APP_AUTHOR}    |    "
            f"Página {doc_.page}"
        )
        canvas.drawCentredString(
            landscape(A4)[0] / 2, 8 * mm, footer
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return str(filename)


# =====================================================================
# API pública
# =====================================================================
def export_month_pdf(month: date = None) -> str:
    """Genera un PDF con el resumen completo de un mes."""
    month = month or date.today()
    start_dt, end_dt, nombre_mes = _month_bounds(month)

    filename = REPORTS_DIR / f"reporte_{month:%Y-%m}.pdf"
    subtitle = f"Reporte de disponibilidad - {nombre_mes}"

    log.info(f"Generando PDF mensual: {filename}")
    return _build_pdf(
        filename, APP_NAME, subtitle,
        start_dt, end_dt, footer_range=nombre_mes,
    )


def export_range_pdf(start: date, end: date) -> str:
    """Genera un PDF para un rango personalizado de fechas."""
    if start > end:
        raise ValueError("La fecha de inicio es posterior a la final.")

    start_dt, end_dt = _range_bounds(start, end)

    filename = REPORTS_DIR / f"reporte_{start:%Y%m%d}_{end:%Y%m%d}.pdf"
    subtitle = (
        f"Reporte de disponibilidad - "
        f"{start:%d/%m/%Y} a {end:%d/%m/%Y}"
    )

    log.info(f"Generando PDF de rango: {filename}")
    return _build_pdf(
        filename, APP_NAME, subtitle,
        start_dt, end_dt,
        footer_range=f"{start:%d/%m/%Y} - {end:%d/%m/%Y}",
    )


# Alias retro-compatible
def export_pdf(start: datetime, end: datetime) -> str:
    """Compat: exporta el mes al que pertenece `start`."""
    return export_month_pdf(start.date())