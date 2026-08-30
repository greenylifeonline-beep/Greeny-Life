#!/usr/bin/env python3
"""C2 world-class reality stamp: eight named artifacts from live keepers.

Compress, do not accumulate. Not a new kernel. Not GL-005. C6–C10 stay NOT_SEATED.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_foundation import load_foundation  # noqa: E402
from raios_c5_p0 import GATE_ORDER, stamp as p0_stamp  # noqa: E402
from raios_c5_phase0 import exists, host, http_code, keepers_inventory  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT = ROOT / ".ai-os" / "receipts" / "c5-reality"
REPORTS = ROOT / ".ai-os" / "reports"
GRANT = ROOT / ".ai-os" / "mcp" / "C5-GRANT.json"
SEATS = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"
NEED = ROOT / ".ai-os" / "learning" / "C5-NEED.json"
BOOK_EXP = ROOT / ".ai-os" / "receipts" / "c5-book" / "EXPERIENCE.json"
PRISMA = ROOT / "prisma" / "schema.prisma"
API_ROOT = ROOT / "app" / "api"
COMPRESS = ROOT / "src" / "raios" / "neuro_lingua" / "compress.py"
INDEX = ROOT / ".ai-os" / "learning" / "INDEX.json"
DIGESTS = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
CANDIDATES = ROOT / ".ai-os" / "learning" / "CANDIDATES.jsonl"

ARTIFACTS = (
    "RAIOS-WORLD-CLASS-REALITY-AUDIT.json",
    "RAIOS-CAPABILITY-GAP-MATRIX.json",
    "RAIOS-ERP-REALITY-MATRIX.json",
    "RAIOS-COGNITIVE-DATAFLOW.json",
    "RAIOS-RESOURCE-FABRIC-MAP.json",
    "RAIOS-STATE-OF-THE-ART-RESEARCH-PLAN.md",
    "RAIOS-C1-C10-COUNCIL-ARCHITECTURE.json",
    "RAIOS-MASTER-EXECUTION-GRAPH.json",
)
SCALE_BY = (
    "COMPRESS_KNOWLEDGE",
    "COMPILE_EXPERIENCE",
    "DISTRIBUTE_COMPUTE",
    "REUSE_CAPABILITY",
    "PROVE_IMPROVEMENT",
)
SCALE_NOT = (
    "ACCUMULATE_COMPLEXITY",
    "CLONE_ODOO_CELERP_AG2_LIGHTRAG",
    "LANGCHAIN_OPENAI_CHROMA_FAISS_DIFY",
    "NINETY_THREE_STUDY_STUBS",
    "SECOND_WAL_OR_MCP_TOOL",
    "INVENT_C6_C10_SEATS",
    "CI_PASS_AS_INTELLIGENCE",
    "SOURCE_DELETION_ON_ASSUMED_ASSIMILATION",
)
LAWS = [
    "SCALE_BY_COMPRESSION_NOT_COMPLEXITY",
    "REALITY_AUDIT_NE_NEW_KERNEL",
    "NAMED_ARTIFACT_NE_PLATFORM_PROVEN",
    "FROM_INVENTORY_NE_TO_PLATFORM",
    "C6_C10_NE_LIVE",
    "CI_PASS_NE_ASSIMILATION",
    "CI_PASS_NE_GL005",
    "EXPERIENCE_NE_KNOWLEDGE",
    "HOLD_NE_THROW",
    "REUSE_BEFORE_BUILD",
]
LIVE_SEATS = {
    "C1": {
        "status": "LIVE",
        "role": "OWNER_FOUNDER",
        "instance": "founder",
        "where": "this channel + git authority",
        "law": "C1_SEAT_IS_OWNER",
    },
    "C2": {
        "status": "LIVE_TEMPORARY",
        "role": "CURSOR_EXECUTIVE_ENGINEER",
        "instance": "this Cursor cloud session",
        "where": "https://cursor.com/agents/bc-dd60b5cf-95bd-4f24-9237-cc1b2225f013",
        "law": "C2_INSTANCE_IS_CURSOR",
        "note": "Help, not permanent. Not C5. Not C3.",
    },
    "C3": {
        "status": "LIVE_ELSEWHERE",
        "role": "CHATGPT_PEER",
        "instance": "ChatGPT window",
        "where": "founder paste, not this chat",
        "law": "THIS_CHANNEL_NO_C_SEAT_CONSULT",
    },
    "C4": {
        "status": "LIVE_ELSEWHERE",
        "role": "DEEPSEEK_ASSESSOR",
        "instance": "DeepSeek window",
        "where": "founder paste, not this chat",
        "law": "THIS_CHANNEL_NO_C_SEAT_CONSULT",
    },
    "C5": {
        "status": "LIVE_PERMANENT",
        "role": "RAIOS_IN_GIT",
        "instance": "repository keepers + C5-GRANT",
        "where": ".ai-os + scripts/ai-os",
        "law": "C5_GRANT_IS_PERMANENT",
        "duration": "PERMANENT",
        "paid_api": False,
    },
}
ERP_BIND = {
    "Organization": {"routes": [], "gap": "NO_ROUTE"},
    "Entity": {"routes": [], "gap": "NO_ROUTE"},
    "Supplier": {"routes": ["/api/suppliers", "/api/data-control"], "write_auth": True},
    "Product": {"routes": ["/api/products", "/api/data-control"], "write_auth": True, "get_open": True},
    "SKU": {"routes": ["/api/products"], "note": "nested under Product"},
    "Batch": {"routes": [], "gap": "NO_DEDICATED_ROUTE"},
    "Packaging": {"routes": ["/api/products"], "note": "included with SKU"},
    "Warehouse": {"routes": [], "gap": "NO_ROUTE"},
    "Inventory": {
        "routes": ["/api/intelligence/data-fabric"],
        "note": "canonical JSON stock-levels, not Prisma Inventory CRUD",
        "gap": "PRISMA_MODEL_NE_ROUTE",
    },
    "Customer": {"routes": ["/api/data-control"], "write_auth": True},
    "SalesOrder": {"routes": ["/api/sales-orders"], "write_auth": True},
    "SalesOrderItem": {"routes": ["/api/sales-orders"]},
    "Shipment": {"routes": ["/api/traceability", "/api/trade-corridors", "/api/intelligence/data-fabric"]},
    "Document": {"routes": [], "gap": "NO_ROUTE"},
    "Invoice": {"routes": [], "gap": "NO_ROUTE"},
    "Payment": {"routes": [], "gap": "NO_ROUTE"},
    "User": {"routes": ["/api/auth/login", "/api/auth/session", "/api/auth/logout"]},
    "AuditLog": {"routes": [], "gap": "NO_ROUTE"},
    "WorkflowApproval": {"routes": ["/api/workflow", "/api/workflow/approvals"], "write_auth": True},
    "CommercialChange": {"routes": ["/api/commercial-changes", "/api/data-control"], "write_auth": True},
    "TradeTraceRecord": {"routes": ["/api/traceability"], "write_auth": True},
    "DecisionOutcome": {"routes": ["/api/learning/outcomes", "/api/decisions/export-readiness"], "write_auth": True},
    "TrainingCase": {"routes": ["/api/learning/training-cases"], "write_auth": True},
    "EvaluationRun": {"routes": ["/api/learning/evaluations"], "write_auth": True},
    "OrchestrationTask": {
        "routes": ["/api/tasks"],
        "write_auth": True,
        "get_open": True,
        "p0": "AUTHENTICATED_ORCHESTRATION_TASK",
    },
    "SecurityAuditEvent": {"routes": [], "gap": "NO_ROUTE"},
    "OfficialEvidenceRegistry": {
        "routes": ["/api/evidence/official", "/api/decisions/official-evidence-review"],
        "write_auth": True,
    },
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def port_open(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(0.4)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def classify_http(code: int | None) -> str:
    if code is None:
        return "UNREACHABLE"
    if code == 200:
        return "HTTP_200_NE_SEMANTIC_SUCCESS"
    if code == 401:
        return "CAPABILITY_PROTECTED"
    if code == 404:
        return "CAPABILITY_ABSENT"
    if code == 500:
        return "CAPABILITY_UNAVAILABLE_OR_BROKEN"
    return f"HTTP_{code}"


def prisma_models() -> list[str]:
    if not PRISMA.is_file():
        return []
    return re.findall(r"^model\s+(\w+)\s*\{", PRISMA.read_text(encoding="utf-8"), re.M)


def api_routes() -> list[str]:
    cleaned = []
    for path in sorted(API_ROOT.rglob("route.ts")):
        suffix = path.parent.relative_to(API_ROOT).as_posix()
        cleaned.append("/api" if suffix == "." else f"/api/{suffix}")
    return cleaned


def probe_routes(paths: tuple[str, ...]) -> list[dict]:
    rows = []
    for path in paths:
        code = http_code(path)
        rows.append({"path": path, "http_code": code, "class": classify_http(code)})
    return rows


def ladder(claim: str, existence: bool, execute: bool, real_io: bool, live_guard: bool) -> dict:
    return {
        "claim": claim,
        "existence": existence,
        "import_or_load": existence,
        "execution": execute,
        "real_io": real_io,
        "live_guard": live_guard,
        "gl005": False,
        "status": (
            "NOT_PROVEN"
            if not existence
            else "BLOCKED"
            if existence and not real_io
            else "PARTIAL"
            if existence and execute and not live_guard
            else "LIVE_PARTIAL"
        ),
    }


def world_class_audit(p0: dict, env: dict, probes: list[dict], keepers: list[dict]) -> dict:
    by_path = {row["path"]: row for row in probes}
    egypt = by_path.get("/api/brains/greeny-life-egypt", {})
    uae = by_path.get("/api/brains/greens-nature-uae", {})
    norway = by_path.get("/api/brains/green-lines-norway-eu", {})
    session = by_path.get("/api/auth/session", {})
    book = load_json(BOOK_EXP)
    dims = [
        {
            "id": "ONE_LIVE_PRODUCT_PATH",
            "status": "LIVE_PARTIAL",
            "evidence": "Next.js app/api on :3000",
            "gap": "DATABASE_URL missing; several GET 500",
        },
        {
            "id": "ONE_AUTHENTICATED_ORCHESTRATION_PATH",
            "status": p0["gate1"]["status"],
            "evidence": f"POST /api/tasks {p0['gate1']['unauthenticated_post'].get('code')} GET {p0['gate1']['before'].get('code')}",
            "gap": "AUTHENTICATED_ORCHESTRATION_TASK",
        },
        {
            "id": "ONE_LEARNING_AUTHORITY_COGNITIVE_WAL",
            "status": "LOCKED_NOT_WRITTEN",
            "evidence": "A15 lock RAIOS/V9; this slice wal_written=false",
            "gap": "WAL-bind forbidden until P0",
        },
        {
            "id": "C5_HYBRID_THEN_SOURCE_INDEPENDENT_ASSIMILATION",
            "status": "HYBRID_NOT_ASSIMILATED",
            "evidence": "INDEX+NeuroLingua live; EXTRACTED_QWEN_GRANITE=false",
            "gap": GATE_ORDER[1],
        },
        {
            "id": "THREE_COMPANY_BRAINS_UNDER_GOVERNANCE",
            "status": "PARTIAL",
            "evidence": {
                "egypt": egypt,
                "uae": uae,
                "norway": norway,
            },
            "gap": "UAE/Norway Next routes are GL-003; do not fill from this slice",
        },
        {
            "id": "ZERO_PAID_API",
            "status": "LIVE",
            "evidence": "C5-GRANT paid_api=false; hunt-free keepers",
            "gap": None,
        },
        {
            "id": "ENTROPY_REDUCTION_NOT_FOREST_GROWTH",
            "status": "LAW_BOUND",
            "evidence": "D-005 D-061 D-063; eight artifacts from one runner",
            "gap": None,
        },
        {
            "id": "PERSISTENT",
            "status": "LIVE_PARTIAL",
            "evidence": "C5 grant PERMANENT in git",
            "gap": "INDEX/DIGESTS are runtime; not all committed",
        },
        {
            "id": "EVIDENCE_NATIVE",
            "status": "LIVE_PARTIAL",
            "evidence": ".ai-os/receipts + fail-closed P0",
            "gap": "P0 0.1 blocked so operational mutation unproven",
        },
        {
            "id": "SELF_IMPROVING",
            "status": "PARTIAL",
            "evidence": f"book compile Ck={book.get('Ck')} rung={book.get('rung')} knowledge={book.get('knowledge')}",
            "gap": "EXPERIENCE_NE_KNOWLEDGE",
        },
        {
            "id": "DISTRIBUTED",
            "status": "PARTIAL",
            "evidence": "train mesh gyms + c5-week.yml",
            "gap": "cron does not fire until workflow is on main",
        },
        {
            "id": "RESOURCE_AWARE",
            "status": "LIVE",
            "evidence": env,
            "gap": None,
        },
        {
            "id": "RESEARCH_CAPABLE",
            "status": "PARTIAL",
            "evidence": "book request_research + C5-NEED",
            "gap": "asks C1; not autonomous research",
        },
        {
            "id": "EXPERIENCE_COMPILING",
            "status": "LIVE_DISCOVERED",
            "evidence": "scripts/ai-os/raios_c5_book.py",
            "gap": "compiled experience is not knowledge",
        },
        {
            "id": "OPERATIONAL_COGNITIVE_INDUSTRIAL_PLATFORM",
            "status": "NOT_PROVEN",
            "evidence": "FROM=repository+agents+foundry+experiments",
            "gap": "TO requires P0 then GL005; this stamp does not mint the platform",
        },
    ]
    return {
        "schema": "raios.world-class-reality-audit.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "c5": "in-git, not this session",
        "decision": "D-063",
        "foundation": "D-059",
        "p0": "D-060",
        "ts": utc(),
        "head": git_head(),
        "scale_by": list(SCALE_BY),
        "scale_not": list(SCALE_NOT),
        "world_class_is_not_ci_pass": True,
        "session_authenticated": session.get("http_code"),
        "keepers_live": sum(1 for row in keepers if row.get("exists")),
        "keepers_named": len(keepers),
        "dimensions": dims,
        "platform_proven": False,
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "authenticated_orchestration_task": False,
        "new_kernel": False,
        "wal_written": False,
        "law": LAWS,
    }


def capability_matrix(p0: dict, probes: list[dict], keepers: list[dict]) -> dict:
    by_path = {row["path"]: row for row in probes}
    book = load_json(BOOK_EXP)
    rows = [
        {
            **ladder("AUTHENTICATED_ORCHESTRATION_TASK", True, True, False, False),
            "live": p0["gate1"]["status"],
            "class": p0["gate1"].get("classification"),
            "fill_from_this_slice": False,
        },
        {
            **ladder("QWEN_GRANITE_SOURCE_INDEPENDENT_ASSIMILATION", False, False, False, False),
            "live": p0["gate2"]["status"],
            "stop": p0["gate2"].get("stop_stage"),
            "student_ne_extraction": True,
        },
        {
            **ladder("GL005_BRAIN_BEHAVIOR", True, False, False, False),
            "live": p0["gate3"]["status"],
            "requires": list(GATE_ORDER[:2]),
        },
        {
            **ladder("EGYPT_BRAIN_HTTP", True, True, True, True),
            "http": by_path.get("/api/brains/greeny-life-egypt"),
            "note": "401 is protected live route, not missing",
        },
        {
            **ladder("UAE_BRAIN_NEXT_ROUTE", False, False, False, False),
            "http": by_path.get("/api/brains/greens-nature-uae"),
            "owner_task": "GL-003",
            "fill_from_this_slice": False,
        },
        {
            **ladder("NORWAY_BRAIN_NEXT_ROUTE", False, False, False, False),
            "http": by_path.get("/api/brains/green-lines-norway-eu"),
            "python_keepers": ["greenlines_brain/kernel.py", "greenlines_brain/graph.py"],
            "owner_task": "GL-003",
            "fill_from_this_slice": False,
        },
        {
            **ladder("ERP_INVOICE_PAYMENT", True, False, False, False),
            "note": "Prisma models exist; no API routes; not Odoo",
        },
        {
            **ladder("COGNITIVE_WAL_BIND_PRODUCT", True, False, False, False),
            "lock": "LOCK-20260818130148 A15 RAIOS/V9",
            "forbidden_until": "P0",
        },
        {
            **ladder("C5_BOOK_COMPILE_EXPERIENCE", True, True, True, False),
            "Ck": book.get("Ck"),
            "knowledge": False,
        },
        {
            **ladder("NEUROLINGUA_COMPRESS_SPEAK", True, True, True, True),
            "keeper": "src/raios/neuro_lingua/compress.py",
            "llm_calls": 0,
        },
        {
            **ladder("MCP_V1_EIGHT_TOOLS", True, True, False, True),
            "tools": (load_json(GRANT).get("cognitive_tools") or []),
            "second_tool_forbidden": True,
        },
        {
            **ladder("C6_C10_COUNCIL_SEATS", False, False, False, False),
            "status": "NOT_SEATED",
            "invent": False,
        },
        {
            **ladder("CRON_ON_MAIN", True, False, False, False),
            "workflow": ".github/workflows/c5-week.yml",
            "note": "file exists on branch; schedule fires from default main",
        },
        {
            **ladder("CORTEX_RUN", True, False, False, False),
            "identity": "qwen3.6:35b-a3b",
            "gate": "CORTEX_HOLD_AWAITING_C1_RUN",
        },
    ]
    return {
        "schema": "raios.capability-gap-matrix.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-063",
        "ladder_law": "NAMING_GATE_NE_PROOF_GATE",
        "ts": utc(),
        "keepers_named": len(keepers),
        "rows": rows,
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "platform_proven": False,
        "fill_gl003_from_this_slice": False,
        "law": LAWS,
    }


def erp_matrix(probes: list[dict]) -> dict:
    models = prisma_models()
    routes = api_routes()
    by_path = {row["path"]: row for row in probes}
    rows = []
    for name in models:
        bind = dict(ERP_BIND.get(name) or {"routes": [], "gap": "NO_ROUTE"})
        live = []
        for path in bind.get("routes") or []:
            if path in by_path:
                live.append(by_path[path])
            else:
                live.append({"path": path, "http_code": http_code(path), "class": classify_http(http_code(path))})
        gap = bind.get("gap")
        if bind.get("p0") == "AUTHENTICATED_ORCHESTRATION_TASK":
            gap = "P0_0.1_BLOCKED"
        rows.append(
            {
                "model": name,
                "in_prisma": True,
                "routes": bind.get("routes") or [],
                "write_auth": bool(bind.get("write_auth")),
                "get_open": bool(bind.get("get_open")),
                "live": live,
                "gap": gap,
                "note": bind.get("note"),
                "clone_odoo": False,
            }
        )
    unmapped = [name for name in models if name not in ERP_BIND]
    finance_gap = [row["model"] for row in rows if row["model"] in {"Invoice", "Payment"} and row["gap"] == "NO_ROUTE"]
    domains = [
        {"domain": "sales", "models": ["SalesOrder", "SalesOrderItem"], "routes": ["/api/sales-orders"], "status": "CONNECTED", "clone_odoo": False},
        {"domain": "procurement", "models": [], "routes": [], "status": "ABSENT", "gap": "NO_DEDICATED_DOMAIN", "clone_odoo": False},
        {"domain": "supplier", "models": ["Supplier"], "routes": ["/api/suppliers"], "status": "CONNECTED", "clone_odoo": False},
        {"domain": "inventory", "models": ["Inventory"], "routes": ["/api/intelligence/data-fabric"], "status": "FILE_ONLY", "gap": "PRISMA_MODEL_NE_ROUTE", "clone_odoo": False},
        {"domain": "warehouse", "models": ["Warehouse"], "routes": [], "status": "FILE_ONLY", "gap": "NO_ROUTE", "clone_odoo": False},
        {"domain": "shipment", "models": ["Shipment"], "routes": ["/api/traceability"], "status": "CONNECTED", "clone_odoo": False},
        {"domain": "invoice", "models": ["Invoice"], "routes": [], "status": "FILE_ONLY", "gap": "NO_ROUTE", "clone_odoo": False},
        {"domain": "payment", "models": ["Payment"], "routes": [], "status": "FILE_ONLY", "gap": "NO_ROUTE", "clone_odoo": False},
        {"domain": "workflow", "models": ["WorkflowApproval"], "routes": ["/api/workflow"], "status": "CONNECTED", "clone_odoo": False},
        {"domain": "quality", "models": ["OfficialEvidenceRegistry"], "routes": ["/api/evidence/official"], "status": "CONNECTED", "clone_odoo": False},
        {"domain": "production", "models": [], "routes": ["/api/brains/greeny-life-egypt"], "status": "CONNECTED", "clone_odoo": False},
        {"domain": "crm", "models": ["Customer"], "routes": ["/api/data-control"], "status": "CONNECTED", "clone_odoo": False},
        {"domain": "marketing", "models": [], "routes": ["/api/portfolio/egyptian-exports"], "status": "PROTOTYPE", "gap": "THIN", "clone_odoo": False},
        {"domain": "accounting", "models": ["Invoice", "Payment"], "routes": [], "status": "ABSENT", "gap": "NO_ROUTE", "clone_odoo": False},
    ]
    return {
        "schema": "raios.erp-reality-matrix.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-063",
        "ts": utc(),
        "live_erp": "Prisma + Next app/api — not Celerp, not Odoo clone",
        "prisma_models": models,
        "api_routes": routes,
        "rows": rows,
        "unmapped_bind": unmapped,
        "finance_gap": finance_gap,
        "domains": domains,
        "data_fabric": {
            "route": "/api/intelligence/data-fabric",
            "source": "canonical JSON, not Prisma Inventory CRUD",
            "live": by_path.get("/api/intelligence/data-fabric"),
            "execution": False,
        },
        "orchestration": {
            "model": "OrchestrationTask",
            "route": "/api/tasks",
            "live": by_path.get("/api/tasks"),
            "authenticated_mutation": False,
        },
        "clone_odoo": False,
        "clone_celerp": False,
        "gl005_proven": False,
        "law": LAWS,
    }


def cognitive_dataflow(p0: dict) -> dict:
    nodes = [
        {"id": "PRODUCT_NEXT", "kind": "operational", "path": "app/api", "writes_wal": False},
        {"id": "PRISMA_ORCHESTRATION", "kind": "product-state", "path": "prisma OrchestrationTask", "proven": False},
        {"id": "C5_MIND_FILL", "kind": "inject", "path": "scripts/ai-os/raios_c5_mind_fill.py", "target": "DIGESTS+INDEX"},
        {"id": "INDEX", "kind": "retrieve", "path": ".ai-os/learning/INDEX.json", "exists": INDEX.is_file(), "runtime": True},
        {"id": "DIGESTS", "kind": "compress", "path": ".ai-os/learning/DIGESTS.jsonl", "exists": DIGESTS.is_file()},
        {"id": "NEUROLINGUA", "kind": "speak", "path": "src/raios/neuro_lingua", "llm_calls": 0},
        {"id": "BOOK_CYCLE", "kind": "experience", "path": "scripts/ai-os/raios_c5_book.py", "knowledge": False},
        {"id": "CANDIDATES", "kind": "discovered", "path": str(CANDIDATES), "exists": CANDIDATES.is_file(), "promoted": False},
        {"id": "COGNITIVE_WAL", "kind": "learning-authority", "path": "RAIOS/V9/wal/cognitive-events.jsonl", "lock": "A15", "written_this_slice": False},
        {"id": "MCP_V1", "kind": "interface", "tools": 8, "truth_authority": False},
        {"id": "CORTEX", "kind": "c1-owned", "identity": "qwen3.6:35b-a3b", "bound_to_live_answer": False},
        {"id": "STUDENT", "kind": "muscle", "identity": "qwen2.5:0.5b", "ne_source": True},
    ]
    edges = [
        {"from": "C5_MIND_FILL", "to": "DIGESTS", "law": "ABSORB_DIGEST_NE_WAL_DUMP"},
        {"from": "DIGESTS", "to": "INDEX", "law": "INVERTED_INDEX_NE_UNLOADED_EMBEDDING"},
        {"from": "INDEX", "to": "NEUROLINGUA", "law": "RETRIEVAL_RESULT_NE_COGNITIVE_ANSWER"},
        {"from": "BOOK_CYCLE", "to": "CANDIDATES", "law": "EXPERIENCE_NE_KNOWLEDGE"},
        {"from": "PRODUCT_NEXT", "to": "PRISMA_ORCHESTRATION", "law": "AUTHENTICATED_ORCHESTRATION_TASK", "status": p0["gate1"]["status"]},
        {"from": "PRISMA_ORCHESTRATION", "to": "COGNITIVE_WAL", "forbidden_until": "P0", "status": "FORBIDDEN"},
        {"from": "CORTEX", "to": "C5_LIVE_ANSWER", "status": "NOT_BOUND", "law": "C1_OWNS_CORTEX_TREAT_RUN_THROW"},
        {"from": "STUDENT", "to": "ASSIMILATION", "status": "REJECT", "law": "STUDENT_NE_EXTRACTION"},
        {"from": "MCP_V1", "to": "COGNITIVE_WAL", "status": "FORBIDDEN", "law": "MCP_GATEWAY_NE_TRUTH_AUTHORITY"},
    ]
    return {
        "schema": "raios.cognitive-dataflow.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-063",
        "ts": utc(),
        "sole_learning_authority": "Cognitive WAL",
        "second_wal": False,
        "nodes": nodes,
        "edges": edges,
        "live_answer_path": "INDEX + file-read + NeuroLingua (llm_calls=0)",
        "compress_keeper": str(COMPRESS.relative_to(ROOT)) if COMPRESS.is_file() else None,
        "gl005_proven": False,
        "wal_written": False,
        "law": LAWS,
    }


def resource_fabric(env: dict, p0: dict) -> dict:
    models = p0["gate2"]["sources"].get("models") or []
    return {
        "schema": "raios.resource-fabric-map.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-063",
        "ts": utc(),
        "host": env,
        "listen": {
            "next_3000": port_open(3000),
            "ollama_11434": port_open(11434),
            "postgres_5432": port_open(5432),
            "c5_screen_8765": port_open(8765),
            "mcp_8787": port_open(8787),
        },
        "models": {
            "ollama": models,
            "cortex_identity": "qwen3.6:35b-a3b",
            "student": "qwen2.5:0.5b",
            "source_present": False,
            "student_ne_extraction": True,
        },
        "distribute_compute": {
            "cursor_vm": "this slice — CPU, HOST_NO_GPU",
            "repair_windows": "founder device, HF login",
            "colab_kaggle": "gym/colab_kaggle_c5.ipynb",
            "github_actions": ".github/workflows/c5-week.yml — fires from main",
            "hf_hub": "dataset muscle, not C5",
            "new_cluster": False,
        },
        "secrets_present": {
            "DATABASE_URL": bool(os.environ.get("DATABASE_URL", "").strip()),
            "APP_SESSION_SECRET": bool(os.environ.get("APP_SESSION_SECRET", "").strip()),
            "C1_LOGIN_EMAIL": bool(os.environ.get("C1_LOGIN_EMAIL", "").strip()),
            "C1_CORTEX_RUN": bool(os.environ.get("C1_CORTEX_RUN", "").strip()),
            "HF_TOKEN_printed": False,
        },
        "paid_api": False,
        "weight_download_this_slice": False,
        "gl005_proven": False,
        "law": LAWS,
    }


def council_architecture() -> dict:
    grant = load_json(GRANT)
    seat_map = load_json(SEATS)
    seats = []
    for code in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "C10"):
        if code in LIVE_SEATS:
            row = {"code": code, **LIVE_SEATS[code], "invented_this_slice": False}
        else:
            row = {
                "code": code,
                "status": "NOT_SEATED",
                "role": None,
                "invented_this_slice": False,
                "law": "C6_C10_NE_LIVE",
                "note": "Do not mint seats to look like a ten-node council. Compression first.",
            }
        seats.append(row)
    return {
        "schema": "raios.c1-c10-council-architecture.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-063",
        "ts": utc(),
        "adopted_identity": "D-032",
        "c0_abolished": True,
        "live_count": 5,
        "not_seated": ["C6", "C7", "C8", "C9", "C10"],
        "this_channel": ["C1", "C2", "C5_in_git"],
        "elsewhere": ["C3", "C4"],
        "permanent_mind": "C5 in git",
        "cursor_session_ne_c5": True,
        "tools_v1": grant.get("cognitive_tools") or [],
        "deny_c5": grant.get("deny") or [],
        "seat_map_live": seat_map.get("live") or [],
        "seats": seats,
        "second_bus": False,
        "summon_this_channel": False,
        "gl005_proven": False,
        "law": LAWS,
    }


def execution_graph(p0: dict) -> dict:
    nodes = [
        {
            "id": "Z",
            "name": "PHASE_ZERO_MAP",
            "status": "DONE_DISCOVERED",
            "keeper": "scripts/ai-os/raios_c5_phase0.py",
            "skip": False,
        },
        {
            "id": "0.1",
            "name": GATE_ORDER[0],
            "status": p0["gate1"]["status"],
            "keeper": "scripts/ai-os/raios_c5_p0.py",
            "requires": ["existing DATABASE_URL", "legitimate session"],
            "forbids": ["mint secret", "forge gl_session", "provision postgres from GET 500"],
            "skip": False,
        },
        {
            "id": "0.2",
            "name": GATE_ORDER[1],
            "status": p0["gate2"]["status"],
            "stop": p0["gate2"].get("stop_stage"),
            "requires": ["0.1 PASS", "cortex qwen3.6:35b-a3b", "Granite"],
            "forbids": ["treat student 0.5b as source", "delete weights"],
            "skip": False,
        },
        {
            "id": "0.3",
            "name": GATE_ORDER[2],
            "status": p0["gate3"]["status"],
            "requires": ["0.1 PASS", "0.2 PASS", "routing+association+execution+persistence+reuse"],
            "forbids": ["print GL005_PROVEN from CI or this stamp"],
            "skip": False,
        },
        {
            "id": "1",
            "name": "WAL_BIND_PRODUCT_EXPERIENCES",
            "status": "FORBIDDEN_UNTIL_P0",
            "lock": "A15 RAIOS/V9",
            "skip": False,
        },
        {
            "id": "2",
            "name": "GL003_UAE_NORWAY_NEXT",
            "status": "OTHER_AGENT",
            "claimed_by": "deepseek-local",
            "fill_from_this_slice": False,
        },
        {
            "id": "3",
            "name": "CRON_ON_MAIN",
            "status": "HOLD",
            "note": "c5-week.yml exists; schedule idle until main",
        },
        {
            "id": "4",
            "name": "C1_CORTEX_TREAT_RUN_THROW",
            "status": "HOLD_NE_THROW",
            "executor_ne_throw": True,
        },
    ]
    edges = [
        {"from": "Z", "to": "0.1", "skip": False},
        {"from": "0.1", "to": "0.2", "skip": False},
        {"from": "0.2", "to": "0.3", "skip": False},
        {"from": "0.3", "to": "1", "skip": False},
        {"from": "Z", "to": "2", "parallel": True, "note": "other agent; not this slice"},
        {"from": "SCALE", "to": "ALL", "constraint": list(SCALE_BY)},
    ]
    return {
        "schema": "raios.master-execution-graph.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-063",
        "ts": utc(),
        "stop": p0["stop"],
        "next": GATE_ORDER[0],
        "nodes": nodes,
        "edges": edges,
        "no_skip": True,
        "platform_proven": False,
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "law": LAWS,
    }


def research_plan(p0: dict, env: dict) -> str:
    need = load_json(NEED)
    asks = need.get("asks") or []
    now = [row for row in asks if row.get("needed_now")]
    later = [row for row in asks if not row.get("needed_now")]
    lines = [
        "# RAIOS STATE OF THE ART — RESEARCH PLAN",
        "",
        "- Decision: `D-063` (DISCOVERED, not CANONICAL).",
        "- Stamp: C2 reality audit. C5 remains in git.",
        "- Law: `SCALE_BY_COMPRESSION_NOT_COMPLEXITY`.",
        "- `GL005_PROVEN=false` `EXTRACTED_QWEN_GRANITE=false` `PLATFORM_PROVEN=false`",
        "",
        "## What state-of-the-art means here",
        "",
        "SOTA is not a paper forest and not a paid RAG stack. It is measured improvement on one live path:",
        "",
        "1. Compress knowledge (NeuroLingua + DIGESTS/INDEX, not disk fill).",
        "2. Compile experience (book cycle; experience ≠ knowledge).",
        "3. Distribute compute (existing gyms; no new cluster).",
        "4. Reuse capability (live keepers before any clone).",
        "5. Prove improvement (P0 fail-closed evidence).",
        "",
        "## Reject as research-install",
        "",
        "- LangChain / OpenAIEmbeddings / Chroma / FAISS / AnythingLLM / Dify / Flowise",
        "- Celerp / Odoo clone / AG2 / LightRAG",
        "- 93 `study_*.py` stubs",
        "- Second WAL or ninth MCP tool",
        "- Inventing C6–C10 seats",
        "- Deleting Qwen/Granite sources because CI is green",
        "",
        "## Ordered research (fail-closed, no skip)",
        "",
        f"1. **Now / 0.1** — authenticated OrchestrationTask. Gate1=`{p0['gate1']['status']}`. "
        "Need existing `DATABASE_URL` + legitimate login. Do not mint secrets.",
        f"2. **Then / 0.2** — Qwen `qwen3.6:35b-a3b` + Granite source-independent assimilation chain. "
        f"Stop=`{p0['gate2'].get('stop_stage')}`. Student `qwen2.5:0.5b` is not the source. "
        f"GPU_here=`{str(env.get('gpu')).lower()}`. `HOLD_NE_THROW`.",
        "3. **Then / 0.3** — GL-005 brain behavior: routing + association + execution + persistence + reuse.",
        "4. **Only then** — WAL-bind product experiences (A15 still locked).",
        "5. **Other agent** — GL-003 UAE/Norway Next routes. Not this Cursor slice.",
        "",
        "## Live asks already on C5-NEED",
        "",
        "### needed_now",
    ]
    for row in now or [{"kind": "none", "what": "none recorded"}]:
        lines.append(f"- `{row.get('kind')}` — {row.get('what')} (blocks `{row.get('blocks')}`)")
    lines += ["", "### later"]
    for row in later:
        lines.append(f"- `{row.get('kind')}` — {row.get('what')} (blocks `{row.get('blocks')}`)")
    lines += [
        "",
        "## External research allowed later (catalog only)",
        "",
        "- Local retrieval quality vs unloaded embeddings (already bound: inverted INDEX).",
        "- Source-independent skill transfer evaluations — only after source is present on a capable host.",
        "- Evidence-native process mining over OrchestrationTask once 0.1 PASSes.",
        "",
        "Do not download secret-repo weights. Do not pay an API. Do not treat a paper as a keeper.",
        "",
        "`NEXT=AUTHENTICATED_ORCHESTRATION_TASK`",
        "`GL005_PROVEN=false`",
        "",
    ]
    return "\n".join(lines)


def render_kv(rec: dict) -> str:
    return "\n".join(
        [
            "############################################################",
            "# RAIOS C2 WORLD-CLASS REALITY STAMP — EIGHT ARTIFACTS",
            "############################################################",
            f"HEAD={rec['head'][:12] if rec['head'] else 'unknown'}",
            "FROM=C2",
            "PARENT=C1",
            "C5=git_not_this_session",
            "DECISION=D-063",
            "SCALE_BY_COMPRESSION_NOT_COMPLEXITY=true",
            "REALITY_AUDIT_NE_NEW_KERNEL=true",
            "NAMED_ARTIFACT_NE_PLATFORM_PROVEN=true",
            "FROM_INVENTORY_NE_TO_PLATFORM=true",
            "C6_C10_NE_LIVE=true",
            "PLATFORM_PROVEN=false",
            "AUTHENTICATED_ORCHESTRATION_TASK=false",
            "EXTRACTED_QWEN_GRANITE=false",
            "SAFE_TO_REMOVE_SOURCE=false",
            "GL005_PROVEN=false",
            "WAL_WRITTEN=false",
            "NEW_KERNEL=false",
            f"ARTIFACTS={','.join(ARTIFACTS)}",
            f"STOP={rec['stop']}",
            f"NEXT={rec['next']}",
            "############################################################",
            "",
        ]
    )


def stamp() -> dict:
    wal_before = wal_mtime()
    foundation = load_foundation()
    p0 = p0_stamp()
    env = host()
    keepers = keepers_inventory()
    probes = probe_routes(
        (
            "/api/auth/session",
            "/api/tasks",
            "/api/products",
            "/api/brains/greeny-life-egypt",
            "/api/brains/greens-nature-uae",
            "/api/brains/green-lines-norway-eu",
            "/api/intelligence/data-fabric",
            "/api/suppliers",
            "/api/sales-orders",
        )
    )
    compact_p0 = {
        "stop": p0["stop"],
        "gate1": {
            "status": p0["gate1"]["status"],
            "classification": p0["gate1"].get("classification"),
            "session": p0["gate1"]["session"],
            "before": p0["gate1"]["before"],
            "unauthenticated_post": p0["gate1"]["unauthenticated_post"],
            "mock": p0["gate1"]["mock"],
            "minted_secret": p0["gate1"]["minted_secret"],
            "authenticated_orchestration_task": False,
        },
        "gate2": {
            "status": p0["gate2"]["status"],
            "stop_stage": p0["gate2"]["stop_stage"],
            "sources": p0["gate2"]["sources"],
            "extracted_qwen_granite": False,
        },
        "gate3": {"status": p0["gate3"]["status"], "gl005_proven": False},
    }
    audit = world_class_audit(compact_p0, env, probes, keepers)
    gaps = capability_matrix(compact_p0, probes, keepers)
    erp = erp_matrix(probes)
    flow = cognitive_dataflow(compact_p0)
    fabric = resource_fabric(env, compact_p0)
    council = council_architecture()
    graph = execution_graph(compact_p0)
    plan = research_plan(compact_p0, env)
    payloads = {
        ARTIFACTS[0]: audit,
        ARTIFACTS[1]: gaps,
        ARTIFACTS[2]: erp,
        ARTIFACTS[3]: flow,
        ARTIFACTS[4]: fabric,
        ARTIFACTS[6]: council,
        ARTIFACTS[7]: graph,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    written = []
    for name, payload in payloads.items():
        path = REPORTS / name
        dump_json(path, payload)
        written.append({"name": name, "path": str(path.relative_to(ROOT)), "sha256": sha256_text(path.read_text(encoding="utf-8"))})
    plan_path = REPORTS / ARTIFACTS[5]
    plan_path.write_text(plan, encoding="utf-8")
    written.insert(5, {"name": ARTIFACTS[5], "path": str(plan_path.relative_to(ROOT)), "sha256": sha256_text(plan)})
    live_c_seats = [row["code"] for row in council["seats"] if row["status"] != "NOT_SEATED"]
    rec = {
        "schema": "raios.c2-reality-stamp.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "c5": "git_not_this_session",
        "decision": "D-063",
        "foundation_decision": "D-059",
        "p0_decision": "D-060",
        "ts": utc(),
        "head": git_head(),
        "facts": foundation["facts"],
        "artifacts": written,
        "probes": probes,
        "stop": p0["stop"],
        "next": GATE_ORDER[0],
        "live_c_seats": live_c_seats,
        "c6_c10_live": False,
        "new_kernel": False,
        "platform_proven": False,
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "authenticated_orchestration_task": False,
        "wal_written": False,
        "paid_api": False,
        "law": LAWS,
        "ok": True,
    }
    rec["ok"] = (
        len(written) == 8
        and rec["gl005_proven"] is False
        and rec["extracted_qwen_granite"] is False
        and rec["platform_proven"] is False
        and rec["new_kernel"] is False
        and rec["c6_c10_live"] is False
        and rec["facts"]["GL005_PROVEN"] is False
        and council["seats"][5]["status"] == "NOT_SEATED"
        and compact_p0["gate1"]["minted_secret"] is False
        and "SCALE_BY_COMPRESSION_NOT_COMPLEXITY" in rec["law"]
    )
    rec["text"] = render_kv(rec)
    if wal_mtime() != wal_before:
        raise SystemExit("REALITY_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in rec.items() if k != "probes"}
    public["probe_classes"] = {row["path"]: row["class"] for row in probes}
    dump_json(OUT / "LAST.json", public)
    (OUT / "LAST.txt").write_text(rec["text"], encoding="utf-8")
    return rec


def main() -> int:
    rec = stamp()
    print(rec["text"], end="")
    for row in rec["artifacts"]:
        print(f"ARTIFACT={row['path']}")
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
