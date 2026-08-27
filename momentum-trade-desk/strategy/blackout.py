"""Event blackout calendar — blocks new naked sells on known risk dates."""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

from strategy.config import BLACKOUT_CSV


def _parse_date(value: str) -> date | None:
    from datetime import datetime

    value = value.strip()
    if not value or value.startswith("#"):
        return None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def load_blackout_dates(path: str = BLACKOUT_CSV) -> set[date]:
    dates: set[date] = set()
    p = Path(path)
    if not p.exists():
        return dates
    with p.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = _parse_date(row.get("date", ""))
            if d:
                dates.add(d)
    return dates


def is_blackout_day(today: date, blackout: set[date] | None = None) -> bool:
    blackout = blackout if blackout is not None else load_blackout_dates()
    return today in blackout


def is_expiry_week_gamma_zone(today: date) -> bool:
    """Wednesday onward in Nifty weekly expiry week (Thursday expiry)."""
    # Thursday = 3; block Wed(2) through expiry
    if today.weekday() == 2:  # Wednesday
        return True
    if today.weekday() == 3:  # Thursday expiry day
        return True
    return False


def days_to_next_blackout(today: date, window: int = 5) -> list[dict]:
    blackout = load_blackout_dates()
    upcoming = []
    for i in range(window + 1):
        d = today + timedelta(days=i)
        if d in blackout:
            upcoming.append({"date": d.isoformat(), "daysAway": i})
    return upcoming
