#!/usr/bin/env python3
"""In-repo mission board. One file everyone opens. Opinions go to Cognitive WAL. Not a second bus."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / ".ai-os" / "board"
NOW_JSON = BOARD / "NOW.json"
NOW_MD = BOARD / "NOW.md"
OPINIONS = BOARD / "opinions.jsonl"

CODES = {
    "C0": {"actor": "USER", "name": "صاحب المشروع", "where": "داخل الشات / داخل اللوحة"},
    "C1": {"actor": "COMMANDER", "name": "القائد Cursor", "where": "داخل المشروع"},
    "C2": {"actor": "CONSULTANT", "name": "المستشار التنفيذي", "where": "خارج المشروع — يقرأ اللوحة ويكتب رأيه"},
    "C3": {"actor": "ENGINEER", "name": "المهندس PowerShell", "where": "Repair"},
    "C4": {"actor": "RAIOS", "name": "نواة الخدمة", "where": "داخل المشروع"},
}
ACTOR_TO_CODE = {v["actor"]: k for k, v in CODES.items()}
ACTOR_TO_CODE["POWERSHELL"] = "C3"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def emit_wal(actor: str, text: str, msg_id: str, intent: str) -> dict:
    runtime = ROOT / "RAIOS" / "V9" / "runtime"
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    import cognitive_event_bus as bus  # type: ignore

    out = bus.emit(
        event_type="LEARNING",
        actor=actor.lower(),
        intent=intent,
        tool="raios-board",
        success=True,
        confidence=1.0,
        metadata={
            "board": ".ai-os/board/NOW.md",
            "code": ACTOR_TO_CODE.get(actor, "?"),
            "message_id": msg_id,
            "text": text[:4000],
            "knowledge_state": "DISCOVERED",
        },
        materialize=False,
    )
    result = out.get("result") or {}
    event = out.get("event") or {}
    return {
        "wal_status": result.get("status"),
        "event_id": event.get("event_id") or result.get("event_id"),
    }


def load_now() -> dict:
    if NOW_JSON.exists():
        return json.loads(NOW_JSON.read_text(encoding="utf-8"))
    return {}


def load_opinions() -> list[dict]:
    if not OPINIONS.exists():
        return []
    rows = []
    for raw in OPINIONS.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def render(state: dict) -> None:
    BOARD.mkdir(parents=True, exist_ok=True)
    opinions = load_opinions()
    lines = [
        "# لوحة المهمة — NOW",
        "",
        "ملف واحد داخل المشروع. المستشار الخارجي لا يحتاج أن يعيش في المستودع؛ يسحب هذا الملف ويعرف الحالة والمطلوب ويكتب رأيه برمزه.",
        "",
        f"- الفرع: `{state.get('branch')}`",
        f"- HEAD: `{state.get('head')}`",
        f"- حدّث: `{state.get('updated_at')}`",
        f"- الحالة: `{state.get('mission_status')}`",
        "",
        "## الرموز",
        "",
        "| رمز | الطرف | مكانه | المطلوب منه الآن |",
        "|---|---|---|---|",
    ]
    required = state.get("required") or {}
    for code, meta in CODES.items():
        lines.append(
            f"| `{code}` | {meta['name']} (`{meta['actor']}`) | {meta['where']} | {required.get(code, '—')} |"
        )
    lines += [
        "",
        "## المهمة الحالية",
        "",
        state.get("mission") or "—",
        "",
        "## الجدول",
        "",
        f"- الآن: {state.get('schedule', {}).get('now', '—')}",
        f"- التالي: {state.get('schedule', {}).get('next', '—')}",
        f"- ممنوع: {state.get('schedule', {}).get('forbidden', '—')}",
        "",
        "## كيف يشارك المستشار (C2) من خارج المشروع",
        "",
        "1. `git pull origin v9-neurolingua-semantic-kernel`",
        "2. اقرأ `.ai-os/board/NOW.md`",
        "3. اكتب رأيك:",
        "",
        "```bash",
        'python3 scripts/ai-os/raios-board.py opinion --code C2 --text "رأيك هنا"',
        "```",
        "",
        "إن لم يستطع الدفع: يلصق النص في الشات، والقائد يضعه على اللوحة.",
        "",
        "## الآراء",
        "",
    ]
    if not opinions:
        lines.append("_لا آراء بعد._")
        lines.append("")
    for rec in opinions[-20:]:
        lines.append(f"### {rec.get('ts')} — {rec.get('code')} {rec.get('from')}")
        lines.append("")
        lines.append(str(rec.get("text") or "").strip())
        lines.append("")
        if rec.get("event_id"):
            lines.append(f"`event_id={rec['event_id']}`")
            lines.append("")
    NOW_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_code(value: str) -> tuple[str, str]:
    value = value.strip().upper()
    if value in CODES:
        return value, CODES[value]["actor"]
    if value in ACTOR_TO_CODE:
        return ACTOR_TO_CODE[value], value if value != "POWERSHELL" else "ENGINEER"
    raise SystemExit(f"UNKNOWN_CODE:{value}")


def save_now(state: dict) -> None:
    BOARD.mkdir(parents=True, exist_ok=True)
    NOW_JSON.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    render(state)


def opinion(code: str, text: str) -> dict:
    code, actor = resolve_code(code)
    text = text.strip()
    if not text:
        raise SystemExit("EMPTY_TEXT")
    msg_id = str(uuid.uuid4())
    wal = emit_wal(actor, text, msg_id, "BOARD_OPINION")
    rec = {
        "schema": "raios.board-opinion.v1",
        "id": msg_id,
        "ts": utc(),
        "code": code,
        "from": actor,
        "text": text,
        "knowledge_state": "DISCOVERED",
        **wal,
    }
    BOARD.mkdir(parents=True, exist_ok=True)
    with OPINIONS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    state = load_now()
    state["updated_at"] = utc()
    save_now(state)
    return rec


def bootstrap() -> dict:
    state = {
        "schema": "raios.mission-board.v1",
        "branch": git("branch", "--show-current") or "v9-neurolingua-semantic-kernel",
        "head": git("rev-parse", "HEAD"),
        "updated_at": utc(),
        "mission_status": "WAIT_ATOMIC_RECEIPT",
        "mission": "تنظيم قبل التوسع. المهندس يشغّل منفّذاً ذرياً fail-closed لـ GL-004/GL-005. المستشار يراجع الإيصال. القائد يحاول كسر أي false-PASS. لا census. لا حذف health-reporter.ts.",
        "schedule": {
            "now": "انتظار حمولة الإيصال الثمانية: HEAD, SAFETY_TAG, children[] exits, PARENT_EXIT, RECEIPT, RECEIPT_SHA256, GL004_PROVEN, GL005_PROVEN",
            "next": "المراجع يكسر الإيصال إن وُجد false-PASS ثم تحويل الحلقة إلى CICF: ربط الحذف بـ HEAD ورسم الاعتمادات",
            "forbidden": "census، estate-hash-gc كبوابة اعتماد، migration/gl-004 أو gl-005 للتجميل، ناقل/WAL ثانٍ، مسّ RAIOS/V9 تحت قفل A15",
        },
        "required": {
            "C0": "يقرأ اللوحة ويقرر. لا يصادق على PASS بدون مخارج أبناء.",
            "C1": "قائد ومراجع تنفيذي. يستقبل الإيصال ويحاول كسره.",
            "C2": "مستشار خارجي. يقرأ NOW.md، يترك رأياً برمز C2، لا ينفّذ حذفاً من خارج الرسم الحي.",
            "C3": "منفّذ ذري على Repair: PARENT_EXIT≠0 إذا فشل أي child مطلوب. لا يحذف health-reporter.ts.",
            "C4": "خدمة: نبض + WAL. قوانين DISCOVERED فقط. لا مرحلة جديدة.",
        },
    }
    save_now(state)
    return state


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="c", required=True)
    sub.add_parser("show")
    sub.add_parser("init")
    op = sub.add_parser("opinion")
    op.add_argument("--code", required=True)
    op.add_argument("--text", required=True)
    args = p.parse_args()
    if args.c == "init":
        print(json.dumps(bootstrap(), ensure_ascii=False, indent=2))
        return 0
    if args.c == "opinion":
        rec = opinion(args.code, args.text)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0 if rec.get("wal_status") == "WAL_COMMITTED" else 1
    if not NOW_JSON.exists():
        bootstrap()
    render(load_now())
    print(NOW_MD.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
