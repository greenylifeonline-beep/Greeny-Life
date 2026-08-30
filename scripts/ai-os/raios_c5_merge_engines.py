#!/usr/bin/env python3
"""Inventory merge engines and their copies. Discover, do not merge.

Fail-closed. No WAL write. No brain.py execution. No archive merge plan run.
Not a new kernel. Not GL-005.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"
OUT = ROOT / ".ai-os" / "receipts" / "c5-merge-engines"
ARTIFACTS = (
    "RAIOS-MERGE-ENGINES-INVENTORY.json",
    "RAIOS-MERGE-ENGINES-INVENTORY.md",
)
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".next",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
}
LAWS = [
    "MERGE_ENGINE_INVENTORY_NE_MERGE_EXECUTION",
    "FILE_NAMED_ENGINE_NE_LIVE_ENGINE",
    "ARCHIVE_COPY_NE_RUNTIME",
    "SECOND_WAL_FORBIDDEN",
    "DESTRUCTIVE_MERGE_FORBIDDEN",
    "BRAIN_PY_BROAD_MERGE_DO_NOT_RUN",
    "REUSE_BEFORE_BUILD",
    "SCALE_BY_COMPRESSION_NOT_COMPLEXITY",
    "CI_PASS_NE_GL005",
    "HOLD_NE_THROW",
]

# Live and named merge/consolidation engines. Copies are attached at stamp time.
CATALOG = (
    {
        "id": "mind-fill",
        "name_ar": "حقن العقل",
        "name_en": "C5 mind-fill",
        "path": "scripts/ai-os/raios_c5_mind_fill.py",
        "plane": "live_keeper",
        "merges": "ملفات مصرّح بها → DIGESTS ثم INDEX",
        "benefit_ar": "C5 يقرأ العقد والقرارات والمنتجات بلا WAL وبلا LangChain. هذا دمج معرفة بالضغط لا بالتراكم.",
        "run": "python3 scripts/ai-os/raios_c5_mind_fill.py",
        "status": "LIVE",
        "execute_here": True,
    },
    {
        "id": "absorb",
        "name_ar": "الامتصاص",
        "name_en": "digest absorb",
        "path": "scripts/ai-os/raios_absorb.py",
        "plane": "live_keeper",
        "merges": "ملفات كبيرة → تجزئة +skim في DIGESTS.jsonl",
        "benefit_ar": "يدمج المدخلات الضخمة في لحظات. لا يُفرَّغ في Cognitive WAL.",
        "run": "python3 scripts/ai-os/raios_absorb.py",
        "status": "LIVE",
        "execute_here": True,
    },
    {
        "id": "index",
        "name_ar": "الفهرس المقلوب",
        "name_en": "C5 inverted index",
        "path": "scripts/ai-os/raios_c5_index.py",
        "plane": "live_keeper",
        "merges": "DIGESTS → INDEX.json postings",
        "benefit_ar": "استرجاع محلي أسرع من embeddings غير محمّلة. إصابة الفهرس ليست إجابة معرفية كاملة.",
        "run": "python3 scripts/ai-os/raios_c5_index.py",
        "status": "LIVE",
        "execute_here": True,
    },
    {
        "id": "kae",
        "name_ar": "محرك توريق المعرفة",
        "name_en": "Knowledge Assimilation Engine",
        "path": "src/raios/neuro_lingua/kae.py",
        "plane": "neuro_lingua",
        "merges": "خرج مصرّح → بلاطات FACT/RULE/WHY/PROCEDURE ثم CANDIDATES DISCOVERED",
        "benefit_ar": "يعيد استخدام المعنى. ليس LightRAG وليس WAL ثانيًا وليس استخراج استدلال خفي.",
        "run": "python3 scripts/ai-os/raios_c5_kae.py",
        "status": "LIVE",
        "execute_here": True,
    },
    {
        "id": "book",
        "name_ar": "دورة الكتاب",
        "name_en": "C5 book cycle",
        "path": "scripts/ai-os/raios_c5_book.py",
        "plane": "live_keeper",
        "merges": "حرّاس حيّة → EXPERIENCE.json",
        "benefit_ar": "يجمع تجربة التشغيل. التجربة ليست معرفة. لا يغلق GL-005.",
        "run": "python3 scripts/ai-os/raios_c5_book.py",
        "status": "LIVE",
        "execute_here": True,
    },
    {
        "id": "neurolingua-speak",
        "name_ar": "NeuroLingua كلام العملاء",
        "name_en": "NeuroLingua speak",
        "path": "src/raios/neuro_lingua",
        "plane": "neuro_lingua",
        "merges": "ar-EG / ar-GULF / en / nb-NO كلام كتالوج حتمي",
        "benefit_ar": "دمج لغات العملاء بدون استدعاء LLM (llm_calls=0). ليس دمج أوزان.",
        "run": "python3 scripts/ai-os/raios_c5_train.py",
        "status": "LIVE",
        "execute_here": True,
    },
    {
        "id": "nl-wal-adapter",
        "name_ar": "محوّل WAL لـ NeuroLingua",
        "name_en": "ExistingCognitiveWALWriter",
        "path": "src/raios/neuro_lingua/wal.py",
        "plane": "neuro_lingua",
        "merges": "بروتوكول NL فوق cognitive_event_bus",
        "benefit_ar": "يمنع WAL ثانيًا. الدمج هنا محوّل لا حافلة جديدة. هذه الشريحة لا تكتب WAL (قفل A15).",
        "run": None,
        "status": "ADAPTER",
        "execute_here": False,
        "merge_target": "RAIOS/V9/runtime/cognitive_event_bus.py",
    },
    {
        "id": "cognitive-wal",
        "name_ar": "حافلة الأحداث المعرفية",
        "name_en": "cognitive event bus / Cognitive WAL",
        "path": "RAIOS/V9/runtime/cognitive_event_bus.py",
        "plane": "raios_v9",
        "merges": "أحداث تعلّم بـ fsync وevent_hash وإعادة تشغيل",
        "benefit_ar": "سلطة التعلّم الوحيدة. لا تُنقل ولا تُكتب من هذه الشريحة (A15). ليست شاشة C5.",
        "run": None,
        "status": "PRIMARY_LOCKED_A15",
        "execute_here": False,
    },
    {
        "id": "semantic-engine",
        "name_ar": "المحرك الدلالي V9",
        "name_en": "V9 semantic engine",
        "path": "RAIOS/V9/cognition/semantic/semantic_engine.py",
        "plane": "raios_v9",
        "merges": "ثقة [0,1] ومسارات داخل المستودع — ليس دمج ملفات مكررة",
        "benefit_ar": "قيد إبستيمي. لا تشغّله كمدمج أصول. لا تكتب V9 من هذه الشريحة.",
        "run": None,
        "status": "REFERENCE_LOCKED_A15",
        "execute_here": False,
    },
    {
        "id": "workflow-engine",
        "name_ar": "محرك سير الطلب",
        "name_en": "EOSWorkflowEngine",
        "path": "canonical/lib/workflowEngine.ts",
        "plane": "canonical",
        "merges": "حالة طلب بيع + موافقة بشرية متميزة",
        "benefit_ar": "دمج تشغيلي للطلب لا للمعرفة. يحتاج Prisma حيًا. ليس GL-005.",
        "run": None,
        "status": "CANONICAL_GATED",
        "execute_here": False,
    },
    {
        "id": "audit-engine",
        "name_ar": "محرك تدقيق المنتجات",
        "name_en": "canonical audit-engine",
        "path": "canonical/intelligence/intelligence/engines/audit-engine.ts",
        "plane": "canonical",
        "merges": "مصادر منتج → نتائج تكرار/حقول ناقصة",
        "benefit_ar": "يكشف التعارض قبل الدمج. لا يحذف. استخدمه قراءة قبل أي consolidation.",
        "run": None,
        "status": "CANONICAL_OFFLINE",
        "execute_here": False,
    },
    {
        "id": "data-integrity-engine",
        "name_ar": "محرك سلامة البيانات",
        "name_en": "data-integrity-engine",
        "path": "canonical/intelligence/intelligence/engines/data-integrity-engine.ts",
        "plane": "canonical",
        "merges": "ملفات canonical مقابل تكرار المعرّف/الـ slug",
        "benefit_ar": "يمنع دمجًا يفسد master_products. ليس حذفًا تلقائيًا.",
        "run": None,
        "status": "CANONICAL_OFFLINE",
        "execute_here": False,
    },
    {
        "id": "controlled-runtime",
        "name_ar": "المنسّق المحكوم",
        "name_en": "ControlledRuntimeOrchestrator",
        "path": "canonical/intelligence/runtime/controlled-runtime-orchestrator.ts",
        "plane": "canonical",
        "merges": "طلب → حوكمة GL-DOS → تنفيذ محكوم",
        "benefit_ar": "حدود تنفيذ المنتج. لا تخلطه بدمج الأرشيف. إثباته المنفصل ما زال مطلوبًا.",
        "run": None,
        "status": "CANONICAL_GATED",
        "execute_here": False,
    },
    {
        "id": "task-orchestration",
        "name_ar": "عقد المهام",
        "name_en": "task-orchestration",
        "path": "lib/intelligence/task-orchestration.ts",
        "plane": "product",
        "merges": "عقد مراجعة execution:false",
        "benefit_ar": "مسار GL-005 الحيّ عندما يوجد POST /api/tasks مصادق. الوحدة وحدها لا تثبت GL-005.",
        "run": None,
        "status": "PRODUCT_UNPROVEN",
        "execute_here": False,
    },
    {
        "id": "engine-registry",
        "name_ar": "سجل المحركات الحي",
        "name_en": "ENGINE_REGISTRY",
        "path": "canonical/intelligence/intelligence/core/engine-registry.ts",
        "plane": "canonical",
        "merges": "قائمة الحرّاس الحيّة فقط — النسخ التاريخية ليست قدرات",
        "benefit_ar": "مصدر أسماء المحركات المعتمدة في الكود الكنسي. لا تضف أرشيف JSON كقدرة.",
        "run": None,
        "status": "LIVE_INDEX",
        "execute_here": False,
    },
    {
        "id": "a13-dedup",
        "name_ar": "Dedup قدرات الوكلاء A13",
        "name_en": "A13 agent capability dedup",
        "path": "RAIOS/V9/runtime/a13_agent_capability_dedup_certification.py",
        "plane": "raios_v9",
        "merges": "لا شيء تلقائيًا — automatic_merge=false",
        "benefit_ar": "يفصل التكرار دون دمج هدّام. لا تشغّل دمج أصول الوكلاء.",
        "run": None,
        "status": "CERTIFY_NO_AUTO_MERGE",
        "execute_here": False,
    },
    {
        "id": "brain-discover-merge",
        "name_ar": "دامج ذكاء brain.py",
        "name_en": "brain.py discover_and_merge_intelligence",
        "path": "brain.py",
        "plane": "legacy",
        "merges": "يمسح intelligence/ وقد ينفّذ أدوات --analyze ويكتب tools_manifest.json",
        "benefit_ar": "لا تشغّله. استخرج أفكار التصنيف فقط عبر محوّل محكوم. أوضاع البناء/التنظيف/التطور محظورة.",
        "run": None,
        "status": "DO_NOT_RUN",
        "execute_here": False,
    },
    {
        "id": "e3-ledger",
        "name_ar": "دفتر قرارات E3",
        "name_en": "E3 engine decision ledger",
        "path": "E3-ENGINE-DECISION-LEDGER.md",
        "plane": "e3_recon",
        "merges": "112 مرشحًا مصنّفًا قراءة فقط",
        "benefit_ar": "خريطة KEEP/RECONNECT/DO_NOT_RUN. ليست دليل تشغيل. 45 عنصرًا placeholder.",
        "run": None,
        "status": "DISCOVERED_LEDGER",
        "execute_here": False,
    },
    {
        "id": "knowledge-merge-analysis",
        "name_ar": "تحليل دمج المعرفة phase-22",
        "name_en": "legacy knowledge-merge-analysis",
        "path": "archive/old_folders/unified-intelligence/reports/architecture/phase-22/knowledge-merge-analysis-20260726-180626.json",
        "plane": "archive",
        "merges": "34152 أثرًا على مسارات Windows — تضخيم جرد",
        "benefit_ar": "لا تنفّذ خطته. لا تعامل عدد الملفات كذكاء. اضغط الحيّ بدل إعادة المسح.",
        "run": None,
        "status": "ARCHIVE_INFLATED",
        "execute_here": False,
    },
    {
        "id": "domain-merge-plan",
        "name_ar": "خطة دمج النطاقات EOS",
        "name_en": "domain-merge-plan-v1",
        "path": "archive/old_folders/GREENY-LIFE-EOS/governance/domain-merge-plan-v1.json",
        "plane": "archive",
        "merges": "نطاقات EOS — الملف يلوّث بمسارات venv/torch",
        "benefit_ar": "فاسد كسلطة نطاق. لا تدمجه. المصدر الحي للمنتجات canonical/data.",
        "run": None,
        "status": "ARCHIVE_POLLUTED",
        "execute_here": False,
    },
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump_text(path: Path, text: str) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def plane_of(rel: str) -> str:
    rel = rel.replace("\\", "/")
    if rel.startswith("archive/"):
        return "archive"
    if rel.startswith("RAIOS/"):
        return "raios_v9"
    if rel.startswith("canonical/"):
        return "canonical"
    if rel.startswith("scripts/ai-os"):
        return "live_keeper"
    if rel.startswith("src/raios"):
        return "neuro_lingua"
    if rel.startswith("E3-") or rel.startswith("E3_"):
        return "e3_recon"
    if rel.startswith("reports/"):
        return "reports"
    if rel.startswith(".ai-os/"):
        return "ai_os"
    if rel.startswith("lib/"):
        return "product"
    return "other"


def interesting(name: str) -> bool:
    low = name.lower()
    return ("merge" in low) or ("engine" in low and low.endswith((".py", ".ts", ".js", ".json", ".md")))


def scan_copies() -> dict:
    rows: list[dict] = []
    counts: dict[str, int] = {}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".venv")]
        rel_dir = os.path.relpath(dirpath, ROOT)
        if rel_dir.replace("\\", "/").startswith("archive/old_folders/GREENY-LIFE-EOS-PRODUCTION") and len(rows) > 400:
            # still count, skip extra file rows for this noisy forest
            pass
        for name in filenames:
            if not interesting(name):
                continue
            full = Path(dirpath) / name
            rel = str(full.relative_to(ROOT)).replace("\\", "/")
            if "/site-packages/" in rel or "/.venv" in rel:
                continue
            pl = plane_of(rel)
            counts[pl] = counts.get(pl, 0) + 1
            if pl == "archive" and counts[pl] > 80:
                continue
            try:
                size = full.stat().st_size
            except OSError:
                size = None
            rows.append({"path": rel, "plane": pl, "bytes": size, "name": name})
    return {"files": rows, "by_plane": counts, "file_count": sum(counts.values())}


def e3_count() -> dict:
    path = ROOT / "E3-RECON-OUTPUT" / "E3-ENGINE-CANDIDATES.json"
    deep = ROOT / "E3-RECON-OUTPUT" / "E3-ENGINE-CANDIDATES-DEEP.json"
    out = {"candidates": None, "deep": None}
    if path.is_file():
        try:
            out["candidates"] = len(json.loads(path.read_text(encoding="utf-8-sig")))
        except (json.JSONDecodeError, OSError):
            out["candidates"] = None
    if deep.is_file():
        try:
            out["deep"] = len(json.loads(deep.read_text(encoding="utf-8-sig")))
        except (json.JSONDecodeError, OSError):
            out["deep"] = None
    return out


def attach_copies(catalog: list[dict], scanned: dict) -> list[dict]:
    files = scanned.get("files") or []
    out = []
    for item in catalog:
        stem = Path(item["path"]).name.lower()
        copies = [f["path"] for f in files if Path(f["path"]).name.lower() == stem and f["path"] != item["path"]]
        # also same basename without first dirs
        if not copies and stem.endswith((".py", ".ts", ".json", ".md")):
            copies = [f["path"] for f in files if f["path"] != item["path"] and stem.split(".")[0] in f["name"].lower()][:12]
        row = dict(item)
        row["exists"] = (ROOT / item["path"]).exists()
        row["copies"] = copies[:20]
        row["copy_count"] = len(copies)
        row["gl005_proven"] = False
        row["merged_now"] = False
        out.append(row)
    return out


def how_to_benefit() -> list[str]:
    return [
        "شغّل المسار الحي فقط: mind-fill → absorb/INDEX → KAE → NeuroLingua. أمر واحد: python3 scripts/ai-os/raios_c5_train.py",
        "لا تشغّل brain.py ولا خطط الأرشيف ولا JSON محركات EOS-PRODUCTION.",
        "لا تدمج تلقائيًا. A13 يقول automatic_merge=false.",
        "WAL المعرفي لا يُنقل ولا يُكتب هنا (A15). محوّل NeuroLingua ليس حافلة ثانية.",
        "سجل ENGINE_REGISTRY هو قائمة الحرّاس الكنسية. ملف اسمه engine في الأرشيف ليس قدرة حيّة.",
        "الاستفادة = ضغط المعرفة وإعادة الاستخدام، لا محرك دمج رقم 113.",
        "إغلاق GL-005 يبقى AUTHENTICATED_ORCHESTRATION_TASK ثم استيعاب Qwen/Granite مستقل ثم GL005.",
    ]


def render_md(rec: dict) -> str:
    lines = [
        "# جرد محركات الدمج — RAIOS",
        "",
        "هذه الجلسة **C2**. C5 يسكن في git. الجرد DISCOVERED وليس CANONICAL. لم يُنفَّذ أي دمج.",
        "",
        f"- الرأس: `{rec['head']}`",
        f"- ملفات باسم merge/engine بعد الاستبعاد: `{rec['scan']['file_count']}`",
        f"- مرشحو E3: `{rec['e3']}`",
        f"- دمج نُفّذ الآن: `false`",
        f"- WAL كُتب: `false`",
        f"- GL005_PROVEN: `false`",
        "",
        "## كيف نستفيد",
        "",
    ]
    for tip in rec["how_to_benefit"]:
        lines.append(f"- {tip}")
    lines += [
        "",
        "## المحركات المسماة",
        "",
        "| id | الحالة | المسار | ماذا يدمج | نسخ |",
        "|---|---|---|---|---:|",
    ]
    for eng in rec["engines"]:
        lines.append(
            f"| `{eng['id']}` | `{eng['status']}` | `{eng['path']}` | {eng['merges']} | {eng['copy_count']} |"
        )
    lines += ["", "## وصف كل محرك وكيف نستخدمه", ""]
    for eng in rec["engines"]:
        lines += [
            f"### {eng['name_ar']} (`{eng['id']}`)",
            "",
            f"- الإنجليزي: {eng['name_en']}",
            f"- الحالة: `{eng['status']}` — موجود: `{eng['exists']}`",
            f"- التشغيل: `{eng.get('run') or 'لا يُشغَّل من هذه الشريحة'}`",
            f"- الاستفادة: {eng['benefit_ar']}",
        ]
        if eng.get("copies"):
            shown = ", ".join(f"`{c}`" for c in eng["copies"][:6])
            lines.append(f"- نسخ أخرى: {shown}")
        lines.append("")
    lines += [
        "## النسخ حسب الطبقة",
        "",
        "| طبقة | عدد ملفات merge/engine |",
        "|---|---:|",
    ]
    for k, v in sorted((rec["scan"].get("by_plane") or {}).items()):
        lines.append(f"| `{k}` | {v} |")
    lines += [
        "",
        "عدد الملفات ليس ذكاءً. أرشيف EOS-PRODUCTION مليء بتقارير JSON اسمها engine وليست وقت تشغيل.",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    return "\n".join(lines) + "\n"


def stamp() -> dict:
    wal_before = wal_mtime()
    scanned = scan_copies()
    engines = attach_copies(list(CATALOG), scanned)
    rec = {
        "schema": "raios.c5-merge-engines.v1",
        "ts": utc(),
        "from": "C2",
        "parent": "C1",
        "c5": "git",
        "canonical": False,
        "knowledge_state": "DISCOVERED",
        "head": git_head(),
        "merged_now": False,
        "destructive_merge": False,
        "brain_py_executed": False,
        "archive_plan_executed": False,
        "new_kernel": False,
        "openai": False,
        "langchain": False,
        "wal_written": False,
        "gl005_proven": False,
        "engines": engines,
        "live_ids": [e["id"] for e in engines if e["status"] == "LIVE"],
        "do_not_run_ids": [e["id"] for e in engines if e["status"] == "DO_NOT_RUN"],
        "scan": {"file_count": scanned["file_count"], "by_plane": scanned["by_plane"]},
        "e3": e3_count(),
        "how_to_benefit": how_to_benefit(),
        "next": "AUTHENTICATED_ORCHESTRATION_TASK",
        "law": LAWS,
    }
    if wal_mtime() != wal_before:
        raise SystemExit("MERGE_ENGINES_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    rec["ok"] = (
        rec["merged_now"] is False
        and rec["gl005_proven"] is False
        and rec["brain_py_executed"] is False
        and rec["wal_written"] is False
        and rec["new_kernel"] is False
        and any(e["id"] == "mind-fill" and e["exists"] for e in engines)
        and any(e["id"] == "brain-discover-merge" and e["status"] == "DO_NOT_RUN" for e in engines)
    )
    body = json.dumps(rec, indent=2, ensure_ascii=False) + "\n"
    rows = []
    digest = dump_text(REPORTS / ARTIFACTS[0], body)
    rows.append({"name": ARTIFACTS[0], "sha256": digest})
    md = render_md(rec)
    digest_md = dump_text(REPORTS / ARTIFACTS[1], md)
    rows.append({"name": ARTIFACTS[1], "sha256": digest_md})
    rec["artifacts"] = rows
    OUT.mkdir(parents=True, exist_ok=True)
    dump_text(OUT / "LAST.json", json.dumps({"ok": rec["ok"], "gl005_proven": False, "merged_now": False}, indent=2) + "\n")
    return rec


def main() -> int:
    rec = stamp()
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "engines": len(rec["engines"]),
                "scan_files": rec["scan"]["file_count"],
                "merged_now": False,
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
