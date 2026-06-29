"""Event simulator for the Pulse Dashboard.

Posts a stream of realistic orders and bookings to the running server so the
dashboard visibly updates in real time. Stop with Ctrl+C.
"""

from __future__ import annotations

import random
import sys
import time

import httpx

from app.config import base_url

ITEMS = [
    ("Espresso", 2.5, 4.0),
    ("Cappuccino", 3.0, 5.0),
    ("Croissant", 2.0, 3.5),
    ("Avocado Toast", 7.0, 11.0),
    ("House Lunch", 9.0, 16.0),
    ("Cold Brew", 3.5, 6.0),
]
BOOKING_SLOTS = ["Table for 2", "Table for 4", "Private Room", "Patio Seat"]


def build_event() -> dict[str, object]:
    """Generate a random order or booking payload."""
    if random.random() < 0.8:
        name, low, high = random.choice(ITEMS)
        return {"kind": "order", "item": name, "amount": round(random.uniform(low, high), 2)}
    slot = random.choice(BOOKING_SLOTS)
    return {"kind": "booking", "item": slot, "amount": round(random.uniform(15.0, 60.0), 2)}


def run() -> None:
    """Continuously post events at a randomised interval."""
    url = f"{base_url()}/api/events"
    print(f"Posting live events to {url} (Ctrl+C to stop)")
    with httpx.Client(timeout=5.0) as client:
        while True:
            event = build_event()
            try:
                client.post(url, json=event)
                print(f"sent {event['kind']:8} {event['item']:14} {event['amount']:.2f}")
            except httpx.HTTPError as exc:
                print(f"request failed: {exc}", file=sys.stderr)
            time.sleep(random.uniform(0.8, 2.5))


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\nStopped.")
