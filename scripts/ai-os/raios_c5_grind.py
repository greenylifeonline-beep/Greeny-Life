#!/usr/bin/env python3
"""Mill the live three-company keepers. Gym muscle, not a second mind. No WAL. No PASS."""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-grind"
MEETING = "GL-COUNCIL-4a11023c3c321b6f"
MODEL_RE = re.compile(r"^model\s+(\w+)", re.M)
SKIP_DIR = {".git", "node_modules", ".next", ".next-gl004-proof", "__pycache__", ".venv"}
ENTITY_RE = re.compile(
    r"GREENY_LIFE_EGYPT|GREENS_NATURE_UAE|GREEN_LINES_NORWAY_EU|OrchestrationTask|SalesOrder|Inventory|Supplier|Shipment|Invoice|Payment"
)

BRAINS = (
    {
        "id": "GREENY_LIFE_EGYPT",
        "name": "Greeny-Life Egypt",
        "territory": "Egypt",
        "keepers": (
            "lib/intelligence/greeny-life-egypt-brain.ts",
            "app/api/brains/greeny-life-egypt/route.ts",
            "tests/greeny_life_egypt_brain_check.ts",
        ),
        "gaps": (),
    },
    {
        "id": "GREENS_NATURE_UAE",
        "name": "Greens Nature UAE",
        "territory": "UAE / GCC",
        "keepers": ("lib/intelligence/three-operating-brains.ts",),
        "gaps": (
            "lib/intelligence/greens-nature-uae-brain.ts",
            "app/api/brains/greens-nature-uae/route.ts",
            "tests/greens_nature_uae_brain_check.ts",
        ),
    },
    {
        "id": "GREEN_LINES_NORWAY_EU",
        "name": "Green Lines Norway/EU",
        "territory": "Norway / EU",
        "keepers": (
            "greenlines_brain/kernel.py",
            "greenlines_brain/graph.py",
            "greenlines_brain/identity.py",
            "lib/intelligence/three-operating-brains.ts",
        ),
        "gaps": (
            "lib/intelligence/greenlines-norway-brain.ts",
            "app/api/brains/greenlines-norway/route.ts",
            "tests/greenlines_norway_brain_check.ts",
        ),
    },
)

