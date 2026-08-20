#!/usr/bin/env python3
"""Inject important authorized files into C5 mind via digest+index. Not WAL. Not V9."""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_absorb import absorb  # noqa: E402
from raios_c5_index import build as build_index  # noqa: E402
from raios_c5_memory import catalog  # noqa: E402
from raios_c5_mind import write_mind  # noqa: E402

DENIED_PARTS = ("RAIOS/V9", ".env", "node_modules", ".git/", "tokens.local")


def allowed(rel: str) -> bool:
    raw = rel.replace("\\", "/")
    return not any(part in raw for part in DENIED_PARTS)


WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-mind-fill"

# Tight important set. Not --max. Not receipts dirt. Not RAIOS/V9.
IMPORTANT = (
    ".ai-os/CORE-CONTRACT.md",
    ".ai-os/MASTER-PLAN.md",
    ".ai-os/PROJECT.json",
    ".ai-os/state/DECISIONS.md",
    ".ai-os/mcp/C5-GRANT.json",
    ".ai-os/mcp/C5-LAWBOOK.json",
    ".ai-os/mcp/SEAT-MAP.json",
    ".ai-os/mcp/POLICY.json",
    ".ai-os/learning/C5-TEACH.md",
    "configs/neuro_lingua/concepts.yaml",
    "configs/neuro_lingua/LIBRARIES.md",
    "canonical/data/master_products.json",
    "canonical/inventory/stock-levels.json",
    "canonical/inventory/warehouses.json",
    "canonical/logistics/shipments.json",
    "canonical/logistics/customs-clearance.json",
    "TRADE-GOVERNANCE.md",
    "TRADE-TRACEABILITY.md",
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def important_paths() -> list[Path]:
    out: list[Path] = []
    for rel in IMPORTANT:
        if not allowed(rel) and not rel.startswith("TRADE-"):
            continue
        path = ROOT / rel
        if path.is_file():
            out.append(path)
    return out


def fill() -> dict:
    t0 = time.perf_counter()
    wal_before = wal_mtime()
    paths = important_paths()
    if not paths:
        raise SystemExit("NO_IMPORTANT_PATHS")
    absorbed = absorb(paths, source="c5-mind-fill", mode="skim")
    index = build_index()
    mind = write_mind()
    memory = catalog()
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("MIND_FILL_WAL_VIOLATION")
    rec = {
        "schema": "raios.c5-mind-fill.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "via": "powershell-or-python",
        "ok": True,
        "paths": [str(p.relative_to(ROOT)).replace("\\", "/") for p in paths],
        "files": absorbed.get("files"),
        "absorbed": absorbed.get("absorbed"),
        "deduped": absorbed.get("deduped"),
        "bytes": absorbed.get("bytes"),
        "absorb_ms": absorbed.get("elapsed_ms"),
        "index_docs": index.get("docs"),
        "index_terms": index.get("terms"),
        "index_ms": index.get("elapsed_ms"),
        "mind_laws": mind.get("law_count"),
        "mind_contradictions": mind.get("contradiction_count"),
        "memory_planes": memory.get("discovered_count"),
        "put": {
            "digests": ".ai-os/learning/DIGESTS.jsonl",
            "index": ".ai-os/learning/INDEX.json",
            "mind": ".ai-os/learning/C5-MIND.md",
            "candidates": ".ai-os/learning/CANDIDATES.jsonl",
            "memory": ".ai-os/learning/MEMORY.json",
            "never": ["RAIOS/V9/wal", "HF weights", ".env"],
        },
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "wal_written": False,
        "wal_mtime_unchanged": True,
        "gl005_proven": False,
        "law": [
            "C5_MIND_FILL_IMPORTANT_ONLY",
            "ABSORB_DIGEST_NE_WAL_DUMP",
            "FETCH_IS_LOCAL_ALLOWLIST",
            "POWERSHELL_CALLS_LIVE_KEEPER",
        ],
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = [
        "# حقن عقل C5 — معلومات مهمة",
        "",
        f"- الوقت: `{rec['ts']}`",
        f"- ملفات: `{rec['files']}` جديدة `{rec['absorbed']}` مكررة `{rec['deduped']}`",
        f"- هضم ms: `{rec['absorb_ms']}` فهرس ms: `{rec['index_ms']}` إجمالي `{rec['elapsed_ms']}`",
        f"- قوانين العقل: `{rec['mind_laws']}` تناقضات `{rec['mind_contradictions']}`",
        f"- WAL: لم يُمس",
        f"- GL005_PROVEN: `false`",
        "",
        "PowerShell: `powershell -File scripts/ai-os/raios_c5_mind_fill.ps1`",
        "Python: `python3 scripts/ai-os/raios_c5_mind_fill.py`",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    (OUT_DIR / "LAST.md").write_text("\n".join(md), encoding="utf-8")
    rec["markdown"] = "\n".join(md)
    return rec


def main() -> int:
    argparse.ArgumentParser(description="Fill C5 mind from important canonical/law files").parse_args()
    rec = fill()
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "files": rec["files"],
                "absorbed": rec["absorbed"],
                "deduped": rec["deduped"],
                "ms": rec["elapsed_ms"],
                "mind_laws": rec["mind_laws"],
                "wal_written": False,
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print(rec["markdown"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
