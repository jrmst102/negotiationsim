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

    # Check if demo already exists (users file present)
    if csv_exists(DEMO_SIM_ID, "users.csv"):
        return False

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

    # Create users
    users = [
        {
            "user_id": "usr_admin001",
            "username": "professor",
            "password_hash": hash_password("Secret123!"),
            "role": "ADMIN",
            "first_name": "Professor",
            "last_name": "Admin",
            "email": "admin@example.com",
        },
        {
            "user_id": "usr_student001",
            "username": "student1",
            "password_hash": hash_password("student1"),
            "role": "USER",
            "first_name": "Alice",
            "last_name": "Johnson",
            "email": "alice@example.com",
        },
        {
            "user_id": "usr_student002",
            "username": "student2",
            "password_hash": hash_password("student2"),
            "role": "USER",
            "first_name": "Bob",
            "last_name": "Smith",
            "email": "bob@example.com",
        },
        {
            "user_id": "usr_student003",
            "username": "student3",
            "password_hash": hash_password("student3"),
            "role": "USER",
            "first_name": "Carol",
            "last_name": "Williams",
            "email": "carol@example.com",
        },
    ]

    fieldnames = ["user_id", "username", "password_hash", "role", "first_name", "last_name", "email"]
    write_csv(DEMO_SIM_ID, "users.csv", fieldnames, users)

    # Initialize empty data files
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
               "round_duration_seconds", "status", "current_round",
               "created_by", "created_at", "started_at", "completed_at"], [])
    write_csv(DEMO_SIM_ID, "session_pairings.csv",
              ["pairing_id", "session_id", "student_group_id", "partner_group_id",
               "counterpart_type", "status"], [])
    write_csv(DEMO_SIM_ID, "round_timers.csv",
              ["timer_id", "session_id", "round_number", "duration_seconds",
               "started_at", "paused_at", "elapsed_before_pause"], [])

    logger.info("Demo simulation '%s' provisioned with 4 users.", DEMO_SIM_ID)
    return True
