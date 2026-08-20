#!/usr/bin/env python3
"""Shared RAIOS channel. Surface: .ai-os/channel/LIVE.md. Authority: Cognitive WAL. Not a second bus."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHAN = ROOT / ".ai-os" / "channel"
LIVE = CHAN / "LIVE.md"
LOG = CHAN / "messages.jsonl"
ACTORS = ("USER", "COMMANDER", "POWERSHELL", "RAIOS")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def emit_wal(actor: str, text: str, msg_id: str) -> dict:
    runtime = ROOT / "RAIOS" / "V9" / "runtime"
    if str(runtime) not in sys.path:
        sys.path.insert(0, str(runtime))
    import cognitive_event_bus as bus  # type: ignore

    out = bus.emit(
        event_type="LEARNING",
        actor=actor.lower(),
        intent="CHANNEL_MESSAGE",
        tool="raios-channel",
        success=True,
        confidence=1.0,
        metadata={
            "channel": "ai-os/channel",
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
        "wal_file": str(getattr(bus, "WAL_FILE", "")),
    }


def render(records: list[dict]) -> None:
    CHAN.mkdir(parents=True, exist_ok=True)
    lines = [
        "# قناة RAIOS الحية",
        "",
        "هذه غرفة التواصل المشتركة. تكتب هنا كما تكتب لي.",
        "",
        "| الطرف | كيف يكتب |",
        "|---|---|",
        "| أنت | قل لي في الشات، أو: `python3 scripts/ai-os/raios-channel.py post --from USER --text \"...\"` |",
        "| القائد (Cursor) | نفس الأمر `--from COMMANDER` |",
        "| مساعد PowerShell | `python3 scripts/ai-os/raios-channel.py post --from POWERSHELL --text \"GC_EXIT=...\"` |",
        "| RAIOS | نبض الخدمة + رسائل `--from RAIOS` |",
        "",
        "السلطة: Cognitive WAL. ليست ناقلاً ثانياً. الحالة DISCOVERED حتى الاعتماد.",
        "",
        "## الرسائل",
        "",
    ]
    for rec in records[-80:]:
        lines.append(f"### {rec.get('ts')} — {rec.get('from')}")
        lines.append("")
        lines.append(str(rec.get("text") or "").strip() or "_(empty)_")
        lines.append("")
        if rec.get("event_id"):
            lines.append(f"`event_id={rec['event_id']}` `wal={rec.get('wal_status')}`")
            lines.append("")
    LIVE.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load() -> list[dict]:
    if not LOG.exists():
        return []
    rows = []
    for raw in LOG.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def post(actor: str, text: str) -> dict:
    actor = actor.upper()
    if actor not in ACTORS:
        raise SystemExit(f"UNKNOWN_ACTOR:{actor}")
    text = text.strip()
    if not text:
        raise SystemExit("EMPTY_TEXT")
    msg_id = str(uuid.uuid4())
    wal = emit_wal(actor, text, msg_id)
    rec = {
        "schema": "raios.channel-message.v1",
        "id": msg_id,
        "ts": utc(),
        "from": actor,
        "text": text,
        "knowledge_state": "DISCOVERED",
        **wal,
    }
    CHAN.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    rows = load()
    render(rows)
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="c", required=True)
    post_p = sub.add_parser("post")
    post_p.add_argument("--from", dest="actor", required=True)
    post_p.add_argument("--text", required=True)
    sub.add_parser("show")
    args = p.parse_args()
    if args.c == "post":
        rec = post(args.actor, args.text)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0 if rec.get("wal_status") == "WAL_COMMITTED" else 1
    rows = load()
    render(rows)
    print(LIVE.read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
