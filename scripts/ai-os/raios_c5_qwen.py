#!/usr/bin/env python3
"""Qwen student + C1 cortex verbs. Executor never throws. No WAL. No HF dump."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from raios.neuro_lingua.cortex import (  # noqa: E402
    CORTEX_IDENTITY,
    OWNER,
    gate_run,
    refuse_throw,
    status as cortex_status,
    treat,
)
from raios.neuro_lingua.qwen_runtime import generate, probe  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-qwen"
CORTEX_DIR = ROOT / ".ai-os" / "receipts" / "c5-cortex"
TEACH_PROMPT = (
    "Compress this to actor/action/object/destination in one short line, English: "
    "The supplier shipped the products to Norway."
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def _write(path: Path, rec: dict, md: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (path / "LAST.md").write_text(md, encoding="utf-8")


def run_student(*, do_generate: bool, prompt: str) -> dict:
    wal_before = wal_mtime()
    status = probe(use_cache=False)
    st = cortex_status()
    rec: dict = {
        "schema": "raios.c5-qwen.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "probe": status,
        "cortex_identity": CORTEX_IDENTITY,
        "cortex_owner": OWNER,
        "isolated_as_disposal": False,
        "cortex_hold": st["hold"],
        "cortex_isolated": False,
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
    lines = [
        "# Qwen الطالب — القشرة ملك C1",
        "",
        f"- الوقت: `{rec['ts']}`",
        f"- Ollama: `{status.get('present')}`",
        f"- الطالب: `{rec['student_model']}` حي=`{rec['student_live']}`",
        f"- هوية القشرة: `{CORTEX_IDENTITY}`",
        f"- المالك: `{OWNER}` أفعال: treat / run / throw",
        f"- عزل كرمي: `false`",
        f"- انتظار أمر التشغيل: `{st['hold']}`",
        f"- استُخدمت القشرة: `{rec['cortex_used']}`",
        f"- توليد: `{bool((rec.get('generate') or {}).get('ok'))}`",
        f"- GL005_PROVEN: `false`",
        "",
        "المنفّذ لا يرمي القشرة. الطالب ليس هويتها.",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    _write(OUT_DIR, rec, "\n".join(lines))
    return rec


def emit_cortex(kind: str, rec: dict, extra_md: list[str]) -> dict:
    rec = {**rec, "ts": utc(), "from": "C5", "parent": "C1"}
    lines = [
        "# القشرة — ملك C1",
        "",
        f"- الفعل: `{kind}`",
        f"- الهوية: `{CORTEX_IDENTITY}`",
        f"- المالك: `{OWNER}`",
        f"- عزل كرمي: `false`",
        f"- GL005_PROVEN: `false`",
        "",
        *extra_md,
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    _write(CORTEX_DIR, rec, "\n".join(lines))
    print(json.dumps(rec, ensure_ascii=False, indent=2, default=str))
    print((CORTEX_DIR / "LAST.md").read_text(encoding="utf-8"))
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--probe", action="store_true")
    p.add_argument("--generate", action="store_true")
    p.add_argument("--prompt", default=TEACH_PROMPT)
    p.add_argument("--cortex", action="store_true", help="C1 cortex status: treat / run / throw")
    p.add_argument("--treat", action="store_true", help="diagnose cortex; does not load or throw")
    p.add_argument("--run", action="store_true", help="run only if C1 granted and host can")
    p.add_argument("--throw", action="store_true", help="refused: only C1 throws")
    args = p.parse_args()
    if args.throw:
        rec = refuse_throw()
        emit_cortex("throw", rec, ["المنفّذ لا يرمي. C1 فقط."])
        return 2
    if args.treat:
        rec = treat()
        emit_cortex(
            "treat",
            rec,
            [
                f"- ضعف: `{rec['weakness']}`",
                f"- إصلاح: `{rec['repair']}`",
                f"- gate: `{rec['gate']['reason']}`",
            ],
        )
        return 0
    if args.cortex or args.run:
        gate = gate_run()
        rec = {
            "ok": bool(gate["admitted"]) if args.run else True,
            "verb": "run" if args.run else "status",
            "error": None if (gate["admitted"] or not args.run) else gate["reason"],
            "gate": {k: gate[k] for k in ("admitted", "reason", "fallback", "hold", "thrown", "run_granted", "host_can_run", "host_reason")},
            "identity": CORTEX_IDENTITY,
            "owner": OWNER,
            "verbs": ["treat", "run", "throw"],
            "isolated_as_disposal": False,
            "loaded": False,
            "gl005_proven": False,
        }
        emit_cortex(
            rec["verb"],
            rec,
            [
                f"- hold: `{gate['hold']}`",
                f"- run_granted: `{gate['run_granted']}`",
                f"- host: `{gate['host_reason']}`",
                f"- reason: `{gate['reason']}`",
                "لا تحميل أوزان. هذه الآلة بلا GPU.",
            ],
        )
        if args.run and not gate["admitted"]:
            return 2
        return 0
    rec = run_student(do_generate=args.generate or not args.probe, prompt=args.prompt)
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "student_live": rec["student_live"],
                "student_model": rec["student_model"],
                "cortex_owner": OWNER,
                "isolated_as_disposal": False,
                "cortex_hold": rec["cortex_hold"],
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
