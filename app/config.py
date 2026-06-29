"""Environment-driven configuration for the Pulse Dashboard.

Loads optional settings from a local .env file and exposes typed accessors with
sensible defaults so the application runs without any configuration.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def db_path() -> Path:
    """Return the path to the SQLite database file."""
    return Path(os.getenv("PULSE_DB_PATH", "pulse.db"))


def host() -> str:
    """Return the host the server is expected to bind to."""
    return os.getenv("PULSE_HOST", "127.0.0.1")


def port() -> int:
    """Return the port the server is expected to bind to."""
    return int(os.getenv("PULSE_PORT", "8000"))


def base_url() -> str:
    """Return the base URL used by the simulator to reach the server."""
    return f"http://{host()}:{port()}"
