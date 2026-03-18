"""
Admin routes — instructor views, configuration, user management.
=================================================================
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.auth.password_manager import hash_password
from app.auth.login_manager import get_all_simulations, get_active_simulation_ids
from app.core.scenarios import SCENARIOS, get_scenario
from app.data.csv_manager import read_csv_rows, write_csv, csv_exists, store_exists, write_text
from web.routes.auth_routes import get_session

router = APIRouter(prefix="/admin")


def _require_admin(request: Request) -> dict | None:
    session = get_session(request)
    if not session or session.get("role") != "ADMIN":
        return None
    return session


# ── Admin Dashboard ───────────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    from web.main import templates
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]

    # Get simulation info
    users = read_csv_rows(sim_id, "users.csv")
    students = [u for u in users if u.get("role", "").upper() == "USER"]
    attempts = read_csv_rows(sim_id, "attempts.csv")
    scores = read_csv_rows(sim_id, "scores.csv")

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "session": session,
        "sim_id": sim_id,
        "student_count": len(students),
        "attempt_count": len(attempts),
        "score_count": len(scores),
        "scenarios": SCENARIOS,
    })


# ── Student Scores ───────────────────────────────────────────────────

@router.get("/scores", response_class=HTMLResponse)
async def admin_scores(request: Request):
    from web.main import templates
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]

    users = read_csv_rows(sim_id, "users.csv")
    aliases = read_csv_rows(sim_id, "aliases.csv")
    alias_map = {a["user_id"]: a["alias"] for a in aliases}

    scores = read_csv_rows(sim_id, "scores.csv")
    attempts = read_csv_rows(sim_id, "attempts.csv")

    # Build student table
    students = []
    for user in users:
        if user.get("role", "").upper() != "USER":
            continue
        uid = user["user_id"]
        user_scores = [s for s in scores if s.get("user_id") == uid]
        user_attempts = [a for a in attempts if a.get("user_id") == uid]

        avg_score = 0
        if user_scores:
            avg_score = sum(float(s["composite_score"]) for s in user_scores) / len(user_scores)

        students.append({
            "user_id": uid,
            "username": user.get("username", ""),
            "first_name": user.get("first_name", ""),
            "last_name": user.get("last_name", ""),
            "alias": alias_map.get(uid, "—"),
            "average_score": round(avg_score, 1),
            "attempt_count": len(user_attempts),
            "completed_count": len([a for a in user_attempts if a.get("status") == "COMPLETED"]),
        })

    students.sort(key=lambda s: s["average_score"], reverse=True)

    return templates.TemplateResponse("admin/scores.html", {
        "request": request,
        "session": session,
        "students": students,
    })


# ── Export CSV ────────────────────────────────────────────────────────

@router.get("/scores/export")
async def export_scores(request: Request):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    users = read_csv_rows(sim_id, "users.csv")
    aliases = read_csv_rows(sim_id, "aliases.csv")
    alias_map = {a["user_id"]: a["alias"] for a in aliases}
    scores = read_csv_rows(sim_id, "scores.csv")

    # Build export data
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Username", "Alias", "Scenario", "Score", "Date"])

    user_map = {u["user_id"]: u for u in users}
    for s in scores:
        user = user_map.get(s["user_id"], {})
        name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        writer.writerow([
            name,
            user.get("username", ""),
            alias_map.get(s["user_id"], ""),
            s.get("scenario_id", ""),
            s.get("composite_score", ""),
            s.get("scored_at", ""),
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=negotiation_scores.csv"},
    )


# ── Manage Users ──────────────────────────────────────────────────────

@router.get("/users", response_class=HTMLResponse)
async def manage_users(request: Request):
    from web.main import templates
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    users = read_csv_rows(sim_id, "users.csv")

    return templates.TemplateResponse("admin/users.html", {
        "request": request,
        "session": session,
        "users": users,
        "sim_id": sim_id,
    })


@router.post("/users/add")
async def add_user(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    first_name: str = Form(""),
    last_name: str = Form(""),
    role: str = Form("USER"),
):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    users = read_csv_rows(sim_id, "users.csv")

    # Check for duplicate username
    if any(u["username"].lower() == username.lower() for u in users):
        return RedirectResponse(url="/admin/users?error=duplicate", status_code=302)

    new_user = {
        "user_id": f"usr_{uuid.uuid4().hex[:12]}",
        "username": username,
        "password_hash": hash_password(password),
        "role": role.upper(),
        "first_name": first_name,
        "last_name": last_name,
        "email": "",
    }

    users.append(new_user)
    fieldnames = ["user_id", "username", "password_hash", "role", "first_name", "last_name", "email"]
    write_csv(sim_id, "users.csv", fieldnames, users)

    return RedirectResponse(url="/admin/users", status_code=302)


# ── Setup Simulation ─────────────────────────────────────────────────

@router.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    from web.main import templates
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    simulations = get_all_simulations()

    return templates.TemplateResponse("admin/setup.html", {
        "request": request,
        "session": session,
        "simulations": simulations,
    })


@router.post("/setup/create")
async def create_simulation(request: Request, sim_name: str = Form(...)):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = f"sim_{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    # Create simulation registry entry
    from app.storage.store import get_store
    store = get_store()

    registry_key = "admin/simulations.csv"
    existing = []
    if store.exists(registry_key):
        existing_text = store.read_text(registry_key)
        existing = list(csv.DictReader(io.StringIO(existing_text)))

    existing.append({
        "simulation_id": sim_id,
        "name": sim_name,
        "status": "CREATED",
        "created_at": now,
        "created_by": session["username"],
    })

    buf = io.StringIO()
    writer = csv.DictWriter(buf,
                            fieldnames=["simulation_id", "name", "status", "created_at", "created_by"],
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(existing)
    store.write_text(registry_key, buf.getvalue())

    # Create admin user in the new simulation
    admin_user = {
        "user_id": session["user_id"] or f"usr_{uuid.uuid4().hex[:12]}",
        "username": session["username"],
        "password_hash": hash_password("admin"),  # Default, admin should change
        "role": "ADMIN",
        "first_name": session.get("first_name", ""),
        "last_name": session.get("last_name", ""),
        "email": "",
    }
    fieldnames = ["user_id", "username", "password_hash", "role", "first_name", "last_name", "email"]
    write_csv(sim_id, "users.csv", fieldnames, [admin_user])

    # Initialize empty data files
    write_csv(sim_id, "attempts.csv",
              ["attempt_id", "user_id", "scenario_id", "mode", "status",
               "current_round", "started_at", "completed_at"], [])
    write_csv(sim_id, "rounds.csv",
              ["round_id", "attempt_id", "round_number", "status", "started_at", "completed_at"], [])
    write_csv(sim_id, "submissions.csv",
              ["submission_id", "attempt_id", "round_number", "submission_number",
               "terms_json", "ai_response_json", "score_json", "submitted_at"], [])
    write_csv(sim_id, "scores.csv",
              ["score_id", "attempt_id", "user_id", "scenario_id",
               "economic_value", "strategic_alignment", "relationship_preservation",
               "information_management", "composite_score", "round_scores_json", "scored_at"], [])
    write_csv(sim_id, "leaderboard.csv",
              ["rank", "user_id", "scenario_id", "average_score", "attempt_count", "percentile"], [])
    write_csv(sim_id, "aliases.csv", ["user_id", "alias"], [])

    return RedirectResponse(url="/admin/setup", status_code=302)


@router.post("/setup/start/{sim_id}")
async def start_simulation(request: Request, sim_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    from app.storage.store import get_store
    store = get_store()

    registry_key = "admin/simulations.csv"
    if not store.exists(registry_key):
        return RedirectResponse(url="/admin/setup", status_code=302)

    text = store.read_text(registry_key)
    rows = list(csv.DictReader(io.StringIO(text)))

    for row in rows:
        if row["simulation_id"] == sim_id:
            row["status"] = "STARTED"

    buf = io.StringIO()
    writer = csv.DictWriter(buf,
                            fieldnames=["simulation_id", "name", "status", "created_at", "created_by"],
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    store.write_text(registry_key, buf.getvalue())

    return RedirectResponse(url="/admin/setup", status_code=302)
