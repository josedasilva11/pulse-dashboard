"""Seed the Pulse Dashboard SQLite database with sample data.

Run as a module (python -m app.seed) to create the schema and populate it with
a spread of historical orders and bookings so the dashboard is populated on
first load.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.config import db_path
from app.database import get_connection, init_db

ITEMS = [
    ("Espresso", 2.5, 4.0),
    ("Cappuccino", 3.0, 5.0),
    ("Croissant", 2.0, 3.5),
    ("Avocado Toast", 7.0, 11.0),
    ("House Lunch", 9.0, 16.0),
    ("Cold Brew", 3.5, 6.0),
]
BOOKING_SLOTS = ["Table for 2", "Table for 4", "Private Room", "Patio Seat"]


def seed(count: int = 220) -> None:
    """Create the schema and insert a batch of sample events.

    Args:
        count: Number of events to generate across the last 12 hours.
    """
    init_db()
    conn = get_connection()
    now = datetime.now(timezone.utc)
    rows: list[tuple[str, str, float, str]] = []
    for _ in range(count):
        minutes_ago = random.randint(0, 12 * 60)
        ts = (now - timedelta(minutes=minutes_ago)).isoformat()
        if random.random() < 0.8:
            name, low, high = random.choice(ITEMS)
            amount = round(random.uniform(low, high), 2)
            rows.append(("order", name, amount, ts))
        else:
            slot = random.choice(BOOKING_SLOTS)
            amount = round(random.uniform(15.0, 60.0), 2)
            rows.append(("booking", slot, amount, ts))
    try:
        conn.executemany(
            "INSERT INTO events (kind, item, amount, created_at) VALUES (?, ?, ?, ?)",
            rows,
        )
        conn.commit()
    finally:
        conn.close()
    print(f"Seeded {len(rows)} events into {db_path()}")


if __name__ == "__main__":
    seed()
