# core/summary.py
import logging
from datetime import datetime, date, timedelta

from core.database import Database
from core.constants import (
    EVENT_BOOT, EVENT_SHUTDOWN, EVENT_POWER_LOSS,
    EVENT_SUSPEND, EVENT_RESUME,
)

log = logging.getLogger(__name__)


# Eventos que indican "equipo encendido"
_ON_STARTS = {EVENT_BOOT, EVENT_RESUME}
# Eventos que indican "equipo apagado"
_ON_ENDS = {EVENT_SHUTDOWN, EVENT_POWER_LOSS, EVENT_SUSPEND}


def build_summary(day: date, persist: bool = True) -> dict:
    """
    Calcula el resumen de un día:
      - hours_on / hours_off
      - reboots (BOOTs)
      - cuts (POWER_LOSS)

    Si `persist=True`, guarda el resultado en la tabla `summaries`.
    """
    start = datetime.combine(day, datetime.min.time())
    tomorrow = day + timedelta(days=1)
    end = datetime.combine(tomorrow, datetime.min.time())

    # Si el día es HOY, limitamos el cálculo a la hora actual
    now = datetime.now()
    is_today = (day == now.date())
    effective_end = now if is_today else end

    events = Database.events_between(start, effective_end)

    total_on = timedelta()
    last_on = None
    reboots = 0
    cuts = 0

    for e in events:
        ts = datetime.fromisoformat(e["timestamp"])
        ev = e["event"]

        if ev in _ON_STARTS:
            last_on = ts
            if ev == EVENT_BOOT:
                reboots += 1
        elif ev in _ON_ENDS and last_on is not None:
            total_on += ts - last_on
            last_on = None

        if ev == EVENT_POWER_LOSS:
            cuts += 1

    # Si seguimos "ON" al final del periodo
    if last_on is not None:
        total_on += effective_end - last_on

    hours_on = total_on.total_seconds() / 3600
    # Horas OFF: desde el inicio del día hasta ahora (o 24 h si es pasado)
    elapsed_hours = (effective_end - start).total_seconds() / 3600
    hours_off = max(0.0, elapsed_hours - hours_on)

    result = {
        "day": day,
        "hours_on": hours_on,
        "hours_off": hours_off,
        "reboots": reboots,
        "cuts": cuts,
    }

    if persist:
        try:
            Database.save_summary(day, hours_on, hours_off, reboots, cuts)
        except Exception as e:
            log.warning(f"No se pudo guardar summary de {day}: {e}")

    return result