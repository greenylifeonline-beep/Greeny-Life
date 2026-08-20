#!/usr/bin/env python3
"""C5 minute exam: inject-before-execute, fail-closed. Overwrites LAST. No WAL. No PASS."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
LADDER = ROOT / ".ai-os" / "learning" / "TOOLS-LADDER.json"
GRANT = ROOT / ".ai-os" / "mcp" / "C5-GRANT.json"
CASE002 = ROOT / ".ai-os" / "council" / "CASE-002.json"
LEARN = ROOT / ".ai-os" / "learning" / "LAST-LEARN.json"
MIND = ROOT / ".ai-os" / "learning" / "C5-MIND.json"
OUT = ROOT / ".ai-os" / "reports" / "raios-service" / "LAST-MINUTE.json"
OUT_MD = ROOT / ".ai-os" / "reports" / "raios-service" / "LAST-MINUTE.md"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def exam() -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    ladder = load(LADDER)
    grant = load(GRANT)
    case = load(CASE002)
    learn = load(LEARN)
    mind = load(MIND)
    deny = set(grant.get("deny") or [])
    inject = bool(ladder.get("inject_before_execute"))
    core = (ROOT / ".ai-os" / "CORE-CONTRACT.md").exists()
    decisions = (ROOT / ".ai-os" / "state" / "DECISIONS.md").exists()
    ratio = learn.get("practice_ratio")
    checks = [
        check("inject_flag", inject, "INJECT_BEFORE_EXECUTE"),
        check("live_memory_core", core, "CORE-CONTRACT"),
        check("live_memory_decisions", decisions, "DECISIONS"),
        check("ladder_present", bool(ladder.get("learn_from_system")), "TOOLS-LADDER"),
        check("gl005_false", case.get("gl005_proven") is False or not case, "GL-005 not proven"),
        check("no_self_promote", "promote" in deny and "set_proven" in deny, "grant deny"),
        check("practice_ratio", ratio is None or float(ratio) >= 0.85, str(ratio)),
        check("contradictions", int(mind.get("contradiction_count") or 0) == 0, str(mind.get("contradiction_count"))),
        check("no_shell_tool", "shell" in deny, "C5 has no shell"),
    ]
    ok = all(c["ok"] for c in checks)
    rec = {
        "schema": "raios.c5-minute.v1",
        "ts": utc(),
        "from": "C5",
        "ok": ok,
        "checks": checks,
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": ["INJECT_BEFORE_EXECUTE", "MINUTE_EXAM_NE_SECOND_WAL", "PROMOTE_THEN_RETIRE_TRAINER"],
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("MINUTE_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        f"# امتحان الدقيقة\n\n- نجح: `{ok}`\n- حقن قبل التنفيذ: `{inject}`\n- GL005_PROVEN: `false`\n",
        encoding="utf-8",
    )
    return rec


def main() -> int:
    rec = exam()
    print(json.dumps({"ok": rec["ok"], "gl005_proven": False}, ensure_ascii=False))
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
