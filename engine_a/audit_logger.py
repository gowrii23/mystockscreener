import json
from pathlib import Path
from datetime import datetime

def audit_log(ticker: str, decision: str, reason: str, metrics: dict = None):
    log_path = Path("logs/audit_log.jsonl")
    log_path.parent.mkdir(exist_ok=True)
    entry = {
        "timestamp": datetime.now().isoformat(),
        "ticker": ticker,
        "decision": decision,
        "reason": reason,
        "metrics": metrics or {}
    }
    with open(log_path, "a") as f:
        f.write(json.dumps(entry) + "\n")
