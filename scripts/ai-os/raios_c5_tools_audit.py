#!/usr/bin/env python3
"""Prove language + teaching tools. Main Cortex is not the spine. No WAL. No PASS print."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios.neuro_lingua.compress import compress_meaning  # noqa: E402
from raios.neuro_lingua.experience import learning_score, route_path  # noqa: E402
from raios.neuro_lingua.governor import CognitiveResourceGovernor  # noqa: E402
from raios.neuro_lingua.kernel import NeuroLingua  # noqa: E402
from raios.neuro_lingua.qwen_runtime import CORTEX_IDENTITY, generate, probe  # noqa: E402
from raios.neuro_lingua.kae import HTTP_DEMO, assimilate  # noqa: E402
from raios.neuro_lingua.training import decide_training  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-tools"

LANGUAGE_MODULES = (
    "kernel.py",
    "customer.py",
    "compress.py",
    "realize.py",
    "pragmatics.py",
    "language.py",
    "dialect.py",
    "concepts.py",
    "protected.py",
    "verify.py",
    "governor.py",
    "router.py",
    "schema.py",
    "qwen_runtime.py",
    "kae.py",
)
TEACHING_SCRIPTS = (
    "raios_learn_ingest.py",
    "raios_c5_minute.py",
    "raios_c5_experience.py",
    "raios_c5_train.py",
    "raios_c5_watchdog.py",
    "raios_c5_speak.py",
    "raios_c5_qwen.py",
    "raios_c5_kae.py",
    "raios_c5_grind.py",
    "raios_c5_week.py",
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def files_exist() -> list[dict]:
    rows = []
    for name in LANGUAGE_MODULES:
        path = ROOT / "src" / "raios" / "neuro_lingua" / name
        rows.append(check(f"lang:{name}", path.is_file(), str(path.relative_to(ROOT))))
    for name in TEACHING_SCRIPTS:
        path = ROOT / "scripts" / "ai-os" / name
        rows.append(check(f"teach:{name}", path.is_file(), str(path.relative_to(ROOT))))
    return rows


async def language_live() -> list[dict]:
    nl = NeuroLingua()
    gov = CognitiveResourceGovernor()
    admission = gov.admit("SEMANTIC_INTERPRETATION")
    interpreted = await nl.interpret("The supplier shipped the products to Norway.")
    realized = await nl.realize(interpreted.meaning, "en")
    spoken = await nl.speak_to_customer("لو سمحت عندكم عسل البرسيم؟", "GREENY_LIFE_EGYPT")
    gulf = await nl.speak_to_customer("إذا ما عليك أمر نبيه عرض سعر للعسل", "GREENS_NATURE_UAE")
    norway = await nl.speak_to_customer("Har dere shipment status for H001?", "GREEN_LINES_NORWAY_EU")
    compressed = compress_meaning("The supplier shipped the products to Norway.")
    return [
        check("cortex_denied", admission.admitted is False, admission.reason),
        check("cortex_reason", admission.reason == "MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK", admission.reason),
        check("interpret", interpreted.meaning.semantics.action is not None or compressed["pattern"]["action"] == "ship", interpreted.meaning.source_locale or "und"),
        check("compress_pattern", compressed["pattern"]["actor"] == "supplier" and compressed["word_list"] is False, str(compressed["pattern"])),
        check("realize", bool(realized.text), realized.text[:80]),
        check("speak_eg", spoken.get("ok") is True and spoken.get("llm_calls") == 0, spoken.get("customer_text") or ""),
        check("speak_uae_no_price", gulf.get("action") == "quote_request" and gulf.get("facts", {}).get("price_proven") is False, gulf.get("customer_text") or ""),
        check("speak_no", norway.get("ok") is True and "och" not in (norway.get("customer_text") or "").split(), norway.get("customer_text") or ""),
        check("speak_not_cortex", spoken.get("llm_calls") == 0, str(spoken.get("llm_calls"))),
    ]


def teaching_live(*, require_student: bool) -> list[dict]:
    from raios_learn_ingest import ingest
    from raios_c5_minute import exam
    from raios_c5_experience import main as experience_main

    ingest_rec = ingest(
        "Qwen student live; Main Cortex isolated as dangerous/weak.",
        "tools-audit",
        ["CASE-016", "D-048"],
    )
    minute = exam()
    exp_code = experience_main()
    status = probe(use_cache=False)
    gen = generate("Say only: student")
    train_path = ROOT / "scripts" / "ai-os" / "raios_c5_train.py"
    watchdog_path = ROOT / "scripts" / "ai-os" / "raios_c5_watchdog.py"
    path = route_path(complexity=0.9, risk=0.4, novelty=0.8, ck=0.4, deep_available=bool(status.get("student_live")))
    score = learning_score(1, 1, 1, 1, 1, 1)
    policy = decide_training("changing_fact")
    kae = assimilate(HTTP_DEMO, ingest=True, external_calls=0)
    student_ok = bool(status.get("student_live") and gen.get("ok") and not gen.get("cortex_used"))
    rows = [
        check("ingest_discovered", ingest_rec.get("knowledge_state") == "DISCOVERED" and ingest_rec.get("wal_written") is False, ingest_rec.get("id") or ""),
        check("minute", minute.get("ok") is True and minute.get("gl005_proven") is False, json.dumps(minute.get("ok"))),
        check("experience", exp_code == 0, str(exp_code)),
        check("train_script", train_path.is_file(), "raios_c5_train.py"),
        check("watchdog_script", watchdog_path.is_file(), "raios_c5_watchdog.py"),
        check("learning_score", score == 1.0, str(score)),
        check("training_policy", policy.get("install_cpt") is False, policy.get("decision") or ""),
        check("student_probe", bool(status.get("student_live")), status.get("reason") or ""),
        check("student_generate", bool(gen.get("ok")), (gen.get("response") or gen.get("error") or "")[:120]),
        check("cortex_not_used", gen.get("cortex_used") is False or gen.get("error") == "MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK" or not gen.get("ok"), str(gen.get("cortex_used"))),
        check("deep_path_label", path["deep_available"] == bool(status.get("student_live")), path["reason"]),
        check("identity_unswapped", CORTEX_IDENTITY == "qwen3.6:35b-a3b", CORTEX_IDENTITY),
        check("kae_retile", kae.get("ok") is True and len(kae.get("tiles") or {}) == 16, str((kae.get("metrics") or {}).get("knowledge_yield"))),
        check("kae_no_cortex", kae.get("cortex_used") is False and kae.get("consult_used") is False, "isolated"),
    ]
    if require_student:
        rows.append(check("require_student", student_ok, status.get("student_model") or status.get("reason") or ""))
    else:
        rows.append(check("require_student", True, "optional_on_this_host"))
    return rows


def audit(*, require_student: bool) -> dict:
    wal_before = wal_mtime()
    checks = files_exist() + asyncio.run(language_live()) + teaching_live(require_student=require_student)
    ok = all(row["ok"] for row in checks)
    rec = {
        "schema": "raios.c5-tools-audit.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "ok": ok,
        "failed": [row["name"] for row in checks if not row["ok"]],
        "checks": checks,
        "cortex_identity": CORTEX_IDENTITY,
        "cortex_isolated": True,
        "require_student": require_student,
        "consult_used": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "MAIN_CORTEX_ISOLATED_DANGEROUS_WEAK",
            "STUDENT_NE_MAIN_CORTEX",
            "LANGUAGE_PROFESSIONAL_IS_NEUROLINGUA",
            "WORD_LIST_NE_LANGUAGE",
        ],
    }
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("TOOLS_AUDIT_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# تدقيق أدوات اللغة والتعليم",
        "",
        f"- نجح: `{ok}`",
        f"- فشل: `{rec['failed']}`",
        f"- القشرة معزولة: `true` (`{CORTEX_IDENTITY}`)",
        f"- GL005_PROVEN: `false`",
        "",
    ]
    for row in checks:
        mark = "OK" if row["ok"] else "FAIL"
        lines.append(f"- `{mark}` {row['name']} — {row['detail'][:160]}")
    lines += ["", "`GL005_PROVEN=false`", ""]
    (OUT_DIR / "LAST.md").write_text("\n".join(lines), encoding="utf-8")
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--require-student", action="store_true", default=True)
    p.add_argument("--allow-missing-student", action="store_true")
    args = p.parse_args()
    rec = audit(require_student=not args.allow_missing_student)
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "failed": rec["failed"],
                "n": len(rec["checks"]),
                "cortex_isolated": True,
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
