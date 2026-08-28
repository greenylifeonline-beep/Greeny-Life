#!/usr/bin/env python3
"""Assimilate an authorized output into C5 practice tiles. No C-seat summon. No WAL. No Cortex."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from raios.neuro_lingua.kae import HTTP_DEMO, assimilate, tournament  # noqa: E402
from raios.neuro_lingua.kae_libraries import assimilate_path, assimilate_query, locate  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-kae"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def run(*, text: str, source_kind: str, external_calls: int) -> dict:
    wal_before = wal_mtime()
    rec = assimilate(text, source_kind=source_kind, external_calls=external_calls)
    rec["ts"] = utc()
    rec["from"] = "C5"
    rec["parent"] = "C1"
    tour = tournament(
        [
            {"source": "authorized-c3-artifact", "text": "HTTP 200 means the write succeeded."},
            {"source": "c5-live-law", "text": "HTTP_2XX_NE_SEMANTIC_SUCCESS PRINTED_SUCCESS_NE_OBSERVED_STATE_CHANGE"},
        ]
    )
    rec["tournament"] = tour
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("KAE_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    metrics = rec.get("metrics") or {}
    tiles = rec.get("tiles") or {}
    lines = [
        "# KAE — إعادة توريق لا محرك ثانٍ",
        "",
        f"- الوقت: `{rec['ts']}`",
        f"- نجح: `{rec.get('ok')}`",
        f"- بلاطات: `{len(tiles)}`",
        f"- Knowledge Yield: `{metrics.get('knowledge_yield')}` (tiles / max(calls,1))",
        f"- Assimilation Efficiency: `{metrics.get('assimilation_efficiency')}`",
        f"- استدعاء خارجي: `{metrics.get('external_calls')}` saved=`{metrics.get('call_saved')}`",
        f"- استشارة مقاعد: `{rec.get('consult_used')}`",
        f"- القشرة: معزولة، غير مستخدمة",
        f"- GL005_PROVEN: `false`",
        "",
        "| بلاطة | نص |",
        "|---|---|",
    ]
    for key, value in tiles.items():
        lines.append(f"| `{key}` | {(value or '').replace('|', '/')} |")
    lines += [
        "",
        f"Tournament conflict: `{bool((tour.get('conflict') or []))}` summoned=`{tour.get('summoned')}`",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    (OUT_DIR / "LAST.md").write_text("\n".join(lines), encoding="utf-8")
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--text", default=None)
    p.add_argument("--source", default="authorized_text")
    p.add_argument("--calls", type=int, default=0)
    p.add_argument("--demo", action="store_true")
    p.add_argument("--libraries", action="store_true")
    p.add_argument("--from-path", dest="from_path", default=None)
    p.add_argument("--query", default=None)
    args = p.parse_args()
    if args.libraries:
        rec = locate()
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "LIBRARIES.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        lines = [
            "# مكتبات C5",
            "",
            f"- يعرف أين هي: `{rec.get('knows_where')}`",
            f"- معروفة موجودة: `{rec.get('known_count')}`",
            f"- ناقصة: `{rec.get('missing')}`",
            "",
            "| id | مسار | دور | موجود | يجلب |",
            "|---|---|---|---|---|",
        ]
        for row in rec.get("libraries") or []:
            lines.append(
                f"| `{row['id']}` | `{row['path']}` | `{row['role']}` | `{row['exists']}` | `{row.get('fetchable')}` |"
            )
        lines += [
            "",
            "الوضع: `.ai-os/learning/CANDIDATES.jsonl` + `.ai-os/receipts/c5-kae/`",
            "الجلب: قراءة محلية مسموحة. لا ويب. لا مقاعد C.",
            "",
            "`GL005_PROVEN=false`",
            "",
        ]
        (OUT_DIR / "LIBRARIES.md").write_text("\n".join(lines), encoding="utf-8")
        print(json.dumps({"ok": rec["ok"], "known_count": rec["known_count"], "missing": rec["missing"], "put": rec["put"], "how": rec["how"], "gl005_proven": False}, ensure_ascii=False, indent=2))
        print((OUT_DIR / "LIBRARIES.md").read_text(encoding="utf-8"))
        return 0
    if args.from_path:
        rec = assimilate_path(args.from_path, ingest=True)
        rec["ts"] = utc()
        rec["from"] = "C5"
        rec["parent"] = "C1"
        rec["tournament"] = {"consult_used": False, "summoned": False}
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": rec.get("ok"), "path": (rec.get("fetched") or rec).get("path"), "tiles": list((rec.get("tiles") or {}).keys()), "put": ".ai-os/learning/CANDIDATES.jsonl", "gl005_proven": False}, ensure_ascii=False, indent=2))
        return 0 if rec.get("ok") else 2
    if args.query:
        rec = assimilate_query(args.query, ingest=True)
        rec["ts"] = utc()
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": rec.get("ok"), "find": rec.get("find"), "tiles": list((rec.get("tiles") or {}).keys()), "gl005_proven": False}, ensure_ascii=False, indent=2))
        return 0 if rec.get("ok") else 2
    text = HTTP_DEMO if args.demo or not args.text else args.text
    rec = run(text=text, source_kind=args.source, external_calls=args.calls)
    print(
        json.dumps(
            {
                "ok": rec.get("ok"),
                "tiles": list((rec.get("tiles") or {}).keys()),
                "knowledge_yield": (rec.get("metrics") or {}).get("knowledge_yield"),
                "assimilation_efficiency": (rec.get("metrics") or {}).get("assimilation_efficiency"),
                "consult_used": rec.get("consult_used"),
                "cortex_used": rec.get("cortex_used"),
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print((OUT_DIR / "LAST.md").read_text(encoding="utf-8"))
    return 0 if rec.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
