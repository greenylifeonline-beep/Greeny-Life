#!/usr/bin/env python3
"""Run the local Qwen student. Main Cortex stays isolated. No WAL. No HF dump into the repo."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from raios.neuro_lingua.qwen_runtime import CORTEX_IDENTITY, generate, probe  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-qwen"
TEACH_PROMPT = (
    "Compress this to actor/action/object/destination in one short line, English: "
    "The supplier shipped the products to Norway."
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def run(*, do_generate: bool, prompt: str) -> dict:
    wal_before = wal_mtime()
    status = probe(use_cache=False)
    rec: dict = {
        "schema": "raios.c5-qwen.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "probe": status,
        "cortex_identity": CORTEX_IDENTITY,
        "cortex_isolated": True,
        "cortex_used": False,
        "student_live": bool(status.get("student_live")),
        "student_model": status.get("student_model"),
        "generate": None,
        "ok": bool(status.get("student_live")),
        "consult_used": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": status.get("law") or [],
    }
    if do_generate:
        rec["generate"] = generate(prompt)
        rec["ok"] = bool(rec["generate"].get("ok")) and rec["cortex_used"] is False
        rec["cortex_used"] = bool(rec["generate"].get("cortex_used"))
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("QWEN_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# Qwen الطالب — القشرة الرئيسية معزولة",
        "",
        f"- الوقت: `{rec['ts']}`",
        f"- Ollama: `{status.get('present')}`",
        f"- الطالب: `{rec['student_model']}` حي=`{rec['student_live']}`",
        f"- هوية القشرة: `{CORTEX_IDENTITY}`",
        f"- القشرة معزولة: `true`",
        f"- استُخدمت القشرة: `{rec['cortex_used']}`",
        f"- توليد: `{bool((rec.get('generate') or {}).get('ok'))}`",
        f"- GL005_PROVEN: `false`",
        "",
        "Main Cortex أخطر وأضعف نقطة. لا تُقبل على المسار الحي. الطالب ليس هويتها.",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    (OUT_DIR / "LAST.md").write_text("\n".join(lines), encoding="utf-8")
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--generate", action="store_true")
    p.add_argument("--prompt", default=TEACH_PROMPT)
    p.add_argument("--cortex", action="store_true", help="refused: Main Cortex is isolated")
    args = p.parse_args()
    if args.cortex:
        print(json.dumps({"ok": False, "error": "MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK", "gl005_proven": False}, ensure_ascii=False))
        return 2
    rec = run(do_generate=args.generate or not args.probe, prompt=args.prompt)
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "student_live": rec["student_live"],
                "student_model": rec["student_model"],
                "cortex_isolated": True,
                "cortex_used": rec["cortex_used"],
                "response": ((rec.get("generate") or {}).get("response") or "")[:240],
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
