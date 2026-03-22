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

    # Create users — matches DecisionLab classlist
    users = [
        {
            "user_id": "usr_admin001",
            "username": "jm10697",
            "password_hash": hash_password("LimeKoala1!"),
            "role": "ADMIN",
            "first_name": "Jose",
            "last_name": "Mendoza",
            "email": "jm10697@nyu.edu",
        },
        {
            "user_id": "usr_prof001",
            "username": "josermendoza",
            "password_hash": hash_password("LimeKoala1!"),
            "role": "ADMIN",
            "first_name": "Jose",
            "last_name": "Mendoza",
            "email": "josermendoza@icloud.com",
        },
        {
            "user_id": "usr_student001",
            "username": "ma9876",
            "password_hash": hash_password("RedLion1"),
            "role": "USER",
            "first_name": "Montserrat",
            "last_name": "Avila Muñoz",
            "email": "ma9876@nyu.edu",
        },
        {
            "user_id": "usr_student002",
            "username": "cab10151",
            "password_hash": hash_password("BlueTiger2"),
            "role": "USER",
            "first_name": "Carlos",
            "last_name": "Bernal",
            "email": "cab10151@nyu.edu",
        },
        {
            "user_id": "usr_student003",
            "username": "anb6060",
            "password_hash": hash_password("GreenBear3"),
            "role": "USER",
            "first_name": "Annika",
            "last_name": "Brown",
            "email": "anb6060@nyu.edu",
        },
        {
            "user_id": "usr_student004",
            "username": "vac340",
            "password_hash": hash_password("YellowWolf4"),
            "role": "USER",
            "first_name": "Valerie",
            "last_name": "Cadena",
            "email": "vac340@nyu.edu",
        },
        {
            "user_id": "usr_student005",
            "username": "jcg533",
            "password_hash": hash_password("OrangeDeer5"),
            "role": "USER",
            "first_name": "Juan Pablo",
            "last_name": "Cajiga Gordillo",
            "email": "jcg533@nyu.edu",
        },
        {
            "user_id": "usr_student006",
            "username": "cd4020",
            "password_hash": hash_password("PurpleEagle6"),
            "role": "USER",
            "first_name": "Charlotte",
            "last_name": "Detwiler",
            "email": "cd4020@nyu.edu",
        },
        {
            "user_id": "usr_student007",
            "username": "cwd8685",
            "password_hash": hash_password("WhiteFox7"),
            "role": "USER",
            "first_name": "Chris",
            "last_name": "Dillmeier",
            "email": "cwd8685@nyu.edu",
        },
        {
            "user_id": "usr_student008",
            "username": "xf931",
            "password_hash": hash_password("BlackHawk8"),
            "role": "USER",
            "first_name": "Xuke",
            "last_name": "Feng",
            "email": "xf931@nyu.edu",
        },
        {
            "user_id": "usr_student009",
            "username": "kk5887",
            "password_hash": hash_password("SilverLynx9"),
            "role": "USER",
            "first_name": "Keri",
            "last_name": "Kaleja",
            "email": "kk5887@nyu.edu",
        },
        {
            "user_id": "usr_student010",
            "username": "hl6614",
            "password_hash": hash_password("GoldPanda1"),
            "role": "USER",
            "first_name": "Hallie",
            "last_name": "Lau",
            "email": "hl6614@nyu.edu",
        },
        {
            "user_id": "usr_student011",
            "username": "nl3125",
            "password_hash": hash_password("BrownOtter2"),
            "role": "USER",
            "first_name": "Natalie",
            "last_name": "Lee",
            "email": "nl3125@nyu.edu",
        },
        {
            "user_id": "usr_student012",
            "username": "jl17781",
            "password_hash": hash_password("TealRaven3"),
            "role": "USER",
            "first_name": "Jiayi",
            "last_name": "Li",
            "email": "jl17781@nyu.edu",
        },
        {
            "user_id": "usr_student013",
            "username": "xl6160",
            "password_hash": hash_password("PinkShark4"),
            "role": "USER",
            "first_name": "Xinjue",
            "last_name": "Li",
            "email": "xl6160@nyu.edu",
        },
        {
            "user_id": "usr_student014",
            "username": "chl6920",
            "password_hash": hash_password("GrayWhale5"),
            "role": "USER",
            "first_name": "Cheryl",
            "last_name": "Liang",
            "email": "chl6920@nyu.edu",
        },
        {
            "user_id": "usr_student015",
            "username": "wl3557",
            "password_hash": hash_password("VioletZebra6"),
            "role": "USER",
            "first_name": "Weilin",
            "last_name": "Liang",
            "email": "wl3557@nyu.edu",
        },
        {
            "user_id": "usr_student016",
            "username": "mcl9746",
            "password_hash": hash_password("IndigoSwan7"),
            "role": "USER",
            "first_name": "Camila",
            "last_name": "Lievano",
            "email": "mcl9746@nyu.edu",
        },
        {
            "user_id": "usr_student017",
            "username": "rl5858",
            "password_hash": hash_password("MaroonOwl8"),
            "role": "USER",
            "first_name": "Skylar",
            "last_name": "Lin",
            "email": "rl5858@nyu.edu",
        },
        {
            "user_id": "usr_student018",
            "username": "jm11756",
            "password_hash": hash_password("NavyFalcon9"),
            "role": "USER",
            "first_name": "Juliana",
            "last_name": "Martinez Aparicio",
            "email": "jm11756@nyu.edu",
        },
        {
            "user_id": "usr_student019",
            "username": "jm11696",
            "password_hash": hash_password("AquaDolphin2"),
            "role": "USER",
            "first_name": "Kristen",
            "last_name": "Miao",
            "email": "jm11696@nyu.edu",
        },
        {
            "user_id": "usr_student020",
            "username": "vm2806",
            "password_hash": hash_password("CoralCheetah3"),
            "role": "USER",
            "first_name": "Vanessa Cibelle",
            "last_name": "Moura Caxias",
            "email": "vm2806@nyu.edu",
        },
        {
            "user_id": "usr_student021",
            "username": "jp7862",
            "password_hash": hash_password("BeigeBadger4"),
            "role": "USER",
            "first_name": "Jiaying",
            "last_name": "Pan",
            "email": "jp7862@nyu.edu",
        },
        {
            "user_id": "usr_student022",
            "username": "sfr9778",
            "password_hash": hash_password("CyanCobra5"),
            "role": "USER",
            "first_name": "Sasha",
            "last_name": "Rachmadi",
            "email": "sfr9778@nyu.edu",
        },
        {
            "user_id": "usr_student023",
            "username": "lmv9494",
            "password_hash": hash_password("OliveOcelot7"),
            "role": "USER",
            "first_name": "Lanie",
            "last_name": "Veazey",
            "email": "lmv9494@nyu.edu",
        },
        {
            "user_id": "usr_student024",
            "username": "sw7168",
            "password_hash": hash_password("MagentaMoose6"),
            "role": "USER",
            "first_name": "Senette",
            "last_name": "Wiah",
            "email": "sw7168@nyu.edu",
        },
        {
            "user_id": "usr_student025",
            "username": "fz2481",
            "password_hash": hash_password("PeachPython8"),
            "role": "USER",
            "first_name": "Fangyuan",
            "last_name": "Zheng",
            "email": "fz2481@nyu.edu",
        },
        {
            "user_id": "usr_student026",
            "username": "hz4386",
            "password_hash": hash_password("RubyRhino9"),
            "role": "USER",
            "first_name": "Haihua",
            "last_name": "Zhu",
            "email": "hz4386@nyu.edu",
        },
    ]

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
