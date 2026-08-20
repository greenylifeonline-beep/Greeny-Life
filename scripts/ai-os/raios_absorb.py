#!/usr/bin/env python3
"""C5 digest plane: absorb huge inputs in moments. Hash + skim. Never dump into Cognitive WAL."""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from raios_c5_read import read_file, skip_path  # noqa: E402
from raios_learn_ingest import ingest  # noqa: E402
DIGESTS = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
CYCLE_PATHS = (
    ".ai-os/board/NOW.md",
    ".ai-os/board/NOW.json",
    ".ai-os/state/DECISIONS.md",
    ".ai-os/state/LOCKS.json",
    ".ai-os/mcp/SEAT-MAP.json",
    ".ai-os/mcp/POLICY.json",
    ".ai-os/mcp/C5-GRANT.json",
    ".ai-os/receipts",
    ".ai-os/mail/OUTBOX.md",
    ".ai-os/reports/raios-service/LAST-HEARTBEAT.json",
)
INHERIT_PATHS = (
    ".ai-os/handoffs",
    ".ai-os/receipts",
    ".ai-os/state/DECISIONS.md",
    ".ai-os/COMMAND-VISION.md",
    ".ai-os/CORE-CONTRACT.md",
    ".ai-os/MASTER-PLAN.md",
    ".ai-os/board",
    ".ai-os/mail",
    ".ai-os/experience/pending-validation",
    ".ai-os/mcp",
    ".ai-os/summon",
    ".ai-os/learning/C1-GIT-MEMORY.md",
    ".ai-os/training/README.md",
    ".ai-os/MODEL-REGISTRY.json",
    ".ai-os/LOCAL-AI-PRIVACY.md",
)
MAX_PATHS = (
    ".ai-os",
    "scripts/ai-os",
    ".github/ISSUE_TEMPLATE",
    "lib",
    "app/api/auth",
)


def utc() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def load_seen() -> set[str]:
    seen: set[str] = set()
    if not DIGESTS.exists():
        return seen
    for raw in DIGESTS.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if rec.get("sha256"):
            seen.add(rec["sha256"])
    return seen


def append_digest(rec: dict) -> None:
    DIGESTS.parent.mkdir(parents=True, exist_ok=True)
    with DIGESTS.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def relpath(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path)


def iter_files(root: Path) -> list[Path]:
    if root.is_file():
        return [root]
    if not root.is_dir():
        return []
    out: list[Path] = []
    for path in root.rglob("*"):
        if path.is_file() and not skip_path(path):
            out.append(path)
    return out


def digest_file(path: Path, seen: set[str], *, mode: str = "skim") -> dict:
    rec = read_file(path, mode=mode)
    digest = rec.get("sha256")
    if digest in seen:
        return {
            "schema": "raios.absorb-digest.v1",
            "path": rec.get("path"),
            "kind": rec.get("kind"),
            "sha256": digest,
            "bytes": rec.get("bytes"),
            "status": "DEDUPED",
            "wal_written": False,
            "gl005_proven": False,
        }
    rec["schema"] = "raios.absorb-digest.v1"
    rec["knowledge_state"] = "DISCOVERED"
    rec["law"] = "ABSORB_DIGEST_NE_WAL_DUMP"
    append_digest(rec)
    seen.add(str(digest))
    return rec


def absorb(paths: list[Path], *, source: str, mode: str = "skim") -> dict:
    t0 = time.perf_counter()
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    seen = load_seen()
    results = []
    for raw in paths:
        for file_path in iter_files(raw):
            results.append(digest_file(file_path, seen, mode=mode))
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    absorbed = [r for r in results if r.get("status") == "ABSORBED"]
    dupes = [r for r in results if r.get("status") == "DEDUPED"]
    total_bytes = sum(int(r.get("bytes") or 0) for r in results)
    summary = (
        f"C5 absorbed {len(absorbed)} new / {len(dupes)} dupes / {len(results)} files / "
        f"{total_bytes} bytes in {elapsed_ms} ms. Digest plane only. WAL untouched. GL005 stays false."
    )
    learned = ingest(
        summary,
        source,
        [r.get("sha256") for r in absorbed[:20] if r.get("sha256")],
    )
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after or learned.get("wal_written"):
        raise SystemExit("ABSORB_WAL_VIOLATION")
    return {
        "schema": "raios.absorb-cycle.v1",
        "from": "C5",
        "parent": "C1",
        "files": len(results),
        "absorbed": len(absorbed),
        "deduped": len(dupes),
        "bytes": total_bytes,
        "elapsed_ms": elapsed_ms,
        "learning_candidate": learned["id"],
        "wal_mtime_unchanged": True,
        "wal_written": False,
        "gl005_proven": False,
        "mode": mode,
        "law": "ABSORB_DIGEST_NE_WAL_DUMP",
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("paths", nargs="*", type=Path)
    p.add_argument("--cycle", action="store_true")
    p.add_argument("--inherit", action="store_true")
    p.add_argument("--max", action="store_true")
    p.add_argument("--deep", action="store_true")
    p.add_argument("--source", default="c5-absorb")
    args = p.parse_args()
    selected: list[Path] = []
    if args.cycle:
        selected.extend(ROOT / rel for rel in CYCLE_PATHS)
    if args.inherit:
        selected.extend(ROOT / rel for rel in INHERIT_PATHS)
    if args.max:
        selected.extend(ROOT / rel for rel in MAX_PATHS)
    selected.extend(path if path.is_absolute() else ROOT / path for path in args.paths)
    selected = [path for path in selected if path.exists()]
    if not selected:
        raise SystemExit("NO_ABSORB_PATHS")
    rec = absorb(selected, source=args.source, mode="deep" if args.deep else "skim")
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
