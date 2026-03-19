"""
Student routes — scenario dashboard, negotiation flow, leaderboard.
====================================================================
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from app.core.scenarios import SCENARIOS, get_scenario, get_term_fields, get_briefing, get_partner_briefing
from app.core.scoring import compute_round_score, compute_attempt_score, compute_percentile
from app.core.aliases import generate_alias
from app.core.groups import get_user_group, list_members, is_lead
from app.core.sessions import (
    get_active_session, get_session as get_class_session,
    list_pairings, get_pairing_for_group, get_timer, get_remaining_seconds,
)
from app.data.csv_manager import read_csv_rows, write_csv, csv_exists
from app.ai.openai_client import evaluate_submission, evaluate_hh_exchange
from web.routes.auth_routes import get_session

router = APIRouter()


def _require_student(request: Request) -> dict | None:
    """Return session dict or None if not a logged-in student."""
    session = get_session(request)
    if not session:
        return None
    return session


def _ensure_alias(sim_id: str, user_id: str) -> str:
    """Get or create an anonymous alias for the user."""
    rows = read_csv_rows(sim_id, "aliases.csv")
    for row in rows:
        if row.get("user_id") == user_id:
            return row["alias"]

    existing = [r["alias"] for r in rows]
    alias = generate_alias(existing)

    rows.append({"user_id": user_id, "alias": alias})
    write_csv(sim_id, "aliases.csv", ["user_id", "alias"], rows)
    return alias


# ── Scenario Dashboard ────────────────────────────────────────────────

@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    # Get student's attempts for status display
    attempts = read_csv_rows(sim_id, "attempts.csv")
    user_attempts = [a for a in attempts if a.get("user_id") == user_id]

    # Build scenario cards with status
    scenario_cards = []
    for scenario in SCENARIOS:
        card = {**scenario}
        s_attempts = [a for a in user_attempts if a.get("scenario_id") == scenario["id"]]
        completed = [a for a in s_attempts if a.get("status") == "COMPLETED"]
        in_progress = [a for a in s_attempts if a.get("status") == "IN_PROGRESS"]

        if completed:
            scores = read_csv_rows(sim_id, "scores.csv")
            user_scores = [
                float(s["composite_score"])
                for s in scores
                if s.get("user_id") == user_id
                and s.get("scenario_id") == scenario["id"]
            ]
            card["student_status"] = "Completed"
            card["best_score"] = max(user_scores) if user_scores else 0
            card["attempt_count"] = len(completed)
        elif in_progress:
            card["student_status"] = "In Progress"
            card["current_attempt_id"] = in_progress[-1]["attempt_id"]
            card["attempt_count"] = len(s_attempts)
        else:
            card["student_status"] = "Not Started"
            card["attempt_count"] = 0

        scenario_cards.append(card)

    alias = _ensure_alias(sim_id, user_id)

    # Check for active class session
    active_session = get_active_session(sim_id)
    group = get_user_group(sim_id, user_id)

    # Check if student has in-progress session attempt
    session_attempt = None
    if active_session:
        session_attempt = next(
            (a for a in attempts
             if a.get("session_id") == active_session["session_id"]
             and a.get("user_id") == user_id
             and a.get("status") == "IN_PROGRESS"),
            None,
        )

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "session": session,
        "scenarios": scenario_cards,
        "alias": alias,
        "active_session": active_session,
        "group": group,
        "session_attempt": session_attempt,
    })


# ── Start Attempt (Mode Selection) ───────────────────────────────────

@router.post("/scenario/{scenario_id}/start")
async def start_attempt(request: Request, scenario_id: str, mode: str = Form(...)):
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    scenario = get_scenario(scenario_id)
    if not scenario or scenario["status"] != "ACTIVE":
        return RedirectResponse(url="/dashboard", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    # Check for existing in-progress attempt
    attempts = read_csv_rows(sim_id, "attempts.csv")
    in_progress = [
        a for a in attempts
        if a.get("user_id") == user_id
        and a.get("scenario_id") == scenario_id
        and a.get("status") == "IN_PROGRESS"
    ]
    if in_progress:
        attempt_id = in_progress[-1]["attempt_id"]
        return RedirectResponse(url=f"/attempt/{attempt_id}/round/1", status_code=302)

    # Create new attempt
    attempt_id = f"att_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    new_attempt = {
        "attempt_id": attempt_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "mode": mode.upper(),
        "status": "IN_PROGRESS",
        "current_round": "1",
        "started_at": now,
        "completed_at": "",
    }

    attempts.append(new_attempt)
    fieldnames = ["attempt_id", "user_id", "scenario_id", "mode", "status",
                   "current_round", "started_at", "completed_at"]
    write_csv(sim_id, "attempts.csv", fieldnames, attempts)

    # Create round 1 entry
    rounds = read_csv_rows(sim_id, "rounds.csv")
    rounds.append({
        "round_id": f"rnd_{uuid.uuid4().hex[:12]}",
        "attempt_id": attempt_id,
        "round_number": "1",
        "status": "OPEN",
        "started_at": now,
        "completed_at": "",
    })
    write_csv(sim_id, "rounds.csv",
              ["round_id", "attempt_id", "round_number", "status", "started_at", "completed_at"],
              rounds)

    return RedirectResponse(url=f"/attempt/{attempt_id}/round/1", status_code=302)


# ── Briefing ──────────────────────────────────────────────────────────

@router.get("/attempt/{attempt_id}/round/{round_num}", response_class=HTMLResponse)
async def briefing_page(request: Request, attempt_id: str, round_num: int):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next((a for a in attempts if a["attempt_id"] == attempt_id), None)
    if not attempt or attempt["user_id"] != session["user_id"]:
        return RedirectResponse(url="/dashboard", status_code=302)

    scenario_id = attempt["scenario_id"]
    briefing = get_briefing(scenario_id, round_num)
    scenario = get_scenario(scenario_id)

    return templates.TemplateResponse("briefing.html", {
        "request": request,
        "session": session,
        "attempt": attempt,
        "scenario": scenario,
        "briefing": briefing,
        "round_num": round_num,
        "total_rounds": scenario["total_rounds"],
    })


# ── Term Sheet (Negotiate) ───────────────────────────────────────────

@router.get("/attempt/{attempt_id}/round/{round_num}/negotiate", response_class=HTMLResponse)
async def negotiate_page(request: Request, attempt_id: str, round_num: int):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next((a for a in attempts if a["attempt_id"] == attempt_id), None)
    if not attempt or attempt["user_id"] != session["user_id"]:
        return RedirectResponse(url="/dashboard", status_code=302)

    scenario_id = attempt["scenario_id"]
    term_fields = get_term_fields(scenario_id)

    # If already submitted for this round, redirect to the response page
    submissions = read_csv_rows(sim_id, "submissions.csv")
    round_subs = [
        s for s in submissions
        if s.get("attempt_id") == attempt_id and s.get("round_number") == str(round_num)
    ]

    if round_subs:
        last_sub = round_subs[-1]
        return RedirectResponse(
            url=f"/attempt/{attempt_id}/round/{round_num}/response?sub={last_sub['submission_id']}",
            status_code=302,
        )

    last_terms = {}
    last_ai_response = None

    return templates.TemplateResponse("negotiate.html", {
        "request": request,
        "session": session,
        "attempt": attempt,
        "scenario": get_scenario(scenario_id),
        "term_fields": term_fields,
        "round_num": round_num,
        "last_terms": last_terms,
        "last_ai_response": last_ai_response,
        "submission_count": len(round_subs),
    })


# ── Submit Terms ──────────────────────────────────────────────────────

@router.post("/attempt/{attempt_id}/round/{round_num}/submit")
async def submit_terms(request: Request, attempt_id: str, round_num: int):
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next((a for a in attempts if a["attempt_id"] == attempt_id), None)
    if not attempt or attempt["user_id"] != session["user_id"]:
        return RedirectResponse(url="/dashboard", status_code=302)

    # Prevent duplicate submissions for the same round
    all_submissions = read_csv_rows(sim_id, "submissions.csv")
    existing_subs = [
        s for s in all_submissions
        if s.get("attempt_id") == attempt_id and s.get("round_number") == str(round_num)
    ]
    if existing_subs:
        last_sub = existing_subs[-1]
        return RedirectResponse(
            url=f"/attempt/{attempt_id}/round/{round_num}/response?sub={last_sub['submission_id']}",
            status_code=302,
        )

    scenario_id = attempt["scenario_id"]
    term_fields = get_term_fields(scenario_id)

    # Parse form data
    form = await request.form()
    terms = {}
    for field in term_fields:
        raw = form.get(field.key, "")
        if field.input_type in ("slider", "numeric"):
            try:
                terms[field.key] = float(raw)
            except (ValueError, TypeError):
                terms[field.key] = field.default
        else:
            terms[field.key] = raw or field.default

    # Build history from previous submissions
    submissions = read_csv_rows(sim_id, "submissions.csv")
    history = []
    for s in submissions:
        if s.get("attempt_id") == attempt_id:
            try:
                h_terms = json.loads(s.get("terms_json", "{}"))
                h_ai = json.loads(s.get("ai_response_json", "{}")) if s.get("ai_response_json") else None
            except json.JSONDecodeError:
                continue
            history.append({
                "round_number": int(s.get("round_number", 1)),
                "submission_number": int(s.get("submission_number", 1)),
                "terms": h_terms,
                "ai_response": h_ai,
            })

    # Compute cumulative trust
    cumulative_trust = 0.0
    for h in history:
        if h.get("ai_response") and "trust_delta" in h["ai_response"]:
            cumulative_trust += float(h["ai_response"]["trust_delta"])

    # Get briefing for context
    briefing_data = get_briefing(scenario_id, round_num)
    briefing_text = briefing_data["content"] if briefing_data else ""

    # Call AI
    ai_response = evaluate_submission(
        round_number=round_num,
        briefing=briefing_text,
        submission=terms,
        history=history,
        cumulative_trust=cumulative_trust,
    )

    # Compute round score from AI scores
    round_score = {}
    if "scores" in ai_response:
        from app.core.scoring import compute_round_score
        round_score = compute_round_score(ai_response["scores"])

    # Save submission
    round_subs = [
        s for s in submissions
        if s.get("attempt_id") == attempt_id and s.get("round_number") == str(round_num)
    ]
    sub_num = len(round_subs) + 1
    now = datetime.now(timezone.utc).isoformat()

    new_sub = {
        "submission_id": f"sub_{uuid.uuid4().hex[:12]}",
        "attempt_id": attempt_id,
        "round_number": str(round_num),
        "submission_number": str(sub_num),
        "terms_json": json.dumps(terms),
        "ai_response_json": json.dumps(ai_response),
        "score_json": json.dumps(round_score),
        "submitted_at": now,
    }
    submissions.append(new_sub)
    fieldnames = ["submission_id", "attempt_id", "round_number", "submission_number",
                   "terms_json", "ai_response_json", "score_json", "submitted_at"]
    write_csv(sim_id, "submissions.csv", fieldnames, submissions)

    return RedirectResponse(
        url=f"/attempt/{attempt_id}/round/{round_num}/response?sub={new_sub['submission_id']}",
        status_code=302,
    )


# ── AI Response ───────────────────────────────────────────────────────

@router.get("/attempt/{attempt_id}/round/{round_num}/response", response_class=HTMLResponse)
async def response_page(request: Request, attempt_id: str, round_num: int):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    sub_id = request.query_params.get("sub", "")

    submissions = read_csv_rows(sim_id, "submissions.csv")
    submission = next((s for s in submissions if s.get("submission_id") == sub_id), None)

    if not submission:
        # Fall back to latest submission for this round
        round_subs = [
            s for s in submissions
            if s.get("attempt_id") == attempt_id and s.get("round_number") == str(round_num)
        ]
        submission = round_subs[-1] if round_subs else None

    if not submission:
        return RedirectResponse(url=f"/attempt/{attempt_id}/round/{round_num}/negotiate", status_code=302)

    terms = json.loads(submission.get("terms_json", "{}"))
    ai_response = json.loads(submission.get("ai_response_json", "{}"))
    round_score = json.loads(submission.get("score_json", "{}"))

    scenario_id = None
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next((a for a in attempts if a["attempt_id"] == attempt_id), None)
    if attempt:
        scenario_id = attempt["scenario_id"]

    term_fields = get_term_fields(scenario_id) if scenario_id else []
    scenario = get_scenario(scenario_id) if scenario_id else {}

    return templates.TemplateResponse("ai_response.html", {
        "request": request,
        "session": session,
        "attempt": attempt,
        "scenario": scenario,
        "terms": terms,
        "ai_response": ai_response,
        "round_score": round_score,
        "term_fields": term_fields,
        "round_num": round_num,
        "total_rounds": scenario.get("total_rounds", 3) if scenario else 3,
    })


# ── Accept / Lock-in / Close Round ───────────────────────────────────

@router.post("/attempt/{attempt_id}/round/{round_num}/close")
async def close_round(request: Request, attempt_id: str, round_num: int):
    """Close the current round (accept counter, lock-in, or auto-close)."""
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    form = await request.form()
    action = form.get("action", "lock_in")  # accept_counter, lock_in

    # Mark round as closed
    rounds = read_csv_rows(sim_id, "rounds.csv")
    now = datetime.now(timezone.utc).isoformat()
    for r in rounds:
        if r["attempt_id"] == attempt_id and r["round_number"] == str(round_num):
            r["status"] = "CLOSED"
            r["completed_at"] = now
            break
    write_csv(sim_id, "rounds.csv",
              ["round_id", "attempt_id", "round_number", "status", "started_at", "completed_at"],
              rounds)

    # Check if this was the final round
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next((a for a in attempts if a["attempt_id"] == attempt_id), None)
    scenario = get_scenario(attempt["scenario_id"]) if attempt else None
    total_rounds = scenario["total_rounds"] if scenario else 3

    if round_num >= total_rounds:
        # Complete the attempt — compute final score
        _complete_attempt(sim_id, attempt_id, attempt["scenario_id"], session["user_id"])
        return RedirectResponse(url=f"/attempt/{attempt_id}/results", status_code=302)
    else:
        # Open next round
        next_round = round_num + 1

        # Update attempt current_round
        for a in attempts:
            if a["attempt_id"] == attempt_id:
                a["current_round"] = str(next_round)
        write_csv(sim_id, "attempts.csv",
                  ["attempt_id", "user_id", "scenario_id", "mode", "status",
                   "current_round", "started_at", "completed_at"],
                  attempts)

        # Create next round entry
        rounds = read_csv_rows(sim_id, "rounds.csv")
        rounds.append({
            "round_id": f"rnd_{uuid.uuid4().hex[:12]}",
            "attempt_id": attempt_id,
            "round_number": str(next_round),
            "status": "OPEN",
            "started_at": now,
            "completed_at": "",
        })
        write_csv(sim_id, "rounds.csv",
                  ["round_id", "attempt_id", "round_number", "status", "started_at", "completed_at"],
                  rounds)

        return RedirectResponse(url=f"/attempt/{attempt_id}/round/{next_round}", status_code=302)


def _complete_attempt(sim_id: str, attempt_id: str, scenario_id: str, user_id: str):
    """Compute final scores and update leaderboard."""
    submissions = read_csv_rows(sim_id, "submissions.csv")

    # Get last submission per round
    round_scores = []
    for rn in range(1, 4):
        round_subs = [
            s for s in submissions
            if s.get("attempt_id") == attempt_id and s.get("round_number") == str(rn)
        ]
        if round_subs:
            last_sub = round_subs[-1]
            try:
                score = json.loads(last_sub.get("score_json", "{}"))
                round_scores.append(score)
            except json.JSONDecodeError:
                round_scores.append({"economic_value": 0, "strategic_alignment": 0,
                                     "relationship_preservation": 0, "information_management": 0, "composite": 0})

    final_score = compute_attempt_score(round_scores)

    # Mark attempt as completed
    attempts = read_csv_rows(sim_id, "attempts.csv")
    now = datetime.now(timezone.utc).isoformat()
    for a in attempts:
        if a["attempt_id"] == attempt_id:
            a["status"] = "COMPLETED"
            a["completed_at"] = now
    write_csv(sim_id, "attempts.csv",
              ["attempt_id", "user_id", "scenario_id", "mode", "status",
               "current_round", "started_at", "completed_at"],
              attempts)

    # Save score
    scores = read_csv_rows(sim_id, "scores.csv")
    scores.append({
        "score_id": f"scr_{uuid.uuid4().hex[:12]}",
        "attempt_id": attempt_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "economic_value": str(final_score["economic_value"]),
        "strategic_alignment": str(final_score["strategic_alignment"]),
        "relationship_preservation": str(final_score["relationship_preservation"]),
        "information_management": str(final_score["information_management"]),
        "composite_score": str(final_score["composite"]),
        "round_scores_json": json.dumps([rs for rs in round_scores]),
        "scored_at": now,
    })
    write_csv(sim_id, "scores.csv",
              ["score_id", "attempt_id", "user_id", "scenario_id",
               "economic_value", "strategic_alignment", "relationship_preservation",
               "information_management", "composite_score", "round_scores_json", "scored_at"],
              scores)

    # Update leaderboard
    _update_leaderboard(sim_id, scenario_id)


def _update_leaderboard(sim_id: str, scenario_id: str):
    """Recalculate leaderboard for a scenario (both homework and class session)."""
    scores = read_csv_rows(sim_id, "scores.csv")
    scenario_scores = [s for s in scores if s.get("scenario_id") == scenario_id]

    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt_map = {a["attempt_id"]: a for a in attempts}

    # Build entries for both activity modes
    all_entries = []
    for activity_mode in ("HOMEWORK", "CLASS_SESSION"):
        # Determine which attempts count for this mode
        if activity_mode == "CLASS_SESSION":
            mode_attempts = {a["attempt_id"] for a in attempts
                             if a.get("activity_mode") == "CLASS_SESSION"}
        else:
            # Homework = GRADED attempts without a session (legacy + new)
            mode_attempts = {a["attempt_id"] for a in attempts
                             if a.get("mode") == "GRADED"
                             and a.get("activity_mode", "HOMEWORK") != "CLASS_SESSION"}

        user_scores: dict[str, list[float]] = {}
        for s in scenario_scores:
            if s.get("attempt_id") in mode_attempts:
                uid = s["user_id"]
                user_scores.setdefault(uid, []).append(float(s["composite_score"]))

        entries = []
        all_avgs = []
        for uid, sc_list in user_scores.items():
            avg = sum(sc_list) / len(sc_list)
            all_avgs.append(avg)
            entries.append({
                "user_id": uid,
                "scenario_id": scenario_id,
                "activity_mode": activity_mode,
                "average_score": str(round(avg, 1)),
                "attempt_count": str(len(sc_list)),
                "percentile": "0",
            })

        for entry in entries:
            avg = float(entry["average_score"])
            entry["percentile"] = str(compute_percentile(avg, all_avgs))

        entries.sort(key=lambda e: float(e["average_score"]), reverse=True)
        for i, entry in enumerate(entries):
            entry["rank"] = str(i + 1)

        all_entries.extend(entries)

    # Merge: remove old entries for this scenario, add new
    leaderboard = read_csv_rows(sim_id, "leaderboard.csv")
    leaderboard = [lb for lb in leaderboard if lb.get("scenario_id") != scenario_id]
    leaderboard.extend(all_entries)

    write_csv(sim_id, "leaderboard.csv",
              ["rank", "user_id", "scenario_id", "activity_mode",
               "average_score", "attempt_count", "percentile"],
              leaderboard)


# ── Attempt Results ───────────────────────────────────────────────────

@router.get("/attempt/{attempt_id}/results", response_class=HTMLResponse)
async def results_page(request: Request, attempt_id: str):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next((a for a in attempts if a["attempt_id"] == attempt_id), None)
    if not attempt or attempt["user_id"] != session["user_id"]:
        return RedirectResponse(url="/dashboard", status_code=302)

    scores = read_csv_rows(sim_id, "scores.csv")
    score = next((s for s in scores if s.get("attempt_id") == attempt_id), None)

    round_scores = []
    if score and score.get("round_scores_json"):
        try:
            round_scores = json.loads(score["round_scores_json"])
        except json.JSONDecodeError:
            pass

    scenario = get_scenario(attempt["scenario_id"])

    return templates.TemplateResponse("results.html", {
        "request": request,
        "session": session,
        "attempt": attempt,
        "scenario": scenario,
        "score": score,
        "round_scores": round_scores,
    })


# ── Leaderboard ───────────────────────────────────────────────────────

@router.get("/scenario/{scenario_id}/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request, scenario_id: str):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    leaderboard = read_csv_rows(sim_id, "leaderboard.csv")
    all_entries = [lb for lb in leaderboard if lb.get("scenario_id") == scenario_id]

    # Resolve aliases
    aliases = read_csv_rows(sim_id, "aliases.csv")
    alias_map = {a["user_id"]: a["alias"] for a in aliases}

    for entry in all_entries:
        entry["alias"] = alias_map.get(entry["user_id"], "Unknown")
        entry["is_current_user"] = entry["user_id"] == user_id

    # Split by activity mode
    homework_entries = sorted(
        [e for e in all_entries if e.get("activity_mode", "HOMEWORK") != "CLASS_SESSION"],
        key=lambda e: float(e.get("average_score", "0")), reverse=True,
    )
    class_entries = sorted(
        [e for e in all_entries if e.get("activity_mode") == "CLASS_SESSION"],
        key=lambda e: float(e.get("average_score", "0")), reverse=True,
    )

    scores = read_csv_rows(sim_id, "scores.csv")
    my_scores = [s for s in scores if s.get("user_id") == user_id and s.get("scenario_id") == scenario_id]

    scenario = get_scenario(scenario_id)
    tab = request.query_params.get("tab", "homework")

    return templates.TemplateResponse("leaderboard.html", {
        "request": request,
        "session": session,
        "scenario": scenario,
        "homework_entries": homework_entries,
        "class_entries": class_entries,
        "entries": homework_entries if tab != "class" else class_entries,
        "my_scores": my_scores,
        "alias": alias_map.get(user_id, "Unknown"),
        "active_tab": tab,
    })


# ══════════════════════════════════════════════════════════════════════
#  CLASS SESSION FLOW  (v1.2)
# ══════════════════════════════════════════════════════════════════════

def _get_session_context(sim_id: str, user_id: str, session_id: str):
    """Return (class_session, group, pairing, role) or Nones."""
    class_session = get_class_session(sim_id, session_id)
    if not class_session:
        return None, None, None, None

    group = get_user_group(sim_id, user_id)
    if not group:
        return class_session, None, None, None

    pairing = get_pairing_for_group(sim_id, session_id, group["group_id"])
    if not pairing:
        return class_session, group, None, None

    # Determine role: student_group_id is buyer/STUDENT_ROLE, partner is PARTNER_ROLE
    if pairing.get("student_group_id") == group["group_id"]:
        role = "STUDENT_ROLE"
    else:
        role = "PARTNER_ROLE"

    return class_session, group, pairing, role


def _get_or_create_session_attempt(sim_id: str, user_id: str, session_id: str,
                                    scenario_id: str, group_id: str,
                                    counterpart_type: str, role: str):
    """Find existing attempt for this user+session or create one."""
    attempts = read_csv_rows(sim_id, "attempts.csv")
    for a in attempts:
        if (a.get("user_id") == user_id
                and a.get("session_id") == session_id
                and a.get("status") == "IN_PROGRESS"):
            return a, attempts

    attempt_id = f"att_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    new_attempt = {
        "attempt_id": attempt_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "mode": "GRADED",
        "status": "IN_PROGRESS",
        "current_round": "0",
        "started_at": now,
        "completed_at": "",
        "activity_mode": "CLASS_SESSION",
        "session_id": session_id,
        "group_id": group_id,
        "counterpart_type": counterpart_type,
        "role": role,
    }
    attempts.append(new_attempt)
    write_csv(sim_id, "attempts.csv",
              ["attempt_id", "user_id", "scenario_id", "mode", "status",
               "current_round", "started_at", "completed_at",
               "activity_mode", "session_id", "group_id", "counterpart_type", "role"],
              attempts)
    return new_attempt, attempts


# ── Join Session ──────────────────────────────────────────────────────

@router.get("/session/{session_id}/join", response_class=HTMLResponse)
async def join_session(request: Request, session_id: str):
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    class_session, group, pairing, role = _get_session_context(sim_id, user_id, session_id)

    if not class_session:
        return RedirectResponse(url="/dashboard", status_code=302)
    if not group:
        return RedirectResponse(url="/dashboard", status_code=302)
    if not pairing:
        return RedirectResponse(url="/dashboard", status_code=302)

    counterpart_type = pairing.get("counterpart_type", "AI")
    _get_or_create_session_attempt(
        sim_id, user_id, session_id, class_session["scenario_id"],
        group["group_id"], counterpart_type, role,
    )

    return RedirectResponse(url=f"/session/{session_id}/lobby", status_code=302)


# ── Session Lobby ─────────────────────────────────────────────────────

@router.get("/session/{session_id}/lobby", response_class=HTMLResponse)
async def session_lobby(request: Request, session_id: str):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    class_session, group, pairing, role = _get_session_context(sim_id, user_id, session_id)
    if not class_session or not group:
        return RedirectResponse(url="/dashboard", status_code=302)

    # If session is active and round > 0, redirect to the round
    if class_session["status"] == "ACTIVE":
        current_round = int(class_session.get("current_round", "0"))
        if current_round > 0:
            return RedirectResponse(
                url=f"/session/{session_id}/round/{current_round}",
                status_code=302,
            )

    if class_session["status"] == "COMPLETED":
        return RedirectResponse(url=f"/session/{session_id}/results", status_code=302)

    scenario = get_scenario(class_session["scenario_id"])
    members = list_members(sim_id, group["group_id"])

    return templates.TemplateResponse("session_lobby.html", {
        "request": request,
        "session": session,
        "class_session": class_session,
        "group": group,
        "members": members,
        "role": role,
        "scenario": scenario,
        "pairing": pairing,
    })


# ── Session Round Briefing ────────────────────────────────────────────

@router.get("/session/{session_id}/round/{round_num}", response_class=HTMLResponse)
async def session_round_briefing(request: Request, session_id: str, round_num: int):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    class_session, group, pairing, role = _get_session_context(sim_id, user_id, session_id)
    if not class_session or not group or not pairing:
        return RedirectResponse(url="/dashboard", status_code=302)

    scenario_id = class_session["scenario_id"]
    scenario = get_scenario(scenario_id)

    if role == "PARTNER_ROLE":
        briefing = get_partner_briefing(scenario_id, round_num)
    else:
        briefing = get_briefing(scenario_id, round_num)

    timer = get_timer(sim_id, session_id, round_num)
    remaining = get_remaining_seconds(timer) if timer else 0

    return templates.TemplateResponse("session_briefing.html", {
        "request": request,
        "session": session,
        "class_session": class_session,
        "group": group,
        "role": role,
        "scenario": scenario,
        "briefing": briefing,
        "round_num": round_num,
        "total_rounds": scenario["total_rounds"],
        "remaining_seconds": remaining,
        "session_id": session_id,
    })


# ── Session Negotiate ─────────────────────────────────────────────────

@router.get("/session/{session_id}/round/{round_num}/negotiate", response_class=HTMLResponse)
async def session_negotiate(request: Request, session_id: str, round_num: int):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    class_session, group, pairing, role = _get_session_context(sim_id, user_id, session_id)
    if not class_session or not group or not pairing:
        return RedirectResponse(url="/dashboard", status_code=302)

    scenario_id = class_session["scenario_id"]
    term_fields = get_term_fields(scenario_id)

    # Check if already submitted
    submissions = read_csv_rows(sim_id, "submissions.csv")
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next(
        (a for a in attempts
         if a.get("user_id") == user_id and a.get("session_id") == session_id
         and a.get("status") == "IN_PROGRESS"),
        None,
    )
    if not attempt:
        return RedirectResponse(url=f"/session/{session_id}/lobby", status_code=302)

    round_subs = [
        s for s in submissions
        if s.get("attempt_id") == attempt["attempt_id"]
        and s.get("round_number") == str(round_num)
    ]
    if round_subs:
        return RedirectResponse(
            url=f"/session/{session_id}/round/{round_num}/waiting",
            status_code=302,
        )

    timer = get_timer(sim_id, session_id, round_num)
    remaining = get_remaining_seconds(timer) if timer else 0

    return templates.TemplateResponse("session_negotiate.html", {
        "request": request,
        "session": session,
        "class_session": class_session,
        "group": group,
        "role": role,
        "scenario": get_scenario(scenario_id),
        "term_fields": term_fields,
        "round_num": round_num,
        "remaining_seconds": remaining,
        "session_id": session_id,
        "attempt": attempt,
    })


# ── Session Submit ────────────────────────────────────────────────────

@router.post("/session/{session_id}/round/{round_num}/submit")
async def session_submit(request: Request, session_id: str, round_num: int):
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    class_session, group, pairing, role = _get_session_context(sim_id, user_id, session_id)
    if not class_session or not group or not pairing:
        return RedirectResponse(url="/dashboard", status_code=302)

    scenario_id = class_session["scenario_id"]
    term_fields = get_term_fields(scenario_id)

    # Get the attempt
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next(
        (a for a in attempts
         if a.get("user_id") == user_id and a.get("session_id") == session_id
         and a.get("status") == "IN_PROGRESS"),
        None,
    )
    if not attempt:
        return RedirectResponse(url=f"/session/{session_id}/lobby", status_code=302)

    # Prevent duplicate submission
    all_submissions = read_csv_rows(sim_id, "submissions.csv")
    existing = [
        s for s in all_submissions
        if s.get("attempt_id") == attempt["attempt_id"]
        and s.get("round_number") == str(round_num)
    ]
    if existing:
        return RedirectResponse(
            url=f"/session/{session_id}/round/{round_num}/waiting",
            status_code=302,
        )

    # Parse form data
    form = await request.form()
    terms = {}
    for field in term_fields:
        raw = form.get(field.key, "")
        if field.input_type in ("slider", "numeric"):
            try:
                terms[field.key] = float(raw)
            except (ValueError, TypeError):
                terms[field.key] = field.default
        else:
            terms[field.key] = raw or field.default

    now = datetime.now(timezone.utc).isoformat()
    counterpart_type = pairing.get("counterpart_type", "AI")

    if counterpart_type == "AI":
        # Same as homework: call AI, get response immediately
        submissions_for_history = [
            s for s in all_submissions if s.get("attempt_id") == attempt["attempt_id"]
        ]
        history = []
        for s in submissions_for_history:
            try:
                h_terms = json.loads(s.get("terms_json", "{}"))
                h_ai = json.loads(s.get("ai_response_json", "{}")) if s.get("ai_response_json") else None
            except json.JSONDecodeError:
                continue
            history.append({
                "round_number": int(s.get("round_number", 1)),
                "submission_number": int(s.get("submission_number", 1)),
                "terms": h_terms,
                "ai_response": h_ai,
            })

        cumulative_trust = sum(
            float(h["ai_response"].get("trust_delta", 0))
            for h in history if h.get("ai_response")
        )
        briefing_data = get_briefing(scenario_id, round_num)
        briefing_text = briefing_data["content"] if briefing_data else ""

        ai_response = evaluate_submission(
            round_number=round_num,
            briefing=briefing_text,
            submission=terms,
            history=history,
            cumulative_trust=cumulative_trust,
        )
        round_score = {}
        if "scores" in ai_response:
            round_score = compute_round_score(ai_response["scores"], role="STUDENT_ROLE")

        new_sub = {
            "submission_id": f"sub_{uuid.uuid4().hex[:12]}",
            "attempt_id": attempt["attempt_id"],
            "round_number": str(round_num),
            "submission_number": "1",
            "terms_json": json.dumps(terms),
            "ai_response_json": json.dumps(ai_response),
            "score_json": json.dumps(round_score),
            "submitted_at": now,
        }
    else:
        # Human-Human: just save the submission, no AI call yet
        new_sub = {
            "submission_id": f"sub_{uuid.uuid4().hex[:12]}",
            "attempt_id": attempt["attempt_id"],
            "round_number": str(round_num),
            "submission_number": "1",
            "terms_json": json.dumps(terms),
            "ai_response_json": "",
            "score_json": "",
            "submitted_at": now,
        }

    all_submissions.append(new_sub)
    write_csv(sim_id, "submissions.csv",
              ["submission_id", "attempt_id", "round_number", "submission_number",
               "terms_json", "ai_response_json", "score_json", "submitted_at"],
              all_submissions)

    return RedirectResponse(
        url=f"/session/{session_id}/round/{round_num}/waiting",
        status_code=302,
    )


# ── Waiting Page (after submission) ───────────────────────────────────

@router.get("/session/{session_id}/round/{round_num}/waiting", response_class=HTMLResponse)
async def session_waiting(request: Request, session_id: str, round_num: int):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    class_session, group, pairing, role = _get_session_context(sim_id, user_id, session_id)
    if not class_session or not group or not pairing:
        return RedirectResponse(url="/dashboard", status_code=302)

    counterpart_type = pairing.get("counterpart_type", "AI")

    # Find my attempt and submission
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next(
        (a for a in attempts
         if a.get("user_id") == user_id and a.get("session_id") == session_id
         and a.get("status") == "IN_PROGRESS"),
        None,
    )
    if not attempt:
        return RedirectResponse(url=f"/session/{session_id}/lobby", status_code=302)

    submissions = read_csv_rows(sim_id, "submissions.csv")
    my_sub = next(
        (s for s in submissions
         if s.get("attempt_id") == attempt["attempt_id"]
         and s.get("round_number") == str(round_num)),
        None,
    )

    if not my_sub:
        return RedirectResponse(
            url=f"/session/{session_id}/round/{round_num}/negotiate",
            status_code=302,
        )

    # For AI mode: we already have the response
    if counterpart_type == "AI" and my_sub.get("ai_response_json"):
        return RedirectResponse(
            url=f"/session/{session_id}/round/{round_num}/response",
            status_code=302,
        )

    # For HH mode: check if partner has submitted
    partner_submitted = False
    other_group_id = (
        pairing.get("partner_group_id")
        if pairing.get("student_group_id") == group["group_id"]
        else pairing.get("student_group_id")
    )

    if other_group_id:
        partner_attempt = next(
            (a for a in attempts
             if a.get("session_id") == session_id
             and a.get("group_id") == other_group_id
             and a.get("status") == "IN_PROGRESS"),
            None,
        )
        if partner_attempt:
            partner_sub = next(
                (s for s in submissions
                 if s.get("attempt_id") == partner_attempt["attempt_id"]
                 and s.get("round_number") == str(round_num)),
                None,
            )
            if partner_sub:
                partner_submitted = True

                # Both submitted — trigger AI evaluation if not done yet
                if not my_sub.get("ai_response_json"):
                    _evaluate_hh_round(
                        sim_id, session_id, round_num, pairing, attempts, submissions,
                    )
                return RedirectResponse(
                    url=f"/session/{session_id}/round/{round_num}/response",
                    status_code=302,
                )

    timer = get_timer(sim_id, session_id, round_num)
    remaining = get_remaining_seconds(timer) if timer else 0

    return templates.TemplateResponse("session_waiting.html", {
        "request": request,
        "session": session,
        "class_session": class_session,
        "group": group,
        "role": role,
        "round_num": round_num,
        "partner_submitted": partner_submitted,
        "remaining_seconds": remaining,
        "session_id": session_id,
    })


def _evaluate_hh_round(sim_id, session_id, round_num, pairing, attempts, submissions):
    """Run AI evaluator on both sides of an HH exchange."""
    student_gid = pairing.get("student_group_id")
    partner_gid = pairing.get("partner_group_id")

    # Find attempts by group
    student_attempt = next(
        (a for a in attempts
         if a.get("session_id") == session_id and a.get("group_id") == student_gid),
        None,
    )
    partner_attempt = next(
        (a for a in attempts
         if a.get("session_id") == session_id and a.get("group_id") == partner_gid),
        None,
    )
    if not student_attempt or not partner_attempt:
        return

    student_sub = next(
        (s for s in submissions
         if s.get("attempt_id") == student_attempt["attempt_id"]
         and s.get("round_number") == str(round_num)),
        None,
    )
    partner_sub = next(
        (s for s in submissions
         if s.get("attempt_id") == partner_attempt["attempt_id"]
         and s.get("round_number") == str(round_num)),
        None,
    )
    if not student_sub or not partner_sub:
        return

    student_terms = json.loads(student_sub.get("terms_json", "{}"))
    partner_terms = json.loads(partner_sub.get("terms_json", "{}"))

    # Build history from previous rounds
    history = []
    for rn in range(1, round_num):
        prev_s = next(
            (s for s in submissions
             if s.get("attempt_id") == student_attempt["attempt_id"]
             and s.get("round_number") == str(rn)),
            None,
        )
        prev_p = next(
            (s for s in submissions
             if s.get("attempt_id") == partner_attempt["attempt_id"]
             and s.get("round_number") == str(rn)),
            None,
        )
        if prev_s and prev_p:
            history.append({
                "round_number": rn,
                "student_terms": json.loads(prev_s.get("terms_json", "{}")),
                "partner_terms": json.loads(prev_p.get("terms_json", "{}")),
            })

    # Call AI evaluator
    eval_result = evaluate_hh_exchange(
        round_number=round_num,
        student_submission=student_terms,
        partner_submission=partner_terms,
        history=history,
    )

    # Compute scores from evaluation
    student_scores = eval_result.get("student_scores", {})
    partner_scores = eval_result.get("partner_scores", {})

    student_round_score = compute_round_score(student_scores, role="STUDENT_ROLE")
    partner_round_score = compute_round_score(partner_scores, role="PARTNER_ROLE")

    # Update both submissions with eval results
    student_eval = {
        "evaluation": eval_result.get("narrative", ""),
        "scores": student_scores,
        "partner_terms": partner_terms,
        "term_comparison": eval_result.get("term_comparison", {}),
    }
    partner_eval = {
        "evaluation": eval_result.get("narrative", ""),
        "scores": partner_scores,
        "student_terms": student_terms,
        "term_comparison": eval_result.get("term_comparison", {}),
    }

    for s in submissions:
        if s["submission_id"] == student_sub["submission_id"]:
            s["ai_response_json"] = json.dumps(student_eval)
            s["score_json"] = json.dumps(student_round_score)
        elif s["submission_id"] == partner_sub["submission_id"]:
            s["ai_response_json"] = json.dumps(partner_eval)
            s["score_json"] = json.dumps(partner_round_score)

    write_csv(sim_id, "submissions.csv",
              ["submission_id", "attempt_id", "round_number", "submission_number",
               "terms_json", "ai_response_json", "score_json", "submitted_at"],
              submissions)


# ── Session Response ──────────────────────────────────────────────────

@router.get("/session/{session_id}/round/{round_num}/response", response_class=HTMLResponse)
async def session_response(request: Request, session_id: str, round_num: int):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    class_session, group, pairing, role = _get_session_context(sim_id, user_id, session_id)
    if not class_session or not group:
        return RedirectResponse(url="/dashboard", status_code=302)

    counterpart_type = pairing.get("counterpart_type", "AI") if pairing else "AI"

    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next(
        (a for a in attempts
         if a.get("user_id") == user_id and a.get("session_id") == session_id
         and a.get("status") == "IN_PROGRESS"),
        None,
    )
    if not attempt:
        return RedirectResponse(url=f"/session/{session_id}/lobby", status_code=302)

    submissions = read_csv_rows(sim_id, "submissions.csv")
    my_sub = next(
        (s for s in submissions
         if s.get("attempt_id") == attempt["attempt_id"]
         and s.get("round_number") == str(round_num)),
        None,
    )
    if not my_sub:
        return RedirectResponse(
            url=f"/session/{session_id}/round/{round_num}/negotiate",
            status_code=302,
        )

    terms = json.loads(my_sub.get("terms_json", "{}"))
    ai_response = json.loads(my_sub.get("ai_response_json", "{}")) if my_sub.get("ai_response_json") else {}
    round_score = json.loads(my_sub.get("score_json", "{}")) if my_sub.get("score_json") else {}

    scenario = get_scenario(class_session["scenario_id"])
    term_fields = get_term_fields(class_session["scenario_id"])

    timer = get_timer(sim_id, session_id, round_num)
    remaining = get_remaining_seconds(timer) if timer else 0

    # Determine if there's a next round
    current_round = int(class_session.get("current_round", "0"))

    return templates.TemplateResponse("session_response.html", {
        "request": request,
        "session": session,
        "class_session": class_session,
        "group": group,
        "role": role,
        "scenario": scenario,
        "terms": terms,
        "ai_response": ai_response,
        "round_score": round_score,
        "term_fields": term_fields,
        "round_num": round_num,
        "total_rounds": scenario.get("total_rounds", 3),
        "remaining_seconds": remaining,
        "session_id": session_id,
        "counterpart_type": counterpart_type,
        "current_session_round": current_round,
    })


# ── Session Close Round ───────────────────────────────────────────────

@router.post("/session/{session_id}/round/{round_num}/close")
async def session_close_round(request: Request, session_id: str, round_num: int):
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    # Mark round as complete for the student
    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next(
        (a for a in attempts
         if a.get("user_id") == user_id and a.get("session_id") == session_id
         and a.get("status") == "IN_PROGRESS"),
        None,
    )
    if not attempt:
        return RedirectResponse(url=f"/session/{session_id}/lobby", status_code=302)

    # Update current_round
    for a in attempts:
        if a["attempt_id"] == attempt["attempt_id"]:
            a["current_round"] = str(round_num)
    write_csv(sim_id, "attempts.csv",
              ["attempt_id", "user_id", "scenario_id", "mode", "status",
               "current_round", "started_at", "completed_at",
               "activity_mode", "session_id", "group_id", "counterpart_type", "role"],
              attempts)

    # Check if session has advanced to a new round
    class_session = get_class_session(sim_id, session_id)
    if not class_session:
        return RedirectResponse(url="/dashboard", status_code=302)

    current_round = int(class_session.get("current_round", "0"))
    if class_session["status"] == "COMPLETED":
        _complete_session_attempt(sim_id, attempt, user_id)
        return RedirectResponse(url=f"/session/{session_id}/results", status_code=302)

    if current_round > round_num:
        return RedirectResponse(
            url=f"/session/{session_id}/round/{current_round}",
            status_code=302,
        )

    # Still on same round — go to lobby/wait
    return RedirectResponse(url=f"/session/{session_id}/lobby", status_code=302)


def _complete_session_attempt(sim_id: str, attempt: dict, user_id: str):
    """Complete a class session attempt."""
    attempt_id = attempt["attempt_id"]
    scenario_id = attempt["scenario_id"]
    role = attempt.get("role", "STUDENT_ROLE")

    submissions = read_csv_rows(sim_id, "submissions.csv")

    round_scores = []
    for rn in range(1, 4):
        round_subs = [
            s for s in submissions
            if s.get("attempt_id") == attempt_id and s.get("round_number") == str(rn)
        ]
        if round_subs:
            try:
                score = json.loads(round_subs[-1].get("score_json", "{}"))
                round_scores.append(score)
            except json.JSONDecodeError:
                round_scores.append({})

    final_score = compute_attempt_score(round_scores, role=role)

    # Mark attempt completed
    attempts = read_csv_rows(sim_id, "attempts.csv")
    now = datetime.now(timezone.utc).isoformat()
    for a in attempts:
        if a["attempt_id"] == attempt_id:
            a["status"] = "COMPLETED"
            a["completed_at"] = now
    write_csv(sim_id, "attempts.csv",
              ["attempt_id", "user_id", "scenario_id", "mode", "status",
               "current_round", "started_at", "completed_at",
               "activity_mode", "session_id", "group_id", "counterpart_type", "role"],
              attempts)

    # Save score
    scores = read_csv_rows(sim_id, "scores.csv")
    scores.append({
        "score_id": f"scr_{uuid.uuid4().hex[:12]}",
        "attempt_id": attempt_id,
        "user_id": user_id,
        "scenario_id": scenario_id,
        "economic_value": str(final_score.get("economic_value", 0)),
        "strategic_alignment": str(final_score.get("strategic_alignment", 0)),
        "relationship_preservation": str(final_score.get("relationship_preservation", 0)),
        "information_management": str(final_score.get("information_management", 0)),
        "composite_score": str(final_score.get("composite", 0)),
        "round_scores_json": json.dumps(round_scores),
        "scored_at": now,
    })
    write_csv(sim_id, "scores.csv",
              ["score_id", "attempt_id", "user_id", "scenario_id",
               "economic_value", "strategic_alignment", "relationship_preservation",
               "information_management", "composite_score", "round_scores_json", "scored_at"],
              scores)

    _update_leaderboard(sim_id, scenario_id)


# ── Session Results ───────────────────────────────────────────────────

@router.get("/session/{session_id}/results", response_class=HTMLResponse)
async def session_results(request: Request, session_id: str):
    from web.main import templates
    session = _require_student(request)
    if not session:
        return RedirectResponse(url="/login", status_code=302)

    sim_id = session["sim_id"]
    user_id = session["user_id"]

    attempts = read_csv_rows(sim_id, "attempts.csv")
    attempt = next(
        (a for a in attempts
         if a.get("user_id") == user_id and a.get("session_id") == session_id),
        None,
    )
    if not attempt:
        return RedirectResponse(url="/dashboard", status_code=302)

    scores = read_csv_rows(sim_id, "scores.csv")
    score = next((s for s in scores if s.get("attempt_id") == attempt["attempt_id"]), None)

    round_scores = []
    if score and score.get("round_scores_json"):
        try:
            round_scores = json.loads(score["round_scores_json"])
        except json.JSONDecodeError:
            pass

    scenario = get_scenario(attempt["scenario_id"])

    return templates.TemplateResponse("results.html", {
        "request": request,
        "session": session,
        "attempt": attempt,
        "scenario": scenario,
        "score": score,
        "round_scores": round_scores,
    })


# ── Session Status (polling endpoint for students) ────────────────────

@router.get("/session/{session_id}/status", response_class=JSONResponse)
async def session_status_student(request: Request, session_id: str):
    session = _require_student(request)
    if not session:
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    sim_id = session["sim_id"]
    class_session = get_class_session(sim_id, session_id)
    if not class_session:
        return JSONResponse({"error": "not_found"}, status_code=404)

    current_round = int(class_session.get("current_round", "0"))
    timer = get_timer(sim_id, session_id, current_round) if current_round > 0 else None
    remaining = get_remaining_seconds(timer) if timer else 0

    return JSONResponse({
        "status": class_session["status"],
        "current_round": current_round,
        "remaining_seconds": remaining,
    })
