# core/excel_manager.py
import logging
from datetime import datetime, date

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from core.constants import REPORTS_DIR, APP_NAME, APP_AUTHOR, APP_EMAIL, APP_VERSION
from core.database import Database

log = logging.getLogger(__name__)


class ExcelManager:

    HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
    HEADER_FONT = Font(bold=True, color="FFFFFF")

    # ------------------------------------------------------------------
    @staticmethod
    def _month_file(month: date) -> "Path":
        from pathlib import Path
        return REPORTS_DIR / f"{month:%Y-%m}.xlsx"

    @classmethod
    def _style_header(cls, ws):
        for cell in ws[1]:
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center")

    # ------------------------------------------------------------------
    @classmethod
    def _write_cover(cls, wb, month: date):
        ws = wb.create_sheet("Portada", 0)
        ws.column_dimensions["A"].width = 30
        ws.column_dimensions["B"].width = 50

        rows = [
            (APP_NAME, ""),
            ("Version", APP_VERSION),
            ("Autor", APP_AUTHOR),
            ("Contacto", APP_EMAIL),
            ("Reporte", month.strftime("%Y-%m")),
            ("Generado", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ]
        for i, (k, v) in enumerate(rows, start=1):
            ws.cell(row=i, column=1, value=k).font = Font(bold=True)
            ws.cell(row=i, column=2, value=v)

        ws["A1"].font = Font(bold=True, size=16, color="1F4E78")
        ws["A9"].value = f"Creada por {APP_AUTHOR}"
        ws["A9"].font = Font(italic=True, color="888888")

    # ------------------------------------------------------------------
    @classmethod
    def export_month(cls, month: date = None) -> str:
        """Genera el xlsx del mes indicado (o el actual)."""
        month = month or date.today()
        first = month.replace(day=1)
        if month.month == 12:
            next_first = month.replace(year=month.year + 1, month=1, day=1)
        else:
            next_first = month.replace(month=month.month + 1, day=1)

        start_dt = datetime.combine(first, datetime.min.time())
        end_dt   = datetime.combine(next_first, datetime.min.time())

        events = Database.events_between(start_dt, end_dt)

        wb = Workbook()
        ws = wb.active
        ws.title = "Eventos"
        ws.append(["FechaHora", "Evento", "Detalle"])
        cls._style_header(ws)

        for ev in events:
            ws.append([
                ev["timestamp"].replace("T", " "),
                ev["event"],
                ev["detail"] or "",
            ])

        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["B"].width = 15
        ws.column_dimensions["C"].width = 60

        # Hoja Resumen
        ws2 = wb.create_sheet("Resumen")
        ws2.append(["Fecha", "Horas_ON", "Horas_OFF",
                    "Reinicios", "Cortes"])
        cls._style_header(ws2)

        for r in Database.summaries_between(first, next_first):
            ws2.append([
                r["day"],
                round(r["hours_on"] or 0, 2),
                round(r["hours_off"] or 0, 2),
                r["reboots"] or 0,
                r["cuts"] or 0,
            ])

        for col in "ABCDE":
            ws2.column_dimensions[col].width = 14

        # Portada al inicio
        cls._write_cover(wb, month)

        out = cls._month_file(month)
        try:
            wb.save(out)
            log.info(f"Excel generado: {out}")
        except PermissionError:
            log.error(f"No se pudo guardar {out}: archivo en uso")
            raise

        return str(out)

    # ------------------------------------------------------------------
    @classmethod
    def export_all(cls) -> list:
        """Exporta todos los meses con eventos."""
        with Database._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT substr(timestamp,1,7) AS m "
                "FROM events ORDER BY m"
            ).fetchall()

        generated = []
        for r in rows:
            y, m = map(int, r["m"].split("-"))
            try:
                generated.append(cls.export_month(date(y, m, 1)))
            except Exception as e:
                log.warning(f"Error exportando {y}-{m}: {e}")
        return generated