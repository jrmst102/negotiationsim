"""
Scoring engine — objective rubric-based scoring for negotiation attempts.
=========================================================================
Components:
  - Economic Value (40%)
  - Strategic Alignment (30%)
  - Relationship Preservation (20%)
  - Information Management (10%)

Round weights: R1=25%, R2=35%, R3=40%
"""

from __future__ import annotations


COMPONENT_WEIGHTS = {
    "economic_value": 0.40,
    "strategic_alignment": 0.30,
    "relationship_preservation": 0.20,
    "information_management": 0.10,
}

# Partner role (larger brand) has a different rubric
PARTNER_COMPONENT_WEIGHTS = {
    "brand_protection": 0.40,
    "deal_economics": 0.30,
    "strategic_value": 0.20,
    "counterpart_management": 0.10,
}

ROUND_WEIGHTS = {1: 0.25, 2: 0.35, 3: 0.40}


def compute_round_score(ai_score: dict, role: str = "STUDENT_ROLE") -> dict:
    """Given AI-returned component scores (0-100), compute weighted round score.

    For STUDENT_ROLE: uses economic_value, strategic_alignment, etc.
    For PARTNER_ROLE: uses brand_protection, deal_economics, etc.
    """
    weights = PARTNER_COMPONENT_WEIGHTS if role == "PARTNER_ROLE" else COMPONENT_WEIGHTS
    components = {}
    for key in weights:
        components[key] = float(ai_score.get(key, 0))

    composite = sum(components[k] * weights[k] for k in weights)

    return {
        **components,
        "composite": round(composite, 1),
    }


def compute_attempt_score(round_scores: list[dict], role: str = "STUDENT_ROLE") -> dict:
    """Compute the final attempt score from per-round scores."""
    weights = PARTNER_COMPONENT_WEIGHTS if role == "PARTNER_ROLE" else COMPONENT_WEIGHTS
    final = {k: 0.0 for k in weights}
    final["composite"] = 0.0

    for i, rs in enumerate(round_scores):
        round_num = i + 1
        weight = ROUND_WEIGHTS.get(round_num, 0)
        for k in weights:
            final[k] += float(rs.get(k, 0)) * weight
        final["composite"] += float(rs.get("composite", 0)) * weight

    return {k: round(v, 1) for k, v in final.items()}


def compute_percentile(student_score: float, all_scores: list[float]) -> float:
    """Compute percentile: % of scores below the student's score."""
    if not all_scores:
        return 0.0
    below = sum(1 for s in all_scores if s < student_score)
    return round(100.0 * below / len(all_scores), 1)
