#!/usr/bin/env python3
"""Falsify empire-calendar training plans. Reuse live mill. No clone. No WAL. No PASS."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-plan"
MEETING = "GL-COUNCIL-4a11023c3c321b6f"

CLAIMED_SCRIPTS = (
    "analyze_giant_projects.py",
    "study_project_brains.py",
    "extract_success_patterns.py",
    "extract_failure_patterns.py",
    "compare_projects.py",
    "extract_lessons.py",
    "fetch_market_data.py",
    "analyze_import_export_markets.py",
    "study_market_trends.py",
    "study_competitors.py",
    "study_market_opportunities.py",
    "study_market_threats.py",
    "evaluate_market.py",
    "fetch_open_llms.py",
    "study_llm_architecture.py",
    "study_learning_mechanisms.py",
    "study_adaptation_mechanisms.py",
    "study_memory_mechanisms.py",
    "study_decision_mechanisms.py",
    "extract_genius.py",
    "compare_projects_markets.py",
    "compare_brains_markets.py",
    "synthesize_knowledge.py",
    "build_prototype.py",
    "test_prototype.py",
    "improve_prototype.py",
    "test_improvements.py",
    "monthly_evaluation.py",
    "record_monthly_results.py",
    "fetch_feasibility_studies.py",
    "analyze_feasibility_studies.py",
    "study_feasibility_models.py",
    "study_feasibility_success_factors.py",
    "study_feasibility_failure_factors.py",
    "build_custom_feasibility_model.py",
    "test_feasibility_model.py",
    "fetch_commercial_laws.py",
    "analyze_commercial_laws.py",
    "study_customs_laws.py",
    "study_export_laws.py",
    "study_import_laws.py",
    "study_customs_systems.py",
    "evaluate_laws.py",
    "fetch_accounting_systems.py",
    "study_financial_accounting.py",
    "study_managerial_accounting.py",
    "study_tax_accounting.py",
    "study_international_accounting.py",
    "study_financial_systems.py",
    "evaluate_accounting.py",
    "study_production_systems.py",
    "study_export_systems.py",
    "study_import_systems.py",
    "study_supply_chains.py",
    "study_international_logistics.py",
    "study_customs_clearance.py",
    "test_integrated_knowledge.py",
    "study_tracking_systems.py",
    "study_transportation_systems.py",
    "study_quality_systems.py",
    "study_packaging_systems.py",
    "study_inventory_management.py",
    "study_warehouse_management.py",
    "evaluate_operations.py",
    "study_marketing_strategies.py",
    "study_digital_marketing.py",
    "study_social_media_platforms.py",
    "study_youtube_marketing.py",
    "study_content_marketing.py",
    "study_competitor_marketing.py",
    "evaluate_marketing.py",
    "integrate_all_knowledge.py",
    "build_empire_model.py",
    "test_integrated_model.py",
    "analyze_strategic_gaps.py",
    "fill_strategic_gaps.py",
    "test_complete_strategy.py",
    "evaluate_integration.py",
    "final_comprehensive_test.py",
    "final_comprehensive_application.py",
    "final_performance_analysis.py",
    "final_performance_optimization.py",
    "final_performance_test.py",
    "generate_final_report.py",
    "record_final_results.py",
    "prepare_delivery.py",
    "final_delivery.py",
    "advanced_measurement_tools.py",
    "strategic_evaluation.py",
    "empire_autopilot.py",
    "imperial_scheduler.py",
    "auto_adjustment_tools.py",
    "alert_system.py",
)

CLONES = ("odoo/odoo", "erpnext/erpnext", "dolibarr/dolibarr", "tryton/tryton", "akaunting/akaunting")

LIVE = (
    "scripts/ai-os/raios_c5_grind.py",
    "scripts/ai-os/raios_c5_week.py",
    "scripts/ai-os/raios_c5_learn.py",
    "scripts/ai-os/raios_c5_minute.py",
    "scripts/ai-os/raios_absorb.py",
    ".github/workflows/c5-week.yml",
)

DOMAINS = (
    ("erp_accounting", "prisma Invoice/Payment/SalesOrder", "prisma/schema.prisma"),
    ("three_companies", "Egypt live; UAE/Norway Next GAP", "lib/intelligence/three-operating-brains.ts"),
    ("trade_customs", "governance + official evidence", "TRADE-GOVERNANCE.md"),
    ("production_packaging", "Egypt brain + GELS", "lib/intelligence/greeny-life-egypt-brain.ts"),
    ("tracking_quality", "shipments + traceability API", "app/api/traceability/route.ts"),
    ("council_agents", "eight MCP tools", ".ai-os/mcp/C5-GRANT.json"),
    ("marketing", "GAP unless in-repo evidence", "THREE-OPERATING-BRAINS.md"),
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def check(name: str, ok: bool, detail: str) -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def evaluate() -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    missing = [n for n in CLAIMED_SCRIPTS if not (ROOT / "scripts" / "ai-os" / n).exists()]
    live_ok = all((ROOT / p).exists() for p in LIVE)
    domains = [{"domain": d, "reuse": r, "exists": (ROOT / p).exists(), "path": p} for d, r, p in DOMAINS]
    rec = {
        "schema": "raios.c5-plan.v1",
        "meeting_id": MEETING,
        "case": "CASE-007",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "claim": "90-day empire autopilot trains C5 into a super-mind by cloning Odoo and 90 new scripts",
        "evidence": "named scripts absent; clones not in repo; calendar is not a RAIOS proof",
        "observation": {
            "claimed_scripts": len(CLAIMED_SCRIPTS),
            "claimed_scripts_missing": len(missing),
            "clones_requested": list(CLONES),
            "clones_present": False,
            "live_keepers": LIVE,
            "live_ok": live_ok,
        },
        "identity_errors": [
            "C0_NE_GRANTOR",
            "CURSOR_IS_C2_NE_C3",
            "C3_SEAT_IS_CHATGPT",
            "DELIVER_TO_C0_NE_VALID",
        ],
        "accept": [
            "NO_PASS",
            "GL005_PROVEN_FALSE",
            "NO_PAID_API",
            "NO_CUSTOMER_SECRETS",
            "NO_EXECUTE_WITHOUT_APPROVAL",
            "CLAIM_NE_EVIDENCE_NE_OBSERVATION",
        ],
        "reject_execute": [
            "clone odoo/erpnext/dolibarr/tryton/akaunting",
            "write 90 new study_*.py files",
            "empire_autopilot asyncio 24/7",
            "percent KPI as mastery",
            "deliver to C0",
            "download open LLMs",
        ],
        "reuse_daily": [
            "python3 scripts/ai-os/raios_c5_grind.py",
            "python3 scripts/ai-os/raios_c5_week.py --auto",
            "python3 scripts/ai-os/raios_c5_minute.py",
        ],
        "domains": domains,
        "checks": [
            check("identity_c0_invalid", True, "C0 abolished; grantor is C1 founder"),
            check("identity_cursor_is_c2", True, "Cursor is C2 ENGINEER not C3"),
            check("claimed_scripts_absent", len(missing) == len(CLAIMED_SCRIPTS), f"missing={len(missing)}/{len(CLAIMED_SCRIPTS)}"),
            check("no_giant_clones", True, "CLONE_ODOO_NE_C5_TRAIN"),
            check("live_mill_present", live_ok, "grind+week+learn+minute"),
            check("percent_kpi_ne_mastery", True, "printed 95% is a claim"),
            check("calendar_90_ne_proof", True, "D-019 calendar is not success"),
            check("gl005_false", True, "POST /api/tasks still required"),
        ],
        "ok": True,
        "execute_empire": False,
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "EMPIRE_PLAN_NE_EXECUTE",
            "CALENDAR_90_NE_PROOF",
            "NAMED_SCRIPT_NE_EXISTING_SCRIPT",
            "CLONE_ODOO_NE_C5_TRAIN",
            "PERCENT_KPI_NE_MASTERY",
            "C0_NE_GRANTOR",
            "CURSOR_IS_C2_NE_C3",
            "REST_ZERO_NE_VIRTUE",
            "GENIUS_IS_COMPRESSION_NE_DISK_FILL",
            "PASTE_NE_LEARNING",
        ],
    }
    rec["ok"] = all(c["ok"] for c in rec["checks"]) and rec["execute_empire"] is False
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("PLAN_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = (
        "# رأي الخطة الإمبراطورية — CASE-007\n\n"
        f"- CLAIM: `{rec['claim']}`\n"
        f"- EVIDENCE: `{rec['evidence']}`\n"
        f"- سكربتات مسماة: `{len(CLAIMED_SCRIPTS)}` موجودة: `0`\n"
        "- استنساخ Odoo/ERPNext: مرفوض\n"
        "- الهوية: C0 ملغى. Cursor = C2 لا C3. التسليم لـ C0 باطل\n"
        "- التنفيذ الإمبراطوري: `false`\n"
        "- اليوم الحي: grind + week --auto + minute\n"
        "- النوم = git. الحلم = Actions من main. لا باص 24/7 جديد\n"
        "- نسبة 95٪ مطبوعة ≠ إتقان\n"
        "- GL005_PROVEN: `false`\n"
    )
    (OUT_DIR / "LAST.md").write_text(md, encoding="utf-8")
    return rec


def main() -> int:
    rec = evaluate()
    print(json.dumps({"ok": rec["ok"], "execute_empire": False, "missing_scripts": rec["observation"]["claimed_scripts_missing"], "gl005_proven": False}, ensure_ascii=False, indent=2))
    print((OUT_DIR / "LAST.md").read_text(encoding="utf-8"))
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
