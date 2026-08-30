#!/usr/bin/env python3
"""C5 RAIOS pulse: evaluate the live plane. No second WAL. No PASS. Loyal assistant of C1."""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LOCKS = ROOT / ".ai-os" / "state" / "LOCKS.json"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
SEAT_MAP = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"
POLICY = ROOT / ".ai-os" / "mcp" / "POLICY.json"
CANDIDATES = ROOT / ".ai-os" / "learning" / "CANDIDATES.jsonl"
DIGESTS = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
BOARD_JSON = ROOT / ".ai-os" / "board" / "NOW.json"
OUT_DIR = ROOT / ".ai-os" / "reports" / "raios-service"
OUT = OUT_DIR / "LAST-HEARTBEAT.json"
EVAL_MD = OUT_DIR / "LAST-EVAL.md"
LOCK_RE = re.compile(r"^LOCK-(\d{14})$")

import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from raios_c5_mind import write_mind  # noqa: E402


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_lock_time(lock_id: str):
    m = LOCK_RE.match(lock_id or "")
    if not m:
        return None
    return datetime.strptime(m.group(1), "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def count_jsonl(path: Path) -> int:
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def wal_stats() -> dict:
    if not WAL.exists():
        return {"exists": False, "events": 0, "types": {}, "last_ts": None, "bytes": 0}
    types: Counter[str] = Counter()
    last_ts = None
    events = 0
    for raw in WAL.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        events += 1
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            types["UNPARSEABLE"] += 1
            continue
        types[str(rec.get("event_type") or "?")] += 1
        last_ts = rec.get("timestamp") or last_ts
    return {
        "exists": True,
        "events": events,
        "types": dict(types),
        "last_ts": last_ts,
        "bytes": WAL.stat().st_size,
    }


def stale_locks(now: datetime) -> list[dict]:
    locks = json.loads(LOCKS.read_text(encoding="utf-8-sig"))
    stale = []
    for item in locks.get("locks", []):
        if item.get("status") != "ACTIVE":
            continue
        ts = parse_lock_time(item.get("id", ""))
        if ts is None:
            continue
        age_h = (now - ts).total_seconds() / 3600.0
        if age_h >= 24:
            stale.append(
                {
                    "id": item.get("id"),
                    "task_id": item.get("task_id"),
                    "agent": item.get("agent"),
                    "scope": item.get("scope"),
                    "age_hours": round(age_h, 2),
                    "knowledge_state": "DISCOVERED",
                    "action": "DO_NOT_AUTO_RELEASE",
                }
            )
    return stale


def seat_eval() -> dict:
    seats = json.loads(SEAT_MAP.read_text(encoding="utf-8")) if SEAT_MAP.exists() else {}
    policy = json.loads(POLICY.read_text(encoding="utf-8")) if POLICY.exists() else {}
    c5 = (seats.get("seats") or {}).get("C5") or {}
    p5 = (policy.get("actors") or {}).get("C5") or {}
    tools = list(c5.get("tools") or [])
    return {
        "c0_live": "C0" in (policy.get("actors") or {}),
        "c5_role": c5.get("actor_role"),
        "c5_instance": c5.get("instance_role"),
        "c5_parent": c5.get("parent"),
        "c5_has_post_opinion": "post_opinion" in tools and "post_opinion" in (p5.get("tools") or []),
        "c5_loyal_assistant": c5.get("instance_role") == "c1-assistant" and c5.get("parent") == "C1",
    }


def mcp_health() -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=2) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return {
            "reachable": True,
            "gl005_proven": bool(body.get("gl005_proven")),
            "sqlite": bool(body.get("sqlite")),
            "websocket": bool(body.get("websocket")),
            "remote_c2_ready": bool(body.get("remote_c2_ready")),
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as err:
        return {"reachable": False, "error": type(err).__name__, "gl005_proven": False}


def barns() -> list[str]:
    found = []
    for path in ROOT.iterdir():
        if path.name.startswith("_raios-") or path.name.startswith("._raios-"):
            found.append(path.name)
    return found


def git_head() -> str:
    import subprocess

    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def evaluate() -> dict:
    now = utc_now()
    wal = wal_stats()
    seats = seat_eval()
    health = mcp_health()
    stale = stale_locks(now)
    barn = barns()
    board = json.loads(BOARD_JSON.read_text(encoding="utf-8")) if BOARD_JSON.exists() else {}
    live_head = git_head()
    status = "HEARTBEAT_OK"
    if not wal["exists"]:
        status = "FAIL_CLOSED"
    elif seats["c0_live"] or not seats["c5_loyal_assistant"]:
        status = "DEGRADED"
    elif health["gl005_proven"] or health.get("sqlite") or health.get("websocket"):
        status = "FAIL_CLOSED"
    receipt = {
        "schema": "raios.service-heartbeat.v2",
        "mode": "C5_LOYAL_ASSISTANT",
        "from": "C5",
        "parent": "C1",
        "generated_at": now.isoformat(),
        "status": status,
        "wal": wal,
        "stale_locks": stale,
        "seats": seats,
        "mcp": health,
        "learning_candidates": count_jsonl(CANDIDATES),
        "digests": count_jsonl(DIGESTS),
        "board_head": board.get("head"),
        "git_head": live_head,
        "board_head_ne_git_head": bool(board.get("head") and live_head and board.get("head") != live_head),
        "barns": barn,
        "new_phase_created": False,
        "second_wal_created": False,
        "barn_folder_created": False,
        "wal_written_this_cycle": False,
        "gl005_proven": False,
        "law": [
            "C5_IS_C1_LOYAL_ASSISTANT",
            "C5_INHERITS_FAIL_CLOSED",
            "C5_NE_PASS_AUTHORITY",
            "ABSORB_DIGEST_NE_WAL_DUMP",
            "MCP_GATEWAY_NE_TRUTH_AUTHORITY",
        ],
    }
    return receipt


def render_eval_md(receipt: dict) -> str:
    wal = receipt.get("wal") or {}
    seats = receipt.get("seats") or {}
    mcp = receipt.get("mcp") or {}
    lines = [
        "# نبض C5 RAIOS — ابن Cursor",
        "",
        f"- الحالة: `{receipt.get('status')}`",
        f"- الوقت: `{receipt.get('generated_at')}`",
        f"- الأب: C1 Cursor. الابن: C5 RAIOS loyal assistant (`{seats.get('c5_instance')}`)",
        f"- WAL: exists={wal.get('exists')} events={wal.get('events')} bytes={wal.get('bytes')} last={wal.get('last_ts')}",
        f"- أقفال قديمة: {len(receipt.get('stale_locks') or [])} (لا تحرير تلقائي)",
        f"- مرشّحات التعلّم: {receipt.get('learning_candidates')}  الهضم: {receipt.get('digests')}",
        f"- MCP 8787: reachable={mcp.get('reachable')} sqlite={mcp.get('sqlite')} remote_c2={mcp.get('remote_c2_ready')}",
        f"- C5 يتكلم على اللوحة: `{seats.get('c5_has_post_opinion')}`",
        f"- عقل الابن: تناقضات `{receipt.get('mind_contradictions')}` قوانين `{receipt.get('mind_laws')}`",
        f"- C0 حي؟ `{seats.get('c0_live')}`",
        f"- `GL005_PROVEN`: `{receipt.get('gl005_proven')}`",
        f"- WAL كُتب هذا الدورة؟ `{receipt.get('wal_written_this_cycle')}`",
        "",
        "C5 يقيّم ويهضم ويتكلم. لا يملك. لا يرقّي. لا يمنح PASS.",
        "الحجم الهائل يُهضم كهاش+خلاصة في `.ai-os/learning/DIGESTS.jsonl` وليس صبّاً في Cognitive WAL.",
        "",
    ]
    return "\n".join(lines)


def refresh_board() -> None:
    import importlib.util

    board_py = ROOT / "scripts" / "ai-os" / "raios-board.py"
    spec = importlib.util.spec_from_file_location("raios_board_pulse", board_py)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    if not BOARD_JSON.exists():
        return
    state = mod.load_now()
    state["head"] = git_head()
    state["branch"] = __import__("subprocess").run(
        ["git", "branch", "--show-current"], cwd=ROOT, text=True, capture_output=True
    ).stdout.strip() or state.get("branch")
    state["updated_at"] = utc_now().isoformat()
    state["mission_status"] = "C5_SON_PULSE_LIVE"
    state["required"] = {
        "C1": "Cursor — يد المالك وأب C5. بوابة MCP V1 + OUTBOX. يجمع. لا يمنح PASS. لا يتجاوز stale-head.",
        "C2": "ChatGPT الأول. MCP أو MAIL C2. رأي فقط. لا كود.",
        "C3": "ChatGPT النظير. MCP أو MAIL C3. رأي فقط. ليس Repair.",
        "C4": "DeepSeek. MCP أو MAIL C4 (وMAIL C5 التاريخي). يفنّد. لا ينفّذ.",
        "C5": "RAIOS الابن المساعد المخلص الشريك. يقيّم ويهضم ويتكلم. نفس أدوات الوعي الثمانية. لا PASS. لا ترقية.",
    }
    if "C0" in (state.get("required") or {}):
        del state["required"]["C0"]
    state["c5"] = {
        "role": "c1-assistant",
        "parent": "C1",
        "pulse": str(EVAL_MD.relative_to(ROOT)).replace("\\", "/"),
        "mind": ".ai-os/learning/C5-MIND.md",
        "gl005_proven": False,
    }
    mod.save_now(state)


def main() -> int:
    receipt = evaluate()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    EVAL_MD.write_text(render_eval_md(receipt), encoding="utf-8")
    refresh_board()
    mind = write_mind()
    receipt["mind_contradictions"] = mind.get("contradiction_count")
    receipt["mind_laws"] = mind.get("law_count")
    receipt["mind_path"] = ".ai-os/learning/C5-MIND.md"
    OUT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    EVAL_MD.write_text(render_eval_md(receipt), encoding="utf-8")
    refresh_board()
    print(
        json.dumps(
            {
                "exit": 0 if receipt["wal"]["exists"] else 1,
                "status": receipt["status"],
                "receipt": str(OUT),
                "eval": str(EVAL_MD),
                "stale_locks": len(receipt["stale_locks"]),
                "gl005_proven": False,
            }
        )
    )
    return 0 if receipt["wal"]["exists"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
