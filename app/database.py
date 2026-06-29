"""SQLite access layer for the Pulse Dashboard.

Manages the database connection, schema creation, event inserts and the
aggregate queries that back the KPI cards and charts.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    item TEXT NOT NULL,
    amount REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
"""


def get_connection(path: Path | None = None) -> sqlite3.Connection:
    """Open a SQLite connection with row access by column name.

    Args:
        path: Optional override for the database file path.

    Returns:
        An open SQLite connection.
    """
    conn = sqlite3.connect(path or db_path())
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path: Path | None = None) -> None:
    """Create the schema if it does not already exist."""
    conn = get_connection(path)
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def insert_event(kind: str, item: str, amount: float, created_at: str | None = None) -> dict[str, Any]:
    """Insert a single event and return the stored row as a dict.

    Args:
        kind: Event type, for example 'order' or 'booking'.
        item: Product or service name associated with the event.
        amount: Monetary value of the event.
        created_at: Optional ISO timestamp; defaults to now in UTC.

    Returns:
        The inserted event as a dictionary.
    """
    ts = created_at or datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO events (kind, item, amount, created_at) VALUES (?, ?, ?, ?)",
            (kind, item, amount, ts),
        )
        conn.commit()
        return {
            "id": cur.lastrowid,
            "kind": kind,
            "item": item,
            "amount": amount,
            "created_at": ts,
        }
    finally:
        conn.close()


def get_kpis() -> dict[str, float | int]:
    """Compute the headline KPIs across all events.

    Returns:
        A dictionary with revenue, order count, booking count and average
        order value.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0) AS revenue,
                COALESCE(SUM(CASE WHEN kind = 'order' THEN 1 ELSE 0 END), 0) AS orders,
                COALESCE(SUM(CASE WHEN kind = 'booking' THEN 1 ELSE 0 END), 0) AS bookings
            FROM events
            """
        ).fetchone()
        revenue = float(row["revenue"])
        orders = int(row["orders"])
        bookings = int(row["bookings"])
        aov = round(revenue / orders, 2) if orders else 0.0
        return {
            "revenue": round(revenue, 2),
            "orders": orders,
            "bookings": bookings,
            "avg_order_value": aov,
        }
    finally:
        conn.close()


def get_revenue_timeseries(buckets: int = 12) -> list[dict[str, Any]]:
    """Return revenue grouped into recent hourly buckets.

    Args:
        buckets: Number of most recent hourly buckets to return.

    Returns:
        A list of {label, revenue} dictionaries ordered oldest to newest.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT
                strftime('%Y-%m-%d %H:00', created_at) AS bucket,
                SUM(amount) AS revenue
            FROM events
            GROUP BY bucket
            ORDER BY bucket DESC
            LIMIT ?
            """,
            (buckets,),
        ).fetchall()
        series = [
            {"label": r["bucket"][11:], "revenue": round(float(r["revenue"]), 2)}
            for r in rows
        ]
        series.reverse()
        return series
    finally:
        conn.close()


def get_top_items(limit: int = 6) -> list[dict[str, Any]]:
    """Return the highest grossing items by total revenue.

    Args:
        limit: Maximum number of items to return.

    Returns:
        A list of {item, revenue} dictionaries ordered by revenue descending.
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT item, SUM(amount) AS revenue
            FROM events
            GROUP BY item
            ORDER BY revenue DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [
            {"item": r["item"], "revenue": round(float(r["revenue"]), 2)}
            for r in rows
        ]
    finally:
        conn.close()


def snapshot() -> dict[str, Any]:
    """Return a full dashboard snapshot in one call."""
    return {
        "kpis": get_kpis(),
        "revenue_series": get_revenue_timeseries(),
        "top_items": get_top_items(),
    }
