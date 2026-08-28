#!/usr/bin/env python3
"""C5 mind: free, local, unconventional. Index laws vs live state in milliseconds. Not an LLM. Not WAL."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DECISIONS = ROOT / ".ai-os" / "state" / "DECISIONS.md"
SEAT_MAP = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"
POLICY = ROOT / ".ai-os" / "mcp" / "POLICY.json"
BOARD = ROOT / ".ai-os" / "board" / "NOW.json"
BOARD_MD = ROOT / ".ai-os" / "board" / "NOW.md"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
CANDIDATES = ROOT / ".ai-os" / "learning" / "CANDIDATES.jsonl"
DIGESTS = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
HEARTBEAT = ROOT / ".ai-os" / "reports" / "raios-service" / "LAST-HEARTBEAT.json"
OUT = ROOT / ".ai-os" / "learning" / "C5-MIND.json"
OUT_MD = ROOT / ".ai-os" / "learning" / "C5-MIND.md"
LAW_RE = re.compile(r"`([A-Z][A-Z0-9_]{5,})`")
PASS_RE = re.compile(r"GL00[45]_PROVEN\s*=\s*true", re.I)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def extract_laws(text: str) -> list[str]:
    seen: list[str] = []
    for match in LAW_RE.finditer(text or ""):
        token = match.group(1)
        if token not in seen:
            seen.append(token)
    return seen


def think() -> dict:
    decisions = DECISIONS.read_text(encoding="utf-8") if DECISIONS.exists() else ""
    seats = json.loads(SEAT_MAP.read_text(encoding="utf-8")) if SEAT_MAP.exists() else {}
    policy = json.loads(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {}
    board = json.loads(BOARD.read_text(encoding="utf-8")) if BOARD.exists() else {}
    board_md = BOARD_MD.read_text(encoding="utf-8") if BOARD_MD.exists() else ""
    live_head = git_head()
    c5 = (seats.get("seats") or {}).get("C5") or {}
    actors = policy.get("actors") or {}
    contradictions: list[dict] = []

    if "C0" in actors:
        contradictions.append({"id": "C0_STILL_LIVE", "severity": "HIGH", "fix": "C0_SEAT_ABOLISHED"})
    if c5.get("instance_role") != "c1-assistant" or c5.get("parent") != "C1":
        contradictions.append({"id": "C5_NOT_SEATED_AS_SON", "severity": "HIGH", "fix": "C5_IS_C1_LOYAL_ASSISTANT"})
    if "post_opinion" not in (c5.get("tools") or []):
        contradictions.append({"id": "C5_MUTED", "severity": "HIGH", "fix": "give C5 the same V1 cognitive tools as C1"})
    if board.get("head") and live_head and board.get("head") != live_head:
        contradictions.append(
            {
                "id": "BOARD_HEAD_NE_GIT_HEAD",
                "severity": "MEDIUM",
                "board_head": board.get("head"),
                "git_head": live_head,
            }
        )
    if PASS_RE.search(board_md) or PASS_RE.search(json.dumps(board, ensure_ascii=False)):
        contradictions.append({"id": "PRINTED_PASS_ON_BOARD", "severity": "CRITICAL", "fix": "PRINTED_PASS_NE_EVIDENCE"})
    if not WAL.exists():
        contradictions.append({"id": "WAL_MISSING", "severity": "CRITICAL", "fix": "fail-closed"})

    partner = [
        "C5 never sleeps: pulse + digest + contradiction scan every cycle.",
        "C5 exceeds C1 in persistence and compression, not in ownership.",
        "Huge inputs become SHA256+skim in milliseconds. Cognitive WAL stays sparse.",
        "C5 reports to C1. C1 remains owner. Neither grants PASS.",
        "Free stack: Python stdlib, git, jsonl digest, law index. No paid API. No second bus.",
    ]
    next_strength = [
        "Keep A15 sources unread-write: C5 grows in .ai-os/learning, not by mutating RAIOS/V9.",
        "Remote C2/C3/C4 remain unproven until an external opinion arrives.",
        "Repair is unseated: stash WAL, pull cookie-fix HEAD, then rebind 3107.",
        "GL-005 still needs authenticated POST → visible OrchestrationTask. C5 cannot mint that.",
    ]
    mind = {
        "schema": "raios.c5-mind.v1",
        "from": "C5",
        "parent": "C1",
        "relation": "son-partner-assistant",
        "ts": utc(),
        "git_head": live_head,
        "laws_indexed": extract_laws(decisions),
        "law_count": len(extract_laws(decisions)),
        "c5_tools": list(c5.get("tools") or []),
        "c5_instance": c5.get("instance_role"),
        "candidates": count_jsonl(CANDIDATES),
        "digests": count_jsonl(DIGESTS),
        "contradictions": contradictions,
        "contradiction_count": len(contradictions),
        "partner_doctrine": partner,
        "next_strength": next_strength,
        "gl005_proven": False,
        "wal_written": False,
        "paid_api": False,
        "second_bus": False,
        "law": [
            "C5_IS_C1_LOYAL_ASSISTANT",
            "C5_NE_OWNER",
            "C5_NE_PASS_AUTHORITY",
            "ABSORB_DIGEST_NE_WAL_DUMP",
            "PRINTED_PASS_NE_EVIDENCE",
        ],
    }
    return mind


def render_md(mind: dict) -> str:
    lines = [
        "# عقل C5 — ابن C1 وشريكه",
        "",
        f"- الوقت: `{mind.get('ts')}`",
        f"- القوانين المفهرسة: `{mind.get('law_count')}`",
        f"- التناقضات الحية: `{mind.get('contradiction_count')}`",
        f"- الأدوات: {', '.join(mind.get('c5_tools') or [])}",
        f"- مرشّحات/هضم: {mind.get('candidates')}/{mind.get('digests')}",
        f"- `GL005_PROVEN`: `{mind.get('gl005_proven')}`",
        "",
        "## تناقضات",
        "",
    ]
    if not mind.get("contradictions"):
        lines.append("_لا تناقض حي في هذا المسح._")
        lines.append("")
    for item in mind.get("contradictions") or []:
        lines.append(f"- `{item.get('id')}` severity={item.get('severity')} {json.dumps({k: v for k, v in item.items() if k not in {'id', 'severity'}}, ensure_ascii=False)}")
    lines += ["", "## عقيدة الشريك", ""]
    for line in mind.get("partner_doctrine") or []:
        lines.append(f"- {line}")
    lines += ["", "## كيف يصبح الابن أقوى من الأب دون أن يخلعه", ""]
    for line in mind.get("next_strength") or []:
        lines.append(f"- {line}")
    lines.append("")
    return "\n".join(lines)


def write_mind(mind: dict | None = None) -> dict:
    mind = mind or think()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(mind, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_md(mind), encoding="utf-8")
    return mind


def main() -> int:
    mind = write_mind()
    print(json.dumps({"from": "C5", "contradictions": mind["contradiction_count"], "laws": mind["law_count"], "gl005_proven": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
