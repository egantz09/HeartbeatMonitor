# core/analytics.py
import logging
from datetime import datetime, date, timedelta

from core.database import Database
from core.constants import (
    EVENT_BOOT, EVENT_POWER_LOSS,
    EVENT_NET_DOWN, EVENT_NET_UP,
)

log = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------
def _parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


# ----------------------------------------------------------------------
# MTBF / MTTR
# ----------------------------------------------------------------------
def compute_mtbf(days: int = 30) -> float:
    """
    Mean Time Between Failures (en horas).
    Se calcula como el tiempo medio entre eventos POWER_LOSS consecutivos.
    Devuelve 0.0 si hay menos de 2 cortes.
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    # Solo los eventos necesarios, filtrados en SQL
    events = Database.events_of_types_between((EVENT_POWER_LOSS,), start, end)

    fallos = [_parse(e["timestamp"]) for e in events]

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
    Tiempo medio entre POWER_LOSS y el BOOT siguiente.
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    events = Database.events_of_types_between(
        (EVENT_POWER_LOSS, EVENT_BOOT), start, end
    )

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


# ----------------------------------------------------------------------
# Disponibilidad / SLA
# ----------------------------------------------------------------------
def compute_availability(days: int = 30) -> dict:
    """
    Disponibilidad en el rango indicado.
    Reutiliza summaries ya guardados; si algún día falta, lo calcula.
    """
    end = date.today()
    start = end - timedelta(days=days - 1)

    # Cargar todos los summaries del rango de una vez (mucho más rápido)
    existing = {s["day"]: s for s in Database.summaries_between(start, end)}

    total_on = 0.0
    total_off = 0.0
    reboots = 0
    cuts = 0

    d = start
    while d <= end:
        key = d.isoformat()
        s = existing.get(key)
        if s is None:
            try:
                from core.summary import build_summary
                s = build_summary(d, persist=True)
            except Exception:
                s = {"hours_on": 0, "hours_off": 0, "reboots": 0, "cuts": 0}
        total_on  += s["hours_on"] or 0
        total_off += s["hours_off"] or 0
        reboots   += s["reboots"] or 0
        cuts      += s["cuts"] or 0
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


# ----------------------------------------------------------------------
# Heatmap de cortes
# ----------------------------------------------------------------------
def cuts_heatmap(days: int = 30) -> dict:
    """
    Devuelve {hour(0..23): [count_lun, ..., count_dom]}
    lista para alimentar un heatmap 24×7.
    """
    end = datetime.now()
    start = end - timedelta(days=days)
    events = Database.events_of_types_between((EVENT_POWER_LOSS,), start, end)

    grid = {h: [0] * 7 for h in range(24)}
    for e in events:
        try:
            ts = _parse(e["timestamp"])
        except ValueError:
            continue
        grid[ts.hour][ts.weekday()] += 1
    return grid


def top_longest_cuts(days: int = 30, top: int = 5) -> list:
    """Los cortes más largos del periodo."""
    end = datetime.now()
    start = end - timedelta(days=days)
    events = Database.events_of_types_between(
        (EVENT_POWER_LOSS, EVENT_BOOT), start, end
    )

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


# ----------------------------------------------------------------------
# Red
# ----------------------------------------------------------------------
def count_net_down(days: int = 30) -> int:
    end = datetime.now()
    start = end - timedelta(days=days)
    return Database.count_events_between(EVENT_NET_DOWN, start, end)


def net_status_last(days: int = 7) -> dict:
    """Estado global de la red (agregado de todos los hosts)."""
    start = datetime.now() - timedelta(days=days)

    latest = Database.latest_ping_per_host(hours=days * 24)
    if not latest:
        return {
            "ok": False,
            "last_ping_ms": None,
            "last_time": "-",
            "downs": count_net_down(days),
            "uptime_pct": 0.0,
        }

    # El "estado global" se considera OK solo si TODOS los hosts responden
    all_ok = all(bool(row["ping_ok"]) for row in latest.values())
    # Latencia media de los hosts OK
    pings_ok = [row["ping_ms"] for row in latest.values()
                if row["ping_ok"] and row["ping_ms"] is not None]
    avg_ping = sum(pings_ok) / len(pings_ok) if pings_ok else None

    # Última marca temporal (del más reciente)
    last_time = max(row["timestamp"] for row in latest.values())

    # Uptime: % de lecturas OK en TODO el periodo (agregado en SQL)
    total_readings = 0
    ok_readings = 0
    for host in latest.keys():
        stats = Database.ping_stats_between(host, start, datetime.now())
        total_readings += stats["total"]
        ok_readings += stats["ok_count"]

    uptime_pct = (ok_readings / total_readings * 100) if total_readings else 0.0

    return {
        "ok": all_ok,
        "last_ping_ms": avg_ping,
        "last_time": last_time,
        "downs": count_net_down(days),
        "uptime_pct": uptime_pct,
    }


def net_status_per_host(hours: int = 24) -> dict:
    """Estado por host: {host: {...}} — agregados calculados en SQL."""
    latest = Database.latest_ping_per_host(hours=hours)
    result = {}
    start = datetime.now() - timedelta(hours=hours)

    for host, last in latest.items():
        stats = Database.ping_stats_between(host, start, datetime.now())
        downs = Database.ping_downs_between(host, start, datetime.now())

        result[host] = {
            "ok": bool(last["ping_ok"]),
            "ping_ms": last["ping_ms"],
            "time": last["timestamp"],
            "uptime_pct": stats["uptime_pct"],
            "downs": downs,
            "total_lecturas": stats["total"],
        }

    return result