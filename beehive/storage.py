"""SQLite journal: reproducible signal history, daily equity anchors, kill switch."""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3


class Store:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS signals (
              id TEXT PRIMARY KEY, created_at TEXT NOT NULL, symbol TEXT NOT NULL,
              side TEXT NOT NULL, candle_time TEXT NOT NULL, status TEXT NOT NULL,
              detail TEXT NOT NULL DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS equity_day (
              day TEXT PRIMARY KEY, initial_equity REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS kv (
              key TEXT PRIMARY KEY, value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
              key TEXT PRIMARY KEY, created_at TEXT NOT NULL
            );
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(str(self.path), timeout=15)
        try:
            db.execute("PRAGMA journal_mode=WAL")
            yield db
            db.commit()
        finally:
            db.close()

    def start_equity(self, equity):
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        with self.connection() as db:
            db.execute("INSERT OR IGNORE INTO equity_day (day, initial_equity) VALUES (?,?)",
                       (day, equity))
            row = db.execute("SELECT initial_equity FROM equity_day WHERE day=?", (day,)).fetchone()
            return float(row[0])

    def claim_signal(self, signal):
        with self.connection() as db:
            result = db.execute(
                "INSERT OR IGNORE INTO signals (id,created_at,symbol,side,candle_time,status) VALUES (?,?,?,?,?,?)",
                (signal.signal_id, datetime.now(timezone.utc).isoformat(),
                 signal.symbol, signal.side, signal.candle_time, "claimed"),
            )
            return result.rowcount == 1

    def result(self, signal_id, status, detail=""):
        with self.connection() as db:
            db.execute("UPDATE signals SET status=?,detail=? WHERE id=?",
                       (status, str(detail)[:1000], signal_id))

    def set(self, key, value):
        with self.connection() as db:
            db.execute("INSERT INTO kv(key,value) VALUES (?,?) "
                       "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))

    def get(self, key, default=""):
        with self.connection() as db:
            row = db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
            return row[0] if row else default

    def halted(self):
        return self.get("halted", "1") == "1"

    def set_halted(self, halted=True):
        self.set("halted", "1" if halted else "0")

    def claim_message(self, key):
        with self.connection() as db:
            result = db.execute("INSERT OR IGNORE INTO messages(key,created_at) VALUES (?,?)",
                                (key, datetime.now(timezone.utc).isoformat()))
            return result.rowcount == 1

    def recent_signals(self, limit=10):
        with self.connection() as db:
            return db.execute(
                "SELECT created_at,symbol,side,status,detail FROM signals ORDER BY created_at DESC LIMIT ?",
                (limit,)
            ).fetchall()
