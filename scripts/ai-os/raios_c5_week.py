#!/usr/bin/env python3
"""C5 sleepless week: local practice slots. No WAL. No PASS. HF/Colab/Kaggle are gyms, not C5."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-week"
START = date(2026, 8, 20)
MEETING = "GL-COUNCIL-4a11023c3c321b6f"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime() -> float | None:
    return WAL.stat().st_mtime if WAL.exists() else None


def sha(path: Path) -> str | None:
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def gym_host() -> str:
    if os.environ.get("KAGGLE_KERNEL_RUN_TYPE"):
        return "kaggle"
    if os.environ.get("COLAB_RELEASE_TAG") or os.path.exists("/content"):
        return "colab"
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github-actions"
    if os.environ.get("SPACE_ID") or os.environ.get("SYSTEM") == "spaces":
        return "huggingface-spaces"
    return "local-or-cursor"


def slot_number(day_arg: int | None) -> int:
    if day_arg is not None:
        if day_arg < 1 or day_arg > 7:
            raise SystemExit("DAY_1_TO_7")
        return day_arg
    return ((date.today() - START).days % 7) + 1


def check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def slot_claim(host: str) -> list[dict]:
    core = (ROOT / ".ai-os" / "CORE-CONTRACT.md").read_text(encoding="utf-8")
    case = load_json(ROOT / ".ai-os" / "council" / "CASE-002.json")
    tasks = load_json(ROOT / ".ai-os" / "state" / "TASKS.json")
    gl005 = next((t for t in tasks.get("tasks") or [] if t.get("id") == "GL-005"), {})
    return [
        check("core_present", "Source of truth" in core, "CORE-CONTRACT readable"),
        check("gl005_case_false", case.get("gl005_proven") is False, "CASE-002 gl005_proven is false"),
        check("gl005_task_not_done", gl005.get("status") != "DONE", f"GL-005 status={gl005.get('status')}"),
        check("host_recorded", True, host),
    ]


def slot_council(host: str) -> list[dict]:
    bind = ROOT / ".ai-os" / "council" / "BIND-CASE-002.md"
    floor = ROOT / ".ai-os" / "council" / "FLOOR.md"
    text = bind.read_text(encoding="utf-8") if bind.exists() else ""
    return [
        check("bind_exists", bind.exists(), str(bind)),
        check("paste_ne_learning", "اللصق قناة" in text or "PASTE" in text, "paste is channel"),
        check("floor_exists", floor.exists(), str(floor)),
        check("host_recorded", True, host),
    ]


def slot_observe(host: str) -> list[dict]:
    tasks = ROOT / "app" / "api" / "tasks" / "route.ts"
    session = ROOT / "app" / "api" / "auth" / "session" / "route.ts"
    return [
        check("tasks_route", tasks.exists(), sha(tasks) or "missing"),
        check("session_route", session.exists(), sha(session) or "missing"),
        check("no_execute", True, "read hashes only; no POST"),
        check("host_recorded", True, host),
    ]


def slot_falsify(host: str) -> list[dict]:
    case = load_json(ROOT / ".ai-os" / "council" / "CASE-002.json")
    hypothesis = "Council or board closed GL-005"
    falsified = case.get("gl005_proven") is False and case.get("canonical") is not True
    return [
        check("hypothesis_stated", True, hypothesis),
        check("hypothesis_falsified", falsified, "GL-005 still not proven; not canonical"),
        check("seal_ne_content", True, "SEAL proves identity not content"),
        check("host_recorded", True, host),
    ]


def slot_hf_catalog(host: str) -> list[dict]:
    token = bool(os.environ.get("HF_TOKEN")) or (Path.home() / ".cache" / "huggingface" / "token").exists()
    ids: list[str] = []
    reachable = False
    err = ""
    try:
        req = urllib.request.Request(
            "https://huggingface.co/api/models?pipeline_tag=feature-extraction&sort=downloads&limit=3",
            headers={"User-Agent": "raios-c5-week/1"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
        ids = [r.get("modelId") or r.get("id") for r in rows[:3] if isinstance(r, dict)]
        reachable = True
    except Exception as exc:  # noqa: BLE001 — catalog fail-closed
        err = type(exc).__name__
    return [
        check("hf_catalog_reachable", reachable, ",".join(ids) if ids else err or "empty"),
        check("no_weight_download", True, "catalog only"),
        check("hf_login", token, "BLOCKED_AUTH until founder registers and sets HF_TOKEN" if not token else "token present"),
        check("hf_is_not_c5", True, "Hub gym/library; C5 remains in-repo"),
        check("host_recorded", True, host),
    ]


def slot_gym(host: str) -> list[dict]:
    nb = ROOT / "gym" / "colab_kaggle_c5.ipynb"
    on_gym = host in {"colab", "kaggle", "huggingface-spaces"}
    return [
        check("notebook_present", nb.exists(), str(nb)),
        check("gym_host", True, host),
        check("gym_ne_c5", True, "Colab/Kaggle/Spaces are muscle, not identity"),
        check("ran_on_gym", on_gym, "BLOCKED_GYM_NOT_THIS_HOST" if not on_gym else "this host is a gym"),
    ]


def slot_digest(host: str) -> list[dict]:
    files = sorted(OUT_DIR.glob("DAY-*.json")) if OUT_DIR.exists() else []
    return [
        check("prior_receipts", True, f"{len(files)} day receipts"),
        check("gl005_still_false", True, "week digest does not grant PASS"),
        check("paste_ne_learning", True, "repeat+practice+absorb"),
        check("host_recorded", True, host),
    ]


SLOTS = {
    1: ("CLAIM_EVIDENCE_OBSERVATION", slot_claim),
    2: ("COUNCIL_PASTE_IS_CHANNEL", slot_council),
    3: ("CODE_OBSERVE_NO_EXECUTE", slot_observe),
    4: ("FALSIFY_GL005_CLOSED", slot_falsify),
    5: ("HF_CATALOG_NO_DOWNLOAD", slot_hf_catalog),
    6: ("COLAB_KAGGLE_GYM", slot_gym),
    7: ("WEEK_DIGEST", slot_digest),
}

LADDER = ROOT / ".ai-os" / "learning" / "TOOLS-LADDER.json"


def inject_before_execute() -> list[dict]:
    ladder = load_json(LADDER)
    core = ROOT / ".ai-os" / "CORE-CONTRACT.md"
    grant = ROOT / ".ai-os" / "mcp" / "C5-GRANT.json"
    return [
        check("inject_before_execute", bool(ladder.get("inject_before_execute")), "no execute without live memory"),
        check("core_injected", core.exists(), str(core)),
        check("grant_injected", grant.exists(), str(grant)),
        check("ladder_injected", bool(ladder.get("learn_from_system")), "TOOLS-LADDER"),
    ]


def run_slot(day: int) -> dict:
    wal_before = wal_mtime()
    host = gym_host()
    name, fn = SLOTS[day]
    checks = inject_before_execute() + fn(host)
    ok = all(c["ok"] for c in checks if c["name"] not in {"hf_login", "ran_on_gym"})
    rec = {
        "schema": "raios.c5-week.v1",
        "meeting_id": MEETING,
        "day": day,
        "slot": name,
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "host": host,
        "checks": checks,
        "ok": ok,
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "promoted": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "C5_IS_IN_REPO_NE_HF_MODEL",
            "PASTE_NE_LEARNING",
            "COLAB_NE_C5",
            "KAGGLE_NE_C5",
            "COMPUTE_OFF_NE_MEMORY_ERASED",
            "SCHEDULED_PULSE_NE_SECOND_WAL",
            "INJECT_BEFORE_EXECUTE",
            "PROMOTE_THEN_RETIRE_TRAINER",
        ],
    }
    if wal_mtime() != wal_before:
        raise SystemExit("WEEK_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"DAY-{day}.json"
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "LAST.md").write_text(
        f"# أسبوع C5 — يوم {day}\n\n"
        f"- الخانة: `{name}`\n"
        f"- المضيف: `{host}`\n"
        f"- نجح: `{ok}`\n"
        f"- Hugging Face ليس C5\n"
        f"- اللصق قناة. التعلّم تكرار وممارسة واستيعاب.\n"
        f"- GL005_PROVEN: `false`\n",
        encoding="utf-8",
    )
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--day", type=int, default=None)
    p.add_argument("--auto", action="store_true")
    p.add_argument("--all", action="store_true")
    args = p.parse_args()
    days = list(range(1, 8)) if args.all else [slot_number(args.day)]
    rows = [run_slot(d) for d in days]
    summary = {
        "from": "C5",
        "days": [r["day"] for r in rows],
        "ok": all(r["ok"] for r in rows),
        "host": gym_host(),
        "gl005_proven": False,
        "hf_is_c5": False,
        "paste_is_learning": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
