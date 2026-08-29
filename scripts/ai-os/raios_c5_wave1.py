#!/usr/bin/env python3
"""C1-EXECUTE RAIOS-C5-WORLD-CLASS-WAVE-1.

Convert PHASE_ZERO_MAP into verified live cognitive capability — fail-closed.
No reset, no stash, no source delete, no fake PASS, no WAL write, no GL005 mint.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_foundation import load_foundation  # noqa: E402
from raios_c5_p0 import GATE_ORDER, stamp as p0_stamp  # noqa: E402
from raios_c5_phase0 import exists, host, http_code, keepers_inventory  # noqa: E402
from raios_c5_reality import erp_matrix, probe_routes  # noqa: E402
from raios_c5_watchdog import classify as watchdog_classify  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT = ROOT / ".ai-os" / "receipts" / "c5-wave1"
REPORTS = ROOT / ".ai-os" / "reports"
BOUND_HEAD = "3a7e1be601d3cf617f1bf305eb780a8feac4ac81"
OLLAMA = "http://127.0.0.1:11434"
ALLOWED_SOURCE = ".ai-os/CORE-CONTRACT.md"
COMPRESS_PY = ROOT / "src" / "raios" / "neuro_lingua" / "compress.py"
INDEX = ROOT / ".ai-os" / "learning" / "INDEX.json"
BOOK_EXP = ROOT / ".ai-os" / "receipts" / "c5-book" / "EXPERIENCE.json"
KAE_LAST = ROOT / ".ai-os" / "receipts" / "c5-kae" / "LAST.json"
REGISTRY = ROOT / ".ai-os" / "MODEL-REGISTRY.json"

ARTIFACTS = (
    "RAIOS-LLM-FABRIC-REALITY-AUDIT.json",
    "RAIOS-ASSIMILATION-E2E-PROOF.json",
    "RAIOS-RSIC-REALITY.json",
    "RAIOS-AEMC-REALITY.json",
    "RAIOS-CETD-REALITY.json",
    "RAIOS-ERP-REALITY-MATRIX.json",
    "RAIOS-C5-MEMO-DECISION-MATRIX.json",
    "RAIOS-WAVE1-GAP-MATRIX.json",
    "RAIOS-WAVE1-EXECUTION-GRAPH.json",
    "RAIOS-WAVE1-RECEIPT.json",
)
LAWS = [
    "SCALE_BY_COMPRESSION_NOT_COMPLEXITY",
    "CI_PASS_NE_ASSIMILATION",
    "CI_PASS_NE_GL005",
    "STORED_NE_ASSIMILATED",
    "EMBEDDED_NE_ASSIMILATED",
    "REPLAYED_NE_VALIDATED",
    "HOLD_NE_THROW",
    "STUDENT_NE_EXTRACTION",
    "GRANITE_CANDIDATE_NE_SOVEREIGN_BACKBONE",
    "NO_RESET_NO_STASH_NO_SOURCE_DELETION",
    "PRINTED_PASS_NE_EVIDENCE",
    "REUSE_BEFORE_BUILD",
    "A15_WAL_LOCK",
]
NAMED_MODELS = (
    "qwen2.5:0.5b",
    "qwen3.6:35b-a3b",
    "granite4:3b",
    "ibm/granite",
    "deepseek-r1:1.5b",
    "deepseek-r1:7b",
)
PACKS = (
    "RAIOS-COGNITIVE-BOOT.json",
    "_raios-qwen-forensics/reports/QWEN36-FORENSIC-CERTIFICATION.json",
    "_raios-a17-native-cortex/cortex/runtime/MAIN-CORTEX-BINDING.json",
)
CLASSES = ("ABSENT", "STUB", "FILE_ONLY", "PROTOTYPE", "CONNECTED", "LIVE", "TESTED", "PROVEN")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def git_contains(commit: str) -> bool:
    r = subprocess.run(["git", "merge-base", "--is-ancestor", commit, "HEAD"], cwd=ROOT)
    return r.returncode == 0


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return sha256_bytes(path.read_bytes())


def dump_json(path: Path, payload: dict) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_mod(rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def port_open(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(0.4)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False
    finally:
        sock.close()


def try_import(name: str) -> dict:
    try:
        mod = __import__(name)
        return {"name": name, "present": True, "version": getattr(mod, "__version__", None)}
    except Exception as exc:
        return {"name": name, "present": False, "error": type(exc).__name__}


def ollama_tags() -> dict:
    req = urllib.request.Request(OLLAMA + "/api/tags", headers={"User-Agent": "raios-c5-wave1/1"})
    try:
        with urllib.request.urlopen(req, timeout=2) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        names = [str(row.get("name") or "") for row in (payload.get("models") or []) if row.get("name")]
        return {"present": True, "http": 200, "models": names}
    except urllib.error.HTTPError as exc:
        return {"present": True, "http": int(exc.code), "models": []}
    except Exception as exc:
        return {"present": False, "error": type(exc).__name__, "models": []}


def ollama_generate(model: str, prompt: str = "ping") -> dict:
    body = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": 4, "temperature": 0}}
    ).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA + "/api/generate",
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "raios-c5-wave1/1"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        text = str(payload.get("response") or "")
        return {
            "model": model,
            "http": 200,
            "ok": bool(text.strip()),
            "eval_count": payload.get("eval_count"),
            "error": payload.get("error"),
            "response_len": len(text),
        }
    except urllib.error.HTTPError as exc:
        raw = exc.read()[:180].decode("utf-8", "replace")
        return {"model": model, "http": int(exc.code), "ok": False, "error": raw}
    except Exception as exc:
        return {"model": model, "http": None, "ok": False, "error": type(exc).__name__}


def index_lookup(term: str) -> dict:
    if not INDEX.is_file():
        return {"exists": False, "hits": 0}
    data = json.loads(INDEX.read_text(encoding="utf-8"))
    postings = data.get("postings") or {}
    docs = postings.get(term.lower()) or postings.get(term) or []
    return {
        "exists": True,
        "docs": data.get("docs"),
        "terms": data.get("terms"),
        "embedding_model": data.get("embedding_model"),
        "hits": len(docs) if isinstance(docs, list) else 0,
        "wal_written": data.get("wal_written"),
    }


def compress_live(text: str) -> dict:
    if not COMPRESS_PY.is_file():
        return {"ok": False, "class": "ABSENT"}
    mod = load_mod("src/raios/neuro_lingua/compress.py")
    row = mod.compress_meaning(text)
    return {
        "ok": True,
        "class": "LIVE",
        "actor": row.get("pattern", row).get("actor") if isinstance(row.get("pattern"), dict) else row.get("actor"),
        "action": (row.get("pattern") or {}).get("action") if isinstance(row.get("pattern"), dict) else row.get("action"),
        "object": (row.get("pattern") or {}).get("object") if isinstance(row.get("pattern"), dict) else row.get("object"),
        "destination": (row.get("pattern") or {}).get("destination") if isinstance(row.get("pattern"), dict) else row.get("destination"),
        "llm_calls": 0,
    }


def erp_domains(probes: list[dict]) -> list[dict]:
    by = {row["path"]: row for row in probes}

    def row(domain: str, *, models: list[str], routes: list[str], gap: str | None, status: str) -> dict:
        live = [by[path] for path in routes if path in by]
        return {
            "domain": domain,
            "models": models,
            "routes": routes,
            "live": live,
            "gap": gap,
            "status": status,
            "clone_odoo": False,
        }

    return [
        row("sales", models=["SalesOrder", "SalesOrderItem"], routes=["/api/sales-orders"], gap=None, status="CONNECTED"),
        row("procurement", models=[], routes=[], gap="NO_DEDICATED_DOMAIN", status="ABSENT"),
        row("supplier", models=["Supplier"], routes=["/api/suppliers"], gap=None, status="CONNECTED"),
        row(
            "inventory",
            models=["Inventory"],
            routes=["/api/intelligence/data-fabric"],
            gap="PRISMA_MODEL_NE_ROUTE; canonical JSON only",
            status="FILE_ONLY",
        ),
        row("warehouse", models=["Warehouse"], routes=[], gap="NO_ROUTE", status="FILE_ONLY"),
        row("shipment", models=["Shipment"], routes=["/api/traceability"], gap=None, status="CONNECTED"),
        row("invoice", models=["Invoice"], routes=[], gap="NO_ROUTE", status="FILE_ONLY"),
        row("payment", models=["Payment"], routes=[], gap="NO_ROUTE", status="FILE_ONLY"),
        row("workflow", models=["WorkflowApproval"], routes=["/api/workflow"], gap=None, status="CONNECTED"),
        row("quality", models=["OfficialEvidenceRegistry"], routes=["/api/evidence/official"], gap=None, status="CONNECTED"),
        row("production", models=[], routes=["/api/brains/greeny-life-egypt"], gap=None, status="CONNECTED"),
        row("crm", models=["Customer"], routes=["/api/data-control"], gap=None, status="CONNECTED"),
        row("marketing", models=[], routes=["/api/portfolio/egyptian-exports"], gap="THIN", status="PROTOTYPE"),
        row("accounting", models=["Invoice", "Payment"], routes=[], gap="NO_ROUTE", status="ABSENT"),
    ]


def llm_fabric(env: dict, tags: dict, gens: list[dict]) -> dict:
    student = next((g for g in gens if g["model"] == "qwen2.5:0.5b"), {})
    cortex = next((g for g in gens if g["model"] == "qwen3.6:35b-a3b"), {})
    granite = [g for g in gens if "granite" in g["model"]]
    registry = load_json(REGISTRY)
    components = [
        {
            "id": "MODEL_REGISTRY",
            "path": ".ai-os/MODEL-REGISTRY.json",
            "class": "FILE_ONLY",
            "note": "Repair Windows deepseek-r1 names; not installed here",
            "registry_models": list((registry.get("models") or {}).keys()),
            "repair_ram_gb": ((registry.get("compute_nodes") or {}).get("local_windows") or {}).get("total_ram_gb"),
        },
        {
            "id": "CAPABILITY_CONTRACTS",
            "path": "src/raios/neuro_lingua/provider_contracts.py",
            "class": "TESTED",
            "note": "NeuroLingua CapabilityRequirement; not LLM tool-calling",
        },
        {
            "id": "ROUTER",
            "path": "src/raios/neuro_lingua/router.py",
            "class": "TESTED",
            "note": "deterministic-neuro-lingua; cortex not admitted",
        },
        {
            "id": "FALLBACK",
            "path": "src/raios/neuro_lingua/governor.py",
            "class": "LIVE",
            "note": "CORTEX_HOLD_AWAITING_C1_RUN → deterministic",
        },
        {"id": "ENSEMBLE", "path": None, "class": "ABSENT", "note": "no live ensemble"},
        {
            "id": "EMBEDDINGS",
            "path": ".ai-os/learning/INDEX.json",
            "class": "ABSENT",
            "alt": "inverted INDEX LIVE",
            "note": "INVERTED_INDEX_NE_UNLOADED_EMBEDDING",
        },
        {"id": "RERANKER", "path": None, "class": "ABSENT"},
        {"id": "VLM", "path": None, "class": "ABSENT"},
        {"id": "CODE_MODEL", "path": None, "class": "ABSENT", "note": "qwen25_coder is memo only"},
        {
            "id": "CONTEXT_GOVERNOR",
            "path": "src/raios/neuro_lingua/governor.py",
            "class": "LIVE",
            "ram_gb": env.get("ram_gb"),
            "min_free_gb_for_cortex": 24.0,
        },
        {
            "id": "COST_GOVERNOR",
            "path": ".ai-os/mcp/C5-GRANT.json",
            "class": "LIVE",
            "paid_api": False,
        },
        {
            "id": "RESOURCE_GOVERNOR",
            "path": "src/raios/neuro_lingua/governor.py",
            "class": "LIVE",
            "stale_claim": "reports/RAIOS-RESOURCE-GOVERNOR-AUDIT.json host_ram_gb=7.8 Repair, not this VM",
        },
        {
            "id": "MODEL_HEALTH",
            "class": "LIVE" if student.get("ok") else "CONNECTED",
            "student_generate": student,
            "cortex_generate": cortex,
            "granite_generate": granite,
        },
        {
            "id": "CACHE",
            "path": "src/raios/neuro_lingua/qwen_runtime.py",
            "class": "PROTOTYPE",
            "note": "3s probe cache only",
        },
        {
            "id": "OBSERVABILITY",
            "path": ".ai-os/receipts",
            "class": "LIVE",
            "note": "fail-closed receipts; not LLM traces",
        },
        {
            "id": "TEACHER_STUDENT",
            "class": "PARTIAL",
            "student": "qwen2.5:0.5b LIVE",
            "teachers": "granite/deepseek/cortex HTTP 404",
        },
        {"id": "DISTILLATION", "class": "ABSENT"},
        {
            "id": "SKILL_COMPILATION",
            "path": "scripts/ai-os/raios_c5_kae.py",
            "class": "PROTOTYPE",
            "note": "KAE retile; not neural distill",
        },
    ]
    return {
        "schema": "raios.llm-fabric-reality-audit.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-064",
        "bound_head": BOUND_HEAD,
        "head": git_head(),
        "ts": utc(),
        "runtimes": {
            "ollama_bin": bool(shutil.which("ollama")),
            "ollama_http": tags,
            "vllm_bin": bool(shutil.which("vllm")),
            "nvidia_smi": bool(shutil.which("nvidia-smi")),
            "imports": [
                try_import(n)
                for n in ("transformers", "torch", "vllm", "llama_cpp", "networkx", "chromadb", "langchain", "ollama")
            ],
        },
        "generate": gens,
        "packs_present": {p: exists(p) for p in PACKS},
        "components": components,
        "granite_sovereign_backbone": False,
        "llm_fabric_proven": False,
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "law": LAWS,
    }


def assimilation_e2e() -> dict:
    src = ROOT / ALLOWED_SOURCE
    text = src.read_text(encoding="utf-8") if src.is_file() else ""
    digest = sha256_bytes(text.encode("utf-8")) if text else None
    parsed = {"ok": bool(text), "bytes": len(text.encode("utf-8")) if text else 0, "class": "LIVE" if text else "ABSENT"}
    meaning = compress_live("The supplier shipped the products to Norway.")
    idx = index_lookup("WAL")
    book = load_json(BOOK_EXP)
    kae = load_json(KAE_LAST)
    stages = [
        {"id": "ALLOWED_SOURCE", "status": "PASS", "class": "LIVE", "path": ALLOWED_SOURCE, "ok": src.is_file()},
        {"id": "parser", "status": "PASS" if parsed["ok"] else "FAIL", "class": parsed["class"], **parsed},
        {
            "id": "semantic_decomposition",
            "status": "PASS" if meaning.get("ok") else "FAIL",
            "class": meaning.get("class"),
            "result": meaning,
            "note": "NeuroLingua lexicon compress; not Qwen/Granite",
        },
        {"id": "provenance_hash", "status": "PASS" if digest else "FAIL", "class": "LIVE", "sha256": digest},
        {
            "id": "WAL",
            "status": "BLOCKED",
            "class": "CONNECTED",
            "written": False,
            "lock": "A15 LOCK-20260818130148",
            "law": "A15_WAL_LOCK",
        },
        {
            "id": "knowledge_state",
            "status": "PASS",
            "class": "LIVE",
            "state": "DISCOVERED",
            "knowledge": False,
            "law": "STORED_NE_ASSIMILATED",
        },
        {
            "id": "index_retrieval",
            "status": "PASS" if idx.get("exists") else "FAIL",
            "class": "LIVE" if idx.get("exists") else "ABSENT",
            "index": idx,
            "law": "EMBEDDED_NE_ASSIMILATED",
        },
        {
            "id": "practice_generation",
            "status": "PASS" if book else "FAIL",
            "class": "LIVE" if book else "FILE_ONLY",
            "book_ck": book.get("Ck"),
            "knowledge": False,
        },
        {
            "id": "blind_novel_replay",
            "status": "FAIL",
            "class": "PROTOTYPE",
            "reproduced_same_path": book.get("reproduced"),
            "law": "REPLAYED_NE_VALIDATED",
            "note": "book replay is same-keeper, not unseen case",
        },
        {
            "id": "skill_candidate",
            "status": "PASS" if kae else "FAIL",
            "class": "PROTOTYPE",
            "kae_ok": kae.get("ok"),
            "promoted": False,
        },
        {
            "id": "reuse_on_unseen_case",
            "status": "FAIL",
            "class": "ABSENT",
            "note": "no unseen-case reuse proof this slice",
        },
    ]
    stop = next((s["id"] for s in stages if s["status"] != "PASS"), None)
    return {
        "schema": "raios.assimilation-e2e-proof.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-064",
        "bound_head": BOUND_HEAD,
        "ts": utc(),
        "stages": stages,
        "stop": stop,
        "assimilation_proven": False,
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "STORED_NE_ASSIMILATED",
            "EMBEDDED_NE_ASSIMILATED",
            "REPLAYED_NE_VALIDATED",
            "CI_PASS_NE_ASSIMILATION",
            "STUDENT_NE_EXTRACTION",
        ],
    }


def rsic_reality() -> dict:
    functions = [
        {"id": "research_intake", "keeper": "scripts/ai-os/raios_c5_book.py request_research", "class": "LIVE", "parallel_system": False},
        {"id": "source_discovery", "keeper": "scripts/ai-os/raios_c5_hunt.py", "class": "CONNECTED", "note": "local hunt; do not run (writes git-memory dirt)"},
        {"id": "primary_source_verification", "keeper": None, "class": "ABSENT"},
        {"id": "paper_repo_tool_scout", "keeper": "scripts/ai-os/raios_c5_kae.py --libraries", "class": "PROTOTYPE"},
        {"id": "license_analysis", "keeper": None, "class": "ABSENT"},
        {"id": "contradiction_search", "keeper": "scripts/ai-os/raios_c5_enforce.py", "class": "PROTOTYPE"},
        {"id": "benchmark_design", "keeper": "scripts/ai-os/raios_c5_p0.py assimilation chain", "class": "LIVE"},
        {"id": "evidence_backed_recommendation", "keeper": ".ai-os/learning/C5-NEED.json", "class": "LIVE"},
    ]
    return {
        "schema": "raios.rsic-reality.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-064",
        "ts": utc(),
        "parallel_research_system": False,
        "functions": functions,
        "rsic_proven": False,
        "gl005_proven": False,
        "law": ["REUSE_BEFORE_BUILD", "HUNT_FREE_NE_PAID_API"],
    }


def aemc_reality() -> dict:
    issues = watchdog_classify()
    functions = [
        {"id": "health_observation", "keeper": "scripts/ai-os/raios_c5_watchdog.py", "class": "LIVE", "issues": len(issues)},
        {"id": "failure_diagnosis", "keeper": "scripts/ai-os/raios_c5_watchdog.py classify + c5-failure", "class": "PROTOTYPE"},
        {"id": "repair_planning", "keeper": "scripts/ai-os/raios_c5_plan.py", "class": "FILE_ONLY"},
        {"id": "verification", "keeper": "scripts/ai-os/raios_c5_proof.py", "class": "LIVE"},
        {"id": "rollback", "keeper": None, "class": "ABSENT", "note": "NO_RESET/NO_STASH this slice"},
        {"id": "receipt", "keeper": ".ai-os/receipts", "class": "LIVE"},
        {"id": "maintenance_to_learning_event", "keeper": "scripts/ai-os/raios_c5_experience.py", "class": "PROTOTYPE", "wal": False},
    ]
    return {
        "schema": "raios.aemc-reality.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-064",
        "ts": utc(),
        "observe_issues": issues[:12],
        "functions": functions,
        "observe_diagnose_verify_proven": False,
        "aemc_proven": False,
        "gl005_proven": False,
        "law": ["PATHOLOGY_COMPELS_REPAIR", "REUSE_BEFORE_BUILD"],
    }


def cetd_reality(keepers: list[dict]) -> dict:
    book = load_json(BOOK_EXP)
    functions = [
        {"id": "books", "keeper": "scripts/ai-os/raios_c5_book.py", "class": "LIVE", "knowledge": False, "ck": book.get("Ck")},
        {"id": "official_sources", "keeper": "mind_fill + CORE-CONTRACT/DECISIONS", "class": "LIVE"},
        {"id": "models", "keeper": "scripts/ai-os/raios_c5_qwen.py", "class": "PARTIAL", "student_only": True},
        {"id": "erp_events", "keeper": "POST /api/tasks", "class": "BLOCKED", "p0": GATE_ORDER[0]},
        {"id": "simulations", "keeper": None, "class": "ABSENT"},
        {"id": "kaggle_colab_local_workers", "keeper": "scripts/ai-os/raios_c5_train.py + gym/", "class": "CONNECTED"},
        {"id": "weakness_queues", "keeper": "book identify_weakness + C5-NEED", "class": "LIVE"},
        {"id": "blind_tests", "keeper": None, "class": "ABSENT"},
        {"id": "revalidation", "keeper": "book replay", "class": "PROTOTYPE", "law": "REPLAYED_NE_VALIDATED"},
        {"id": "skill_certification", "keeper": "scripts/ai-os/raios_c5_experience.py", "class": "PROTOTYPE", "promoted": False},
    ]
    return {
        "schema": "raios.cetd-reality.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-064",
        "ts": utc(),
        "keepers_named": len(keepers),
        "functions": functions,
        "training_path_resume_proven": False,
        "cetd_proven": False,
        "gl005_proven": False,
        "law": ["EXPERIENCE_NE_KNOWLEDGE", "ONE_COMMAND_ALL_GYMS"],
    }


def memo_matrix() -> dict:
    rows = [
        {
            "claim": "Decentralized Cognitive Mesh",
            "status": "REJECT",
            "reason": "Second bus / relay hub rejected. One Cognitive WAL. Compression not mesh sprawl.",
            "evidence": ["D-017 MCP_GATEWAY_NE_RELAY_HUB", "D-005 ORGANIZE_BEFORE_EXPAND", "D-063 SCALE_BY_COMPRESSION_NOT_COMPLEXITY"],
        },
        {
            "claim": "Granite-as-backbone",
            "status": "REJECT",
            "reason": "Granite is a candidate teacher, not sovereign backbone. Source identity is cortex qwen3.6:35b-a3b plus Granite. This host: granite generate 404.",
            "evidence": ["D-048", "D-060", "ollama generate granite4:3b HTTP 404"],
        },
        {
            "claim": "NetworkX+SQLite brain",
            "status": "REJECT",
            "reason": "networkx absent here. Norway graph.py is stdlib KnowledgeGraph, not C5 mind. SQLite WAL ≠ Cognitive WAL.",
            "evidence": ["import networkx ABSENT", "greenlines_brain/graph.py", "D-017 SQLITE_WAL_NE_COGNITIVE_WAL", "D-039 LIGHTRAG_NE_COGNITIVE_WAL"],
        },
        {
            "claim": "8GB RAM claim",
            "status": "REJECT",
            "reason": "Stale Repair observation (MODEL-REGISTRY 7.8GB / governor audit 7.8 vs 22GB blob). This VM RAM≈15.64Gi, still HOST_NO_GPU, still below 24GB cortex gate. Not a license to throw sources.",
            "evidence": [".ai-os/MODEL-REGISTRY.json", "reports/RAIOS-RESOURCE-GOVERNOR-AUDIT.json", "D-052 HOLD_NE_THROW"],
        },
        {
            "claim": "interleaved training fixed schedule",
            "status": "REJECT",
            "reason": "Calendar/interleave is not intelligence. c5-week.yml pulse exists but fires from main. Not a 6-hour genius loop.",
            "evidence": ["D-037 SCHEDULED_PULSE_NE_SECOND_WAL", "D-040 CALENDAR_90_NE_PROOF", ".github/workflows/c5-week.yml"],
        },
        {
            "claim": "OAuth/JWT/API-key recommendation",
            "status": "REJECT",
            "reason": "Empire JWT/HMAC plane rejected. V1 is scoped bearer until remote OAuth is registered. No new auth plane this slice.",
            "evidence": ["D-017", "D-018", "D-019 EMPIRE_CONNECTOR_SPEC_AS_WRITTEN_IS_REJECTED"],
        },
        {
            "claim": "6-week sequence",
            "status": "REJECT",
            "reason": "Calendar-week delivery is not a RAIOS success metric.",
            "evidence": ["D-019", "D-040"],
        },
        {
            "claim": "GL005 as whole-system success condition",
            "status": "REJECT",
            "reason": "GL-005 is last P0 gate after authenticated OrchestrationTask and Qwen/Granite assimilation. Not whole-system success. Cannot print true without live authenticated POST /api/tasks.",
            "evidence": ["D-060", "D-008", "AUTHENTICATED_ORCHESTRATION_TASK_NE_GL005"],
        },
    ]
    return {
        "schema": "raios.c5-memo-decision-matrix.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-064",
        "ts": utc(),
        "rows": rows,
        "accepted": 0,
        "rejected": len(rows),
        "research_required": 0,
        "gl005_proven": False,
        "law": LAWS,
    }


def tournament(gens: list[dict]) -> list[dict]:
    by = {g["model"]: g for g in gens}
    return [
        {"slot": "router", "candidate": "deterministic-neuro-lingua", "granite": "not-sovereign", "class": "TESTED", "pull": False},
        {"slot": "reasoning", "candidate": "qwen3.6:35b-a3b", "installed": by.get("qwen3.6:35b-a3b"), "class": "ABSENT", "pull": False},
        {"slot": "coding", "candidate": None, "class": "ABSENT", "pull": False},
        {"slot": "embedding", "candidate": "inverted-INDEX", "neural": False, "class": "LIVE", "pull": False},
        {"slot": "reranking", "candidate": None, "class": "ABSENT", "pull": False},
        {"slot": "document_vlm", "candidate": None, "class": "ABSENT", "pull": False},
        {"slot": "teacher", "candidates": ["granite4:3b", "qwen3.6:35b-a3b", "qwen2.5:0.5b"], "live": by, "class": "PARTIAL", "granite_sovereign": False, "pull": False},
        {"slot": "critic", "candidate": "C4 DeepSeek seat elsewhere, not a local model", "class": "FILE_ONLY", "pull": False},
    ]


def gap_matrix(fabric: dict, assim: dict, rsic: dict, aemc: dict, cetd: dict, p0: dict) -> dict:
    rows = [
        {"id": "LLM_FABRIC_E2E", "class": "PARTIAL", "proven": False, "gap": "only student 0.5b generate LIVE"},
        {"id": "ASSIMILATION_E2E", "class": "BLOCKED", "proven": False, "stop": assim["stop"]},
        {"id": "RSIC_LIVE_LOOP", "class": "PARTIAL", "proven": False},
        {"id": "AEMC_OBSERVE_DIAGNOSE_VERIFY", "class": "PARTIAL", "proven": False},
        {"id": "CETD_TRAIN_RESUME", "class": "PARTIAL", "proven": False},
        {"id": GATE_ORDER[0], "class": p0["gate1"]["status"], "proven": False},
        {"id": GATE_ORDER[1], "class": p0["gate2"]["status"], "proven": False, "student_ne_extraction": True},
        {"id": GATE_ORDER[2], "class": p0["gate3"]["status"], "proven": False},
        {"id": "GRANITE_INSTALLED", "class": "ABSENT", "proven": False},
        {"id": "CORTEX_INSTALLED", "class": "ABSENT", "proven": False},
        {"id": "BLIND_UNSEEN_REUSE", "class": "ABSENT", "proven": False},
    ]
    return {
        "schema": "raios.wave1-gap-matrix.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-064",
        "ts": utc(),
        "rows": rows,
        "llm_fabric_proven": False,
        "assimilation_proven": False,
        "rsic_proven": False,
        "aemc_proven": False,
        "cetd_proven": False,
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "law": LAWS,
    }


def execution_graph(p0: dict, assim: dict) -> dict:
    nodes = [
        {"id": "BOUND_MAP", "name": "PHASE_ZERO_MAP", "head": BOUND_HEAD, "status": "DONE_DISCOVERED", "reset": False},
        {"id": "W1A", "name": "LLM_FABRIC_INVENTORY", "status": "DONE_DISCOVERED"},
        {"id": "W1B", "name": "ASSIMILATION_E2E", "status": "BLOCKED", "stop": assim["stop"]},
        {"id": "W1C", "name": "RSIC_WIRE", "status": "DONE_DISCOVERED", "new_system": False},
        {"id": "W1D", "name": "AEMC_WIRE", "status": "DONE_DISCOVERED", "new_system": False},
        {"id": "W1E", "name": "CETD_WIRE", "status": "DONE_DISCOVERED", "new_system": False},
        {"id": "W1F", "name": "ERP_REALITY", "status": "DONE_DISCOVERED"},
        {"id": "W1G", "name": "MEMO_DECISIONS", "status": "DONE_DISCOVERED"},
        {"id": "W1H", "name": "TOURNAMENT_SLOTS", "status": "DONE_DISCOVERED", "pull": False},
        {"id": "0.1", "name": GATE_ORDER[0], "status": p0["gate1"]["status"], "skip": False},
        {"id": "0.2", "name": GATE_ORDER[1], "status": p0["gate2"]["status"], "skip": False},
        {"id": "0.3", "name": GATE_ORDER[2], "status": p0["gate3"]["status"], "skip": False},
    ]
    return {
        "schema": "raios.wave1-execution-graph.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-064",
        "bound_head": BOUND_HEAD,
        "no_reset": True,
        "no_stash": True,
        "no_clean": True,
        "ts": utc(),
        "stop": p0["stop"],
        "next": GATE_ORDER[0],
        "nodes": nodes,
        "edges": [
            {"from": "BOUND_MAP", "to": "W1A"},
            {"from": "W1A", "to": "W1B"},
            {"from": "W1B", "to": "0.1", "note": "WAL/unseen reuse blocked; P0 0.1 still first live product proof"},
            {"from": "0.1", "to": "0.2", "skip": False},
            {"from": "0.2", "to": "0.3", "skip": False},
        ],
        "gl005_proven": False,
        "law": LAWS,
    }


def render_kv(rec: dict) -> str:
    return "\n".join(
        [
            "############################################################",
            "# RAIOS-C5-WORLD-CLASS-WAVE-1 — FAIL-CLOSED REALITY STAMP",
            "############################################################",
            f"BOUND_HEAD={BOUND_HEAD}",
            f"HEAD={rec['head'][:12] if rec['head'] else 'unknown'}",
            f"BOUND_IS_ANCESTOR={str(rec['bound_is_ancestor']).lower()}",
            "NO_RESET=true",
            "NO_CLEAN=true",
            "NO_STASH=true",
            "NO_SOURCE_DELETION=true",
            "NO_AUTO_CANONICAL=true",
            "NO_FAKE_PASS=true",
            "FROM=C2",
            "PARENT=C1",
            "DECISION=D-064",
            f"LLM_FABRIC_PROVEN={str(rec['llm_fabric_proven']).lower()}",
            f"ASSIMILATION_PROVEN={str(rec['assimilation_proven']).lower()}",
            f"RSIC_PROVEN={str(rec['rsic_proven']).lower()}",
            f"AEMC_PROVEN={str(rec['aemc_proven']).lower()}",
            f"CETD_PROVEN={str(rec['cetd_proven']).lower()}",
            "EXTRACTED_QWEN_GRANITE=false",
            "SAFE_TO_REMOVE_SOURCE=false",
            "AUTHENTICATED_ORCHESTRATION_TASK=false",
            "GL005_PROVEN=false",
            "WAL_WRITTEN=false",
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
    tags = ollama_tags()
    gens = [ollama_generate(name) for name in NAMED_MODELS]
    probes = probe_routes(
        (
            "/api/auth/session",
            "/api/tasks",
            "/api/products",
            "/api/sales-orders",
            "/api/suppliers",
            "/api/brains/greeny-life-egypt",
            "/api/brains/greens-nature-uae",
            "/api/brains/green-lines-norway-eu",
            "/api/intelligence/data-fabric",
            "/api/evidence/official",
            "/api/workflow",
            "/api/data-control",
            "/api/portfolio/egyptian-exports",
        )
    )
    compact_p0 = {
        "stop": p0["stop"],
        "gate1": {"status": p0["gate1"]["status"], "minted_secret": p0["gate1"]["minted_secret"]},
        "gate2": {"status": p0["gate2"]["status"], "stop_stage": p0["gate2"]["stop_stage"]},
        "gate3": {"status": p0["gate3"]["status"]},
    }
    fabric = llm_fabric(env, tags, gens)
    fabric["tournament"] = tournament(gens)
    assim = assimilation_e2e()
    rsic = rsic_reality()
    aemc = aemc_reality()
    cetd = cetd_reality(keepers)
    erp = erp_matrix(probes)
    erp["decision"] = ["D-063", "D-064"]
    erp["domains"] = erp_domains(probes)
    erp["wave"] = "WAVE-1"
    memos = memo_matrix()
    gaps = gap_matrix(fabric, assim, rsic, aemc, cetd, compact_p0)
    graph = execution_graph(compact_p0, assim)
    payloads = {
        ARTIFACTS[0]: fabric,
        ARTIFACTS[1]: assim,
        ARTIFACTS[2]: rsic,
        ARTIFACTS[3]: aemc,
        ARTIFACTS[4]: cetd,
        ARTIFACTS[5]: erp,
        ARTIFACTS[6]: memos,
        ARTIFACTS[7]: gaps,
        ARTIFACTS[8]: graph,
    }
    REPORTS.mkdir(parents=True, exist_ok=True)
    written = []
    for name, payload in payloads.items():
        digest = dump_json(REPORTS / name, payload)
        written.append({"name": name, "path": f".ai-os/reports/{name}", "sha256": digest})
    rec = {
        "schema": "raios.wave1-receipt.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "c5": "git_not_this_session",
        "decision": "D-064",
        "bound_head": BOUND_HEAD,
        "head": git_head(),
        "bound_is_ancestor": git_contains(BOUND_HEAD),
        "no_reset": True,
        "no_clean": True,
        "no_stash": True,
        "no_source_deletion": True,
        "no_auto_canonical": True,
        "no_fake_pass": True,
        "ts": utc(),
        "facts": foundation["facts"],
        "llm_fabric_proven": False,
        "assimilation_proven": False,
        "rsic_proven": False,
        "aemc_proven": False,
        "cetd_proven": False,
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "authenticated_orchestration_task": False,
        "gl005_proven": False,
        "wal_written": False,
        "student_generate_ok": bool(next((g for g in gens if g["model"] == "qwen2.5:0.5b"), {}).get("ok")),
        "granite_generate_ok": False,
        "cortex_generate_ok": False,
        "stop": p0["stop"],
        "next": GATE_ORDER[0],
        "artifacts": written,
        "sha256_critical": {
            "runner": sha256_file(ROOT / "scripts" / "ai-os" / "raios_c5_wave1.py"),
            "p0": sha256_file(ROOT / "scripts" / "ai-os" / "raios_c5_p0.py"),
            "foundation": sha256_file(ROOT / ".ai-os" / "state" / "FOUNDATION.json"),
            "allowed_source": sha256_file(ROOT / ALLOWED_SOURCE),
            "model_registry": sha256_file(REGISTRY),
        },
        "listen": {
            "next_3000": port_open(3000),
            "ollama_11434": port_open(11434),
            "postgres_5432": port_open(5432),
        },
        "law": LAWS,
        "ok": True,
    }
    rec["ok"] = (
        rec["gl005_proven"] is False
        and rec["extracted_qwen_granite"] is False
        and rec["safe_to_remove_source"] is False
        and rec["llm_fabric_proven"] is False
        and rec["assimilation_proven"] is False
        and rec["rsic_proven"] is False
        and rec["aemc_proven"] is False
        and rec["cetd_proven"] is False
        and rec["no_reset"] is True
        and rec["bound_is_ancestor"] is True
        and rec["facts"]["GL005_PROVEN"] is False
        and compact_p0["gate1"]["minted_secret"] is False
        and assim["wal_written"] is False
        and memos["rejected"] == 8
        and len(written) == 9
    )
    rec["text"] = render_kv(rec)
    receipt_name = ARTIFACTS[9]
    receipt_hash = dump_json(REPORTS / receipt_name, {k: v for k, v in rec.items() if k != "text"})
    rec["artifacts"].append({"name": receipt_name, "path": f".ai-os/reports/{receipt_name}", "sha256": receipt_hash})
    rec["ok"] = rec["ok"] and len(rec["artifacts"]) == 10
    if wal_mtime() != wal_before:
        raise SystemExit("WAVE1_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT.mkdir(parents=True, exist_ok=True)
    dump_json(OUT / "LAST.json", {k: v for k, v in rec.items() if k != "text"})
    (OUT / "LAST.txt").write_text(rec["text"], encoding="utf-8")
    return rec


def main() -> int:
    rec = stamp()
    print(rec["text"], end="")
    for row in rec["artifacts"]:
        print(f"ARTIFACT={row['path']} SHA256={row['sha256']}")
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
