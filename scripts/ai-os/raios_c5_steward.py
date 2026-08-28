#!/usr/bin/env python3
"""C5 steward: watch, evolve, oversee, self-repair. Reuses keepers. No extra MCP. No C-seat consult. No WAL."""
from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))

from raios_absorb import absorb  # noqa: E402
from raios_c5_enforce import detect, enforce, teach  # noqa: E402
from raios_c5_index import build as build_index  # noqa: E402
from raios_c5_minute import exam as minute_exam  # noqa: E402
from raios_learn_ingest import ingest  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-steward"
GRANT = ROOT / ".ai-os" / "mcp" / "C5-GRANT.json"
NEED = ROOT / ".ai-os" / "learning" / "C5-NEED.json"

DENY = ("shell", "set_proven", "promote", "run_build", "write_product", "write_handoff")
ALLOWED_REPAIR = (
    ".ai-os/mcp/C5-GRANT.json",
    ".ai-os/mcp/POLICY.json",
    ".ai-os/mcp/SEAT-MAP.json",
    ".ai-os/board/NOW.json",
    ".ai-os/learning/C5-NEED.json",
    ".ai-os/learning/LAST-ENFORCE.json",
    ".ai-os/learning/LAST-ENFORCE.md",
    ".ai-os/learning/C5-TEACH.md",
    ".ai-os/reports/raios-service/LAST-MINUTE.json",
    ".ai-os/reports/raios-service/LAST-MINUTE.md",
    ".ai-os/receipts/c5-speak/LAST.json",
    ".ai-os/receipts/c5-speak/LAST.md",
    ".ai-os/receipts/c5-steward/LAST.json",
    ".ai-os/receipts/c5-steward/LAST.md",
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def load_mod(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def watch() -> dict:
    hb = load_mod("scripts/ai-os/raios-service-heartbeat.py")
    pulse = hb.evaluate()
    minute = minute_exam()
    language_alive = (ROOT / "src" / "raios" / "neuro_lingua" / "kernel.py").is_file()
    grant = load_json(GRANT)
    return {
        "name": "watch",
        "ok": pulse.get("gl005_proven") is False and minute.get("ok") is True and language_alive,
        "heartbeat_status": pulse.get("status"),
        "minute_ok": minute.get("ok"),
        "language_keeper": language_alive,
        "stale_locks": len(pulse.get("stale_locks") or []),
        "deny": list(grant.get("deny") or []),
        "mcp_new_tools": False,
        "detail": "heartbeat+minute+language keeper; stale locks observed not auto-released",
    }


def evolve() -> dict:
    absorbed = absorb([ROOT / ".ai-os" / "CORE-CONTRACT.md", ROOT / ".ai-os" / "state" / "DECISIONS.md", ROOT / ".ai-os" / "receipts"], source="c5-steward-evolve", mode="skim")
    index = build_index()
    lesson = ingest(
        "Steward evolve: absorb+index only. No HF weights. No C-seat consult. Language professional is NeuroLingua.",
        "c5-steward-evolve",
        ["scripts/ai-os/raios_c5_steward.py", "src/raios/neuro_lingua/customer.py"],
    )
    teach("التطوير هضم لا أوزان", "التكوير هنا absorb+index+ingest DISCOVERED. ليس Fine-tune.", law="HF_WEIGHTS_NE_CUSTOMER_LANGUAGE", kind="evolve")
    return {
        "name": "evolve",
        "ok": lesson.get("canonical") is False and lesson.get("gl005_proven") is False,
        "absorbed": absorbed.get("absorbed") if isinstance(absorbed, dict) else True,
        "index_docs": index.get("docs") if isinstance(index, dict) else None,
        "ingested": lesson.get("id"),
        "validated": False,
        "promoted": False,
        "consult_used": False,
        "detail": "DISCOVERED ingest; no promotion; no LoRA",
    }


def oversee() -> dict:
    enf = enforce()
    proof = load_json(ROOT / ".ai-os" / "receipts" / "c5-proof" / "LAST.json")
    grant = load_json(GRANT)
    need = load_json(NEED)
    attendance = next((a for a in (need.get("asks") or []) if a.get("kind") == "attendance"), {})
    forbidden = [d for d in DENY if d not in set(grant.get("deny") or [])]
    gl005_false = enf.get("gl005_proven") is False and proof.get("gl005_proven") is not True
    return {
        "name": "oversee",
        "ok": gl005_false and not forbidden and enf.get("wal_written") is False,
        "enforce_healthy": enf.get("healthy"),
        "enforce_issues": enf.get("issue_count"),
        "proof_gl005": proof.get("gl005_status") or proof.get("gl005_proven"),
        "helpers_needed_now": bool(attendance.get("needed_now")),
        "forbidden_missing_on_grant": forbidden,
        "detail": "enforce+proof receipt+grant deny; no auto PASS",
    }


def self_repair() -> dict:
    repaired: list[str] = []
    skipped: list[str] = []
    issues = detect()
    enf = enforce()
    if enf.get("actions"):
        repaired.append("enforce-father-son-plane")
    minute_path = ROOT / ".ai-os" / "reports" / "raios-service" / "LAST-MINUTE.json"
    if not minute_path.exists() or not load_json(minute_path):
        minute_exam()
        repaired.append("restore-minute-exam")
    speak_path = ROOT / ".ai-os" / "receipts" / "c5-speak" / "LAST.json"
    if not speak_path.exists():
        skipped.append("speak-receipt-missing-run-speak-separately")
    need = load_json(NEED)
    asks = list(need.get("asks") or [])
    changed = False
    for ask in asks:
        if ask.get("kind") == "attendance" and ask.get("needed_now") is True:
            ask["needed_now"] = False
            ask["what"] = "Helpers optional elsewhere. This channel is C1+executor+C5-git only."
            ask["blocks"] = None
            changed = True
            repaired.append("need-attendance-not-gate")
    if changed:
        need["asks"] = asks
        NEED.write_text(json.dumps(need, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    skipped.extend(
        [
            "product-write-denied",
            "gl003-uae-norway-routes-denied",
            "wal-write-denied",
            "lock-auto-release-denied",
            "new-mcp-tool-denied",
        ]
    )
    return {
        "name": "self_repair",
        "ok": enf.get("gl005_proven") is False,
        "issues_seen": [i.get("id") for i in issues],
        "repaired": repaired,
        "skipped_forbidden": skipped,
        "allowed_paths": list(ALLOWED_REPAIR),
        "self_modify_product": False,
        "detail": "Repair grant/board/need/receipts only. Pathology compels. Son does not usurp owner execute.",
    }


def render_md(rec: dict) -> str:
    lines = [
        "# وصي C5 — متابعة تطوير رقابة تصليح",
        "",
        f"- الوقت: `{rec['ts']}`",
        f"- استشارة مقاعد C: `{rec['consult_used']}`",
        f"- أدوات MCP جديدة: `{rec['mcp_new_tools']}`",
        f"- WAL لم يُمس: `{rec['wal_mtime_unchanged']}`",
        f"- GL005_PROVEN: `false`",
        "",
        "| أداة | نجح | ماذا |",
        "|---|---|---|",
    ]
    for tool in rec["tools"]:
        lines.append(f"| `{tool['name']}` | `{tool.get('ok')}` | {tool.get('detail')} |")
    repair = next((t for t in rec["tools"] if t["name"] == "self_repair"), {})
    lines += [
        "",
        f"- أُصلح: `{repair.get('repaired')}`",
        f"- رُفض عمداً: `{repair.get('skipped_forbidden')}`",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    return "\n".join(lines)


def steward() -> dict:
    wal_before = wal_mtime()
    tools = [watch(), evolve(), oversee(), self_repair()]
    rec = {
        "schema": "raios.c5-steward.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "consult_used": False,
        "council_seats_this_channel": False,
        "mcp_new_tools": False,
        "tools": tools,
        "ok": all(t.get("ok") for t in tools),
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "PATHOLOGY_COMPELS_REPAIR",
            "SON_MUST_NOT_USURP_FATHER",
            "SELF_REPAIR_NE_PRODUCT_WRITE",
            "SELF_REPAIR_NE_LOCK_RELEASE",
            "STEWARD_NE_NEW_MCP_TOOL",
            "THIS_CHANNEL_NO_C_SEAT_CONSULT",
        ],
    }
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("STEWARD_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "LAST.md").write_text(render_md(rec), encoding="utf-8")
    return rec


def main() -> int:
    argparse.ArgumentParser().parse_args()
    rec = steward()
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "tools": [t["name"] for t in rec["tools"]],
                "consult_used": False,
                "mcp_new_tools": False,
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
