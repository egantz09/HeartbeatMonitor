# services/pdf_export.py
from calendar import monthrange
from datetime import datetime, date, timedelta

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak,
)

from core.database import Database
from core.constants import REPORTS_DIR


# ---------------------------------------------------------------- estilos
_styles = getSampleStyleSheet()

STYLE_TITLE = ParagraphStyle(
    "HMTitle",
    parent=_styles["Title"],
    textColor=colors.HexColor("#1F4E78"),
    fontSize=22,
    spaceAfter=6,
)

STYLE_SUBTITLE = ParagraphStyle(
    "HMSubtitle",
    parent=_styles["Normal"],
    textColor=colors.HexColor("#555555"),
    fontSize=11,
    spaceAfter=18,
)

STYLE_H2 = ParagraphStyle(
    "HMH2",
    parent=_styles["Heading2"],
    textColor=colors.HexColor("#1F4E78"),
    fontSize=14,
    spaceBefore=14,
    spaceAfter=8,
)

STYLE_BODY = _styles["Normal"]

HEADER_BG   = colors.HexColor("#1F4E78")
HEADER_FG   = colors.white
ROW_ALT_BG  = colors.HexColor("#F2F2F2")
GRID_COLOR  = colors.HexColor("#CCCCCC")


# ---------------------------------------------------------------- helpers
def _month_bounds(month: date) -> tuple[datetime, datetime, str]:
    """Devuelve (inicio, fin_exclusivo, nombre_mes) para el mes dado."""
    first = month.replace(day=1)
    if month.month == 12:
        next_first = month.replace(year=month.year + 1, month=1, day=1)
    else:
        next_first = month.replace(month=month.month + 1, day=1)

    start = datetime.combine(first, datetime.min.time())
    end   = datetime.combine(next_first, datetime.min.time())

    meses = [
        "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
    ]
    nombre = f"{meses[month.month - 1]} {month.year}"
    return start, end, nombre


def _fmt_delta(td: timedelta) -> str:
    total = int(td.total_seconds())
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _build_month_summary_rows(start: datetime, end: datetime):
    """Recorre cada día del mes y devuelve filas listas para la tabla."""
    rows = []
    d = start.date()
    last = (end - timedelta(seconds=1)).date()

    while d <= last:
        s = Database.get_summary(d)
        if s:
            pct = (s["hours_on"] / 24) * 100 if s["hours_on"] else 0.0
            rows.append([
                d.strftime("%d/%m/%Y"),
                d.strftime("%a"),
                f"{s['hours_on']:6.2f}",
                f"{s['hours_off']:6.2f}",
                f"{pct:5.1f} %",
                str(s["reboots"]),
                str(s["cuts"]),
            ])
        else:
            rows.append([
                d.strftime("%d/%m/%Y"),
                d.strftime("%a"),
                "—", "—", "—", "—", "—",
            ])
        d += timedelta(days=1)
    return rows


def _summary_totals(start: datetime, end: datetime):
    """Agrega totales del mes para el resumen ejecutivo."""
    total_on = 0.0
    total_off = 0.0
    total_reboots = 0
    total_cuts = 0
    dias_con_datos = 0

    d = start.date()
    last = (end - timedelta(seconds=1)).date()
    while d <= last:
        s = Database.get_summary(d)
        if s:
            dias_con_datos += 1
            total_on += s["hours_on"]
            total_off += s["hours_off"]
            total_reboots += s["reboots"]
            total_cuts += s["cuts"]
        d += timedelta(days=1)

    horas_totales = max(total_on + total_off, 1.0)
    uptime_pct = (total_on / horas_totales) * 100 if dias_con_datos else 0.0

    return {
        "dias_con_datos": dias_con_datos,
        "total_on": total_on,
        "total_off": total_off,
        "uptime_pct": uptime_pct,
        "reboots": total_reboots,
        "cuts": total_cuts,
    }


