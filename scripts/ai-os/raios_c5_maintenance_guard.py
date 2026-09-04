from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LAWBOOK = ROOT / ".ai-os" / "mcp" / "C5-MAINTENANCE-LAWS.json"


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError:
        return ""


def has(path: str, needle: str) -> bool:
    return needle in read(ROOT / path)


def maintenance_issues(root: Path | None = None) -> list[dict[str, Any]]:
    global ROOT, LAWBOOK
    if root is not None:
        ROOT = root.resolve()
        LAWBOOK = ROOT / ".ai-os" / "mcp" / "C5-MAINTENANCE-LAWS.json"
    issues: list[dict[str, Any]] = []
    checks = [
        ("C5_IDLE_REASONING_ON_GAPS_ONLY", "src/raios/manager/live_manager.py", "reasoning_hash = sha(gaps)"),
        ("HEALTH_ENDPOINT_NE_SUBPROCESS", "src/raios/command_center/app.py", '"canonical_head":CANONICAL_HEAD'),
        ("HISTORICAL_ACK_NE_DEAD_LETTER", "src/raios/command_center/message_worker.py", "_historical_actor_ack"),
        ("CANONICAL_RUNTIME_BYTES_MATCH_HEAD", "scripts/runtime/Deploy-RAIOS-C5.ps1", "C5_CANONICAL_SOURCE_DIRTY"),
        ("C5_DEPLOY_STAGE_NE_LIVE_APP_MUTATION", "scripts/runtime/Deploy-RAIOS-C5.ps1", "StageAppRoot"),
        ("SINGLE_CANONICAL_CHANGE_WRITER", "scripts/ai-os/raios_change_gate.py", "active-change.json"),
        ("INTERNAL_COUNCIL_NE_EXTERNAL_A2A", "src/raios/council_ops/operations.py", '"transport":"INTERNAL_BUS"'),
        ("AUTO_ROUTE_REQUIRES_LIVE_CONSUMER", "src/raios/command_center/actor_routing.py", "present and binding_current and consumer_current"),
        ("DELIVERY_ACK_NE_ACTOR_ACK", "src/raios/command_center/message_worker.py", '"actor_ack_synthesized":False'),
        ("C5_IDLE_MODEL_MUST_UNLOAD", "src/raios/c5_gateway/ollama_client.py", 'RAIOS_STUDENT_KEEP_ALIVE","30s"'),
        ("MODEL_PROVIDER_NE_COUNCIL_SEAT", "src/raios/ai_gateway/router.py", '"model_ne_council_seat": True'),
    ]
    if not LAWBOOK.exists():
        issues.append({"id": "C5_MAINTENANCE_LAWBOOK_MISSING", "severity": "CRITICAL"})
    for law, path, needle in checks:
        if not has(path, needle):
            issues.append({"id": law + "_REGRESSION", "law": law, "path": path, "severity": "CRITICAL"})
    if "a2a_all_hands" in read(ROOT / "src/raios/council_ops/operations.py"):
        issues.append({"id": "INTERNAL_COUNCIL_EXTERNAL_A2A_REGRESSION", "law": "INTERNAL_COUNCIL_NE_EXTERNAL_A2A", "severity": "CRITICAL"})
    return issues


def snapshot() -> dict[str, Any]:
    issues = maintenance_issues()
    return {
        "schema": "raios.c5-maintenance-guard.v1",
        "ok": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "lawbook": str(LAWBOOK.relative_to(ROOT)) if LAWBOOK.exists() else None,
        "runtime_mutation": False,
        "wal_written": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="raios-c5-maintenance-guard")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    out = snapshot()
    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print("C5_MAINTENANCE_GUARD=" + ("PASS" if out["ok"] else "FAIL"))
        for row in out["issues"]:
            print(json.dumps(row, ensure_ascii=False))
    return 0 if out["ok"] else 23


if __name__ == "__main__":
    raise SystemExit(main())
