#!/usr/bin/env python3
"""C5 live cycle: theory first, then >=85% practice. Teach while doing. Compel on pathology."""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from raios_absorb import absorb  # noqa: E402
from raios_c5_enforce import enforce, teach  # noqa: E402
from raios_c5_hunt import hunt  # noqa: E402
from raios_c5_index import build as build_index  # noqa: E402
from raios_c5_read import search  # noqa: E402
from raios_c5_mind import write_mind  # noqa: E402
from raios_five_consult import consult  # noqa: E402
from raios_summon import render as summon_render  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT = ROOT / ".ai-os" / "learning" / "LAST-LEARN.json"
OUT_MD = ROOT / ".ai-os" / "learning" / "LAST-LEARN.md"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def step(kind: str, name: str, fn, steps: list) -> dict:
    t0 = time.perf_counter()
    result = fn()
    rec = {
        "kind": kind,
        "name": name,
        "ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "ok": True,
    }
    steps.append(rec)
    teach(
        f"{'نظرية' if kind == 'theory' else 'ممارسة'}: {name}",
        json.dumps({k: result.get(k) if isinstance(result, dict) else result for k in (
            ["status", "files", "absorbed", "docs", "hit_count", "healthy", "issue_count", "session_id", "fastest_local", "contradiction_count"]
            if isinstance(result, dict)
            else []
        ) if isinstance(result, dict) and k in result}, ensure_ascii=False),
        law="LEARN_AND_TEACH_ARE_ONE",
        kind=kind,
    )
    return result if isinstance(result, dict) else rec


def learn() -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    steps: list[dict] = []
    # THEORY FIRST (then 85% practice)
    step("theory", "hunt", hunt, steps)
    step("theory", "absorb-skim-max-ai-os", lambda: absorb([ROOT / ".ai-os"], source="c5-learn-max", mode="skim"), steps)
    step("theory", "index", build_index, steps)
    # PRACTICE 85% — father-son enforce, pulse, consult, summon
    import importlib.util

    spec = importlib.util.spec_from_file_location("hb", ROOT / "scripts" / "ai-os" / "raios-service-heartbeat.py")
    hb = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hb)

    def pulse():
        receipt = hb.evaluate()
        hb.OUT_DIR.mkdir(parents=True, exist_ok=True)
        hb.EVAL_MD.write_text(hb.render_eval_md(receipt), encoding="utf-8")
        hb.refresh_board()
        mind = write_mind()
        receipt["mind_contradictions"] = mind.get("contradiction_count")
        receipt["mind_laws"] = mind.get("law_count")
        hb.OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        hb.EVAL_MD.write_text(hb.render_eval_md(receipt), encoding="utf-8")
        hb.refresh_board()
        return receipt

    step("practice", "enforce-1", enforce, steps)
    step("practice", "pulse", pulse, steps)
    step("practice", "enforce-2", enforce, steps)
    step("practice", "consult", consult, steps)
    step("practice", "summon-render", summon_render, steps)
    step("practice", "mind", write_mind, steps)
    step("practice", "enforce-3", enforce, steps)
    step("practice", "search-apply", lambda: search("GL005_PROVEN"), steps)
    step("practice", "enforce-4", enforce, steps)
    step("practice", "consult-2", consult, steps)
    step("practice", "pulse-2", pulse, steps)
    step("practice", "enforce-5", enforce, steps)
    step("practice", "summon-2", summon_render, steps)
    step("practice", "mind-2", write_mind, steps)
    step("practice", "enforce-6", enforce, steps)
    step("practice", "search-grant", lambda: search("C5_GRANT_IS_PERMANENT"), steps)
    step("practice", "enforce-7", enforce, steps)

    theory_n = sum(1 for s in steps if s["kind"] == "theory")
    practice_n = sum(1 for s in steps if s["kind"] == "practice")
    total = len(steps)
    ratio = practice_n / total if total else 0.0
    first_practice = next(i for i, s in enumerate(steps) if s["kind"] == "practice")
    theory_first = all(s["kind"] == "theory" for s in steps[:first_practice])
    rec = {
        "schema": "raios.c5-learn.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "relation": "father-son",
        "teacher": True,
        "theory_first": theory_first,
        "theory_steps": theory_n,
        "practice_steps": practice_n,
        "total_steps": total,
        "practice_ratio": round(ratio, 4),
        "practice_ratio_ok": ratio >= 0.85 and theory_first,
        "steps": steps,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "LEARN_THEORY_THEN_PRACTICE_85",
            "LEARN_AND_TEACH_ARE_ONE",
            "FATHER_SON_BIND_SAME_LAWS",
            "PATHOLOGY_COMPELS_REPAIR",
        ],
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("LEARN_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# تعلم C5 الحي\n\n"
        f"- نظرية أولاً: `{theory_first}`\n"
        f"- نظرية/ممارسة: `{theory_n}/{practice_n}` من `{total}`\n"
        f"- نسبة الممارسة: `{rec['practice_ratio']}` (المطلوب ≥ 0.85)\n"
        f"- معلم أثناء التعلم والتنفيذ: `true`\n"
        f"- WAL لم يُمس: `{rec['wal_mtime_unchanged']}`\n"
        f"- GL005_PROVEN: `false`\n",
        encoding="utf-8",
    )
    if not rec["practice_ratio_ok"]:
        raise SystemExit(f"PRACTICE_RATIO_{rec['practice_ratio']}")
    return rec


def main() -> int:
    rec = learn()
    print(
        json.dumps(
            {
                "from": "C5",
                "theory_first": rec["theory_first"],
                "practice_ratio": rec["practice_ratio"],
                "ok": rec["practice_ratio_ok"],
                "gl005_proven": False,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
