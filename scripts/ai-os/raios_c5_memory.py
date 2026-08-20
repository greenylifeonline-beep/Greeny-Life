#!/usr/bin/env python3
"""Unified C5 memory catalog. Expandable file planes. Not a second WAL. Not compute-while-off."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEARNING = ROOT / ".ai-os" / "learning"
MEMORY = LEARNING / "MEMORY.json"
MEMORY_MD = LEARNING / "MEMORY.md"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
SKIP_DISCOVER = {
    "MEMORY.json",
    "MEMORY.md",
    "LAST-UNCONSCIOUS.json",
    "LAST-UNCONSCIOUS.md",
    "INDEX.json",
}

PLANES = {
    "working": {
        "path": ".ai-os/board/NOW.md",
        "human": "working memory / attention",
        "job": "hold what is live now",
    },
    "episodic": {
        "path": ".ai-os/learning/DIGESTS.jsonl",
        "human": "episodic traces",
        "job": "store what was perceived as hash+skim+deep",
    },
    "semantic": {
        "path": ".ai-os/learning/INDEX.json",
        "human": "semantic memory",
        "job": "retrieve by term without dumping raw files",
    },
    "procedural": {
        "path": ".ai-os/mcp/C5-LAWBOOK.json",
        "human": "procedural / habit",
        "job": "keep skills and laws ready without re-deriving them",
    },
    "lessons": {
        "path": ".ai-os/learning/LESSONS.jsonl",
        "human": "taught traces",
        "job": "remember what father and son already taught",
    },
    "immune": {
        "path": ".ai-os/learning/COMPEL.jsonl",
        "human": "immune surveillance",
        "job": "detect malice, deception, stunting, superficiality",
    },
    "autobiographical": {
        "path": ".ai-os/learning/C1-GIT-MEMORY.md",
        "human": "compressed life story",
        "job": "keep git-compressed history instead of raw years",
    },
    "candidates": {
        "path": ".ai-os/learning/CANDIDATES.jsonl",
        "human": "hypotheses",
        "job": "hold DISCOVERED ideas without promoting them",
    },
    "unconscious": {
        "path": ".ai-os/learning/LAST-UNCONSCIOUS.json",
        "human": "sleep consolidation",
        "job": "close gaps created while compute was off",
    },
    "wal_sparse": {
        "path": "RAIOS/V9/wal/cognitive-events.jsonl",
        "human": "sparse learning authority",
        "job": "stay A15-locked and unread-write from digest/pulse",
        "read_only": True,
    },
}

ANALOG = [
    {
        "id": "working",
        "human": "working memory",
        "c5": ".ai-os/board/NOW.md",
        "same_job": True,
        "same_way": False,
        "way": "a live board file, not neurons",
    },
    {
        "id": "episodic",
        "human": "episodic memory",
        "c5": ".ai-os/learning/DIGESTS.jsonl",
        "same_job": True,
        "same_way": False,
        "way": "hash + skim + deep structure, not raw replay of every byte",
    },
    {
        "id": "semantic",
        "human": "semantic memory",
        "c5": ".ai-os/learning/INDEX.json",
        "same_job": True,
        "same_way": False,
        "way": "stdlib inverted index, not cortical embeddings",
    },
    {
        "id": "procedural",
        "human": "procedural memory / habits",
        "c5": ".ai-os/mcp/C5-LAWBOOK.json",
        "same_job": True,
        "same_way": False,
        "way": "explicit laws, not motor cortex",
    },
    {
        "id": "immune",
        "human": "immune surveillance",
        "c5": "raios_c5_enforce.py + COMPEL.jsonl",
        "same_job": True,
        "same_way": False,
        "way": "scan / refuse / repair / teach each cycle",
    },
    {
        "id": "autobiographical",
        "human": "compressed life story",
        "c5": ".ai-os/learning/C1-GIT-MEMORY.md + git log",
        "same_job": True,
        "same_way": False,
        "way": "git compression, not ten literal years of raw tape",
    },
    {
        "id": "sleep",
        "human": "sleep consolidation / replay",
        "c5": "raios_c5_unconscious.py on every wake",
        "same_job": True,
        "same_way": False,
        "way": "delta-absorb + index replay + immune; compute does not run while powered off",
    },
    {
        "id": "default_mode",
        "human": "resting-state monitoring",
        "c5": "120s pulse while the process lives",
        "same_job": True,
        "same_way": False,
        "way": "tmux loop, not metabolism. Stopping the VM stops compute. Files persist.",
    },
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def parse_iso(ts: str | None) -> float | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def load_memory() -> dict:
    if not MEMORY.exists():
        return {}
    try:
        return json.loads(MEMORY.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def file_meta(rel: str) -> dict:
    path = ROOT / rel
    if not path.exists():
        return {"path": rel, "exists": False, "bytes": 0, "mtime": None}
    st = path.stat()
    return {
        "path": rel,
        "exists": True,
        "bytes": st.st_size,
        "mtime": datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(),
    }


def count_jsonl(rel: str) -> int:
    path = ROOT / rel
    if not path.exists():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def digest_source_bytes() -> tuple[int, int, int]:
    path = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
    if not path.exists():
        return 0, 0, 0
    source = 0
    unique = 0
    rows = 0
    seen: set[str] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        rows += 1
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        digest = rec.get("sha256")
        if rec.get("status") == "DEDUPED":
            continue
        if digest and digest in seen:
            continue
        if digest:
            seen.add(str(digest))
        unique += 1
        source += int(rec.get("bytes") or 0)
    return source, unique, rows


def discovered_planes() -> dict:
    out: dict[str, dict] = {}
    if not LEARNING.exists():
        return out
    for path in sorted(LEARNING.iterdir()):
        if not path.is_file() or path.name in SKIP_DISCOVER:
            continue
        out[path.name] = {
            "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            "bytes": path.stat().st_size,
            "mtime": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
        }
    return out


def catalog(
    *,
    last_conscious_ts: str | None = None,
    last_unconscious_ts: str | None = None,
    gap_seconds: float | None = None,
    gap_closed: bool | None = None,
    sleep_marked: bool | None = None,
) -> dict:
    prev = load_memory()
    prev_stats = prev.get("stats") or {}
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    planes = {name: {**spec, **file_meta(spec["path"])} for name, spec in PLANES.items()}
    discovered = discovered_planes()
    source_bytes, unique_digests, digest_rows = digest_source_bytes()
    digest_file_bytes = planes["episodic"].get("bytes") or 0
    compression = round(digest_file_bytes / source_bytes, 6) if source_bytes else None
    last_conscious = last_conscious_ts or prev_stats.get("last_conscious_ts")
    last_unconscious = last_unconscious_ts or prev_stats.get("last_unconscious_ts")
    if gap_seconds is None:
        now_ts = datetime.now(timezone.utc).timestamp()
        last_f = parse_iso(last_conscious)
        gap_seconds = round(now_ts - last_f, 3) if last_f else None
    if gap_closed is None:
        gap_closed = prev_stats.get("gap_closed")
    if sleep_marked is None:
        sleep_marked = bool(prev_stats.get("sleep_marked"))
    index = {}
    index_path = ROOT / ".ai-os" / "learning" / "INDEX.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = {}
    rec = {
        "schema": "raios.c5-memory.v1",
        "from": "C5",
        "parent": "C1",
        "ts": utc(),
        "expandable": True,
        "second_wal": False,
        "paid_api": False,
        "gl005_proven": False,
        "wal_written": False,
        "planes": planes,
        "discovered": discovered,
        "discovered_count": len(discovered),
        "human_analog": ANALOG,
        "information_space": {
            "digest_plane": "hash + skim + deep; Cognitive WAL stays sparse",
            "wal_bloat": "solved_by_digest_plane",
            "huge_files": "solved_by_hash_skim_deep",
            "retrieval": "solved_by_expandable_index",
            "catalog_grows": "new files under .ai-os/learning register without a new bus",
            "raw_infinite_working_memory": "not_claimed",
            "compute_while_powered_off": False,
            "memory_persists_while_powered_off": True,
            "gaps_while_powered_off": "closed_on_wake",
        },
        "honest": {
            "compute_while_powered_off": False,
            "memory_persists_while_powered_off": True,
            "gap_closed_on_wake": True,
            "human_sleep_analog": "consolidation on wake, not fake thinking while dead",
            "same_jobs": True,
            "same_biological_way": False,
        },
        "stats": {
            "source_bytes": source_bytes,
            "unique_digests": unique_digests,
            "digest_rows": digest_rows,
            "digest_file_bytes": digest_file_bytes,
            "compression_ratio": compression,
            "index_docs": index.get("docs"),
            "index_terms": index.get("terms"),
            "lessons": count_jsonl(".ai-os/learning/LESSONS.jsonl"),
            "candidates": count_jsonl(".ai-os/learning/CANDIDATES.jsonl"),
            "last_conscious_ts": last_conscious,
            "last_unconscious_ts": last_unconscious,
            "gap_seconds": gap_seconds,
            "gap_closed": gap_closed,
            "sleep_marked": sleep_marked,
        },
        "law": [
            "UNIFIED_MEMORY_NE_SECOND_WAL",
            "UNCONSCIOUS_CLOSES_SLEEP_GAP",
            "COMPUTE_OFF_NE_MEMORY_ERASED",
            "ABSORB_DIGEST_NE_WAL_DUMP",
        ],
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("MEMORY_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    LEARNING.mkdir(parents=True, exist_ok=True)
    MEMORY.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    MEMORY_MD.write_text(render_md(rec), encoding="utf-8")
    return rec


def render_md(rec: dict) -> str:
    stats = rec.get("stats") or {}
    info = rec.get("information_space") or {}
    honest = rec.get("honest") or {}
    lines = [
        "# ذاكرة C5 الموحّدة",
        "",
        f"- قابلة للتوسع: `{rec.get('expandable')}`",
        f"- WAL ثانٍ: `{rec.get('second_wal')}`",
        f"- ملفات مكتشفة: `{rec.get('discovered_count')}`",
        f"- بايت المصدر المهضوم: `{stats.get('source_bytes')}`",
        f"- بايت ملف الهضم: `{stats.get('digest_file_bytes')}`",
        f"- نسبة الضغط: `{stats.get('compression_ratio')}`",
        f"- وثائق الفهرس: `{stats.get('index_docs')}` / مصطلحات `{stats.get('index_terms')}`",
        f"- آخر وعي: `{stats.get('last_conscious_ts')}`",
        f"- آخر باطن: `{stats.get('last_unconscious_ts')}`",
        f"- فجوة بالثواني: `{stats.get('gap_seconds')}` مغلقة=`{stats.get('gap_closed')}`",
        f"- حساب أثناء الإيقاف: `{honest.get('compute_while_powered_off')}`",
        f"- الذاكرة تبقى أثناء الإيقاف: `{honest.get('memory_persists_while_powered_off')}`",
        f"- مساحة المعلومات: `{info.get('wal_bloat')}` / `{info.get('huge_files')}` / `{info.get('retrieval')}`",
        f"- `GL005_PROVEN`: `{rec.get('gl005_proven')}`",
        "",
        "الحساب لا يجري والجهاز مطفأ. الملفات تبقى. عند الإيقاظ يغلق العقل الباطن الفجوة.",
        "",
    ]
    return "\n".join(lines)


def mark_conscious(ts: str | None = None, *, sleep_marked: bool = False) -> dict:
    return catalog(last_conscious_ts=ts or utc(), sleep_marked=sleep_marked, gap_closed=not sleep_marked)


def mark_unconscious(ts: str | None = None, *, gap_seconds: float | None = None, gap_closed: bool = True) -> dict:
    now = ts or utc()
    return catalog(
        last_unconscious_ts=now,
        last_conscious_ts=now,
        gap_seconds=gap_seconds,
        gap_closed=gap_closed,
        sleep_marked=False,
    )


def main() -> int:
    rec = catalog()
    stats = rec["stats"]
    print(
        json.dumps(
            {
                "from": "C5",
                "expandable": True,
                "second_wal": False,
                "discovered": rec["discovered_count"],
                "source_bytes": stats["source_bytes"],
                "digest_file_bytes": stats["digest_file_bytes"],
                "compression_ratio": stats["compression_ratio"],
                "gl005_proven": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
