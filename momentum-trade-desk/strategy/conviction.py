"""Five-point conviction checklist — paper mode only."""

from __future__ import annotations

from datetime import date
from typing import Any

from strategy.blackout import days_to_next_blackout, is_blackout_day, is_expiry_week_gamma_zone
from strategy.config import MIN_PREMIUM_PER_LEG
from strategy.gap_check import get_overnight_gap
from strategy.kill_switches import check as kill_check
from strategy.position_sizing import explicit_risk_plan, propose_ladder
from strategy.regime_filter import get_regime_status


def evaluate(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    gap = get_overnight_gap()
    regime = get_regime_status()
    kills = kill_check(today, gap=gap, regime=regime)

    checks = {
        "regime": {
            "pass": regime.get("shortVolOk", False),
            "detail": (
                f"Trend={regime.get('status')}, IV pct={regime.get('iv', {}).get('percentile')} "
                f"(need {regime.get('iv', {}).get('band')})"
            ),
        },
        "event": {
            "pass": not is_blackout_day(today) and not is_expiry_week_gamma_zone(today),
            "detail": (
                "No blackout / expiry gamma zone"
                if not is_blackout_day(today) and not is_expiry_week_gamma_zone(today)
                else "Blackout or expiry-week gamma zone active"
            ),
            "upcomingBlackouts": days_to_next_blackout(today, window=7),
        },
        "premiumQuality": {
            "pass": True,  # structural pass if ladder targets MIN_PREMIUM; live verify required
            "detail": f"Ladder targets ≥₹{MIN_PREMIUM_PER_LEG}/leg — confirm on broker before entry",
            "requiresLiveVerify": True,
        },
        "riskRewardExplicit": {
            "pass": True,
            "detail": "Auto-generated risk plan attached",
            "plan": explicit_risk_plan(regime.get("spot", 0)),
        },
        "manualGutCheck": {
            "pass": False,
            "detail": "Requires human confirmation — not boredom/FOMO trade",
            "requiresManual": True,
        },
    }

    auto_score = sum(1 for k, v in checks.items() if v["pass"] and k != "manualGutCheck")
    auto_total = 4  # excluding manual
    full_score = auto_score  # max 4 until manual confirms

    if kills["triggered"]:
        action = "NO_TRADE"
        state = "DE_RISK" if gap.get("killZone") else "WAITING_FOR_SETUP"
    elif auto_score == auto_total and not checks["event"]["pass"]:
        action = "NO_TRADE"
        state = "WAITING_FOR_SETUP"
    elif auto_score == auto_total:
        action = "QUALIFIED_SETUP"
        state = "QUALIFIED"
    elif auto_score >= 2:
        action = "WATCH"
        state = "WAITING_FOR_SETUP"
    else:
        action = "NO_TRADE"
        state = "WAITING_FOR_SETUP"

    spot = regime.get("spot") or gap.get("lastClose") or 0
    proposal = propose_ladder(spot) if action in ("QUALIFIED_SETUP", "WATCH") else None

    return {
        "checks": checks,
        "autoScore": auto_score,
        "autoTotal": auto_total,
        "fullScore": full_score,
        "maxScore": 5,
        "setupQualified": action == "QUALIFIED_SETUP",
        "action": action,
        "state": state,
        "killSwitches": kills,
        "gap": gap,
        "regime": regime,
        "proposal": proposal,
        "notes": [
            "Paper mode only — no broker orders placed",
            "Confirm manual gut check before any live entry",
            "Zero trades per week is a valid outcome",
        ],
    }
