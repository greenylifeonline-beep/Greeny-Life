#!/usr/bin/env python3
"""Score live proof as experience. Never promote. Never WAL. Experience ≠ knowledge."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from raios.neuro_lingua.experience import bind_from_proof  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
PROOF = ROOT / ".ai-os" / "receipts" / "c5-proof" / "LAST.json"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-experience"
FAIL_DIR = ROOT / ".ai-os" / "receipts" / "c5-failure"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def main() -> int:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    proof = json.loads(PROOF.read_text(encoding="utf-8")) if PROOF.exists() else {}
    rec = bind_from_proof(proof)
    rec["ts"] = utc()
    rec["from"] = "C5"
    rec["parent"] = "C1"
    rec["consult_used"] = False
    rec["source_proof"] = str(PROOF.relative_to(ROOT)) if PROOF.exists() else None
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("EXPERIENCE_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = [
        "# تجربة C5 — ليست معرفة",
        "",
        f"- Ck: `{rec['Ck']}`",
        f"- الدرجة: `{rec['rung']}`",
        f"- أُعيد إنتاجها: `{rec['reproduced']}`",
        f"- معرفة: `{rec['knowledge']}`",
        f"- ترقية: `{rec['promoted']}`",
        f"- المسار: `{rec['path']['path']}` — `{rec['path']['reason']}`",
        f"- GL005_PROVEN: `false`",
        "",
        "تجربة ≠ معرفة. Knowledge = Validated(Repeated(Evidence)).",
        "مرة واحدة ناجحة ليست دليل قدرة.",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    (OUT_DIR / "LAST.md").write_text("\n".join(md), encoding="utf-8")
    if rec.get("failure_receipt"):
        FAIL_DIR.mkdir(parents=True, exist_ok=True)
        fail = dict(rec["failure_receipt"])
        fail["ts"] = rec["ts"]
        fail["Ck"] = rec["Ck"]
        fail["rung"] = rec["rung"]
        fail["gl005_proven"] = False
        (FAIL_DIR / "LAST.json").write_text(json.dumps(fail, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"Ck": rec["Ck"], "rung": rec["rung"], "promoted": False, "knowledge": False, "gl005_proven": False}, ensure_ascii=False, indent=2))
    print((OUT_DIR / "LAST.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
