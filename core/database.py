# core/database.py
import sqlite3
import threading
from datetime import datetime, date, timedelta
from contextlib import contextmanager

from core.constants import DB_FILE


class Database:

    # Conexión persistente por hilo: sqlite3 no permite compartir una
    # conexión entre hilos y abrir una conexión por operación es caro.
    _local = threading.local()

    @classmethod
    def _connection(cls) -> sqlite3.Connection:
        conn = getattr(cls._local, "conn", None)
        if conn is None:
            conn = sqlite3.connect(DB_FILE, timeout=10)
            conn.row_factory = sqlite3.Row
            try:
                conn.execute("PRAGMA synchronous=NORMAL")
            except sqlite3.DatabaseError:
                pass
            cls._local.conn = conn
        return conn

    @classmethod
    @contextmanager
    def _conn(cls):
        conn = cls._connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------
    @classmethod
    def init(cls):
        with cls._conn() as c:
            # WAL mejora la concurrencia lectura/escritura y es persistente
            # en el fichero: basta con activarlo una vez.
            try:
                c.execute("PRAGMA journal_mode=WAL")
            except sqlite3.DatabaseError:
                pass
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
            # Índice compuesto para las consultas por host + rango de fechas
            c.execute(
                "CREATE INDEX IF NOT EXISTS idx_ping_host_ts "
                "ON ping_metrics(host, timestamp)"
            )

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
    def events_of_types_between(cls, event_types, start: datetime, end: datetime):
        """Eventos de los tipos indicados en el rango (solo timestamp y event)."""
        placeholders = ",".join("?" * len(event_types))
        with cls._conn() as c:
            rows = c.execute(
                f"SELECT timestamp, event FROM events "
                f"WHERE event IN ({placeholders}) "
                f"AND timestamp BETWEEN ? AND ? ORDER BY timestamp",
                (*event_types, start.isoformat(), end.isoformat()),
            ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def count_events_between(cls, event: str, start: datetime, end: datetime) -> int:
        with cls._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) AS n FROM events "
                "WHERE event=? AND timestamp BETWEEN ? AND ?",
                (event, start.isoformat(), end.isoformat()),
            ).fetchone()
        return row["n"] if row else 0

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
                "SELECT timestamp, ping_ms, ping_ok FROM ping_metrics "
                "WHERE host=? AND timestamp >= ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (host, start.isoformat(), limit),
            ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def pings_between_sampled(cls, host: str, start: datetime, end: datetime,
                              max_points: int = 1500) -> list:
        """
        Serie (timestamp, ping_ms, ping_ok) de un host en el rango, ASC.
        Si hay más de `max_points` lecturas, muestrea en SQL para que las
        gráficas no manejen decenas de miles de puntos.
        """
        base = "FROM ping_metrics WHERE host=? AND timestamp BETWEEN ? AND ?"
        params = (host, start.isoformat(), end.isoformat())
        with cls._conn() as c:
            total = c.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
            if total == 0:
                return []
            step = max(1, total // max_points)
            rows = c.execute(
                "SELECT timestamp, ping_ms, ping_ok FROM ("
                "  SELECT timestamp, ping_ms, ping_ok,"
                "         ROW_NUMBER() OVER (ORDER BY timestamp) AS rn"
                f"  {base}"
                ") WHERE (rn - 1) % ? = 0 ORDER BY rn",
                (*params, step),
            ).fetchall()
        return [dict(r) for r in rows]

    @classmethod
    def ping_stats_between(cls, host: str, start: datetime, end: datetime) -> dict:
        """Agregados de un host en el rango, calculados en SQL."""
        with cls._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) AS total,"
                "       COALESCE(SUM(ping_ok), 0) AS ok_count "
                "FROM ping_metrics "
                "WHERE host=? AND timestamp BETWEEN ? AND ?",
                (host, start.isoformat(), end.isoformat()),
            ).fetchone()
        total = row["total"] or 0
        ok_count = row["ok_count"] or 0
        return {
            "total": total,
            "ok_count": ok_count,
            "uptime_pct": (ok_count / total * 100) if total else 0.0,
        }

    @classmethod
    def ping_downs_between(cls, host: str, start: datetime, end: datetime) -> int:
        """Transiciones OK→fallo de un host en el rango (LAG en SQL)."""
        with cls._conn() as c:
            row = c.execute(
                "SELECT COUNT(*) AS n FROM ("
                "  SELECT ping_ok,"
                "         LAG(ping_ok) OVER (ORDER BY timestamp, id) AS prev"
                "  FROM ping_metrics"
                "  WHERE host=? AND timestamp BETWEEN ? AND ?"
                ") WHERE prev=1 AND ping_ok=0",
                (host, start.isoformat(), end.isoformat()),
            ).fetchone()
        return row["n"] if row else 0

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