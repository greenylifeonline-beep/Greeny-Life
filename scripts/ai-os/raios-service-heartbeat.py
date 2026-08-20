#!/usr/bin/env python3
"""RAIOS service heartbeat: stale-lock observe + WAL presence. No new phase, no second WAL."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKS = ROOT / ".ai-os" / "state" / "LOCKS.json"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "reports" / "raios-service"
OUT = OUT_DIR / "LAST-HEARTBEAT.json"
LOCK_RE = re.compile(r"^LOCK-(\d{14})$")


def parse_lock_time(lock_id: str):
    m = LOCK_RE.match(lock_id or "")
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def main() -> int:
    now = datetime.now(timezone.utc)
    locks = json.loads(LOCKS.read_text(encoding="utf-8-sig"))
    stale = []
    for item in locks.get("locks", []):
        if item.get("status") != "ACTIVE":
            continue
        ts = parse_lock_time(item.get("id", ""))
        if ts is None:
            continue
        age_h = (now - ts).total_seconds() / 3600.0
        if age_h >= 24:
            stale.append(
                {
                    "id": item.get("id"),
                    "task_id": item.get("task_id"),
                    "agent": item.get("agent"),
                    "scope": item.get("scope"),
                    "age_hours": round(age_h, 2),
                    "knowledge_state": "DISCOVERED",
                    "action": "DO_NOT_AUTO_RELEASE",
                }
            )
    receipt = {
        "schema": "raios.service-heartbeat.v1",
        "mode": "SERVICE",
        "generated_at": now.isoformat(),
        "wal_exists": WAL.exists(),
        "wal_path": str(WAL.relative_to(ROOT)).replace("\\", "/"),
        "stale_locks": stale,
        "new_phase_created": False,
        "second_wal_created": False,
        "barn_folder_created": False,
        "status": "FAIL_CLOSED" if not WAL.exists() else "HEARTBEAT_OK",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"exit": 0 if WAL.exists() else 1, "receipt": str(OUT), "stale_locks": len(stale)}))
    return 0 if WAL.exists() else 1


if __name__ == "__main__":
    raise SystemExit(main())
