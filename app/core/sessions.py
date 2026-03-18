"""
Class session management — instructor-paced synchronous sessions (v1.2).
=========================================================================
"""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from app.data.csv_manager import read_csv_rows, write_csv

SESSION_FIELDS = [
    "session_id", "sim_id", "scenario_id", "counterpart_mode",
    "round_duration_minutes", "status", "current_round",
    "created_by", "started_at", "completed_at", "created_at",
]

PAIRING_FIELDS = [
    "pairing_id", "session_id", "student_group_id", "partner_group_id",
    "counterpart_type", "student_role", "partner_role",
]

TIMER_FIELDS = [
    "timer_id", "session_id", "round_number", "started_at",
    "duration_seconds", "paused_at", "extended_seconds",
]


def list_sessions(sim_id: str) -> list[dict]:
    return read_csv_rows(sim_id, "class_sessions.csv")


def get_session(sim_id: str, session_id: str) -> dict | None:
    for s in list_sessions(sim_id):
        if s["session_id"] == session_id:
            return s
    return None


def create_session(
    sim_id: str,
    scenario_id: str,
    counterpart_mode: str,
    round_duration_minutes: int,
    created_by: str,
) -> dict:
    sessions = list_sessions(sim_id)
    session = {
        "session_id": f"ses_{uuid.uuid4().hex[:12]}",
        "sim_id": sim_id,
        "scenario_id": scenario_id,
        "counterpart_mode": counterpart_mode,  # ALL_HH, ALL_HA, MIXED
        "round_duration_minutes": str(round_duration_minutes),
        "status": "DRAFT",
        "current_round": "0",
        "created_by": created_by,
        "started_at": "",
        "completed_at": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    sessions.append(session)
    write_csv(sim_id, "class_sessions.csv", SESSION_FIELDS, sessions)
    return session


def update_session(sim_id: str, session_id: str, **updates) -> dict | None:
    sessions = list_sessions(sim_id)
    for s in sessions:
        if s["session_id"] == session_id:
            for k, v in updates.items():
                if k in SESSION_FIELDS:
                    s[k] = str(v) if v is not None else ""
            write_csv(sim_id, "class_sessions.csv", SESSION_FIELDS, sessions)
            return s
    return None


# ── Pairings ──────────────────────────────────────────────────────────

def list_pairings(sim_id: str, session_id: str) -> list[dict]:
    all_p = read_csv_rows(sim_id, "session_pairings.csv")
    return [p for p in all_p if p["session_id"] == session_id]


def get_pairing_for_group(sim_id: str, session_id: str, group_id: str) -> dict | None:
    for p in list_pairings(sim_id, session_id):
        if p["student_group_id"] == group_id or p.get("partner_group_id") == group_id:
            return p
    return None


def generate_pairings(sim_id: str, session_id: str, group_ids: list[str]) -> list[dict]:
    """Auto-generate pairings based on the session's counterpart mode."""
    session = get_session(sim_id, session_id)
    if not session:
        return []

    mode = session["counterpart_mode"]
    all_pairings = read_csv_rows(sim_id, "session_pairings.csv")

    # Remove existing pairings for this session
    all_pairings = [p for p in all_pairings if p["session_id"] != session_id]

    shuffled = list(group_ids)
    random.shuffle(shuffled)
    new_pairings = []

    if mode == "ALL_HA":
        # Every group plays against AI
        for gid in shuffled:
            pairing = {
                "pairing_id": f"pair_{uuid.uuid4().hex[:12]}",
                "session_id": session_id,
                "student_group_id": gid,
                "partner_group_id": "",
                "counterpart_type": "HA",
                "student_role": "STUDENT_ROLE",
                "partner_role": "",
            }
            new_pairings.append(pairing)

    elif mode == "ALL_HH":
        # Pair groups together
        for i in range(0, len(shuffled) - 1, 2):
            pairing = {
                "pairing_id": f"pair_{uuid.uuid4().hex[:12]}",
                "session_id": session_id,
                "student_group_id": shuffled[i],
                "partner_group_id": shuffled[i + 1],
                "counterpart_type": "HH",
                "student_role": "STUDENT_ROLE",
                "partner_role": "PARTNER_ROLE",
            }
            new_pairings.append(pairing)
        # Odd group goes to AI
        if len(shuffled) % 2 == 1:
            pairing = {
                "pairing_id": f"pair_{uuid.uuid4().hex[:12]}",
                "session_id": session_id,
                "student_group_id": shuffled[-1],
                "partner_group_id": "",
                "counterpart_type": "HA",
                "student_role": "STUDENT_ROLE",
                "partner_role": "",
            }
            new_pairings.append(pairing)

    elif mode == "MIXED":
        # Half HH, half HA (randomly)
        hh_count = len(shuffled) // 2  # pairs, not groups
        # Need pairs of 2 for HH
        hh_groups = hh_count * 2
        for i in range(0, min(hh_groups, len(shuffled)) - 1, 2):
            pairing = {
                "pairing_id": f"pair_{uuid.uuid4().hex[:12]}",
                "session_id": session_id,
                "student_group_id": shuffled[i],
                "partner_group_id": shuffled[i + 1],
                "counterpart_type": "HH",
                "student_role": "STUDENT_ROLE",
                "partner_role": "PARTNER_ROLE",
            }
            new_pairings.append(pairing)

        # Remaining groups play AI
        for gid in shuffled[hh_groups:]:
            pairing = {
                "pairing_id": f"pair_{uuid.uuid4().hex[:12]}",
                "session_id": session_id,
                "student_group_id": gid,
                "partner_group_id": "",
                "counterpart_type": "HA",
                "student_role": "STUDENT_ROLE",
                "partner_role": "",
            }
            new_pairings.append(pairing)

    all_pairings.extend(new_pairings)
    write_csv(sim_id, "session_pairings.csv", PAIRING_FIELDS, all_pairings)
    return new_pairings


def update_pairing(sim_id: str, pairing_id: str, **updates) -> dict | None:
    all_p = read_csv_rows(sim_id, "session_pairings.csv")
    for p in all_p:
        if p["pairing_id"] == pairing_id:
            for k, v in updates.items():
                if k in PAIRING_FIELDS:
                    p[k] = str(v) if v is not None else ""
            write_csv(sim_id, "session_pairings.csv", PAIRING_FIELDS, all_p)
            return p
    return None


# ── Timer ─────────────────────────────────────────────────────────────

def get_timer(sim_id: str, session_id: str, round_number: int) -> dict | None:
    timers = read_csv_rows(sim_id, "round_timers.csv")
    for t in timers:
        if t["session_id"] == session_id and t["round_number"] == str(round_number):
            return t
    return None


def start_timer(sim_id: str, session_id: str, round_number: int, duration_seconds: int) -> dict:
    timers = read_csv_rows(sim_id, "round_timers.csv")
    now = datetime.now(timezone.utc).isoformat()
    timer = {
        "timer_id": f"tmr_{uuid.uuid4().hex[:12]}",
        "session_id": session_id,
        "round_number": str(round_number),
        "started_at": now,
        "duration_seconds": str(duration_seconds),
        "paused_at": "",
        "extended_seconds": "0",
    }
    timers.append(timer)
    write_csv(sim_id, "round_timers.csv", TIMER_FIELDS, timers)
    return timer


def pause_timer(sim_id: str, session_id: str, round_number: int) -> dict | None:
    timers = read_csv_rows(sim_id, "round_timers.csv")
    now = datetime.now(timezone.utc).isoformat()
    for t in timers:
        if t["session_id"] == session_id and t["round_number"] == str(round_number):
            if not t["paused_at"]:
                t["paused_at"] = now
            write_csv(sim_id, "round_timers.csv", TIMER_FIELDS, timers)
            return t
    return None


def resume_timer(sim_id: str, session_id: str, round_number: int) -> dict | None:
    timers = read_csv_rows(sim_id, "round_timers.csv")
    now = datetime.now(timezone.utc)
    for t in timers:
        if t["session_id"] == session_id and t["round_number"] == str(round_number):
            if t["paused_at"]:
                # Add the paused duration to extended_seconds
                paused_at = datetime.fromisoformat(t["paused_at"])
                paused_duration = int((now - paused_at).total_seconds())
                t["extended_seconds"] = str(int(t.get("extended_seconds", "0")) + paused_duration)
                t["paused_at"] = ""
            write_csv(sim_id, "round_timers.csv", TIMER_FIELDS, timers)
            return t
    return None


def extend_timer(sim_id: str, session_id: str, round_number: int, extra_seconds: int) -> dict | None:
    timers = read_csv_rows(sim_id, "round_timers.csv")
    for t in timers:
        if t["session_id"] == session_id and t["round_number"] == str(round_number):
            t["extended_seconds"] = str(int(t.get("extended_seconds", "0")) + extra_seconds)
            write_csv(sim_id, "round_timers.csv", TIMER_FIELDS, timers)
            return t
    return None


def get_remaining_seconds(timer: dict) -> int:
    """Calculate remaining seconds on a timer."""
    if not timer or not timer.get("started_at"):
        return 0

    started = datetime.fromisoformat(timer["started_at"])
    duration = int(timer.get("duration_seconds", "0"))
    extended = int(timer.get("extended_seconds", "0"))
    now = datetime.now(timezone.utc)

    if timer.get("paused_at"):
        # Timer is paused — calculate based on pause time
        now = datetime.fromisoformat(timer["paused_at"])

    elapsed = int((now - started).total_seconds())
    remaining = (duration + extended) - elapsed
    return max(0, remaining)


# ── Session Lifecycle ─────────────────────────────────────────────────

def start_session(sim_id: str, session_id: str) -> dict | None:
    """Transition session from DRAFT to ACTIVE, start Round 1."""
    session = get_session(sim_id, session_id)
    if not session or session["status"] != "DRAFT":
        return None

    now = datetime.now(timezone.utc).isoformat()
    duration_min = int(session.get("round_duration_minutes", "10"))

    session = update_session(
        sim_id, session_id,
        status="ACTIVE",
        current_round=1,
        started_at=now,
    )
    start_timer(sim_id, session_id, 1, duration_min * 60)
    return session


def advance_round(sim_id: str, session_id: str) -> dict | None:
    """Close the current round and advance to the next."""
    session = get_session(sim_id, session_id)
    if not session or session["status"] != "ACTIVE":
        return None

    current = int(session.get("current_round", "1"))
    next_round = current + 1

    if next_round > 3:
        return end_session(sim_id, session_id)

    duration_min = int(session.get("round_duration_minutes", "10"))
    session = update_session(sim_id, session_id, current_round=next_round)
    start_timer(sim_id, session_id, next_round, duration_min * 60)
    return session


def end_session(sim_id: str, session_id: str) -> dict | None:
    """Mark session as COMPLETED."""
    now = datetime.now(timezone.utc).isoformat()
    return update_session(sim_id, session_id, status="COMPLETED", completed_at=now)


def get_active_session(sim_id: str, scenario_id: str | None = None) -> dict | None:
    """Get the currently active class session, optionally filtered by scenario."""
    for s in list_sessions(sim_id):
        if s["status"] == "ACTIVE":
            if scenario_id is None or s["scenario_id"] == scenario_id:
                return s
    return None
