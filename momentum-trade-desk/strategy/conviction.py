"""Five-point conviction checklist — paper mode only."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

from strategy.blackout import days_to_next_blackout, is_blackout_day, is_expiry_week_gamma_zone
from strategy.config import MIN_PREMIUM_PER_LEG, OUTPUT_JSON
from strategy.gap_check import get_overnight_gap
from strategy.kill_switches import check as kill_check
from strategy.position_sizing import explicit_risk_plan, propose_ladder
from strategy.regime_filter import get_regime_status


def _load_momentum_alignment() -> dict[str, Any]:
    """Read latest momentum scan when available (EOD runs after scan_momentum)."""
    scan_path = Path(OUTPUT_JSON).parent / "latest_scan.json"
    if not scan_path.exists():
        return {"available": False, "marketRegime": None, "aligned": True, "detail": "No momentum scan yet"}

    try:
        with scan_path.open(encoding="utf-8") as f:
            scan = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"available": False, "marketRegime": None, "aligned": True, "detail": "Momentum scan unreadable"}

    regime = scan.get("summary", {}).get("marketRegime") or scan.get("nifty", {}).get("regime")
    aligned = regime != "BEARISH"
    detail = (
        f"Momentum regime={regime} — aligned with short-vol ladder"
        if aligned
        else "Momentum BEARISH (below 200 SMA) — conflicts with short CE wing; trade logger blocked"
    )
    return {"available": True, "marketRegime": regime, "aligned": aligned, "detail": detail}


def evaluate(today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    gap = get_overnight_gap()
    regime = get_regime_status()
    kills = kill_check(today, gap=gap, regime=regime)
    momentum = _load_momentum_alignment()

    spot = regime.get("spot") or gap.get("lastClose") or 0
    proposal_preview = propose_ladder(spot) if spot else None
    legs = (proposal_preview or {}).get("legs", [])
    premium_ok = bool(legs) and all(
        l.get("targetPremium", 0) >= MIN_PREMIUM_PER_LEG for l in legs
    )

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
            "pass": premium_ok,
            "detail": (
                f"All ladder legs target ≥₹{MIN_PREMIUM_PER_LEG}/leg"
                if premium_ok
                else f"Ladder premium below ₹{MIN_PREMIUM_PER_LEG}/leg floor"
            ),
            "requiresLiveVerify": True,
        },
        "momentumAlignment": {
            "pass": momentum["aligned"],
            "detail": momentum["detail"],
            "marketRegime": momentum.get("marketRegime"),
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
    auto_total = 5  # regime, event, premium, momentum, risk plan
    full_score = auto_score

    if kills["triggered"]:
        action = "NO_TRADE"
        state = "DE_RISK" if gap.get("killZone") else "WAITING_FOR_SETUP"
    elif auto_score == auto_total and not checks["event"]["pass"]:
        action = "NO_TRADE"
        state = "WAITING_FOR_SETUP"
    elif auto_score == auto_total:
        action = "QUALIFIED_SETUP"
        state = "QUALIFIED"
    elif auto_score >= 3:
        action = "WATCH"
        state = "WAITING_FOR_SETUP"
    else:
        action = "NO_TRADE"
        state = "WAITING_FOR_SETUP"

    proposal = propose_ladder(spot) if action in ("QUALIFIED_SETUP", "WATCH") else None
    trade_log_eligible = action == "QUALIFIED_SETUP" and momentum["aligned"]

    notes = [
        "Paper mode only — no broker orders placed",
        "Confirm manual gut check before any live entry",
        "Zero trades per week is a valid outcome",
    ]
    if action == "QUALIFIED_SETUP" and not momentum["aligned"]:
        notes.append("QUALIFIED for display only — momentum BEARISH blocks trade logger until aligned")

    return {
        "checks": checks,
        "autoScore": auto_score,
        "autoTotal": auto_total,
        "fullScore": full_score,
        "maxScore": 6,
        "setupQualified": action == "QUALIFIED_SETUP",
        "tradeLogEligible": trade_log_eligible,
        "action": action,
        "state": state,
        "killSwitches": kills,
        "gap": gap,
        "regime": regime,
        "momentumAlignment": momentum,
        "proposal": proposal,
        "notes": notes,
    }
