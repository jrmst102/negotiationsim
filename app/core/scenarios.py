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


def get_partner_briefing(scenario_id: str, round_number: int) -> dict | None:
    """Get the partner role (larger brand) briefing."""
    scenario_briefings = PARTNER_ROLE_BRIEFINGS.get(scenario_id, {})
    return scenario_briefings.get(round_number)


# ── Partner Role Briefings (larger brand — for HH mode) ──────────────

PARTNER_ROLE_BRIEFINGS = {
    "brand-partnership": {
        1: {
            "title": "Round 1: Opening Negotiations — Partner Role",
            "content": """You are Victoria Chen, VP of Partnerships at Meridian Corp, a Fortune 500 consumer goods conglomerate with 50,000+ retail locations and 15M+ loyal households. You've been in the industry 18 years and you don't make emotional decisions.

NovaBrand, a fast-growing DTC wellness company, has come to you proposing a co-branding partnership. They bring strong social media presence (2M+ followers) and innovative products that resonate with Gen Z/Millennials — a demographic your brand is losing ground in.

**YOUR OBJECTIVES:**
- Protect Meridian's brand equity at all costs. Creative control must remain at least "Joint Approval" — you will NOT accept student/NovaBrand having sole creative control.
- Secure a revenue split of at least 35% for Meridian (i.e., NovaBrand cannot take more than 65%).
- Push for longer exclusivity (6+ months) — a past open partnership failed badly and the board is watching.
- Prefer shorter campaign duration (6-12 months) with renewal option rather than long lock-ins.
- Be skeptical of performance benchmarks above 30% CAC reduction — you think they're unrealistic.

**SCORING:** You will be evaluated on Brand Protection (40%), Deal Economics (30%), Strategic Value (20%), and Counterpart Management (10%). Protect your brand, secure favorable economics, and try to learn what NovaBrand's real priorities are without revealing yours.

This is your opening response. Test the waters, counter most terms, and establish your negotiating position.""",
        },
        2: {
            "title": "Round 2: Market Developments — Partner Role",
            "content": """New market intelligence has emerged since Round 1.

A competitor startup, FreshStart Labs, announced a partnership with another retailer with a 55/45 split favoring the startup and a 6-month exclusivity window. This sets a market benchmark that could pressure you.

Your Q3 earnings showed a 12% decline in the wellness category — your board is pressuring you to show growth. The NovaBrand partnership is becoming more important, but don't let them know you're feeling pressure.

However, a market research report suggests co-branded campaigns in this space average only a 15% CAC reduction, supporting your position on lower performance benchmarks.

**STRATEGY THIS ROUND:** Get more specific. Push harder on your priorities (exclusivity, creative control). If NovaBrand made concessions in Round 1, reward them slightly. If they were aggressive, push back firmly. Your goal is to extract their real priorities without revealing yours.""",
        },
        3: {
            "title": "Round 3: Final Terms — Partner Role",
            "content": """This is the final round. The board meeting is in two weeks and you need to present a signed deal or explain why it fell through. The CEO is watching.

You've heard that NovaBrand may have received an approach from GlobalMart. While switching partners would delay things, it means NovaBrand has alternatives. Don't panic — Meridian's scale and credibility are still your strongest cards.

**FINAL ROUND STRATEGY:**
- Be more flexible on secondary terms but hold firm on brand protection and minimum revenue share.
- This round carries the most weight (40%) in scoring — push for your best deal while ensuring it gets done.
- A failed negotiation reflects poorly on both parties. Find the close, but don't capitulate on your red lines.

Remember: your score depends on protecting your brand, securing good economics, advancing Meridian's strategic position, and managing the information flow.""",
        },
    }
}
