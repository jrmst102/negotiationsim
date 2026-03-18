"""
Anonymous alias generation — Adjective + Noun pattern.
========================================================
"""

from __future__ import annotations

import random

ADJECTIVES = [
    "Steel", "Coral", "Iron", "Silver", "Crimson", "Azure", "Golden",
    "Shadow", "Amber", "Frost", "Jade", "Onyx", "Ruby", "Sapphire",
    "Copper", "Crystal", "Thunder", "Storm", "Arctic", "Solar",
    "Cobalt", "Emerald", "Titanium", "Obsidian", "Platinum", "Velvet",
    "Midnight", "Scarlet", "Ivory", "Neon",
]

NOUNS = [
    "Falcon", "Strategist", "Compass", "Phoenix", "Voyager", "Pioneer",
    "Sentinel", "Navigator", "Architect", "Catalyst", "Vanguard",
    "Ranger", "Hawk", "Titan", "Oracle", "Pathfinder", "Maverick",
    "Phantom", "Wolf", "Eagle", "Leopard", "Shark", "Raptor",
    "Dragon", "Lynx", "Panther", "Condor", "Cobra", "Mustang", "Fox",
]


def generate_alias(existing_aliases: list[str] | None = None) -> str:
    """Generate a unique Adjective + Noun alias.

    Avoids collisions with existing_aliases if provided.
    """
    existing = set(existing_aliases or [])
    attempts = 0
    while attempts < 200:
        alias = f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)}"
        if alias not in existing:
            return alias
        attempts += 1
    # Fallback with number suffix
    return f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.randint(100, 999)}"
