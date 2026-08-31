"""Write timestamped run snapshots for deploy (no git commit needed)."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

RUNS_DIR = Path("data/runs")
MANIFEST = RUNS_DIR / "manifest.json"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, float) and (obj != obj):
        return None
    raise TypeError(f"Not serializable: {type(obj)}")


def save_run(kind: str, payload: dict[str, Any]) -> Path:
    """Save one run snapshot and update manifest. kind: premarket | eod."""
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%dT%H%M%S")
    path = RUNS_DIR / f"{ts}_{kind}.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=_json_default)

    manifest: dict[str, Any] = {"runs": []}
    if MANIFEST.exists():
        with MANIFEST.open(encoding="utf-8") as f:
            manifest = json.load(f)

    manifest["runs"].append(
        {
            "timestamp": ts,
            "kind": kind,
            "file": str(path).replace("\\", "/"),
            "action": payload.get("action") or payload.get("summary", {}).get("otmCeSignal"),
        }
    )
    manifest["runs"] = manifest["runs"][-60:]  # keep last 60 runs

    with MANIFEST.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return path
