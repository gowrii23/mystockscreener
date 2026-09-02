"""Save predictions and validate next-day P&L for the trade logger."""

from __future__ import annotations

import csv
import json
import os
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import yfinance as yf

from strategy.config import MIN_PREMIUM_PER_LEG

PREDICTIONS_DIR = Path("data/predictions")
TRADE_LOG_CSV = Path("data/trade_log.csv")
TRADE_LOG_JSON = Path("output/trade_log.json")
SEED_TRADE_LOG_CSV = Path("data/trade_log.seed.csv")

LOT_SIZE = 75
HEDGE_PREMIUM = 8
BASE_THETA_CAPTURE = 0.20
BREACH_THETA_CAPTURE = 0.05
BREACH_STRESS_FACTOR = 0.75
NEUTRAL_BAND = 1500

LEGACY_PRED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
CANONICAL_PRED_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_(premarket|eod)\.json$")

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
        if SEED_TRADE_LOG_CSV.exists():
            TRADE_LOG_CSV.write_text(SEED_TRADE_LOG_CSV.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            with TRADE_LOG_CSV.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(LOG_HEADER)
        return

    with TRADE_LOG_CSV.open(encoding="utf-8") as f:
        header = next(csv.reader(f), [])
    if header != LOG_HEADER:
        backup = TRADE_LOG_CSV.with_suffix(".csv.bak")
        TRADE_LOG_CSV.rename(backup)
        if SEED_TRADE_LOG_CSV.exists():
            TRADE_LOG_CSV.write_text(SEED_TRADE_LOG_CSV.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            with TRADE_LOG_CSV.open("w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(LOG_HEADER)


def _next_trading_day(d: date) -> date:
    nxt = d
    while True:
        nxt += timedelta(days=1)
        if nxt.weekday() < 5:
            return nxt


def _validate_date(pred_date: date, run_kind: str) -> date:
    if run_kind == "premarket":
        return pred_date
    return _next_trading_day(pred_date)


def _prediction_key_from_path(path: Path) -> tuple[str, str] | None:
    if CANONICAL_PRED_RE.match(path.name):
        pred_date, run_kind = path.stem.rsplit("_", 1)
        return pred_date, run_kind
    if LEGACY_PRED_RE.match(path.name):
        return path.stem, "eod"
    return None


def prune_legacy_predictions() -> list[str]:
    """Remove legacy YYYY-MM-DD.json when canonical run_kind file exists."""
    removed: list[str] = []
    if not PREDICTIONS_DIR.exists():
        return removed

    canonical_dates = {
        p.stem.rsplit("_", 1)[0]
        for p in PREDICTIONS_DIR.glob("*.json")
        if CANONICAL_PRED_RE.match(p.name)
    }
    for path in list(PREDICTIONS_DIR.glob("*.json")):
        if LEGACY_PRED_RE.match(path.name) and path.stem in canonical_dates:
            path.unlink()
            removed.append(path.name)
    return removed


def _canonical_prediction_paths() -> list[Path]:
    if not PREDICTIONS_DIR.exists():
        return []

    chosen: dict[tuple[str, str], Path] = {}
    for path in sorted(PREDICTIONS_DIR.glob("*.json")):
        if path.name in {".gitkeep"} or path.name.endswith(".bak"):
            continue
        key = _prediction_key_from_path(path)
        if not key:
            continue
        existing = chosen.get(key)
        if existing is None:
            chosen[key] = path
            continue
        # Prefer canonical *_eod.json over legacy flat file.
        if CANONICAL_PRED_RE.match(path.name) and LEGACY_PRED_RE.match(existing.name):
            chosen[key] = path

    return sorted(chosen.values())


def _prediction_id(pred: dict[str, Any]) -> str:
    run_kind = pred.get("runKind", "eod")
    return f"{pred['predictionDate']}_{run_kind}"


def _trade_log_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        row["prediction_date"],
        row.get("run_kind", "eod"),
        row["validate_date"],
    )


def _load_trade_log_rows() -> list[dict[str, str]]:
    if not TRADE_LOG_CSV.exists():
        return []
    with TRADE_LOG_CSV.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return _dedupe_trade_rows(rows)


def _dedupe_trade_rows(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[dict[str, str]] = []
    for row in rows:
        key = _trade_log_key(row)
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def _is_already_logged(pred_date: str, run_kind: str, validate_date: str) -> bool:
    key = (pred_date, run_kind, validate_date)
    return key in {_trade_log_key(r) for r in _load_trade_log_rows()}


def _write_trade_log_rows(rows: list[dict[str, str]]) -> None:
    rows = _dedupe_trade_rows(rows)
    with TRADE_LOG_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_HEADER)
        writer.writeheader()
        writer.writerows(rows)
    SEED_TRADE_LOG_CSV.parent.mkdir(parents=True, exist_ok=True)
    SEED_TRADE_LOG_CSV.write_text(TRADE_LOG_CSV.read_text(encoding="utf-8"), encoding="utf-8")


def save_prediction(setup: dict[str, Any], run_kind: str | None = None) -> Path | None:
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

    legacy = PREDICTIONS_DIR / f"{pred_date}.json"
    if legacy.exists():
        legacy.unlink()

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


def cancel_open_predictions(reason: str, as_of: date | None = None) -> list[str]:
    """
    Auto-close all pending predictions at EOD/pre-market when conviction is NO_TRADE.
    Cancelled predictions are never validated and any matching trade-log rows are removed.
    """
    as_of = as_of or date.today()
    prune_legacy_predictions()
    cancelled_ids: list[str] = []

    for path in _canonical_prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)

        if pred.get("validated") or pred.get("cancelled"):
            continue

        pred["cancelled"] = True
        pred["cancelReason"] = reason
        pred["cancelledAt"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S IST")
        pred["cancelledOn"] = as_of.isoformat()
        with path.open("w", encoding="utf-8") as f:
            json.dump(pred, f, indent=2)
        cancelled_ids.append(_prediction_id(pred))

    if cancelled_ids:
        _purge_trade_log_for_cancelled()
        _export_trade_log_json()

    return cancelled_ids


def _cancelled_prediction_keys() -> set[tuple[str, str, str]]:
    keys: set[tuple[str, str, str]] = set()
    for path in _canonical_prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)
        if not pred.get("cancelled"):
            continue
        pred_date = date.fromisoformat(pred["predictionDate"])
        run_kind = pred.get("runKind", "eod")
        keys.add(
            (
                pred_date.isoformat(),
                run_kind,
                _validate_date(pred_date, run_kind).isoformat(),
            )
        )
    return keys


def _purge_trade_log_for_cancelled() -> None:
    cancelled = _cancelled_prediction_keys()
    if not cancelled:
        return
    rows = [r for r in _load_trade_log_rows() if _trade_log_key(r) not in cancelled]
    _write_trade_log_rows(rows)


def _cancelled_predictions() -> list[dict[str, Any]]:
    cancelled: list[dict[str, Any]] = []
    for path in _canonical_prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)
        if not pred.get("cancelled"):
            continue
        pred_date = date.fromisoformat(pred["predictionDate"])
        run_kind = pred.get("runKind", "eod")
        cancelled.append(
            {
                "id": _prediction_id(pred),
                "predictionDate": pred_date.isoformat(),
                "runKind": run_kind,
                "wouldValidateOn": _validate_date(pred_date, run_kind).isoformat(),
                "reason": pred.get("cancelReason"),
                "cancelledAt": pred.get("cancelledAt"),
            }
        )
    return sorted(cancelled, key=lambda x: x["cancelledAt"] or "", reverse=True)


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


