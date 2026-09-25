from datetime import datetime, date, timedelta
from core.database import Database
from core.constants import EVENT_BOOT, EVENT_POWER_LOSS


def build_summary(day: date):
    """Calcula horas ON/OFF, reinicios y cortes para un día dado."""
    start = datetime.combine(day, datetime.min.time())
    end   = datetime.combine(day + timedelta(days=1), datetime.min.time())

    events = Database.events_between(start, end)

    # Tiempo ON = suma de intervalos entre HEARTBEATs consecutivos (≤ umbral)
    from core.constants import POWER_LOSS_THRESHOLD
    heartbeats = [
        datetime.fromisoformat(e["timestamp"])
        for e in events if e["event"] == "HEARTBEAT"
    ]
    # Nota: heartbeat no se persiste; usamos BOOT/RESUME como "inicio on"
    # y SHUTDOWN/POWER_LOSS/SUSPEND como "fin on".
    on_starts = {"BOOT", "RESUME"}
    on_ends   = {"SHUTDOWN", "POWER_LOSS", "SUSPEND"}

    total_on = timedelta()
    last_on = None
    for e in events:
        ts = datetime.fromisoformat(e["timestamp"])
        if e["event"] in on_starts:
            last_on = ts
        elif e["event"] in on_ends and last_on:
            total_on += ts - last_on
            last_on = None

    # Si seguimos "on" al final del día, contar hasta 'end'
    if last_on:
        total_on += end - last_on

    hours_on  = total_on.total_seconds() / 3600
    hours_off = 24 - hours_on

    reboots = Database.count_events(EVENT_BOOT, day)
    cuts    = Database.count_events(EVENT_POWER_LOSS, day)

    Database.save_summary(day, hours_on, hours_off, reboots, cuts)
    return {
        "day": day,
        "hours_on": hours_on,
        "hours_off": hours_off,
        "reboots": reboots,
        "cuts": cuts,
    }