PROPOSED = (
    ("Celerp", "CELERP_NE_LIVE_ERP", "prisma/schema.prisma + app/api"),
    ("AG2/AutoGen", "AG2_NE_RAIOS_COUNCIL", ".ai-os/mcp + council seats"),
    ("LightRAG", "LIGHTRAG_NE_COGNITIVE_WAL", "DIGESTS/INDEX + RAIOS WAL + greenlines_brain/graph.py"),
    ("pygrametl", "PYGRAMETL_NE_ABSORB", "scripts/ai-os/raios_absorb.py + raios_learn_ingest.py"),
    ("BeeAI", "BEEAI_NE_EIGHT_TOOLS", "eight V1 MCP tools"),
    ("LangSwarm", "LANGSWARM_NE_SECOND_BUS", "no second agent bus"),
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def hash_tree(rel: str) -> dict:
    root = ROOT / rel
    files = 0
    bytes_ = 0
    acc = hashlib.sha256()
    entities: dict[str, int] = {}
    if not root.exists():
        return {"path": rel, "exists": False, "files": 0, "bytes": 0, "merkle": None, "entities": {}}
    paths = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
    for path in paths:
        if any(part in SKIP_DIR for part in path.parts):
            continue
        data = path.read_bytes()
        files += 1
        bytes_ += len(data)
        acc.update(hashlib.sha256(data).digest())
        acc.update(path.as_posix().encode())
        if path.suffix in {".ts", ".py", ".prisma", ".md", ".json"} and len(data) < 2_000_000:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            for match in ENTITY_RE.findall(text):
                entities[match] = entities.get(match, 0) + 1
    return {
        "path": rel,
        "exists": True,
        "files": files,
        "bytes": bytes_,
        "merkle": acc.hexdigest() if files else None,
        "entities": dict(sorted(entities.items())),
    }


def prisma_models() -> list[str]:
    text = (ROOT / "prisma" / "schema.prisma").read_text(encoding="utf-8")
    return MODEL_RE.findall(text)


def api_routes() -> list[str]:
    routes = []
    for path in sorted((ROOT / "app" / "api").rglob("route.ts")):
        rel = path.relative_to(ROOT / "app" / "api").parent.as_posix()
        routes.append("/api" if rel == "." else f"/api/{rel}")
    return routes


def json_count(rel: str, key: str) -> int | None:
    path = ROOT / rel
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and key in data and isinstance(data[key], list):
        return len(data[key])
    return None


def proposed_absent() -> list[dict]:
    hay = " ".join(
        p.read_text(encoding="utf-8", errors="ignore")
        for p in (
            ROOT / "package.json",
            ROOT / "requirements.txt" if (ROOT / "requirements.txt").exists() else ROOT / "package.json",
        )
    )
    rows = []
    for name, law, keeper in PROPOSED:
        needle = name.split("/")[0].lower()
        in_lock = needle in hay.lower()
        rows.append(
            {
                "name": name,
                "in_package_manifest": in_lock,
                "law": law,
                "reuse": keeper,
                "install": False,
            }
        )
    return rows


def mill_brains() -> list[dict]:
    rows = []
    for brain in BRAINS:
        keepers = [{"path": p, "exists": exists(p), "sha256": sha(ROOT / p)} for p in brain["keepers"]]
        gaps = [{"path": p, "exists": exists(p)} for p in brain["gaps"]]
        rows.append(
            {
                "id": brain["id"],
                "name": brain["name"],
                "territory": brain["territory"],
                "keepers": keepers,
                "gaps": gaps,
                "keeper_ok": all(k["exists"] for k in keepers),
                "gap_open": any(not g["exists"] for g in gaps) if gaps else False,
            }
        )
    return rows


def graph(brains: list[dict], models: list[str], routes: list[str]) -> dict:
    nodes = [
        {"id": "ERP", "kind": "keeper", "label": "Prisma + Next API"},
        {"id": "COUNCIL", "kind": "keeper", "label": "RAIOS seats + 8 MCP tools"},
        {"id": "KNOWLEDGE", "kind": "keeper", "label": "DIGESTS/INDEX/WAL/graph.py"},
        {"id": "ETL", "kind": "keeper", "label": "absorb + ingest"},
        {"id": "MASTERMIND", "kind": "keeper", "label": "MasterMind AI"},
    ]
    edges = [
        {"from": "MASTERMIND", "to": "ERP", "rel": "reads"},
        {"from": "COUNCIL", "to": "MASTERMIND", "rel": "does_not_replace"},
    ]
    for brain in brains:
        nodes.append({"id": brain["id"], "kind": "company", "label": brain["name"]})
        edges.append({"from": "MASTERMIND", "to": brain["id"], "rel": "coordinates"})
        edges.append({"from": brain["id"], "to": "ERP", "rel": "uses_if_route_exists"})
        for gap in brain["gaps"]:
            if not gap["exists"]:
                nodes.append({"id": gap["path"], "kind": "gap", "label": gap["path"]})
                edges.append({"from": brain["id"], "to": gap["path"], "rel": "missing"})
    nodes.append({"id": "PRISMA_MODELS", "kind": "count", "label": f"{len(models)} models"})
    nodes.append({"id": "API_ROUTES", "kind": "count", "label": f"{len(routes)} routes"})
    return {"nodes": nodes, "edges": edges}


def render_md(rec: dict) -> str:
    lines = [
        "# طاحونة C5 — العقول الثلاثة",
        "",
        f"- الاجتماع: `{rec['meeting_id']}`",
        f"- المضيف: `{rec['host']}`",
        f"- الملفات الممسوحة: `{rec['files_scanned']}`",
        f"- البايتات: `{rec['bytes_scanned']}`",
        f"- نماذج Prisma: `{len(rec['prisma_models'])}`",
        f"- مسارات API: `{len(rec['api_routes'])}`",
        f"- منتجات: `{rec['canonical']['products']}`",
        f"- موردون: `{rec['canonical']['suppliers']}`",
        f"- مخزون: `{rec['canonical']['stock']}`",
        f"- كيانات_مطحونة: `{json.dumps(rec.get('entities') or {}, ensure_ascii=False)}`",
        f"- المدة_ms: `{rec['ms']}`",
        "- اللصق قناة. التعلّم تكرار وممارسة واستيعاب.",
        "- Celerp/AG2/LightRAG اقتراح اكتشاف، ليست تثبيتاً.",
        "- GL005_PROVEN: `false`",
        "",
        "## الشركات",
        "",
        "| شركة | حراس | فجوة |",
        "|---|---|---|",
    ]
    for brain in rec["brains"]:
        keep = ",".join("نعم" if k["exists"] else "لا" for k in brain["keepers"])
        gap = "مفتوحة" if brain["gap_open"] else "لا"
        lines.append(f"| {brain['name']} | {keep} | {gap} |")
    lines += ["", "## رفض الإمبراطورية الجديدة", ""]
    for row in rec["proposed"]:
        lines.append(f"- `{row['name']}` → `{row['law']}` يعاد استخدام `{row['reuse']}`")
    lines += ["", "## نماذج العمليات (ERP الحي)", ""]
    lines.append(", ".join(f"`{m}`" for m in rec["prisma_models"]))
    lines += ["", "## مسارات API", ""]
    lines.append(", ".join(f"`{r}`" for r in rec["api_routes"]))
    lines += [
        "",
        "## التالي (اكتشاف، ليس أمراً بتنصيب)",
        "",
        "- الفجوات UAE/Norway هي GL-003، ليست Celerp.",
        "- التنسيق الحي هو المجلس الثماني الأدوات، ليس AG2.",
        "- الهضم الحي هو absorb/index/WAL، ليس LightRAG كعقل ثانٍ.",
        "- Colab يطحن هذا المستودع. الصفحة البيضاء قبل Run all ليست غياب عقل.",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    return "\n".join(lines)


def grind(host: str = "local-or-cursor") -> dict:
    t0 = time.perf_counter()
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    trees = [
        hash_tree("lib/intelligence"),
        hash_tree("app/api"),
        hash_tree("prisma"),
        hash_tree("greenlines_brain"),
        hash_tree("canonical"),
        hash_tree(".ai-os"),
        hash_tree("scripts/ai-os"),
    ]
    entities: dict[str, int] = {}
    for tree in trees:
        for key, val in (tree.get("entities") or {}).items():
            entities[key] = entities.get(key, 0) + val
    brains = mill_brains()
    models = prisma_models()
    routes = api_routes()
    proposed = proposed_absent()
    rec = {
        "schema": "raios.c5-grind.v1",
        "meeting_id": MEETING,
        "case": "CASE-006",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "host": host,
        "files_scanned": sum(t["files"] for t in trees),
        "bytes_scanned": sum(t["bytes"] for t in trees),
        "trees": trees,
        "brains": brains,
        "prisma_models": models,
        "api_routes": routes,
        "canonical": {
            "products": json_count("canonical/data/master_products.json", "products"),
            "suppliers": json_count("canonical/data/suppliers.json", "suppliers"),
            "stock": json_count("canonical/inventory/stock-levels.json", "stock"),
        },
        "entities": dict(sorted(entities.items())),
        "proposed": proposed,
        "graph": graph(brains, models, routes),
        "ok": all(b["keeper_ok"] for b in brains) and not any(p["in_package_manifest"] for p in proposed),
        "knowledge_state": "DISCOVERED",
        "canonical_flag": False,
        "promoted": False,
        "wal_written": False,
        "gl005_proven": False,
        "install_celerp": False,
        "install_ag2": False,
        "install_lightrag": False,
        "law": [row[1] for row in PROPOSED]
        + [
            "PROPOSAL_PASTE_NE_INSTALL",
            "THREE_COMPANIES_ALREADY_NAMED",
            "WHITE_NOTEBOOK_NE_ABSENT_MIND",
            "REUSE_KEEPER_BEFORE_NEW_STACK",
            "PASTE_NE_LEARNING",
        ],
    }
    rec["ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
    rec["hashes"] = {
        "three_operating_brains": sha(ROOT / "lib/intelligence/three-operating-brains.ts"),
        "schema_prisma": sha(ROOT / "prisma/schema.prisma"),
        "core_contract": sha(ROOT / ".ai-os/CORE-CONTRACT.md"),
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("GRIND_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "GRAPH.json").write_text(json.dumps(rec["graph"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    md = render_md(rec)
    (OUT_DIR / "LAST.md").write_text(md, encoding="utf-8")
    return rec


def main() -> int:
    rec = grind()
    print(json.dumps({"ok": rec["ok"], "files": rec["files_scanned"], "bytes": rec["bytes_scanned"], "models": len(rec["prisma_models"]), "routes": len(rec["api_routes"]), "ms": rec["ms"], "gl005_proven": False}, ensure_ascii=False, indent=2))
    print((OUT_DIR / "LAST.md").read_text(encoding="utf-8"))
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
