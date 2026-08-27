"""Overnight gap check using Nifty spot (GIFT Nifty proxy when live data unavailable)."""

from __future__ import annotations

from typing import Any

import yfinance as yf

from strategy.config import GAP_KILL_THRESHOLD, GAP_REVIEW_THRESHOLD


def get_overnight_gap() -> dict[str, Any]:
    """
    Estimate overnight gap as today's open vs yesterday's close.
    Pre-market runs use latest available bar; true GIFT Nifty needs a broker feed.
    """
    data = yf.download("^NSEI", period="5d", interval="1d", progress=False, auto_adjust=True)
    if data.empty or len(data) < 2:
        return {"gapPoints": None, "error": "insufficient_data"}

    close = data["Close"].squeeze()
    open_ = data["Open"].squeeze()
    prev_close = float(close.iloc[-2])
    today_open = float(open_.iloc[-1])
    last_close = float(close.iloc[-1])

    gap_from_open = today_open - prev_close
    gap_from_last = last_close - prev_close

    gap = gap_from_open
    return {
        "prevClose": round(prev_close, 2),
        "todayOpen": round(today_open, 2),
        "lastClose": round(last_close, 2),
        "gapPoints": round(gap, 2),
        "gapPct": round((gap / prev_close) * 100, 2) if prev_close else None,
        "absGap": round(abs(gap), 2),
        "needsReview": abs(gap) >= GAP_REVIEW_THRESHOLD,
        "killZone": abs(gap) >= GAP_KILL_THRESHOLD,
        "note": "Uses Nifty daily open vs prior close; replace with GIFT Nifty for true pre-market.",
    }
