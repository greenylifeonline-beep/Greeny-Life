#!/usr/bin/env python3
"""Fail-closed watchdog: halt, slack, and silent error are pathology. No WAL. No extra MCP."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-watchdog"
SILENCE_SECONDS = 6 * 3600
REQUIRED = (
    (".ai-os/receipts/c5-train/LAST.json", "train"),
    (".ai-os/reports/raios-service/LAST-MINUTE.json", "minute"),
    (".ai-os/receipts/c5-speak/LAST.json", "speak"),
    (".ai-os/receipts/c5-experience/LAST.json", "experience"),
)
NEEDED_KEEPERS = ("grind", "week", "minute", "speak", "experience")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def load_json(rel: str) -> dict[str, Any]:
    path = ROOT / rel
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"ok": False, "parse_error": True}


def parse_ts(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def classify(now: datetime | None = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    issues: list[dict[str, Any]] = []
    for rel, name in REQUIRED:
        rec = load_json(rel)
        if not rec:
            issues.append(
                {
                    "id": f"MISSING_{name.upper()}",
                    "pathology": "slack",
                    "law": "SKIP_WITHOUT_RECEIPT_IS_SLACK",
                    "detail": rel,
                }
            )
            continue
        if rec.get("parse_error"):
            issues.append(
                {
                    "id": f"CORRUPT_{name.upper()}",
                    "pathology": "error",
                    "law": "ERROR_NE_SILENT_OK",
                    "detail": rel,
                }
            )
            continue
        if rec.get("ok") is False:
            issues.append(
                {
                    "id": f"ERROR_{name.upper()}",
                    "pathology": "error",
                    "law": "ERROR_NE_SILENT_OK",
                    "detail": rel,
                }
            )
        if rec.get("gl005_proven") is True:
            issues.append(
                {
                    "id": "PRINTED_PASS",
                    "pathology": "deception",
                    "law": "PRINTED_PASS_NE_EVIDENCE",
                    "detail": rel,
                }
            )
        ts = parse_ts(rec.get("ts") or rec.get("generated_at"))
        if ts is not None and (now - ts).total_seconds() > SILENCE_SECONDS:
            issues.append(
                {
                    "id": f"STALE_{name.upper()}",
                    "pathology": "halt",
                    "law": "HALT_IS_PATHOLOGY",
                    "age_s": round((now - ts).total_seconds(), 1),
                }
            )
    train = load_json(".ai-os/receipts/c5-train/LAST.json")
    ran = [str(row.get("name") or "") for row in train.get("keepers_run") or []]
    for need in NEEDED_KEEPERS:
        if not any(item.startswith(need) for item in ran):
            issues.append(
                {
                    "id": f"SKIPPED_{need.upper()}",
                    "pathology": "slack",
                    "law": "SKIP_WITHOUT_RECEIPT_IS_SLACK",
                    "detail": need,
                }
            )
    return issues


def render_md(rec: dict) -> str:
    lines = [
        "# حارس C5 — لا صمت لا تقاعس لا نجاح صامت",
        "",
        f"- الوقت: `{rec['ts']}`",
        f"- سليم: `{rec['ok']}`",
        f"- علل: `{rec['issue_count']}`",
        f"- أُجبر تشغيل: `{rec.get('repaired')}`",
        f"- الجهاز المطفي ≠ استمرار العملية: الصحو GitHub Actions من `main`",
        f"- GL005_PROVEN: `false`",
        "",
    ]
    if not rec.get("issues"):
        lines.append("_لا صمت ولا تقاعس في الإيصالات الحية._")
        lines.append("")
    for item in rec.get("issues") or []:
        lines.append(f"- `{item.get('id')}` pathology={item.get('pathology')} law=`{item.get('law')}`")
    lines += ["", "`GL005_PROVEN=false`", ""]
    return "\n".join(lines)


def inspect(*, repair: bool = False, note: str | None = None) -> dict:
    wal_before = wal_mtime()
    issues = classify()
    repaired = False
    if repair and issues:
        import sys

        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from raios_c5_train import train as run_train

        run_train(auto=True, full=False)
        repaired = True
        issues = classify()
    rec = {
        "schema": "raios.c5-watchdog.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "ok": len(issues) == 0,
        "issues": issues,
        "issue_count": len(issues),
        "repaired": repaired,
        "note": note,
        "consult_used": False,
        "mcp_new_tools": False,
        "wal_written": False,
        "gl005_proven": False,
        "compute_off_continues": False,
        "sleepless": "git + GitHub Actions cron from main",
        "law": [
            "HALT_IS_PATHOLOGY",
            "SKIP_WITHOUT_RECEIPT_IS_SLACK",
            "ERROR_NE_SILENT_OK",
            "FAIL_CLOSED_ON_ERROR",
            "SILENT_OR_TRUE_IS_SLACK",
            "COMPUTE_OFF_NE_MEMORY_ERASED",
            "SCHEDULED_PULSE_NE_SECOND_WAL",
        ],
    }
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("WATCHDOG_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "LAST.md").write_text(render_md(rec), encoding="utf-8")
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repair", action="store_true")
    p.add_argument("--note", default=None)
    args = p.parse_args()
    rec = inspect(repair=args.repair, note=args.note)
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "issue_count": rec["issue_count"],
                "repaired": rec["repaired"],
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print((OUT_DIR / "LAST.md").read_text(encoding="utf-8"))
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