# ---------------------------------------------------------------- PDF
def export_month_pdf(month: date = None) -> str:
    """Genera un PDF con el resumen completo de un mes."""
    month = month or date.today()
    start, end, nombre_mes = _month_bounds(month)

    filename = REPORTS_DIR / f"reporte_{month:%Y-%m}.pdf"

    doc = SimpleDocTemplate(
        str(filename),
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"HeartbeatMonitor — {nombre_mes}",
        author="HeartbeatMonitor",
    )

    story = []

    # ----- Portada -----
    story.append(Paragraph("HeartbeatMonitor", STYLE_TITLE))
    story.append(Paragraph(
        f"Reporte de disponibilidad — {nombre_mes}",
        STYLE_SUBTITLE,
    ))

    totals = _summary_totals(start, end)

    resumen_data = [
        ["Métrica", "Valor"],
        ["Días con datos",        f"{totals['dias_con_datos']}"],
        ["Horas ON (acumuladas)", f"{totals['total_on']:.2f} h"],
        ["Horas OFF (acumuladas)",f"{totals['total_off']:.2f} h"],
        ["Uptime promedio",       f"{totals['uptime_pct']:.2f} %"],
        ["Reinicios totales",     f"{totals['reboots']}"],
        ["Cortes eléctricos",     f"{totals['cuts']}"],
    ]
    resumen_table = Table(resumen_data, colWidths=[80 * mm, 60 * mm])
    resumen_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRID_COLOR),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ("ALIGN",         (1, 1), (1, -1), "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(resumen_table)

    story.append(PageBreak())

    # ----- Resumen por día -----
    story.append(Paragraph("Resumen por día", STYLE_H2))

    rows = _build_month_summary_rows(start, end)
    header = ["Fecha", "Día", "ON (h)", "OFF (h)", "Uptime", "Reinicios", "Cortes"]
    data = [header] + rows

    day_table = Table(
        data,
        colWidths=[28 * mm, 15 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm, 22 * mm],
        repeatRows=1,
    )
    day_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRID_COLOR),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ("ALIGN",         (2, 1), (-1, -1), "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(day_table)

    story.append(PageBreak())

    # ----- Eventos -----
    story.append(Paragraph("Eventos del mes", STYLE_H2))

    events = Database.events_between(start, end)
    ev_header = ["Fecha y hora", "Evento", "Detalle"]
    ev_data = [ev_header]
    for e in events:
        ts = e["timestamp"].replace("T", " ")
        ev_data.append([ts, e["event"], e["detail"] or ""])

    if len(ev_data) == 1:
        story.append(Paragraph("Sin eventos registrados este mes.", STYLE_BODY))
    else:
        ev_table = Table(
            ev_data,
            colWidths=[45 * mm, 35 * mm, 165 * mm],
            repeatRows=1,
        )
        ev_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR",     (0, 0), (-1, 0), HEADER_FG),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.25, GRID_COLOR),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(ev_table)

    # ----- Pie de página -----
    def _on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        footer = (
            f"HeartbeatMonitor — {nombre_mes}    |    "
            f"Página {doc_.page}"
        )
        canvas.drawCentredString(
            landscape(A4)[0] / 2, 8 * mm, footer
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return str(filename)


# ---------------------------------------------------------------- compat
def export_pdf(start: datetime, end: datetime) -> str:
    """Compatibilidad: exporta el PDF del mes al que pertenece `start`."""
    return export_month_pdf(start.date())

#--------------------

def export_range_pdf(start: date, end: date) -> str:
    """
    Exporta un PDF para un rango personalizado de fechas (inclusive).
    """
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt   = datetime.combine(end + timedelta(days=1), datetime.min.time())

    filename = REPORTS_DIR / f"reporte_{start:%Y%m%d}_{end:%Y%m%d}.pdf"

    doc = SimpleDocTemplate(
        str(filename),
        pagesize=landscape(A4),
        leftMargin=15 * mm,
        rightMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=f"HeartbeatMonitor — {start} a {end}",
        author="HeartbeatMonitor",
    )

    story = []

    # Portada
    story.append(Paragraph("HeartbeatMonitor", STYLE_TITLE))
    story.append(Paragraph(
        f"Reporte de disponibilidad — {start:%d/%m/%Y} a {end:%d/%m/%Y}",
        STYLE_SUBTITLE,
    ))

    # Resumen agregado del rango
    from core.analytics import compute_availability
    dias = (end - start).days + 1
    res = compute_availability(dias)

    resumen_data = [
        ["Métrica", "Valor"],
        ["Días",               f"{dias}"],
        ["Horas ON",           f"{res['on_hours']:.2f} h"],
        ["Horas OFF",          f"{res['off_hours']:.2f} h"],
        ["Disponibilidad",     f"{res['availability_pct']:.2f} %"],
        ["Reinicios",          f"{res['reboots']}"],
        ["Cortes eléctricos",  f"{res['cuts']}"],
    ]
    table = Table(resumen_data, colWidths=[80 * mm, 60 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 10),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRID_COLOR),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ("ALIGN",         (1, 1), (1, -1), "RIGHT"),
    ]))
    story.append(table)
    story.append(PageBreak())

    # Detalle por día
    story.append(Paragraph("Detalle por día", STYLE_H2))
    rows = _build_month_summary_rows(start_dt, end_dt)
    header = ["Fecha", "Día", "ON (h)", "OFF (h)", "Uptime", "Reinicios", "Cortes"]
    day_table = Table(
        [header] + rows,
        colWidths=[28 * mm, 15 * mm, 25 * mm, 25 * mm, 25 * mm, 25 * mm, 22 * mm],
        repeatRows=1,
    )
    day_table.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
        ("TEXTCOLOR",     (0, 0), (-1, 0), HEADER_FG),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.25, GRID_COLOR),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ("ALIGN",         (2, 1), (-1, -1), "RIGHT"),
    ]))
    story.append(day_table)
    story.append(PageBreak())

    # Eventos
    story.append(Paragraph("Eventos del rango", STYLE_H2))
    events = Database.events_between(start_dt, end_dt)
    ev_data = [["Fecha y hora", "Evento", "Detalle"]]
    for e in events:
        ev_data.append([
            e["timestamp"].replace("T", " "),
            e["event"],
            e["detail"] or "",
        ])
    if len(ev_data) == 1:
        story.append(Paragraph("Sin eventos en el rango.", STYLE_BODY))
    else:
        ev_table = Table(
            ev_data,
            colWidths=[45 * mm, 35 * mm, 165 * mm],
            repeatRows=1,
        )
        ev_table.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR",     (0, 0), (-1, 0), HEADER_FG),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.25, GRID_COLOR),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [colors.white, ROW_ALT_BG]),
        ]))
        story.append(ev_table)

    # Pie
    def _on_page(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#888888"))
        canvas.drawCentredString(
            landscape(A4)[0] / 2, 8 * mm,
            f"HeartbeatMonitor — {start:%d/%m/%Y} a {end:%d/%m/%Y}    |    Página {doc_.page}"
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return str(filename)