def _outcome_from_pnl(pnl: float, *, intraday_breach: bool) -> str:
    if intraday_breach and pnl > 0:
        pnl = min(pnl, NEUTRAL_BAND - 1)
    if pnl > NEUTRAL_BAND:
        return "PROFIT"
    if pnl < -NEUTRAL_BAND:
        return "LOSS"
    return "NEUTRAL"


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
    worst_short_mtm = max(pe_intr_low, pe_intr_close) + max(ce_intr_high, ce_intr_close)
    theta_mult: float | None = None

    if intraday_breach and all_otm_close:
        stress_cost = worst_short_mtm * BREACH_STRESS_FACTOR
        pnl = premium_in * BREACH_THETA_CAPTURE - hedge_cost * 0.5 - stress_cost
        method = "intraday_breach_recovered"
    elif intraday_breach:
        pnl = premium_in - pe_intr_close - ce_intr_close - hedge_cost + max(hedge_val_low, hedge_val_close)
        method = "intraday_breach_close_itm"
    elif all_otm_close:
        day_range = (high_spot - low_spot) / open_spot if open_spot else 0
        theta_mult = max(0.08, BASE_THETA_CAPTURE - day_range * 1.5)
        pnl = premium_in * theta_mult - hedge_cost * 0.5
        method = "theta_decay_otm"
    else:
        pnl = premium_in - pe_intr_close - ce_intr_close - hedge_cost + hedge_val_close
        method = "intrinsic_at_close"

    outcome = _outcome_from_pnl(pnl, intraday_breach=intraday_breach)

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
    as_of = as_of or date.today()
    prune_legacy_predictions()
    _ensure_trade_log()
    results: list[dict[str, Any]] = []

    for path in _canonical_prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)

        pred_date = date.fromisoformat(pred["predictionDate"])
        run_kind = pred.get("runKind", "eod")
        validate_date = _validate_date(pred_date, run_kind)

        if as_of < validate_date:
            continue

        if pred.get("cancelled"):
            continue

        if pred.get("validated") or _is_already_logged(
            pred_date.isoformat(), run_kind, validate_date.isoformat()
        ):
            if not pred.get("validated"):
                pred["validated"] = True
                with path.open("w", encoding="utf-8") as f:
                    json.dump(pred, f, indent=2)
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

        rows = _load_trade_log_rows()
        rows.append({k: str(v) for k, v in row.items()})
        _write_trade_log_rows(rows)

        pred["validated"] = True
        pred["validation"] = {**row, **pnl_info}
        with path.open("w", encoding="utf-8") as f:
            json.dump(pred, f, indent=2)

        results.append({"status": "validated", **row})

    _export_trade_log_json()
    return results


