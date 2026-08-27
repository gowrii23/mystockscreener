#!/usr/bin/env python3
"""
scan_nifty_conviction.py — Nifty conviction checklist (paper mode).

Evaluates regime, gap, blackout calendar, kill-switches, and outputs:
  - output/nifty_setup.json   (latest snapshot for the trade desk UI)
  - data/conviction_results.csv (append-only audit log)
"""

from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from strategy.config import OUTPUT_JSON, RESULTS_CSV
from strategy.conviction import evaluate

CSV_HEADER = [
    "run_date",
    "run_type",
    "setup_qualified",
    "conviction_score",
    "regime_status",
    "gap_points",
    "blackout_flag",
    "kill_switch_triggered",
    "action",
    "state",
    "notes",
]


def _ensure_csv(path: str) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        with p.open("w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(CSV_HEADER)


def _json_default(obj: Any) -> Any:
    if isinstance(obj, float) and (obj != obj):
        return None
    if isinstance(obj, date):
        return obj.isoformat()
    raise TypeError(f"Not serializable: {type(obj)}")


def append_result(row: dict[str, Any], path: str = RESULTS_CSV) -> None:
    _ensure_csv(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow(
            [
                row.get("run_date"),
                row.get("run_type", "paper"),
                row.get("setup_qualified"),
                row.get("conviction_score"),
                row.get("regime_status"),
                row.get("gap_points"),
                row.get("blackout_flag"),
                row.get("kill_switch_triggered"),
                row.get("action"),
                row.get("state"),
                row.get("notes", ""),
            ]
        )


def main() -> None:
    os.makedirs("output", exist_ok=True)
    os.makedirs("data", exist_ok=True)

    today = date.today()
    result = evaluate(today)

    output = {
        "scanDate": datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"),
        "runType": "paper",
        "capital": {
            "total": 1_000_000,
            "maxDeployed": 250_000,
            "coreBuffer": 600_000,
            "reserve": 150_000,
        },
        **result,
    }

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, default=_json_default)

    append_result(
        {
            "run_date": today.isoformat(),
            "run_type": "paper",
            "setup_qualified": result["setupQualified"],
            "conviction_score": f"{result['autoScore']}/{result['autoTotal']}",
            "regime_status": result["regime"].get("status"),
            "gap_points": result["gap"].get("gapPoints"),
            "blackout_flag": not result["checks"]["event"]["pass"],
            "kill_switch_triggered": result["killSwitches"]["triggered"],
            "action": result["action"],
            "state": result["state"],
            "notes": "; ".join(result.get("notes", [])),
        }
    )

    print(f"[ok] wrote {OUTPUT_JSON}")
    print(f"[ok] appended row to {RESULTS_CSV}")
    print(f"Action: {result['action']} | State: {result['state']} | Score: {result['autoScore']}/{result['autoTotal']}")


if __name__ == "__main__":
    main()
