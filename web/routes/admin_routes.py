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
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from app.auth.password_manager import hash_password
from app.auth.login_manager import get_all_simulations, get_active_simulation_ids
from app.core.scenarios import SCENARIOS, get_scenario
from app.core.groups import (
    list_groups, get_group, create_group, delete_group, update_group,
    list_members, add_member, remove_member, set_lead, auto_assign_groups,
)
from app.core.sessions import (
    list_sessions, get_session as get_class_session, create_session as create_class_session,
    update_session as update_class_session, generate_pairings, update_pairing,
    list_pairings, start_session as start_class_session,
    advance_round, end_session, get_timer, get_remaining_seconds,
    pause_timer, resume_timer, extend_timer, get_active_session,
)
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
               "current_round", "started_at", "completed_at",
               "activity_mode", "session_id", "group_id", "counterpart_type", "role"], [])
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
              ["rank", "user_id", "scenario_id", "average_score", "attempt_count",
               "percentile", "activity_mode"], [])
    write_csv(sim_id, "aliases.csv", ["user_id", "alias"], [])

    # v1.2 tables
    write_csv(sim_id, "groups.csv",
              ["group_id", "sim_id", "name", "scenario_id", "created_by", "created_at"], [])
    write_csv(sim_id, "group_members.csv",
              ["member_id", "group_id", "user_id", "is_lead", "joined_at"], [])
    write_csv(sim_id, "class_sessions.csv",
              ["session_id", "sim_id", "scenario_id", "counterpart_mode",
               "round_duration_minutes", "status", "current_round",
               "created_by", "started_at", "completed_at", "created_at"], [])
    write_csv(sim_id, "session_pairings.csv",
              ["pairing_id", "session_id", "student_group_id", "partner_group_id",
               "counterpart_type", "student_role", "partner_role"], [])
    write_csv(sim_id, "round_timers.csv",
              ["timer_id", "session_id", "round_number", "started_at",
               "duration_seconds", "paused_at", "extended_seconds"], [])

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


# ── Group Management ──────────────────────────────────────────────────

@router.get("/groups", response_class=HTMLResponse)
async def groups_page(request: Request):
    from web.main import templates
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    groups = list_groups(sim_id)
    users = read_csv_rows(sim_id, "users.csv")
    students = [u for u in users if u.get("role") == "USER"]

    # Enrich groups with member info
    for group in groups:
        members = list_members(sim_id, group["group_id"])
        member_details = []
        for m in members:
            user = next((u for u in users if u["user_id"] == m["user_id"]), {})
            member_details.append({
                **m,
                "username": user.get("username", ""),
                "first_name": user.get("first_name", ""),
                "last_name": user.get("last_name", ""),
            })
        group["members"] = member_details
        group["member_count"] = len(members)

    return templates.TemplateResponse("admin/groups.html", {
        "request": request,
        "session": session,
        "groups": groups,
        "students": students,
        "scenarios": [s for s in SCENARIOS if s["status"] == "ACTIVE"],
    })


@router.post("/groups/create")
async def create_group_route(
    request: Request,
    name: str = Form(...),
    scenario_id: str = Form(...),
):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    create_group(session["sim_id"], name, scenario_id, session["user_id"])
    return RedirectResponse(url="/admin/groups", status_code=302)


