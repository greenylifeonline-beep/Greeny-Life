#!/usr/bin/env python3
"""The Goal / TOC on live canonical logistics. No simulated minutes. No WAL. No PASS."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from raios.neuro_lingua.toc import hunt  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-toc"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def render_md(rec: dict) -> str:
    ident = rec["steps"]["identify"]
    wip = rec["wip"]
    lines = [
        "# الهدف — قيد حي من السجل المعتمد",
        "",
        f"- الوقت: `{rec['ts']}`",
        f"- محاكاة: `{rec['simulated']}`",
        f"- القيد: `{ident['constraint']}`",
        f"- أكبر WIP شحن: `{ident['physical_wip_leader']}`",
        f"- أصل أوروبا: `{rec['europe_origin_count']}`",
        f"- مخزن خليجي: `{rec['gulf_warehouse_count']}`",
        f"- حقول زمن: `{rec['duration_fields']}`",
        f"- GL005_PROVEN: `false`",
        "",
        "## WIP",
        "",
        f"- IN_TRANSIT `{wip['in_transit']}`",
        f"- AT_PORT `{wip['at_port']}`",
        f"- CUSTOMS_CLEARANCE `{wip['customs_shipment_status']}`",
        f"- uncleared ledger `{wip['clearance_uncleared']}` (pending `{wip['clearance_pending']}` submitted `{wip['clearance_submitted']}`)",
        f"- PACKED `{wip['packed']}` DELIVERED `{wip['delivered']}`",
        f"- status_desync `{wip['status_desync']}`",
        "",
        "## اللصق المخترع",
        "",
    ]
    for row in rec["paste_claims"]:
        lines.append(f"- `{row['verdict']}` — {row['claim']}")
    lines += [
        "",
        "## الخطوات الخمس",
        "",
        f"1. IDENTIFY `{ident['constraint']}` — {ident['why']}",
        "2. EXPLOIT المطحنة الحية. لا تحسّن مطبوع 15%.",
        "3. SUBORDINATE لا تملأ مسارات Next للإمارات/النرويج هنا.",
        "4. ELEVATE `ELEVATE_REQUIRES_C1` — لا 5000 دولار من منفّذ.",
        "5. REPEAT القيد قد ينتقل. لا PASS.",
        "",
        "`python3 scripts/ai-os/raios_c5_toc.py`",
        "`powershell -File scripts/ai-os/raios_c5_toc.ps1`",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    return "\n".join(lines)


def run() -> dict:
    wal_before = wal_mtime()
    rec = hunt()
    rec["ts"] = utc()
    rec["from"] = "C5"
    rec["parent"] = "C1"
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("TOC_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = render_md(rec)
    (OUT_DIR / "LAST.md").write_text(md, encoding="utf-8")
    rec["markdown"] = md
    return rec


def main() -> int:
    argparse.ArgumentParser(description="TOC on canonical shipments/customs/stock").parse_args()
    rec = run()
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "simulated": rec["simulated"],
                "constraint": rec["steps"]["identify"]["constraint"],
                "physical_wip_leader": rec["steps"]["identify"]["physical_wip_leader"],
                "europe_origin_count": rec["europe_origin_count"],
                "gulf_warehouse_count": rec["gulf_warehouse_count"],
                "clearance_uncleared": rec["wip"]["clearance_uncleared"],
                "in_transit": rec["wip"]["in_transit"],
                "elevate": rec["steps"]["elevate"]["reason"],
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