def _pending_predictions() -> list[dict[str, Any]]:
    pending: list[dict[str, Any]] = []
    for path in _canonical_prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)
        if pred.get("validated") or pred.get("cancelled"):
            continue
        pred_date = date.fromisoformat(pred["predictionDate"])
        run_kind = pred.get("runKind", "eod")
        pending.append(
            {
                "id": _prediction_id(pred),
                "predictionDate": pred_date.isoformat(),
                "runKind": run_kind,
                "validateOn": _validate_date(pred_date, run_kind).isoformat(),
                "spot": pred.get("spot"),
                "legsCount": len(pred.get("proposal", {}).get("legs", [])),
            }
        )
    return sorted(pending, key=lambda x: (x["validateOn"], x["predictionDate"]), reverse=True)


def _export_trade_log_json() -> None:
    _purge_trade_log_for_cancelled()
    rows = _dedupe_trade_rows(_load_trade_log_rows())

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
                "cancelled": _cancelled_predictions(),
                "trades": rows,
            },
            f,
            indent=2,
        )


def rebuild_trade_log_from_predictions(as_of: date | None = None) -> None:
    as_of = as_of or date.today()
    prune_legacy_predictions()

    if TRADE_LOG_CSV.exists():
        TRADE_LOG_CSV.unlink()
    _ensure_trade_log()

    for path in _canonical_prediction_paths():
        with path.open(encoding="utf-8") as f:
            pred = json.load(f)
        pred["validated"] = False
        pred.pop("validation", None)
        with path.open("w", encoding="utf-8") as f:
            json.dump(pred, f, indent=2)

    validate_pending(as_of)
