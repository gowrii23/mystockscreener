#!/usr/bin/env python3
"""
validate_trade.py — validate yesterday's QUALIFIED_SETUP against today's Nifty session.

Run daily BEFORE new scans (EOD cron). Logs PROFIT / LOSS / NEUTRAL to data/trade_log.csv.
"""

from __future__ import annotations

import json
from datetime import date

from strategy.trade_logger import validate_pending


def main() -> None:
    results = validate_pending(date.today())

    if not results:
        print("[ok] no pending predictions to validate")
    else:
        for r in results:
            if r.get("status") == "validated":
                print(
                    f"[validated] pred={r['prediction_date']} → {r['validate_date']} "
                    f"{r['outcome']} pnl=₹{r['pnl_inr']:,.0f}"
                )
            else:
                print(f"[skip] {r}")

    print("[ok] trade log updated → data/trade_log.csv, output/trade_log.json")


if __name__ == "__main__":
    main()
