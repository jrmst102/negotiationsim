"""
OpenAI client — GPT-4 Mini integration for AI negotiation counterpart.
=======================================================================
"""

from __future__ import annotations

import json
import logging
import os

from openai import OpenAI

from app.ai.prompts import build_negotiation_prompt, build_hh_evaluator_prompt

logger = logging.getLogger(__name__)


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")
    return OpenAI(api_key=api_key)


def evaluate_submission(
    round_number: int,
    briefing: str,
    submission: dict,
    history: list[dict],
    cumulative_trust: float = 0.0,
) -> dict:
    """Send a term sheet submission to GPT-4 Mini and return the structured response.

    Returns a dict with keys: terms, narrative, deal_status, trust_delta, scores.
    """
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    max_tokens = int(os.environ.get("OPENAI_MAX_TOKENS", "2000"))

    messages = build_negotiation_prompt(
        round_number=round_number,
        briefing=briefing,
        submission=submission,
        history=history,
        cumulative_trust=cumulative_trust,
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON: %s", content[:500])
            return _fallback_response(submission)

        # Validate required keys
        for key in ("terms", "narrative", "deal_status", "trust_delta", "scores"):
            if key not in result:
                logger.warning("AI response missing key '%s', using fallback", key)
                return _fallback_response(submission)

        return result
    except Exception as exc:
        logger.warning("AI call failed (%s), using fallback response", exc)
        return _fallback_response(submission)


# Victoria Chen's preferred positions (the counterparty's ideal terms)
_COUNTERPARTY_TARGETS = {
    "revenue_split": 35.0,           # She wants a lower revenue share for the student
    "creative_control": "Partner Approval",  # She wants her brand to have control
    "campaign_duration": 18,         # She prefers longer campaigns
    "exclusivity_window": 9,         # She wants a longer exclusivity window
    "brand_prominence": "Partner Lead",  # She wants her brand up front
    "performance_benchmark": 25.0,   # She wants aggressive performance targets
    "min_impressions": 3000000,      # She wants higher guarantees
    "exit_clause": "No Exit",        # She prefers no easy exit
}


def _fallback_response(submission: dict) -> dict:
    """Generate a realistic fallback response that pushes back on the student's offer."""
    terms = {}
    for key, value in submission.items():
        target = _COUNTERPARTY_TARGETS.get(key)
        if target is None:
            # Unknown term — accept as-is
            terms[key] = {
                "status": "accept",
                "counter_value": value,
                "reasoning": "This works for us.",
            }
            continue

        # For numeric terms, push halfway toward the counterparty target
        if isinstance(target, (int, float)) and isinstance(value, (int, float)):
            diff = abs(float(value) - float(target))
            if diff < 1:  # Close enough — accept
                terms[key] = {
                    "status": "accept",
                    "counter_value": value,
                    "reasoning": "We can agree on this.",
                }
            else:
                counter = round(float(value) + (float(target) - float(value)) * 0.6, 1)
                terms[key] = {
                    "status": "counter",
                    "counter_value": counter,
                    "reasoning": f"We'd need to move closer to {target} on this one.",
                }
        else:
            # Dropdown / string terms
            if str(value) == str(target):
                terms[key] = {
                    "status": "accept",
                    "counter_value": value,
                    "reasoning": "Agreed.",
                }
            else:
                terms[key] = {
                    "status": "counter",
                    "counter_value": target,
                    "reasoning": f"We'd strongly prefer \"{target}\" here.",
                }

    return {
        "terms": terms,
        "narrative": "I appreciate you bringing this to the table. However, several of these terms don't quite work for us as proposed. Our brand brings significant market reach and consumer trust, so we need the deal structure to reflect that. I've marked up the areas where we'd need movement — let's see if we can find a middle ground in the next round.",
        "deal_status": "FAR",
        "trust_delta": -0.5,
        "scores": {
            "economic_value": 45,
            "strategic_alignment": 40,
            "relationship_preservation": 55,
            "information_management": 50,
        },
    }


# ── Human-Human Evaluator ────────────────────────────────────────────

def evaluate_hh_exchange(
    round_number: int,
    student_submission: dict,
    partner_submission: dict,
    history: list[dict],
) -> dict:
    """Evaluate both sides of a Human-Human exchange.

    Returns a dict with:
      - student_scores: {economic_value, strategic_alignment, ...}
      - partner_scores: {brand_protection, deal_economics, ...}
      - narrative: observer-perspective analysis
      - term_comparison: per-term accept/counter/reject for display
    """
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    max_tokens = int(os.environ.get("OPENAI_MAX_TOKENS", "2000"))

    messages = build_hh_evaluator_prompt(
        round_number=round_number,
        student_submission=student_submission,
        partner_submission=partner_submission,
        history=history,
    )

    try:
        client = _get_client()
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.5,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        try:
            result = json.loads(content)
        except json.JSONDecodeError:
            logger.error("Failed to parse HH evaluator response: %s", content[:500])
            return _fallback_hh_evaluation(student_submission, partner_submission)

        for key in ("student_scores", "partner_scores", "narrative", "term_comparison"):
            if key not in result:
                logger.warning("HH evaluation missing key '%s', using fallback", key)
                return _fallback_hh_evaluation(student_submission, partner_submission)

        return result
    except Exception as exc:
        logger.warning("HH evaluation failed (%s), using fallback", exc)
        return _fallback_hh_evaluation(student_submission, partner_submission)


def _fallback_hh_evaluation(student_sub: dict, partner_sub: dict) -> dict:
    """Deterministic fallback for HH evaluation."""
    term_comparison = {}
    for key in student_sub:
        s_val = student_sub[key]
        p_val = partner_sub.get(key, s_val)
        if str(s_val) == str(p_val):
            term_comparison[key] = {
                "status": "accept",
                "student_value": s_val,
                "partner_value": p_val,
                "reasoning": "Both sides agree on this term.",
            }
        else:
            term_comparison[key] = {
                "status": "counter",
                "student_value": s_val,
                "partner_value": p_val,
                "reasoning": "The two sides have different positions on this term.",
            }

    return {
        "student_scores": {
            "economic_value": 50,
            "strategic_alignment": 50,
            "relationship_preservation": 50,
            "information_management": 50,
        },
        "partner_scores": {
            "brand_protection": 50,
            "deal_economics": 50,
            "strategic_value": 50,
            "counterpart_management": 50,
        },
        "narrative": "Both sides have presented their initial positions. There are areas of agreement and areas that need further negotiation. The exchange shows a pragmatic approach from both parties.",
        "term_comparison": term_comparison,
    }
