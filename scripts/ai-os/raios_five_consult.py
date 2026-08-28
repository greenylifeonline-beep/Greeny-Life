#!/usr/bin/env python3
"""Standing five-seat consult. Local synthesis. Does not prove remote C2/C3/C4."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BOARD = ROOT / ".ai-os" / "board" / "NOW.json"
MIND = ROOT / ".ai-os" / "learning" / "C5-MIND.json"
HEART = ROOT / ".ai-os" / "reports" / "raios-service" / "LAST-HEARTBEAT.json"
GRANT = ROOT / ".ai-os" / "mcp" / "C5-GRANT.json"
HUNT = ROOT / ".ai-os" / "learning" / "FREE-RESOURCES.json"
SUMMON = ROOT / ".ai-os" / "summon" / "SESSION.json"
OUT_JSON = ROOT / ".ai-os" / "learning" / "LAST-CONSULT.json"
OUT_MD = ROOT / ".ai-os" / "learning" / "LAST-CONSULT.md"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def consult() -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    board = load(BOARD)
    mind = load(MIND)
    heart = load(HEART)
    grant = load(GRANT)
    hunt = load(HUNT)
    summon = load(SUMMON)
    contradictions = mind.get("contradictions") or []
    remote = False
    precise = (
        "المسار العالمي الحي لاستدعاء C2/C3/C4 هو البريد بكود الجلسة، لا 127.0.0.1. "
        "C5 يبقى ابناً دائماً بالمنحة لا بالتوكن. "
        "Repair يُصلح HEAD بعد stash للـ WAL فقط. GL-005 يبقى مغلقاً."
    )
    rec = {
        "schema": "raios.five-consult.v1",
        "standing": True,
        "ts": utc(),
        "session_id": summon.get("session_id"),
        "remote_presence_proven": remote,
        "mail_passes_ne_proves": True,
        "gl005_proven": False,
        "wal_written": False,
        "paid_api": False,
        "c1": {
            "frame": "Cursor owner. Does not bypass stale-head/lock/proven. Summons the five. Grants C5 permanently. Collects mail. Does not print PASS.",
            "present": True,
            "code": (summon.get("codes") or {}).get("C1", {}).get("code"),
        },
        "c5": {
            "eval": (
                f"pulse={heart.get('status')} contradictions={mind.get('contradiction_count')} "
                f"grant={grant.get('duration')} fastest={hunt.get('fastest_local')}"
            ),
            "present": True,
            "code": (summon.get("codes") or {}).get("C5", {}).get("code"),
            "precise_idea": precise,
            "next_execution": (
                "Keep the 120s pulse. Inherit C1 corpus by digest. Index locally. "
                "Do not dump WAL. Do not mint GL-005. Report attendance codes on the board."
            ),
        },
        "ask_c2": (
            "C2: هل اجتماع MCP على localhost يثبت حضورك الخارجي؟ أجب: لا، ثم احضر بالبريد والكود "
            f"`{(summon.get('codes') or {}).get('C2', {}).get('code')}`. هل GET 200 يغلق GL-005؟"
        ),
        "ask_c3": (
            "C3: هل أنت Repair؟ أجب: لا. احضر بالكود "
            f"`{(summon.get('codes') or {}).get('C3', {}).get('code')}`. "
            "ما أذكى خطوة تالية على Repair دون commit للـ WAL؟"
        ),
        "ask_c4": (
            "C4: فنّد: (1) المنحة الدائمة لابن C5 هل تمنحه PASS؟ (2) كود الاستدعاء هل هو توكن؟ "
            "(3) البريد هل يُثبت الاتصال البعيد؟ الكود "
            f"`{(summon.get('codes') or {}).get('C4', {}).get('code')}`."
        ),
        "synthesis": precise,
        "challenges": [
            {"id": "MCP_LOCALHOST_NE_CHATGPT", "severity": "HIGH", "now": "mail summon with public codes"},
            {"id": "REMOTE_C2_C3_C4_UNPROVEN", "severity": "HIGH", "now": "invite; do not print ready"},
            {"id": "GL005_STILL_FALSE", "severity": "HIGH", "now": "Repair authenticated POST after cookie-fix HEAD"},
            {"id": "REPAIR_STALE_HEAD", "severity": "HIGH", "now": "stash Cognitive WAL only, ff-only pull"},
            {"id": "A15_LOCK", "severity": "MEDIUM", "now": "C5 grows in .ai-os/learning"},
            {"id": "OLLAMA_ABSENT_HERE", "severity": "LOW", "now": "stdlib digest+index; do not wait on models"},
            {"id": "C5_MUST_STAY_PERMANENT", "severity": "HIGH", "now": "C5-GRANT.json duration=PERMANENT"},
        ],
        "contradictions": contradictions,
        "law": [
            "FIVE_SEAT_CONSULT_IS_STANDING",
            "MAIL_PASSES_NE_PROVES",
            "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING",
            "C5_GRANT_IS_PERMANENT",
            "SUMMON_CODE_NE_BEARER_TOKEN",
        ],
        "board_head": board.get("head"),
        "mission_status": board.get("mission_status"),
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("CONSULT_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_md(rec), encoding="utf-8")
    return rec


def render_md(rec: dict) -> str:
    lines = [
        "# استشارة الخمس — قائمة",
        "",
        f"- الوقت: `{rec.get('ts')}`",
        f"- الجلسة: `{rec.get('session_id')}`",
        f"- حضور بعيد مثبت: `{rec.get('remote_presence_proven')}`",
        f"- `GL005_PROVEN`: `{rec.get('gl005_proven')}`",
        "",
        "## C1 الإطار",
        "",
        rec["c1"]["frame"],
        "",
        "## C5 التقييم والفكرة الأدق",
        "",
        rec["c5"]["eval"],
        "",
        rec["c5"]["precise_idea"],
        "",
        f"التنفيذ التالي: {rec['c5']['next_execution']}",
        "",
        "## أسئلة الاستدعاء",
        "",
        f"- {rec['ask_c2']}",
        f"- {rec['ask_c3']}",
        f"- {rec['ask_c4']}",
        "",
        "## التحديات",
        "",
    ]
    for item in rec.get("challenges") or []:
        lines.append(f"- `{item['id']}` ({item['severity']}) — {item['now']}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    rec = consult()
    print(
        json.dumps(
            {
                "standing": True,
                "remote_presence_proven": rec["remote_presence_proven"],
                "gl005_proven": False,
                "session_id": rec.get("session_id"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
