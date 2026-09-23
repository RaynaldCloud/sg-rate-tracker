"""SQLite storage for scraped interest rates."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import List, Optional

from scrapers.base_scraper import Rate

DB_PATH = Path(__file__).resolve().parent.parent / "rates.db"


@contextmanager
def get_connection():
    """Open a connection, commit on success, and always close it."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """Create the rates table and index if they don't exist yet."""
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rates (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                bank          TEXT    NOT NULL,
                product       TEXT    NOT NULL,
                rate_percent  REAL    NOT NULL,
                tenure_months INTEGER,
                min_deposit   REAL,
                scraped_at    TEXT    NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rates_lookup
            ON rates (bank, product, tenure_months, scraped_at)
        """)


def save_rates(rates: List[Rate]) -> int:
    """Insert scraped rates and return how many were saved."""
    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO rates
               (bank, product, rate_percent, tenure_months, min_deposit, scraped_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [
                (r.bank, r.product, r.rate_percent, r.tenure_months,
                 r.min_deposit, r.scraped_at.isoformat())
                for r in rates
            ],
        )
    return len(rates)


def get_latest_rates() -> List[dict]:
    """Return the most recent rate for each bank, product and tenure."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT r.*
            FROM rates r
            JOIN (
                SELECT bank, product, tenure_months, MAX(scraped_at) AS latest
                FROM rates
                GROUP BY bank, product, tenure_months
            ) l
              ON r.bank = l.bank
             AND r.product = l.product
             AND r.tenure_months IS l.tenure_months
             AND r.scraped_at = l.latest
            ORDER BY r.rate_percent DESC
        """).fetchall()
    return [dict(row) for row in rows]


def get_rate_history(bank: str, product: str,
                     tenure_months: Optional[int] = None) -> List[dict]:
    """Return every recorded rate for one product, oldest first."""
    with get_connection() as conn:
        rows = conn.execute(
            """SELECT * FROM rates
               WHERE bank = ? AND product = ? AND tenure_months IS ?
               ORDER BY scraped_at""",
            (bank, product, tenure_months),
        ).fetchall()
    return [dict(row) for row in rows]