# core/database.py
import sqlite3
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from core.constants import DB_FILE


class Database:

    @staticmethod
    @contextmanager
    def _conn():
        conn = sqlite3.connect(DB_FILE, timeout=10)
        conn.row_factory = sqlite3.Row
        # WAL mejora concurrencia lectura/escritura
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
        except sqlite3.DatabaseError:
            pass
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    @classmethod
    def init(cls):
        with cls._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT    NOT NULL,
                    event     TEXT    NOT NULL,
                    detail    TEXT    DEFAULT ''
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_ts ON events(timestamp)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_events_ev ON events(event)")

            c.execute("""
                CREATE TABLE IF NOT EXISTS summaries (
                    day        TEXT PRIMARY KEY,
                    hours_on   REAL,
                    hours_off  REAL,
                    reboots    INTEGER,
                    cuts       INTEGER
                )
            """)

    @classmethod
    def init_ping(cls):
        with cls._conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS ping_metrics (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    host      TEXT NOT NULL,
                    ping_ms   REAL,
                    ping_ok   INTEGER
                )
            """)
            c.execute("CREATE INDEX IF NOT EXISTS idx_ping_ts ON ping_metrics(timestamp)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_ping_host ON ping_metrics(host)")

    # ------------------------------------------------------------------
    # Eventos
    # ------------------------------------------------------------------
    @classmethod
    def add_event(cls, event: str, detail: str = ""):
        with cls._conn() as c:
            c.execute(
                "INSERT INTO events(timestamp, event, detail) VALUES (?,?,?)",
                (datetime.now().isoformat(timespec="seconds"), event, detail),
            )

    @classmethod
    def events_between(cls, start: datetime, end: datetime):
        with cls._conn() as c:
            rows = c.execute(
                "SELECT timestamp, event, detail FROM events "
                "WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def all_events(cls):
        with cls._conn() as c:
            rows = c.execute(
                "SELECT timestamp, event, detail FROM events ORDER BY timestamp"
            ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def events_with_duration(cls, start: datetime, end: datetime):
        """
        Devuelve los eventos del rango con un campo extra `duration_seconds`
        calculado como la diferencia con el siguiente evento.
        """
        with cls._conn() as c:
            rows = c.execute(
                "SELECT timestamp, event, detail FROM events "
                "WHERE timestamp BETWEEN ? AND ? ORDER BY timestamp",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
            events = [dict(r) for r in rows]

            next_after = c.execute(
                "SELECT timestamp FROM events "
                "WHERE timestamp > ? ORDER BY timestamp LIMIT 1",
                (end.isoformat(),),
            ).fetchone()
            next_ts = next_after["timestamp"] if next_after else None

        result = []
        for i, ev in enumerate(events):
            ts = datetime.fromisoformat(ev["timestamp"])
            if i + 1 < len(events):
                nxt = datetime.fromisoformat(events[i + 1]["timestamp"])
            elif next_ts:
                nxt = datetime.fromisoformat(next_ts)
            else:
                nxt = None

            dur = (nxt - ts).total_seconds() if nxt else None
            result.append({
                "timestamp": ev["timestamp"],
                "event": ev["event"],
                "detail": ev["detail"],
                "duration_seconds": dur,
            })
        return result

    @classmethod
    def count_events(cls, event: str, day: date) -> int:
        start = datetime.combine(day, datetime.min.time())
        end   = datetime.combine(day, datetime.max.time())
        with cls._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) AS n FROM events "
                "WHERE event=? AND timestamp BETWEEN ? AND ?",
                (event, start.isoformat(), end.isoformat()),
            ).fetchone()
        return row["n"] if row else 0

    @classmethod
    def count_events_by_type(cls, event: str) -> int:
        with cls._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) AS n FROM events WHERE event=?", (event,)
            ).fetchone()
        return row["n"] if row else 0

    # ------------------------------------------------------------------
    # Resúmenes diarios
    # ------------------------------------------------------------------
    @classmethod
    def save_summary(cls, day: date, hours_on, hours_off, reboots, cuts):
        with cls._conn() as c:
            c.execute("""
                INSERT INTO summaries(day, hours_on, hours_off, reboots, cuts)
                VALUES (?,?,?,?,?)
                ON CONFLICT(day) DO UPDATE SET
                    hours_on=excluded.hours_on,
                    hours_off=excluded.hours_off,
                    reboots=excluded.reboots,
                    cuts=excluded.cuts
            """, (day.isoformat(), hours_on, hours_off, reboots, cuts))

    @classmethod
    def get_summary(cls, day: date):
        with cls._conn() as c:
            row = c.execute(
                "SELECT * FROM summaries WHERE day=?", (day.isoformat(),)
            ).fetchone()
        return dict(row) if row else None

    @classmethod
    def summaries_between(cls, start: date, end: date):
        with cls._conn() as c:
            rows = c.execute(
                "SELECT * FROM summaries WHERE day BETWEEN ? AND ? ORDER BY day",
                (start.isoformat(), end.isoformat()),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------------
    # Ping multi-host
    # ------------------------------------------------------------------
    @classmethod
    def add_ping(cls, host: str, ping_ms, ping_ok: bool):
        with cls._conn() as c:
            c.execute("""
                INSERT INTO ping_metrics(timestamp, host, ping_ms, ping_ok)
                VALUES (?,?,?,?)
            """, (
                datetime.now().isoformat(timespec="seconds"),
                host,
                ping_ms,
                1 if ping_ok else 0,
            ))

    @classmethod
    def pings_for_host(cls, host: str, hours: int = 24, limit: int = 5000):
        start = datetime.now() - timedelta(hours=hours)
        with cls._conn() as c:
            rows = c.execute(
                "SELECT * FROM ping_metrics "
                "WHERE host=? AND timestamp >= ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (host, start.isoformat(), limit),
            ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def latest_ping_per_host(cls, hours: int = 24):
        start = datetime.now() - timedelta(hours=hours)
        with cls._conn() as c:
            rows = c.execute("""
                SELECT p.* FROM ping_metrics p
                INNER JOIN (
                    SELECT host, MAX(id) AS max_id
                    FROM ping_metrics
                    WHERE timestamp >= ?
                    GROUP BY host
                ) ult ON ult.max_id = p.id
            """, (start.isoformat(),)).fetchall()
        return {r["host"]: dict(r) for r in rows}

    @classmethod
    def hosts_seen(cls, hours: int = 24):
        start = datetime.now() - timedelta(hours=hours)
        with cls._conn() as c:
            rows = c.execute(
                "SELECT DISTINCT host FROM ping_metrics WHERE timestamp >= ?",
                (start.isoformat(),),
            ).fetchall()
        return [r["host"] for r in rows]

    # ------------------------------------------------------------------
    # Mantenimiento
    # ------------------------------------------------------------------
    @classmethod
    def purge_old_data(cls, days: int = 365) -> int:
        """
        Elimina eventos y pings más antiguos que `days`.
        Devuelve el total de filas borradas.
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        deleted = 0
        with cls._conn() as c:
            cur = c.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
            deleted += cur.rowcount
            cur = c.execute("DELETE FROM ping_metrics WHERE timestamp < ?", (cutoff,))
            deleted += cur.rowcount
        return deleted