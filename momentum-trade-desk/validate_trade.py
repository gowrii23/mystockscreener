#!/usr/bin/env python3
"""
validate_trade.py — validate pending predictions against Nifty session OHLC.

Run daily BEFORE new scans (EOD cron). Logs PROFIT / LOSS / NEUTRAL to data/trade_log.csv.

  python3 validate_trade.py           # validate due predictions
  python3 validate_trade.py --rebuild # reset log and re-validate all (after logic changes)
"""

from __future__ import annotations

import argparse
from datetime import date

from strategy.trade_logger import prune_legacy_predictions, rebuild_trade_log_from_predictions, validate_pending


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate pending trade predictions")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Clear trade log and re-validate all prediction files",
    )
    args = parser.parse_args()

    removed = prune_legacy_predictions()
    if removed:
        print(f"[ok] pruned legacy prediction files: {', '.join(removed)}")

    if args.rebuild:
        rebuild_trade_log_from_predictions(date.today())
        print("[ok] rebuilt trade log from all predictions")

    results = validate_pending(date.today())

    if not results:
        print("[ok] no pending predictions to validate")
    else:
        for r in results:
            if r.get("status") == "validated":
                print(
                    f"[validated] {r['prediction_date']} ({r['run_kind']}) → {r['validate_date']} "
                    f"{r['outcome']} pnl=₹{r['pnl_inr']:,.0f} "
                    f"breach={r['intraday_breach']}"
                )
            else:
                print(f"[skip] {r}")

    print("[ok] trade log updated → data/trade_log.csv, output/trade_log.json")


if __name__ == "__main__":
    main()
