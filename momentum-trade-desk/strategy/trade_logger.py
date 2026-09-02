"""Save predictions and validate next-day P&L for the trade logger."""

from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yfinance as yf

from strategy.config import MIN_PREMIUM_PER_LEG

PREDICTIONS_DIR = Path("data/predictions")
TRADE_LOG_CSV = Path("data/trade_log.csv")
TRADE_LOG_JSON = Path("output/trade_log.json")

LOT_SIZE = 75
HEDGE_PREMIUM = 8
BASE_THETA_CAPTURE = 0.20
NEUTRAL_BAND = 1500

LOG_HEADER = [
    "prediction_date",
    "run_kind",
    "validate_date",
    "signal",
    "entry_spot",
    "session_open",
    "exit_close",
    "day_low",
    "day_high",
    "premium_collected",
    "pnl_inr",
    "outcome",
    "legs_count",
    "intraday_breach",
    "notes",
]


def _ensure_trade_log() -> None:
    TRADE_LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    if not TRADE_LOG_CSV.exists():
        with TRADE_LOG_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(LOG_HEADER)
        return

    with TRADE_LOG_CSV.open(encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    if header != LOG_HEADER:
        backup = TRADE_LOG_CSV.with_suffix(".csv.bak")
        TRADE_LOG_CSV.rename(backup)
        with TRADE_LOG_CSV.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(LOG_HEADER)


def _next_trading_day(d: date) -> date:
    nxt = d
    while True:
        nxt += timedelta(days=1)
        if nxt.weekday() < 5:
            return nxt


def _validate_date(pred_date: date, run_kind: str) -> date:
    """Premarket: validate same session at EOD. EOD: validate next trading day."""
    if run_kind == "premarket":
        return pred_date
    return _next_trading_day(pred_date)


def _prediction_paths() -> list[Path]:
    if not PREDICTIONS_DIR.exists():
        return []
    return sorted(
        p
        for p in PREDICTIONS_DIR.glob("*.json")
        if p.name != ".gitkeep" and not p.name.endswith(".bak")
    )


def _prediction_id(pred: dict[str, Any], path: Path) -> str:
    run_kind = pred.get("runKind", "eod")
    return f"{pred['predictionDate']}_{run_kind}"


def save_prediction(setup: dict[str, Any], run_kind: str | None = None) -> Path | None:
    """Save QUALIFIED_SETUP when trade-log eligible (no momentum conflict)."""
    if setup.get("action") != "QUALIFIED_SETUP":
        return None
    if not setup.get("tradeLogEligible", True):
        return None

    proposal = setup.get("proposal")
    if not proposal or not proposal.get("legs"):
        return None

    run_kind = run_kind or os.environ.get("RUN_KIND", "eod")
    PREDICTIONS_DIR.mkdir(parents=True, exist_ok=True)
    pred_date = date.today().isoformat()
    path = PREDICTIONS_DIR / f"{pred_date}_{run_kind}.json"

    legs = proposal["legs"]
    short_legs = [l for l in legs if "buy" not in l.get("instrument", "").lower()]
    premium_per_leg = (
        sum(l.get("targetPremium", MIN_PREMIUM_PER_LEG) for l in short_legs) / len(short_legs)
        if short_legs
        else MIN_PREMIUM_PER_LEG
    )

    payload = {
        "predictionDate": pred_date,
        "runKind": run_kind,
        "savedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "validated": False,
        "action": setup["action"],
        "spot": setup.get("regime", {}).get("spot") or proposal.get("spot"),
        "premiumPerLeg": round(premium_per_leg, 2),
        "lotSize": LOT_SIZE,
        "hedgePremium": HEDGE_PREMIUM,
        "proposal": proposal,
        "regime": setup.get("regime", {}).get("status"),
        "gapPoints": setup.get("gap", {}).get("gapPoints"),
        "momentumRegime": setup.get("momentumAlignment", {}).get("marketRegime"),
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    _export_trade_log_json()
    return path


def _intrinsic_pe(strike: float, spot: float) -> float:
    return max(0.0, strike - spot)


def _intrinsic_ce(strike: float, spot: float) -> float:
    return max(0.0, spot - strike)


def _parse_hedge_strike(hedge: dict[str, Any]) -> int | None:
    if not hedge.get("instrument"):
        return None
    for part in hedge["instrument"].split():
        if part.isdigit():
            return int(part)
    return None


def _short_legs(legs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [l for l in legs if "buy" not in l.get("instrument", "").lower()]


def _premium_collected(legs: list[dict[str, Any]], lot_size: int) -> float:
    return sum(l.get("targetPremium", MIN_PREMIUM_PER_LEG) for l in _short_legs(legs)) * lot_size


def _calc_pnl(
    legs: list[dict[str, Any]],
    hedge_strike: int | None,
    open_spot: float,
    close_spot: float,
    low_spot: float,
    high_spot: float,
    lot_size: int,
    hedge_premium: float,
) -> dict[str, Any]:
    shorts = _short_legs(legs)
    premium_in = _premium_collected(legs, lot_size)
    hedge_cost = hedge_premium * lot_size

    pe_strikes = [l["strike"] for l in shorts if l.get("type") == "PE"]
    ce_strikes = [l["strike"] for l in shorts if l.get("type") == "CE"]

    pe_intr_low = sum(_intrinsic_pe(k, low_spot) for k in pe_strikes) * lot_size
    ce_intr_high = sum(_intrinsic_ce(k, high_spot) for k in ce_strikes) * lot_size
    pe_intr_close = sum(_intrinsic_pe(k, close_spot) for k in pe_strikes) * lot_size
    ce_intr_close = sum(_intrinsic_ce(k, close_spot) for k in ce_strikes) * lot_size

    hedge_val_low = _intrinsic_pe(hedge_strike, low_spot) * lot_size if hedge_strike else 0
    hedge_val_close = _intrinsic_pe(hedge_strike, close_spot) * lot_size if hedge_strike else 0

    intraday_breach = pe_intr_low > 0 or ce_intr_high > 0
    all_otm_close = pe_intr_close == 0 and ce_intr_close == 0
    theta_mult: float | None = None

    if intraday_breach:
        short_mtm_worst = max(pe_intr_low, pe_intr_close) + max(ce_intr_high, ce_intr_close)
        pnl = premium_in - short_mtm_worst - hedge_cost + max(hedge_val_low, hedge_val_close)
        method = "intraday_breach"
    elif all_otm_close:
        day_range = (high_spot - low_spot) / open_spot if open_spot else 0
        theta_mult = max(0.08, BASE_THETA_CAPTURE - day_range * 1.5)
        pnl = premium_in * theta_mult - hedge_cost * 0.5
        method = "theta_decay_otm"
    else:
        pnl = premium_in - pe_intr_close - ce_intr_close - hedge_cost + hedge_val_close
        method = "intrinsic_at_close"

    if pnl > NEUTRAL_BAND:
        outcome = "PROFIT"
    elif pnl < -NEUTRAL_BAND:
        outcome = "LOSS"
    else:
        outcome = "NEUTRAL"

    return {
        "premiumCollected": round(premium_in, 0),
        "pnlInr": round(pnl, 0),
        "outcome": outcome,
        "method": method,
        "intradayBreach": intraday_breach,
        "allOtmAtClose": all_otm_close,
        "peIntrinsicLow": pe_intr_low,
        "ceIntrinsicHigh": ce_intr_high,
        "peIntrinsicClose": pe_intr_close,
        "ceIntrinsicClose": ce_intr_close,
        "thetaMult": round(theta_mult, 3) if method == "theta_decay_otm" else None,
    }


def _fetch_nifty_day(target: date) -> dict[str, float] | None:
    start = target - timedelta(days=7)
    end = target + timedelta(days=2)
    data = yf.download(
        "^NSEI",
        start=start.isoformat(),
        end=end.isoformat(),
        progress=False,
        auto_adjust=True,
    )
    if data.empty:
        return None

    for idx, row in data.iterrows():
        d = idx.date() if hasattr(idx, "date") else idx
        if d == target:
            return {
                "open": float(row["Open"].squeeze()),
                "high": float(row["High"].squeeze()),
                "low": float(row["Low"].squeeze()),
                "close": float(row["Close"].squeeze()),
            }
    return None


def validate_pending(as_of: date | None = None) -> list[dict[str, Any]]:
    """Validate predictions whose validation session has completed by as_of."""
    as_of = as_of or date.today()
    _ensure_trade_log()
    results: list[dict[str, Any]] = []

    for path in _prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)

        if pred.get("validated"):
            continue

        pred_date = date.fromisoformat(pred["predictionDate"])
        run_kind = pred.get("runKind", "eod")
        validate_date = _validate_date(pred_date, run_kind)

        if as_of < validate_date:
            continue

        ohlc = _fetch_nifty_day(validate_date)
        if not ohlc:
            results.append(
                {
                    "predictionDate": pred_date.isoformat(),
                    "runKind": run_kind,
                    "status": "skipped",
                    "reason": f"no_nifty_data_for_{validate_date}",
                }
            )
            continue

        legs = pred["proposal"]["legs"]
        hedge_strike = _parse_hedge_strike(pred["proposal"].get("tailHedge", {}))

        pnl_info = _calc_pnl(
            legs=legs,
            hedge_strike=hedge_strike,
            open_spot=ohlc["open"],
            close_spot=ohlc["close"],
            low_spot=ohlc["low"],
            high_spot=ohlc["high"],
            lot_size=pred.get("lotSize", LOT_SIZE),
            hedge_premium=pred.get("hedgePremium", HEDGE_PREMIUM),
        )

        entry_spot = pred.get("spot") or ohlc["open"]
        row = {
            "prediction_date": pred_date.isoformat(),
            "run_kind": run_kind,
            "validate_date": validate_date.isoformat(),
            "signal": pred.get("action"),
            "entry_spot": round(float(entry_spot), 2),
            "session_open": round(ohlc["open"], 2),
            "exit_close": round(ohlc["close"], 2),
            "day_low": round(ohlc["low"], 2),
            "day_high": round(ohlc["high"], 2),
            "premium_collected": pnl_info["premiumCollected"],
            "pnl_inr": pnl_info["pnlInr"],
            "outcome": pnl_info["outcome"],
            "legs_count": len(legs),
            "intraday_breach": str(pnl_info["intradayBreach"]),
            "notes": (
                f"method={pnl_info['method']}; pred_spot={pred.get('spot')}; "
                f"all_otm_close={pnl_info['allOtmAtClose']}; "
                f"theta_mult={pnl_info.get('thetaMult')}"
            ),
        }

        with TRADE_LOG_CSV.open("a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([row[k] for k in LOG_HEADER])

        pred["validated"] = True
        pred["validation"] = {**row, **pnl_info}
        with path.open("w", encoding="utf-8") as f:
            json.dump(pred, f, indent=2)

        results.append({"status": "validated", **row})

    _export_trade_log_json()
    return results


def _pending_predictions() -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for path in _prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)
        if pred.get("validated"):
            continue
        pred_date = date.fromisoformat(pred["predictionDate"])
        run_kind = pred.get("runKind", "eod")
        pending.append(
            {
                "id": _prediction_id(pred, path),
                "predictionDate": pred_date.isoformat(),
                "runKind": run_kind,
                "validateOn": _validate_date(pred_date, run_kind).isoformat(),
                "spot": pred.get("spot"),
                "legsCount": len(pred.get("proposal", {}).get("legs", [])),
            }
        )
    return sorted(pending, key=lambda x: (x["validateOn"], x["predictionDate"]), reverse=True)


def _export_trade_log_json() -> None:
    rows: list[dict[str, str]] = []
    if TRADE_LOG_CSV.exists():
        with TRADE_LOG_CSV.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

    summary = {
        "totalTrades": len(rows),
        "profit": sum(1 for r in rows if r.get("outcome") == "PROFIT"),
        "loss": sum(1 for r in rows if r.get("outcome") == "LOSS"),
        "neutral": sum(1 for r in rows if r.get("outcome") == "NEUTRAL"),
        "totalPnl": sum(float(r.get("pnl_inr") or 0) for r in rows),
    }

    TRADE_LOG_JSON.parent.mkdir(parents=True, exist_ok=True)
    with TRADE_LOG_JSON.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "updatedAt": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
                "summary": summary,
                "pending": _pending_predictions(),
                "trades": rows,
            },
            f,
            indent=2,
        )


def rebuild_trade_log_from_predictions(as_of: date | None = None) -> None:
    """Reset trade log and re-validate all predictions (after logic/schema changes)."""
    as_of = as_of or date.today()
    if TRADE_LOG_CSV.exists():
        TRADE_LOG_CSV.unlink()
    _ensure_trade_log()

    for path in _prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)
        pred["validated"] = False
        pred.pop("validation", None)
        with path.open("w", encoding="utf-8") as f:
            json.dump(pred, f, indent=2)

    validate_pending(as_of)
