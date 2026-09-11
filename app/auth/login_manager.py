"""Simulation registry helpers for the negotiation sim."""

from __future__ import annotations

import csv
import io


SIMULATIONS_REGISTRY_KEY = "admin/simulations.csv"


def _load_simulation_registry() -> list[dict[str, str]]:
    from app.storage.store import get_store
    store = get_store()
    if not store.exists(SIMULATIONS_REGISTRY_KEY):
        return []
    text = store.read_text(SIMULATIONS_REGISTRY_KEY)
    return list(csv.DictReader(io.StringIO(text)))


def get_active_simulation_ids() -> list[str]:
    rows = _load_simulation_registry()
    active = []
    for r in rows:
        status = r.get("status", "").upper()
        if status in ("CREATED", "STARTED"):
            active.append(r.get("simulation_id", ""))
    return [s for s in active if s]


def get_all_simulations() -> list[dict[str, str]]:
    return _load_simulation_registry()
