"""
CSV Manager — convenience helpers for reading/writing CSV files via the Store.
==============================================================================
All simulation data lives under ``data/simulations/{sim_id}/`` in the backing
store (DigitalOcean Spaces in production, local filesystem in development).
"""

from __future__ import annotations

import csv
import io
from typing import Sequence

from app.storage.store import get_store


def _key(sim_id: str, filename: str) -> str:
    """Build the store key for a simulation file."""
    return f"data/simulations/{sim_id}/{filename}"


def read_csv_rows(sim_id: str, filename: str) -> list[dict[str, str]]:
    """Read a CSV file from the store and return rows as a list of dicts."""
    store = get_store()
    key = _key(sim_id, filename)
    if not store.exists(key):
        return []
    text = store.read_text(key)
    return list(csv.DictReader(io.StringIO(text)))


def write_csv(
    sim_id: str,
    filename: str,
    fieldnames: Sequence[str],
    rows: Sequence[dict[str, str]],
) -> None:
    """Write rows to a CSV file in the store."""
    store = get_store()
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    store.write_text(_key(sim_id, filename), buf.getvalue())


def csv_exists(sim_id: str, filename: str) -> bool:
    """Return True if the CSV file exists in the store."""
    store = get_store()
    return store.exists(_key(sim_id, filename))


def store_exists() -> bool:
    """Return True if the backing store is reachable."""
    try:
        get_store()
        return True
    except Exception:
        return False


def write_text(sim_id: str, filename: str, text: str) -> None:
    """Write arbitrary text to a file in the store."""
    store = get_store()
    store.write_text(_key(sim_id, filename), text)
