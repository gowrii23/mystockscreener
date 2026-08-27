"""Position sizing and OTM strike ladder proposals."""

from __future__ import annotations

from typing import Any

from strategy.config import (
    CE_LADDER_OFFSETS,
    FIRST_ENTRY_DEPLOY_PCT,
    MAX_DEPLOYED,
    MIN_PREMIUM_PER_LEG,
    PE_LADDER_OFFSETS,
)


def round_strike(spot: float, offset: int, option_type: str) -> int:
    """Nifty strikes are multiples of 50."""
    atm = int(round(spot / 50) * 50)
    if option_type == "PE":
        return atm - offset
    return atm + offset


def estimate_margin_per_lot() -> int:
    """Rough NRML margin per Nifty short lot for sizing (conservative estimate)."""
    return 85_000


def propose_ladder(spot: float) -> dict[str, Any]:
    lot_margin = estimate_margin_per_lot()
    first_entry_budget = MAX_DEPLOYED * FIRST_ENTRY_DEPLOY_PCT
    max_lots_first_entry = max(1, int(first_entry_budget / lot_margin))

    pe_strikes = [round_strike(spot, o, "PE") for o in PE_LADDER_OFFSETS]
    ce_strikes = [round_strike(spot, o, "CE") for o in CE_LADDER_OFFSETS]

    legs = []
    for strike in pe_strikes:
        legs.append(
            {
                "instrument": f"NIFTY {strike} PE",
                "strike": strike,
                "type": "PE",
                "targetPremium": MIN_PREMIUM_PER_LEG,
                "note": "Verify live premium ≥ ₹40 before entry",
            }
        )
    for strike in ce_strikes:
        legs.append(
            {
                "instrument": f"NIFTY {strike} CE",
                "strike": strike,
                "type": "CE",
                "targetPremium": MIN_PREMIUM_PER_LEG,
                "note": "Verify live premium ≥ ₹40 before entry",
            }
        )

    return {
        "spot": round(spot, 2),
        "firstEntryBudget": int(first_entry_budget),
        "maxDeployed": MAX_DEPLOYED,
        "estimatedMarginPerLot": lot_margin,
        "suggestedLotsPerLeg": 1,
        "maxLotsFirstEntry": max_lots_first_entry,
        "legs": legs,
        "tailHedge": {
            "instrument": f"NIFTY {round_strike(spot, 500, 'PE')} PE (buy)",
            "note": "Far OTM protective put — insurance, not profit center",
        },
    }


def explicit_risk_plan(spot: float) -> dict[str, Any]:
    return {
        "maxLossPerTrade": "Premium at risk + tail beyond hedge; cap at 4% of ₹10L/day",
        "adjustmentTrigger": "Nifty moves 20/15/10 pts (Mon/Tue/Wed) — Saviour-style hedge",
        "hardExit": "Close all 1 day before expiry; no new naked sells after Wed expiry week",
        "bufferRule": "Stop new entries if buffer < ₹4.5L",
    }
