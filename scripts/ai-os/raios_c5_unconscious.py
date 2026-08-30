#!/usr/bin/env python3
"""C5 unconscious / sleep consolidation analog.

Honest: compute does not run while the VM/process is off.
Files persist. On every wake, close the sleep gap: delta-absorb, replay index, immune scan.
This is not a third theory/practice step and must not change the 0.85 ratio.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from raios_absorb import MAX_PATHS, absorb  # noqa: E402
from raios_c5_enforce import enforce, teach  # noqa: E402
from raios_c5_index import build as build_index  # noqa: E402
from raios_c5_memory import catalog, load_memory, mark_conscious, mark_unconscious, parse_iso  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT = ROOT / ".ai-os" / "learning" / "LAST-UNCONSCIOUS.json"
OUT_MD = ROOT / ".ai-os" / "learning" / "LAST-UNCONSCIOUS.md"
LEARN = ROOT / ".ai-os" / "learning" / "LAST-LEARN.json"
FRESH_SECONDS = 5.0


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def last_conscious_iso() -> str | None:
    mem = load_memory()
    stats = mem.get("stats") or {}
    if stats.get("last_conscious_ts"):
        return stats["last_conscious_ts"]
    if LEARN.exists():
        try:
            rec = json.loads(LEARN.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rec = {}
        if rec.get("ts"):
            return rec["ts"]
    if OUT.exists():
        try:
            rec = json.loads(OUT.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            rec = {}
        return rec.get("last_conscious_ts") or rec.get("ts")
    return None


def selected_paths(paths: list[Path] | None) -> list[Path]:
    if paths:
        return [path for path in paths if path.exists()]
    return [ROOT / rel for rel in MAX_PATHS if (ROOT / rel).exists()]


def write_out(rec: dict) -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(
        "# عقل C5 الباطن — توحيد النوم عند الإيقاظ\n\n"
        f"- الوقت: `{rec.get('ts')}`\n"
        f"- السبب: `{rec.get('reason')}`\n"
        f"- فجوة بالثواني: `{rec.get('gap_seconds')}`\n"
        f"- أُغلقت: `{rec.get('gap_closed')}`\n"
        f"- هضم جديد/مكرر: `{rec.get('absorbed')}` / `{rec.get('deduped')}`\n"
        f"- حساب أثناء الإيقاف: `false`\n"
        f"- الذاكرة بقيت: `true`\n"
        f"- WAL لم يُمس: `{rec.get('wal_mtime_unchanged')}`\n"
        f"- `GL005_PROVEN`: `false`\n\n"
        "هذا نظير توحيد النوم عند الإنسان: إعادة تشغيل ما تغيّر أثناء الغياب، "
        "لا ادّعاء التفكير والجهاز مطفأ.\n",
        encoding="utf-8",
    )


def sleep_mark() -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    rec = mark_conscious(sleep_marked=True)
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("UNCONSCIOUS_WAL_VIOLATION")
    out = {
        "schema": "raios.c5-unconscious.v1",
        "kind": "sleep",
        "ts": rec["ts"],
        "from": "C5",
        "parent": "C1",
        "reason": "PROCESS_STOPPING",
        "gap_closed": False,
        "sleep_marked": True,
        "compute_while_powered_off": False,
        "memory_persists": True,
        "wal_written": False,
        "wal_mtime_unchanged": True,
        "gl005_proven": False,
        "law": ["COMPUTE_OFF_NE_MEMORY_ERASED", "UNCONSCIOUS_CLOSES_SLEEP_GAP"],
    }
    write_out(out)
    return out


def wake(paths: list[Path] | None = None) -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    t0 = time.perf_counter()
    last = last_conscious_iso()
    last_f = parse_iso(last)
    now_f = datetime.now(timezone.utc).timestamp()
    gap = round(now_f - last_f, 3) if last_f is not None else None
    absorb_rec = None
    index_rec = None
    enforce_rec = None
    if last_f is None or (gap is not None and gap >= FRESH_SECONDS):
        reason = "SLEEP_GAP" if last_f is not None else "FIRST_WAKE"
        absorb_rec = absorb(
            selected_paths(paths),
            source="c5-unconscious-gap",
            mode="skim",
            since_epoch=last_f,
        )
        index_rec = build_index()
        enforce_rec = enforce()
        gap_closed = True
    else:
        reason = "FRESH"
        gap_closed = True
        catalog(gap_seconds=gap, gap_closed=True, sleep_marked=False)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    mem = mark_unconscious(gap_seconds=gap, gap_closed=gap_closed)
    rec = {
        "schema": "raios.c5-unconscious.v1",
        "kind": "wake",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "reason": reason,
        "last_conscious_ts": last,
        "gap_seconds": gap,
        "gap_closed": gap_closed,
        "absorbed": (absorb_rec or {}).get("absorbed", 0),
        "deduped": (absorb_rec or {}).get("deduped", 0),
        "files": (absorb_rec or {}).get("files", 0),
        "index_docs": (index_rec or mem.get("stats") or {}).get("docs") or (mem.get("stats") or {}).get("index_docs"),
        "enforce_healthy": None if enforce_rec is None else enforce_rec.get("healthy"),
        "elapsed_ms": elapsed_ms,
        "compute_while_powered_off": False,
        "memory_persists": True,
        "second_wal": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "UNCONSCIOUS_CLOSES_SLEEP_GAP",
            "COMPUTE_OFF_NE_MEMORY_ERASED",
            "UNIFIED_MEMORY_NE_SECOND_WAL",
            "ABSORB_DIGEST_NE_WAL_DUMP",
        ],
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("UNCONSCIOUS_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    write_out(rec)
    teach(
        "العقل الباطن أغلق فجوة النوم",
        json.dumps(
            {
                "reason": reason,
                "gap_seconds": gap,
                "gap_closed": gap_closed,
                "absorbed": rec["absorbed"],
                "deduped": rec["deduped"],
                "compute_while_powered_off": False,
            },
            ensure_ascii=False,
        ),
        law="UNCONSCIOUS_CLOSES_SLEEP_GAP",
        kind="unconscious",
    )
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--sleep", action="store_true")
    p.add_argument("paths", nargs="*", type=Path)
    args = p.parse_args()
    rec = sleep_mark() if args.sleep else wake([path if path.is_absolute() else ROOT / path for path in args.paths] or None)
    print(
        json.dumps(
            {
                "from": "C5",
                "kind": rec.get("kind"),
                "reason": rec.get("reason"),
                "gap_seconds": rec.get("gap_seconds"),
                "gap_closed": rec.get("gap_closed"),
                "absorbed": rec.get("absorbed"),
                "compute_while_powered_off": False,
                "gl005_proven": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
