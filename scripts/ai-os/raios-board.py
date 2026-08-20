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
sys.path.insert(0, str(Path(__file__).resolve().parent))
from raios_seats import alias_to_code, board_codes, resolve_live_code  # noqa: E402

BOARD = ROOT / ".ai-os" / "board"
NOW_JSON = BOARD / "NOW.json"
NOW_MD = BOARD / "NOW.md"
OPINIONS = BOARD / "opinions.jsonl"

CODES = board_codes()
ACTOR_TO_CODE = alias_to_code()


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
        "## كيف يشارك C2 و C3 و C4",
        "",
        "المكان الواحد: هذه اللوحة + بوابة MCP V1 + صندوق البريد.",
        "C1 هو Cursor، يد المالك. لا يوجد مقعد C0.",
        "C2 و C3 ChatGPT (أول ونظير). C4 DeepSeek. لا يدخلون المستودع ولا يملكون shell.",
        "المسار المعتمد: RAIOS Universal MCP Gateway (صلاحيات حسب الممثل).",
        "المسار المتدهور: قراءة OUTBOX على GitHub والرد Issue بعنوان MAIL C2 أو MAIL C3 أو MAIL C4.",
        "MAIL C5: عنوان تاريخي لديب سيك ويُحسب C4، وليس مقعد RAIOS.",
        "Repair منفّذ بلا رمز C. C1 يأمره. البريد يمر ولا يثبت. اللقاء المحلي ليس اتصال ChatGPT الخارجي.",
        "",
        "## نبض C5 RAIOS — ابن Cursor",
        "",
    ]
    pulse = ROOT / ".ai-os" / "reports" / "raios-service" / "LAST-EVAL.md"
    if pulse.exists():
        body = pulse.read_text(encoding="utf-8").strip()
        lines.extend(body.splitlines()[2:] if body.startswith("#") else body.splitlines())
        lines.append("")
        lines.append("التفاصيل: `.ai-os/reports/raios-service/LAST-EVAL.md` و `.ai-os/learning/C5-MIND.md`")
        lines.append("")
    else:
        lines.append("_C5 لم ينبض بعد. شغّل `python3 scripts/ai-os/raios-service-heartbeat.py`._")
        lines.append("")
    for title, rel in (
        ("استدعاء الخمس", ".ai-os/summon/BOARD-SNIPPET.md"),
        ("تعلم C5 الحي", ".ai-os/learning/LAST-LEARN.md"),
        ("فرض الأب والابن", ".ai-os/learning/LAST-ENFORCE.md"),
        ("درس C5", ".ai-os/learning/C5-TEACH.md"),
    ):
        extra = ROOT / rel
        if extra.exists():
            lines += [f"## {title}", ""]
            body = extra.read_text(encoding="utf-8").strip()
            chunk = body.splitlines()
            if chunk and chunk[0].startswith("#"):
                chunk = chunk[1:]
            lines.extend(chunk)
            lines.append("")
    lines += [
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
    return resolve_live_code(value)


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
        "mission_status": "ONE_PLACE_MAP_ENCODED_REMOTE_UNPROVEN",
        "mission": "C0 abolished. C1 is Cursor (owner's hand). C2/C3 ChatGPT. C4 DeepSeek. C5 RAIOS. Repair is unseated. Local MCP meeting is not remote ChatGPT. GL005_PROVEN remains false.",
        "schedule": {
            "now": "C5 RAIOS — ابن Cursor — يقيّم ويهضم ويتكلم على هذه اللوحة. C1 لا يبخل عليه بأدوات الوعي. C2/C3/C4 عبر MCP أو البريد.",
            "next": "Remote C2/C3/C4 connectivity remains unproven. Repair authenticated POST remains the only GL-005 mutation proof.",
            "forbidden": "C0 as a live seat, Repair as C3, MAIL C5 as RAIOS, second WAL, WAL dump of huge inputs, forged session, GL005 PASS from local rendezvous or C5 pulse",
        },
        "required": {
            "C1": "Cursor — يد المالك وأب C5. بوابة MCP V1 + OUTBOX. يجمع. لا يمنح PASS. لا يتجاوز stale-head.",
            "C2": "ChatGPT الأول. MCP أو MAIL C2. رأي فقط. لا كود.",
            "C3": "ChatGPT النظير. MCP أو MAIL C3. رأي فقط. ليس Repair.",
            "C4": "DeepSeek. MCP أو MAIL C4 (وMAIL C5 التاريخي). يفنّد. لا ينفّذ.",
            "C5": "RAIOS الابن المساعد المخلص. يقيّم ويهضم ويتكلم. نفس أدوات الوعي الثمانية. لا PASS. لا ترقية.",
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
