"""
Demo simulation provisioning — creates a demo sim with sample users on startup.
================================================================================
"""

from __future__ import annotations

import csv
import io
import logging

from app.auth.password_manager import hash_password
from app.data.csv_manager import write_csv, csv_exists, read_csv_rows, store_exists
from app.storage.store import get_store

logger = logging.getLogger(__name__)

DEMO_SIM_ID = "sim_demo"
REGISTRY_KEY = "admin/simulations.csv"


def provision_demo() -> bool:
    """Create the demo simulation if it doesn't already exist.

    Returns True if a new demo was created, False if it already existed.
    """
    store = get_store()

    already_exists = csv_exists(DEMO_SIM_ID, "users.csv")

    # Create / update registry entry
    existing = []
    if store.exists(REGISTRY_KEY):
        text = store.read_text(REGISTRY_KEY)
        existing = list(csv.DictReader(io.StringIO(text)))

    # Add to registry if not already there
    if not any(r.get("simulation_id") == DEMO_SIM_ID for r in existing):
        existing.append({
            "simulation_id": DEMO_SIM_ID,
            "name": "Demo Simulation",
            "status": "STARTED",
            "created_at": "2026-01-01T00:00:00+00:00",
            "created_by": "system",
        })

    buf = io.StringIO()
    writer = csv.DictWriter(buf,
                            fieldnames=["simulation_id", "name", "status", "created_at", "created_by"],
                            lineterminator="\n")
    writer.writeheader()
    writer.writerows(existing)
    store.write_text(REGISTRY_KEY, buf.getvalue())

    # Preserve stable IDs so existing demo activity remains linked to its users.
    users = [
        {
            "user_id": user_id,
            "username": username,
            "password_hash": hash_password(username),
            "role": "ADMIN",
            "first_name": "Demo",
            "last_name": f"Instructor {number:02d}",
            "email": f"demo.instructor.{number:02d}@example.com",
        }
        for number, (user_id, username) in enumerate((
            ("usr_admin001", "demo_admin"),
            ("usr_prof001", "demo_admin_02"),
        ), start=1)
    ]
    users.extend({
        "user_id": f"usr_student{number:03d}",
        "username": f"demo_student_{number:02d}",
        "password_hash": hash_password(f"demo_student_{number:02d}"),
        "role": "USER",
        "first_name": "Demo",
        "last_name": f"Student {number:02d}",
        "email": f"demo.student.{number:02d}@example.com",
    } for number in range(1, 27))

    fieldnames = ["user_id", "username", "password_hash", "role", "first_name", "last_name", "email"]
    write_csv(DEMO_SIM_ID, "users.csv", fieldnames, users)

    if already_exists:
        logger.info("Demo simulation '%s' users updated (%d users).", DEMO_SIM_ID, len(users))
        return False

    # Initialize empty data files (first time only)
    write_csv(DEMO_SIM_ID, "attempts.csv",
              ["attempt_id", "user_id", "scenario_id", "mode", "status",
               "current_round", "started_at", "completed_at",
               "activity_mode", "session_id", "group_id", "counterpart_type", "role"], [])
    write_csv(DEMO_SIM_ID, "rounds.csv",
              ["round_id", "attempt_id", "round_number", "status", "started_at", "completed_at"], [])
    write_csv(DEMO_SIM_ID, "submissions.csv",
              ["submission_id", "attempt_id", "round_number", "submission_number",
               "terms_json", "ai_response_json", "score_json", "submitted_at"], [])
    write_csv(DEMO_SIM_ID, "scores.csv",
              ["score_id", "attempt_id", "user_id", "scenario_id",
               "economic_value", "strategic_alignment", "relationship_preservation",
               "information_management", "composite_score", "round_scores_json", "scored_at"], [])
    write_csv(DEMO_SIM_ID, "leaderboard.csv",
              ["rank", "user_id", "scenario_id", "activity_mode",
               "average_score", "attempt_count", "percentile"], [])
    write_csv(DEMO_SIM_ID, "aliases.csv", ["user_id", "alias"], [])

    # v1.2 — Groups, sessions, pairings, timers
    write_csv(DEMO_SIM_ID, "groups.csv",
              ["group_id", "sim_id", "name", "scenario_id", "created_by", "created_at"], [])
    write_csv(DEMO_SIM_ID, "group_members.csv",
              ["member_id", "group_id", "user_id", "is_lead", "joined_at"], [])
    write_csv(DEMO_SIM_ID, "class_sessions.csv",
              ["session_id", "sim_id", "scenario_id", "counterpart_mode",
               "round_duration_minutes", "status", "current_round",
               "created_by", "started_at", "completed_at", "created_at"], [])
    write_csv(DEMO_SIM_ID, "session_pairings.csv",
              ["pairing_id", "session_id", "student_group_id", "partner_group_id",
               "counterpart_type", "student_role", "partner_role"], [])
    write_csv(DEMO_SIM_ID, "round_timers.csv",
              ["timer_id", "session_id", "round_number", "started_at",
               "duration_seconds", "paused_at", "extended_seconds"], [])

    logger.info("Demo simulation '%s' provisioned with %d users.", DEMO_SIM_ID, len(users))
    return True
