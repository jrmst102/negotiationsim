"""
Login Manager — multi-simulation authentication for the negotiation sim.
=========================================================================
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field

from app.auth.password_manager import verify_password
from app.data.csv_manager import read_csv_rows, csv_exists, store_exists

logger = logging.getLogger(__name__)

SIMULATIONS_REGISTRY_KEY = "admin/simulations.csv"


@dataclass(frozen=True)
class AuthUser:
    """Authenticated user record."""
    username: str
    user_id: str
    role: str           # USER or ADMIN
    sim_id: str
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    dashboard: str = ""  # "student" or "admin"


@dataclass
class LoginResult:
    success: bool
    user: AuthUser | None = None
    sim_ids: list[str] = field(default_factory=list)
    needs_sim_picker: bool = False
    message: str = ""


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


def login(username: str, password: str) -> LoginResult:
    """Authenticate username/password across all active simulations."""
    if not username or not password:
        return LoginResult(success=False, message="Username and password are required.")

    key_lower = username.strip().lower()
    active_ids = get_active_simulation_ids()

    if not active_ids:
        return LoginResult(success=False, message="No active simulations available.")

    matches: list[tuple[str, dict[str, str]]] = []
    for sim_id in active_ids:
        if not csv_exists(sim_id, "users.csv"):
            continue
        rows = read_csv_rows(sim_id, "users.csv")
        for row in rows:
            if row.get("username", "").strip().lower() == key_lower:
                matches.append((sim_id, row))
                break

    if not matches:
        return LoginResult(success=False, message="Invalid username or password.")

    sim_id, user_row = matches[0]

    password_hash = user_row.get("password_hash", "")
    if not verify_password(password, password_hash):
        return LoginResult(success=False, message="Invalid username or password.")

    raw_role = user_row.get("role", "USER").upper()
    role = raw_role if raw_role in ("ADMIN", "USER") else "USER"
    dashboard = "admin" if role == "ADMIN" else "student"

    user = AuthUser(
        username=user_row.get("username", username),
        user_id=user_row.get("user_id", ""),
        role=role,
        sim_id=sim_id,
        first_name=user_row.get("first_name", ""),
        last_name=user_row.get("last_name", ""),
        email=user_row.get("email", ""),
        dashboard=dashboard,
    )

    sim_ids = [m[0] for m in matches]
    needs_picker = len(sim_ids) > 1 and dashboard == "admin"

    return LoginResult(
        success=True,
        user=user,
        sim_ids=sim_ids,
        needs_sim_picker=needs_picker,
        message=f"Welcome, {user.first_name or user.username}",
    )