@router.post("/groups/{group_id}/delete")
async def delete_group_route(request: Request, group_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    delete_group(session["sim_id"], group_id)
    return RedirectResponse(url="/admin/groups", status_code=302)


@router.post("/groups/{group_id}/members/add")
async def add_member_route(
    request: Request,
    group_id: str,
    user_id: str = Form(...),
    is_lead: str = Form("false"),
):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    add_member(session["sim_id"], group_id, user_id, is_lead=(is_lead == "true"))
    return RedirectResponse(url="/admin/groups", status_code=302)


@router.post("/groups/{group_id}/members/{user_id}/remove")
async def remove_member_route(request: Request, group_id: str, user_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    remove_member(session["sim_id"], group_id, user_id)
    return RedirectResponse(url="/admin/groups", status_code=302)


@router.post("/groups/{group_id}/lead/{user_id}")
async def set_lead_route(request: Request, group_id: str, user_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    set_lead(session["sim_id"], group_id, user_id)
    return RedirectResponse(url="/admin/groups", status_code=302)


@router.post("/groups/auto-assign")
async def auto_assign_route(
    request: Request,
    scenario_id: str = Form(...),
    group_size: str = Form("4"),
):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    auto_assign_groups(
        session["sim_id"], scenario_id, int(group_size), session["user_id"]
    )
    return RedirectResponse(url="/admin/groups", status_code=302)


# ── Class Session Management ─────────────────────────────────────────

@router.get("/sessions", response_class=HTMLResponse)
async def sessions_page(request: Request):
    from web.main import templates
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    sessions = list_sessions(sim_id)

    return templates.TemplateResponse("admin/sessions.html", {
        "request": request,
        "session": session,
        "sessions": sessions,
        "scenarios": [s for s in SCENARIOS if s["status"] == "ACTIVE"],
    })


@router.post("/sessions/create")
async def create_session_route(
    request: Request,
    scenario_id: str = Form(...),
    counterpart_mode: str = Form("ALL_HA"),
    round_duration: str = Form("10"),
):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    new_session = create_class_session(
        session["sim_id"], scenario_id, counterpart_mode,
        int(round_duration), session["user_id"],
    )
    return RedirectResponse(
        url=f"/admin/sessions/{new_session['session_id']}/pairings",
        status_code=302,
    )


@router.get("/sessions/{session_id}/pairings", response_class=HTMLResponse)
async def pairings_page(request: Request, session_id: str):
    from web.main import templates
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    class_session = get_class_session(sim_id, session_id)
    if not class_session:
        return RedirectResponse(url="/admin/sessions", status_code=302)

    pairings = list_pairings(sim_id, session_id)
    groups = list_groups(sim_id)
    scenario_groups = [g for g in groups if g.get("scenario_id") == class_session["scenario_id"]]

    # Enrich pairings with group names
    group_map = {g["group_id"]: g["name"] for g in groups}
    for p in pairings:
        p["student_group_name"] = group_map.get(p.get("student_group_id"), "Unknown")
        p["partner_group_name"] = group_map.get(p.get("partner_group_id"), "—")

    return templates.TemplateResponse("admin/pairings.html", {
        "request": request,
        "session": session,
        "class_session": class_session,
        "pairings": pairings,
        "groups": scenario_groups,
    })


@router.post("/sessions/{session_id}/generate-pairings")
async def generate_pairings_route(request: Request, session_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    class_session = get_class_session(sim_id, session_id)
    if not class_session:
        return RedirectResponse(url="/admin/sessions", status_code=302)

    groups = list_groups(sim_id)
    scenario_groups = [g for g in groups if g.get("scenario_id") == class_session["scenario_id"]]
    group_ids = [g["group_id"] for g in scenario_groups]

    generate_pairings(sim_id, session_id, group_ids)
    return RedirectResponse(url=f"/admin/sessions/{session_id}/pairings", status_code=302)


@router.post("/sessions/{session_id}/pairings/{pairing_id}/update")
async def update_pairing_route(
    request: Request,
    session_id: str,
    pairing_id: str,
    counterpart_type: str = Form(...),
):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    update_pairing(session["sim_id"], pairing_id, counterpart_type=counterpart_type)
    return RedirectResponse(url=f"/admin/sessions/{session_id}/pairings", status_code=302)


@router.post("/sessions/{session_id}/start")
async def start_session_route(request: Request, session_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    start_class_session(session["sim_id"], session_id)
    return RedirectResponse(url=f"/admin/sessions/{session_id}/control", status_code=302)


# ── Session Control (Live Dashboard) ─────────────────────────────────

@router.get("/sessions/{session_id}/control", response_class=HTMLResponse)
async def session_control(request: Request, session_id: str):
    from web.main import templates
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    class_session = get_class_session(sim_id, session_id)
    if not class_session:
        return RedirectResponse(url="/admin/sessions", status_code=302)

    pairings = list_pairings(sim_id, session_id)
    groups_list = list_groups(sim_id)
    group_map = {g["group_id"]: g["name"] for g in groups_list}

    current_round = int(class_session.get("current_round", "0"))
    timer = get_timer(sim_id, session_id, current_round) if current_round > 0 else None
    remaining = get_remaining_seconds(timer) if timer else 0

    # Get submission status per group
    attempts = read_csv_rows(sim_id, "attempts.csv")
    submissions = read_csv_rows(sim_id, "submissions.csv")

    pairing_statuses = []
    for p in pairings:
        status = {**p, "student_group_name": group_map.get(p.get("student_group_id"), "?"),
                  "partner_group_name": group_map.get(p.get("partner_group_id"), "—")}

        # Check if student group submitted this round
        student_attempt = next(
            (a for a in attempts
             if a.get("session_id") == session_id
             and a.get("group_id") == p.get("student_group_id")),
            None,
        )
        status["student_submitted"] = False
        if student_attempt:
            round_subs = [s for s in submissions
                          if s.get("attempt_id") == student_attempt.get("attempt_id")
                          and s.get("round_number") == str(current_round)]
            status["student_submitted"] = len(round_subs) > 0

        # Check partner group
        status["partner_submitted"] = False
        if p.get("partner_group_id"):
            partner_attempt = next(
                (a for a in attempts
                 if a.get("session_id") == session_id
                 and a.get("group_id") == p.get("partner_group_id")),
                None,
            )
            if partner_attempt:
                round_subs = [s for s in submissions
                              if s.get("attempt_id") == partner_attempt.get("attempt_id")
                              and s.get("round_number") == str(current_round)]
                status["partner_submitted"] = len(round_subs) > 0

        pairing_statuses.append(status)

    return templates.TemplateResponse("admin/session_control.html", {
        "request": request,
        "session": session,
        "class_session": class_session,
        "pairings": pairing_statuses,
        "current_round": current_round,
        "remaining_seconds": remaining,
        "timer": timer,
    })


@router.post("/sessions/{session_id}/advance")
async def advance_round_route(request: Request, session_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    result = advance_round(session["sim_id"], session_id)
    if result and result.get("status") == "COMPLETED":
        return RedirectResponse(url=f"/admin/sessions", status_code=302)
    return RedirectResponse(url=f"/admin/sessions/{session_id}/control", status_code=302)


@router.post("/sessions/{session_id}/end")
async def end_session_route(request: Request, session_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    end_session(session["sim_id"], session_id)
    return RedirectResponse(url="/admin/sessions", status_code=302)


@router.post("/sessions/{session_id}/timer/pause")
async def pause_timer_route(request: Request, session_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    class_session = get_class_session(sim_id, session_id)
    if class_session:
        current_round = int(class_session.get("current_round", "0"))
        pause_timer(sim_id, session_id, current_round)
    return RedirectResponse(url=f"/admin/sessions/{session_id}/control", status_code=302)


@router.post("/sessions/{session_id}/timer/resume")
async def resume_timer_route(request: Request, session_id: str):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    class_session = get_class_session(sim_id, session_id)
    if class_session:
        current_round = int(class_session.get("current_round", "0"))
        resume_timer(sim_id, session_id, current_round)
    return RedirectResponse(url=f"/admin/sessions/{session_id}/control", status_code=302)


@router.post("/sessions/{session_id}/timer/extend")
async def extend_timer_route(
    request: Request,
    session_id: str,
    extra_minutes: str = Form("5"),
):
    session = _require_admin(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    class_session = get_class_session(sim_id, session_id)
    if class_session:
        current_round = int(class_session.get("current_round", "0"))
        extend_timer(sim_id, session_id, current_round, int(extra_minutes) * 60)
    return RedirectResponse(url=f"/admin/sessions/{session_id}/control", status_code=302)


# ── Polling endpoint (JSON for real-time status) ─────────────────────

@router.get("/sessions/{session_id}/status")
async def session_status_json(request: Request, session_id: str):
    session = get_session(request)
    if not session:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    sim_id = session["sim_id"]
    class_session = get_class_session(sim_id, session_id)
    if not class_session:
        return JSONResponse({"error": "not_found"}, status_code=404)

    current_round = int(class_session.get("current_round", "0"))
    timer = get_timer(sim_id, session_id, current_round) if current_round > 0 else None
    remaining = get_remaining_seconds(timer) if timer else 0
    paused = bool(timer and timer.get("paused_at"))

    # Submission statuses
    pairings = list_pairings(sim_id, session_id)
    attempts = read_csv_rows(sim_id, "attempts.csv")
    submissions = read_csv_rows(sim_id, "submissions.csv")

    group_statuses = {}
    for p in pairings:
        for gid_key in ("student_group_id", "partner_group_id"):
            gid = p.get(gid_key, "")
            if not gid:
                continue
            attempt = next(
                (a for a in attempts
                 if a.get("session_id") == session_id and a.get("group_id") == gid),
                None,
            )
            submitted = False
            if attempt:
                round_subs = [s for s in submissions
                              if s.get("attempt_id") == attempt.get("attempt_id")
                              and s.get("round_number") == str(current_round)]
                submitted = len(round_subs) > 0
            group_statuses[gid] = {"submitted": submitted}

    return JSONResponse({
        "status": class_session["status"],
        "current_round": current_round,
        "remaining_seconds": remaining,
        "paused": paused,
        "groups": group_statuses,
    })
