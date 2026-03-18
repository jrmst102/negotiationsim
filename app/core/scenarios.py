"""
Scenario definitions — Brand Partnership MVP.
===============================================
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class TermField:
    """Definition of a single negotiation term field."""
    key: str
    label: str
    input_type: str      # slider, dropdown, numeric
    min_val: float | None = None
    max_val: float | None = None
    step: float | None = None
    options: list[str] | None = None
    unit: str = ""
    default: float | str | None = None
    section: str = ""
    scoring_weight: str = "Medium"  # High, Medium, Low


BRAND_PARTNERSHIP_TERMS: list[TermField] = [
    TermField(
        key="revenue_split",
        label="Revenue Split (Your %)",
        input_type="slider",
        min_val=20, max_val=80, step=1,
        unit="%", default=50,
        section="Financial Terms",
        scoring_weight="High",
    ),
    TermField(
        key="creative_control",
        label="Creative Control",
        input_type="dropdown",
        options=["Student Approval", "Joint Approval", "Partner Approval"],
        default="Joint Approval",
        section="Creative & Brand",
        scoring_weight="High",
    ),
    TermField(
        key="campaign_duration",
        label="Campaign Duration",
        input_type="numeric",
        min_val=3, max_val=24, step=1,
        unit="months", default=12,
        section="Financial Terms",
        scoring_weight="Medium",
    ),
    TermField(
        key="exclusivity_window",
        label="Exclusivity Window",
        input_type="numeric",
        min_val=0, max_val=12, step=1,
        unit="months", default=3,
        section="Financial Terms",
        scoring_weight="Medium",
    ),
    TermField(
        key="brand_prominence",
        label="Brand Prominence",
        input_type="dropdown",
        options=["Co-equal", "Student Lead", "Partner Lead"],
        default="Co-equal",
        section="Creative & Brand",
        scoring_weight="Low",
    ),
    TermField(
        key="performance_benchmark",
        label="Performance Benchmark (CAC Reduction)",
        input_type="slider",
        min_val=5, max_val=50, step=1,
        unit="%", default=15,
        section="Performance & Exit",
        scoring_weight="Medium",
    ),
    TermField(
        key="min_impressions",
        label="Minimum Guaranteed Impressions",
        input_type="numeric",
        min_val=100000, max_val=5000000, step=50000,
        unit="", default=1000000,
        section="Performance & Exit",
        scoring_weight="Medium",
    ),
    TermField(
        key="exit_clause",
        label="Exit Clause Trigger",
        input_type="dropdown",
        options=["No Exit", "30-day Notice", "Performance-based", "Mutual Agreement"],
        default="Mutual Agreement",
        section="Performance & Exit",
        scoring_weight="Low",
    ),
]


SCENARIOS = [
    {
        "id": "brand-partnership",
        "name": "Brand Partnership",
        "slug": "brand-partnership",
        "description": "Brand Partnership / Co-Branding Deal — Negotiate terms for a strategic marketing partnership with a major consumer brand.",
        "status": "ACTIVE",
        "order": 1,
        "total_rounds": 3,
        "terms": BRAND_PARTNERSHIP_TERMS,
    },
    {
        "id": "retail-shelf-space",
        "name": "Retail Shelf Space",
        "slug": "retail-shelf-space",
        "description": "Negotiate product placement and shelf space terms with a major retail chain.",
        "status": "LOCKED",
        "order": 2,
        "total_rounds": 3,
        "terms": [],
    },
    {
        "id": "media-buy",
        "name": "Media Buy",
        "slug": "media-buy",
        "description": "Negotiate a cross-platform media purchasing agreement with a media conglomerate.",
        "status": "LOCKED",
        "order": 3,
        "total_rounds": 3,
        "terms": [],
    },
]


ROUND_BRIEFINGS = {
    "brand-partnership": {
        1: {
            "title": "Round 1: Opening Negotiations",
            "content": """You are the VP of Marketing at NovaBrand, a fast-growing direct-to-consumer wellness company. Your company has been approached by Meridian Corp, a Fortune 500 consumer goods conglomerate, about a potential co-branding partnership for a new premium product line.

Meridian brings massive distribution reach (50,000+ retail locations), established brand credibility, and a loyal customer base of 15M+ households. However, they have been slow to innovate and their digital presence lags behind yours. Your company brings a strong social media following (2M+ engaged followers), cutting-edge product formulations, and a brand that resonates with Gen Z and Millennials.

Your CEO wants this deal to accelerate growth, but has made clear: you must protect NovaBrand's creative identity and secure economics that reflect the value you bring. Your target is to reduce customer acquisition cost (CAC) by at least 20% through Meridian's distribution network.

Review the proposed terms carefully. This is your opening offer — set the tone for the negotiation.""",
        },
        2: {
            "title": "Round 2: Market Developments",
            "content": """Since your opening round, new market intelligence has emerged. A competitor, FreshStart Labs, just announced a similar partnership with another major retailer. This deal reportedly includes a 55/45 revenue split in the startup's favor and a 6-month exclusivity window.

Additionally, Meridian's Q3 earnings report showed a 12% decline in their wellness category — making your product innovation even more valuable to them. Internal sources suggest they are under board pressure to show growth in the DTC/wellness space.

However, a market research firm has published a report suggesting that co-branded campaigns in this space average only a 15% CAC reduction, not the 25%+ some brands have claimed. This could affect your performance benchmarks.

Use this new information strategically. Consider adjusting your terms to reflect your strengthened negotiating position while maintaining a constructive relationship.""",
        },
        3: {
            "title": "Round 3: Final Terms",
            "content": """This is the final round of negotiation. Both sides need to reach agreement or risk the deal collapsing entirely.

You've learned that Meridian's VP of Partnerships (your counterpart) has been given a hard deadline by their CEO — the board meeting is in two weeks, and they need to present a signed partnership or explain why it fell through. This creates urgency on their side.

At the same time, your CEO has received an unsolicited approach from a different retailer, GlobalMart, offering "competitive terms." While this is a real option, switching to a new negotiation would delay your product launch by at least 3 months.

This round carries the most weight in your final score. Push for your best terms while ensuring the deal gets done. A walkaway here would be costly for both parties.""",
        },
    }
}


def get_scenario(scenario_id: str) -> dict | None:
    for s in SCENARIOS:
        if s["id"] == scenario_id:
            return s
    return None


def get_term_fields(scenario_id: str) -> list[TermField]:
    scenario = get_scenario(scenario_id)
    if not scenario:
        return []
    return scenario.get("terms", [])


def get_briefing(scenario_id: str, round_number: int) -> dict | None:
    scenario_briefings = ROUND_BRIEFINGS.get(scenario_id, {})
    return scenario_briefings.get(round_number)
