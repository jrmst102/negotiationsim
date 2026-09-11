"""
Access routes — automatic admin sessions and DecisionLab SSO.
=============================================================
"""

from __future__ import annotations

import logging
import os
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeSerializer

import jwt

from app.auth.login_manager import get_active_simulation_ids
from app.auth.password_manager import hash_password
from app.data.csv_manager import read_csv_rows, write_csv, csv_exists

router = APIRouter()
logger = logging.getLogger(__name__)

SESSION_SECRET = os.environ.get("SESSION_SECRET", "negotiation-sim-dev-secret")
TOOL_SSO_SECRET = os.environ.get("TOOL_SSO_SECRET", "tool-sso-secret-change-me")
COOKIE_NAME = "neg_session"
_signer = URLSafeSerializer(SESSION_SECRET, salt="neg-session")


def get_session(request: Request) -> dict | None:
    """Read a signed SSO session or provide the active simulation's admin."""
    raw = request.cookies.get(COOKIE_NAME)
    if raw:
        try:
            return _signer.loads(raw)
        except Exception:
            pass

    for sim_id in get_active_simulation_ids():
        if not csv_exists(sim_id, "users.csv"):
            continue
        for user in read_csv_rows(sim_id, "users.csv"):
            if user.get("role", "").upper() == "ADMIN":
                return {
                    "username": user.get("username", ""),
                    "user_id": user.get("user_id", ""),
                    "role": "ADMIN",
                    "sim_id": sim_id,
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "dashboard": "admin",
                }
    return None


def set_session_cookie(response, session_data: dict):
    """Set a signed session cookie on the response."""
    token = _signer.dumps(session_data)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,
    )
    return response


@router.get("/")
async def root(request: Request):
    session = get_session(request)
    if session:
        if session.get("role") == "ADMIN":
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/dashboard", status_code=302)
    return RedirectResponse(url="/admin", status_code=302)


@router.get("/login")
async def legacy_login_redirect():
    return RedirectResponse(url="/", status_code=302)


# ── SSO from DecisionLab ──────────────────────────────────────────────

USER_FIELDS = ["user_id", "username", "password_hash", "role", "first_name", "last_name", "email"]


def _find_or_create_sso_user(email: str, role: str) -> tuple[str, dict[str, str]]:
    """Find user by email across active sims, or create in the first active sim.

    Returns (sim_id, user_row).
    """
    active_ids = get_active_simulation_ids()

    # Search existing sims for the user by email
    for sim_id in active_ids:
        if not csv_exists(sim_id, "users.csv"):
            continue
        rows = read_csv_rows(sim_id, "users.csv")
        for row in rows:
            if row.get("email", "").strip().lower() == email.strip().lower():
                return sim_id, row

    # User not found — create in first active sim (or demo)
    target_sim = active_ids[0] if active_ids else "sim_demo"

    user_id = f"usr_sso_{uuid.uuid4().hex[:8]}"
    local_part = email.split("@")[0] if "@" in email else email
    sim_role = "ADMIN" if role == "ADMIN" else "USER"

    new_user = {
        "user_id": user_id,
        "username": local_part,
        "password_hash": hash_password(uuid.uuid4().hex),  # random; SSO users don't need a password
        "role": sim_role,
        "first_name": local_part.replace(".", " ").title(),
        "last_name": "",
        "email": email,
    }

    # Append to existing users
    existing = read_csv_rows(target_sim, "users.csv") if csv_exists(target_sim, "users.csv") else []
    existing.append(new_user)
    write_csv(target_sim, "users.csv", USER_FIELDS, existing)

    return target_sim, new_user


@router.get("/auth/sso")
async def sso_login(request: Request, token: str = ""):
    """Verify a DecisionLab SSO JWT and establish a session."""
    if not token:
        return RedirectResponse(url="/login", status_code=302)

    try:
        payload = jwt.decode(
            token,
            TOOL_SSO_SECRET,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        logger.warning("SSO token expired")
        return RedirectResponse(url="/login", status_code=302)
    except jwt.InvalidTokenError:
        logger.warning("Invalid SSO token")
        return RedirectResponse(url="/login", status_code=302)

    email = payload.get("email", "")
    role = payload.get("role", "USER")

    if not email:
        return RedirectResponse(url="/login", status_code=302)

    try:
        sim_id, user_row = _find_or_create_sso_user(email, role)
    except Exception:
        logger.exception("SSO user provisioning failed")
        return RedirectResponse(url="/login", status_code=302)

    raw_role = user_row.get("role", "USER").upper()
    dashboard = "admin" if raw_role == "ADMIN" else "student"

    session_data = {
        "username": user_row.get("username", ""),
        "user_id": user_row.get("user_id", ""),
        "role": raw_role,
        "sim_id": sim_id,
        "first_name": user_row.get("first_name", ""),
        "last_name": user_row.get("last_name", ""),
        "dashboard": dashboard,
    }

    redirect_url = "/admin" if dashboard == "admin" else "/dashboard"
    response = RedirectResponse(url=redirect_url, status_code=302)
    return set_session_cookie(response, session_data)
