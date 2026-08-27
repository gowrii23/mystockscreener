"""Portfolio circuit breakers — run before any trade logic."""

from __future__ import annotations

from typing import Any

from strategy.blackout import is_blackout_day, is_expiry_week_gamma_zone
from strategy.config import DAILY_LOSS_KILL_PCT, GAP_KILL_THRESHOLD, TOTAL_CAPITAL
from strategy.gap_check import get_overnight_gap
from strategy.regime_filter import get_regime_status


def check(
    today,
    gap: dict[str, Any] | None = None,
    regime: dict[str, Any] | None = None,
    simulated_daily_loss: float | None = None,
) -> dict[str, Any]:
    gap = gap or get_overnight_gap()
    regime = regime or get_regime_status()

    triggers: list[str] = []

    if gap.get("killZone"):
        triggers.append(f"gap>{GAP_KILL_THRESHOLD}pts ({gap.get('gapPoints')})")

    if is_blackout_day(today):
        triggers.append("blackout_calendar")

    if is_expiry_week_gamma_zone(today):
        triggers.append("expiry_week_gamma_zone")

    if regime.get("status") in ("BULLISH", "BEARISH"):
        triggers.append(f"strong_trend_{regime.get('status').lower()}")

    if simulated_daily_loss is not None:
        loss_pct = (abs(simulated_daily_loss) / TOTAL_CAPITAL) * 100
        if simulated_daily_loss < 0 and loss_pct >= DAILY_LOSS_KILL_PCT:
            triggers.append(f"daily_loss>{DAILY_LOSS_KILL_PCT}%")

    return {
        "triggered": len(triggers) > 0,
        "triggers": triggers,
        "dailyLossKillPct": DAILY_LOSS_KILL_PCT,
    }
