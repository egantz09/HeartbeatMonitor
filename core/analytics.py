# core/analytics.py
from datetime import datetime, date, timedelta
from core.database import Database
from core.constants import EVENT_BOOT, EVENT_POWER_LOSS, EVENT_SHUTDOWN


def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


def compute_mtbf(days: int = 30) -> float:
    """
    Mean Time Between Failures (en horas).
    Se calcula como el tiempo total entre eventos de fallo (POWER_LOSS).
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    events = Database.events_between(start, end)

    fallos = [_parse(e["timestamp"]) for e in events if e["event"] == EVENT_POWER_LOSS]
    if len(fallos) < 2:
        return 0.0

    intervalos = [
        (fallos[i + 1] - fallos[i]).total_seconds() / 3600
        for i in range(len(fallos) - 1)
    ]
    return sum(intervalos) / len(intervalos) if intervalos else 0.0


def compute_mttr(days: int = 30) -> float:
    """
    Mean Time To Recovery (en minutos).
    Se calcula como el tiempo medio entre POWER_LOSS y el BOOT siguiente.
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    events = Database.events_between(start, end)

    tiempos = []
    fallo_ts = None
    for e in events:
        ts = _parse(e["timestamp"])
        if e["event"] == EVENT_POWER_LOSS:
            fallo_ts = ts
        elif e["event"] == EVENT_BOOT and fallo_ts is not None:
            tiempos.append((ts - fallo_ts).total_seconds() / 60)
            fallo_ts = None

    return sum(tiempos) / len(tiempos) if tiempos else 0.0


def compute_availability(days: int = 30) -> dict:
    """
    Disponibilidad en el rango indicado.
    Retorna:
        {
          "days": N,
          "on_hours": X,
          "off_hours": Y,
          "availability_pct": Z,
          "reboots": R,
          "cuts": C,
          "sla_995_ok": bool,   # cumple SLA 99.5 %
          "sla_999_ok": bool,   # cumple SLA 99.9 %
        }
    """
    end = date.today()
    start = end - timedelta(days=days - 1)

    # Sumar desde la tabla summaries; si algún día falta, calcularlo
    from core.summary import build_summary

    total_on = 0.0
    total_off = 0.0
    reboots = 0
    cuts = 0

    d = start
    while d <= end:
        s = Database.get_summary(d)
        if s is None:
            s = build_summary(d)
        total_on += s["hours_on"]
        total_off += s["hours_off"]
        reboots += s["reboots"]
        cuts += s["cuts"]
        d += timedelta(days=1)

    total = total_on + total_off
    availability = (total_on / total * 100) if total > 0 else 0.0

    return {
        "days": days,
        "on_hours": total_on,
        "off_hours": total_off,
        "availability_pct": availability,
        "reboots": reboots,
        "cuts": cuts,
        "sla_995_ok": availability >= 99.5,
        "sla_999_ok": availability >= 99.9,
    }


def cuts_heatmap(days: int = 30) -> dict[int, list[int]]:
    """
    Devuelve un dict {hour: [conteo_por_dia_semana]}
    donde día_semana 0=lunes, 6=domingo.
    Sirve para dibujar un heatmap 24x7.
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    events = Database.events_between(start, end)

    grid = {h: [0] * 7 for h in range(24)}
    for e in events:
        if e["event"] != EVENT_POWER_LOSS:
            continue
        ts = _parse(e["timestamp"])
        grid[ts.hour][ts.weekday()] += 1
    return grid


def top_longest_cuts(days: int = 30, top: int = 5) -> list[dict]:
    """Los cortes más largos del periodo, ordenados descendente."""
    end = datetime.now()
    start = end - timedelta(days=days)
    events = Database.events_between(start, end)

    cortes = []
    fallo_ts = None
    for e in events:
        ts = _parse(e["timestamp"])
        if e["event"] == EVENT_POWER_LOSS:
            fallo_ts = ts
        elif e["event"] == EVENT_BOOT and fallo_ts is not None:
            dur = (ts - fallo_ts).total_seconds() / 60
            cortes.append({
                "inicio": fallo_ts,
                "fin": ts,
                "duracion_min": dur,
            })
            fallo_ts = None

    cortes.sort(key=lambda x: x["duracion_min"], reverse=True)
    return cortes[:top]

from core.constants import EVENT_NET_DOWN, EVENT_NET_UP


def count_net_down(days: int = 30) -> int:
    end = datetime.now()
    start = end - timedelta(days=days)
    events = Database.events_between(start, end)
    return sum(1 for e in events if e["event"] == EVENT_NET_DOWN)


def net_status_last(days: int = 7) -> dict:
    start = datetime.now() - timedelta(days=days)

    metrics = Database.metrics_since(start, limit=10_000)
    if metrics:
        last = metrics[0]
        ok = bool(last["ping_ok"])
        ping_ms = last["ping_ms"]
        last_time = last["timestamp"]
    else:
        ok = False
        ping_ms = None
        last_time = "—"

    total = len(metrics)
    ok_count = sum(1 for m in metrics if m["ping_ok"])
    uptime_pct = (ok_count / total * 100) if total else 0.0

    downs = count_net_down(days)

    return {
        "ok": ok,
        "last_ping_ms": ping_ms,
        "last_time": last_time,
        "downs": downs,
        "uptime_pct": uptime_pct,
    }

def net_status_per_host(hours: int = 24) -> dict:
    """
    Devuelve {host: {"ok": bool, "ping_ms": float|None, "time": str,
                     "uptime_pct": float, "downs": int}}
    """
    latest = Database.latest_ping_per_host(hours=hours)
    result = {}

    for host, last in latest.items():
        metrics = Database.pings_for_host(host, hours=hours)
        total = len(metrics)
        ok_count = sum(1 for m in metrics if m["ping_ok"])
        uptime = (ok_count / total * 100) if total else 0.0

        # Contar caídas (transiciones OK -> fallo)
        downs = 0
        prev = None
        for m in reversed(metrics):   # orden cronológico ascendente
            ok = bool(m["ping_ok"])
            if prev is True and ok is False:
                downs += 1
            prev = ok

        result[host] = {
            "ok": bool(last["ping_ok"]),
            "ping_ms": last["ping_ms"],
            "time": last["timestamp"],
            "uptime_pct": uptime,
            "downs": downs,
            "total_lecturas": total,
        }

    return result