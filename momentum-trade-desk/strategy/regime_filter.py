"""Regime filter — Nifty trend + India VIX percentile for short-vol suitability."""

from __future__ import annotations

from typing import Any

import pandas as pd
import yfinance as yf

from strategy.config import IV_PCT_MAX, IV_PCT_MIN, SMA200_NEUTRAL_BAND_PCT


def _iv_percentile() -> dict[str, Any]:
    vix = yf.download("^INDIAVIX", period="1y", interval="1d", progress=False, auto_adjust=True)
    if vix.empty or len(vix) < 30:
        return {"current": None, "percentile": None, "ok": False, "note": "VIX data unavailable"}

    series = vix["Close"].squeeze().dropna()
    current = float(series.iloc[-1])
    pct = float((series <= current).mean() * 100)
    ok = IV_PCT_MIN <= pct <= IV_PCT_MAX
    return {
        "current": round(current, 2),
        "percentile": round(pct, 1),
        "ok": ok,
        "band": f"{IV_PCT_MIN}-{IV_PCT_MAX}",
    }


def get_regime_status() -> dict[str, Any]:
    nifty = yf.download("^NSEI", period="1y", interval="1d", progress=False, auto_adjust=True)
    if nifty.empty or len(nifty) < 200:
        return {"status": "UNKNOWN", "shortVolOk": False, "error": "insufficient_nifty_history"}

    close = nifty["Close"].squeeze()
    spot = float(close.iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])
    dist_from_200_pct = ((spot - sma200) / sma200) * 100

    if abs(dist_from_200_pct) <= SMA200_NEUTRAL_BAND_PCT:
        trend = "NEUTRAL"
        short_vol_trend_ok = True
    elif spot > sma200 and sma50 >= sma200 * 0.995:
        trend = "MILD_BULL"
        short_vol_trend_ok = True
    elif spot < sma200 and sma50 <= sma200 * 1.005:
        trend = "MILD_BEAR"
        short_vol_trend_ok = True
    elif spot > sma200:
        trend = "BULLISH"
        short_vol_trend_ok = False  # fighting uptrend with naked shorts is risky
    else:
        trend = "BEARISH"
        short_vol_trend_ok = False

    iv = _iv_percentile()
    short_vol_ok = short_vol_trend_ok and iv.get("ok", False)

    return {
        "status": trend,
        "spot": round(spot, 2),
        "sma50": round(sma50, 2),
        "sma200": round(sma200, 2),
        "distFrom200Pct": round(dist_from_200_pct, 2),
        "shortVolTrendOk": short_vol_trend_ok,
        "iv": iv,
        "shortVolOk": short_vol_ok,
    }
