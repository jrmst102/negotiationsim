"""
Group management — CRUD for negotiation groups (v1.2).
=======================================================
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.data.csv_manager import read_csv_rows, write_csv


GROUPS_FIELDS = ["group_id", "sim_id", "name", "scenario_id", "created_by", "created_at"]
MEMBERS_FIELDS = ["member_id", "group_id", "user_id", "is_lead", "joined_at"]


def list_groups(sim_id: str) -> list[dict]:
    return read_csv_rows(sim_id, "groups.csv")


def get_group(sim_id: str, group_id: str) -> dict | None:
    for g in list_groups(sim_id):
        if g["group_id"] == group_id:
            return g
    return None


def create_group(sim_id: str, name: str, scenario_id: str, created_by: str) -> dict:
    groups = list_groups(sim_id)
    group = {
        "group_id": f"grp_{uuid.uuid4().hex[:12]}",
        "sim_id": sim_id,
        "name": name,
        "scenario_id": scenario_id,
        "created_by": created_by,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    groups.append(group)
    write_csv(sim_id, "groups.csv", GROUPS_FIELDS, groups)
    return group


def delete_group(sim_id: str, group_id: str) -> bool:
    groups = list_groups(sim_id)
    filtered = [g for g in groups if g["group_id"] != group_id]
    if len(filtered) == len(groups):
        return False
    write_csv(sim_id, "groups.csv", GROUPS_FIELDS, filtered)
    # Also remove members
    members = read_csv_rows(sim_id, "group_members.csv")
    members = [m for m in members if m["group_id"] != group_id]
    write_csv(sim_id, "group_members.csv", MEMBERS_FIELDS, members)
    return True


def update_group(sim_id: str, group_id: str, **updates) -> dict | None:
    groups = list_groups(sim_id)
    for g in groups:
        if g["group_id"] == group_id:
            for k, v in updates.items():
                if k in GROUPS_FIELDS:
                    g[k] = v
            write_csv(sim_id, "groups.csv", GROUPS_FIELDS, groups)
            return g
    return None


# ── Members ───────────────────────────────────────────────────────────

def list_members(sim_id: str, group_id: str) -> list[dict]:
    all_members = read_csv_rows(sim_id, "group_members.csv")
    return [m for m in all_members if m["group_id"] == group_id]


def add_member(sim_id: str, group_id: str, user_id: str, is_lead: bool = False) -> dict:
    all_members = read_csv_rows(sim_id, "group_members.csv")

    # Check if already a member
    for m in all_members:
        if m["group_id"] == group_id and m["user_id"] == user_id:
            return m

    member = {
        "member_id": f"mbr_{uuid.uuid4().hex[:12]}",
        "group_id": group_id,
        "user_id": user_id,
        "is_lead": str(is_lead),
        "joined_at": datetime.now(timezone.utc).isoformat(),
    }
    all_members.append(member)
    write_csv(sim_id, "group_members.csv", MEMBERS_FIELDS, all_members)
    return member


def remove_member(sim_id: str, group_id: str, user_id: str) -> bool:
    all_members = read_csv_rows(sim_id, "group_members.csv")
    filtered = [m for m in all_members if not (m["group_id"] == group_id and m["user_id"] == user_id)]
    if len(filtered) == len(all_members):
        return False
    write_csv(sim_id, "group_members.csv", MEMBERS_FIELDS, filtered)
    return True


def set_lead(sim_id: str, group_id: str, user_id: str) -> bool:
    all_members = read_csv_rows(sim_id, "group_members.csv")
    found = False
    for m in all_members:
        if m["group_id"] == group_id:
            m["is_lead"] = str(m["user_id"] == user_id)
            if m["user_id"] == user_id:
                found = True
    if found:
        write_csv(sim_id, "group_members.csv", MEMBERS_FIELDS, all_members)
    return found


def get_user_group(sim_id: str, user_id: str, scenario_id: str | None = None) -> dict | None:
    """Find the group a user belongs to, optionally filtered by scenario."""
    all_members = read_csv_rows(sim_id, "group_members.csv")
    for m in all_members:
        if m["user_id"] == user_id:
            group = get_group(sim_id, m["group_id"])
            if group and (scenario_id is None or group.get("scenario_id") == scenario_id):
                return group
    return None


def is_lead(sim_id: str, group_id: str, user_id: str) -> bool:
    members = list_members(sim_id, group_id)
    for m in members:
        if m["user_id"] == user_id and m.get("is_lead") in ("True", "true", "1"):
            return True
    return False


def auto_assign_groups(sim_id: str, scenario_id: str, group_size: int, created_by: str) -> list[dict]:
    """Auto-assign unassigned students to groups of the specified size."""
    users = read_csv_rows(sim_id, "users.csv")
    students = [u for u in users if u.get("role") == "USER"]

    # Find students already in a group for this scenario
    groups = list_groups(sim_id)
    scenario_groups = [g for g in groups if g.get("scenario_id") == scenario_id]
    all_members = read_csv_rows(sim_id, "group_members.csv")
    assigned_ids = set()
    for g in scenario_groups:
        for m in all_members:
            if m["group_id"] == g["group_id"]:
                assigned_ids.add(m["user_id"])

    unassigned = [s for s in students if s["user_id"] not in assigned_ids]

    created_groups = []
    group_num = len(scenario_groups) + 1
    for i in range(0, len(unassigned), group_size):
        chunk = unassigned[i:i + group_size]
        if not chunk:
            break
        group = create_group(sim_id, f"Group {group_num}", scenario_id, created_by)
        for j, student in enumerate(chunk):
            add_member(sim_id, group["group_id"], student["user_id"], is_lead=(j == 0))
        created_groups.append(group)
        group_num += 1

    return created_groups
