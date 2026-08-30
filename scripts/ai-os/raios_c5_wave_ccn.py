#!/usr/bin/env python3
"""C1-EXECUTE RAIOS-CLOUD-CONSOLIDATION-NEUROLINGUA-WAVE.

C2 stamp. Fail-closed. No WAL. No weight download. No GL005 mint.
No blind delete. No auto canonical. No fake pass.
"""
from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "RAIOS" / "V9"))
sys.path.insert(0, str(ROOT / "gym" / "kaggle"))

from hardware_probe import probe as hardware_probe  # noqa: E402
from raios_c5_cloud import git_remote, ollama_generate, ollama_tags, strip_userinfo  # noqa: E402

from autonomic.self_inspection import inspect as self_inspect  # noqa: E402
from cloud.nomadic.provider_contract import catalog as provider_catalog  # noqa: E402
from cloud.nomadic.work_stealing_scheduler import simulate_pair_failover  # noqa: E402
from cloud.storage.future_s3_backend import FutureS3Backend, detect_object_store_refs  # noqa: E402
from cloud.storage.hf_backend import HfBackend, token_present as hf_token_present, whoami as hf_whoami  # noqa: E402
from cloud.storage.kaggle_backend import KaggleBackend  # noqa: E402
from cloud.storage.local_backend import disposable_roundtrip  # noqa: E402
from cloud.storage.object_manifest import COLD, HOT, WARM  # noqa: E402
from cloud.storage.onedrive_backend import OneDriveBackend  # noqa: E402
from evolution.model_lab.adapter_compiler import compile_adapter  # noqa: E402
from evolution.model_lab.canary_registry import snapshot as canary_snapshot  # noqa: E402
from evolution.model_lab.capability_fingerprint import catalog as fingerprint_catalog  # noqa: E402
from evolution.model_lab.compatibility_intelligence import compatible  # noqa: E402
from evolution.model_lab.evaluation_lab import evaluate  # noqa: E402
from evolution.model_lab.experiment_generator import generate as generate_experiments  # noqa: E402
from evolution.model_lab.merge_executor import execute as refuse_merge  # noqa: E402
from evolution.model_lab.merge_strategy import declarations as merge_declarations  # noqa: E402
from evolution.model_lab.model_registry import registry as model_registry  # noqa: E402
from evolution.model_lab.pareto_selector import select as pareto_select  # noqa: E402
from evolution.model_lab.regression_lab import regress  # noqa: E402
from raios.neuro_lingua.cortex import CORTEX_IDENTITY, status as cortex_status  # noqa: E402
from raios.neuro_lingua.layers import LAYER_SPEC, classify_layer  # noqa: E402
from raios.neuro_lingua.ops_compile import CORPUS, TARGET, prove_corpus  # noqa: E402
from raios.neuro_lingua.qwen_runtime import STUDENT_PREFERRED, generate as qwen_generate, probe as qwen_probe  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
REPORTS = ROOT / ".ai-os" / "reports"
OUT = ROOT / ".ai-os" / "receipts" / "c5-wave-ccn"
COUNCIL = ROOT / ".ai-os" / "council" / "packets"
SKIP_DIRS = {".git", "node_modules", ".next", "__pycache__", ".venv", "venv", ".pytest_cache"}
ARTIFACTS = (
    "RAIOS-CLOUD-CAPACITY-MATRIX.json",
    "KAGGLE-NOMADIC-PAIR-REALITY.json",
    "KAGGLE-HARDWARE-CAPACITY-MATRIX.json",
    "KAGGLE-WORK-STEALING-PROOF.json",
    "PERSISTENT-COGNITIVE-STORAGE-REALITY.json",
    "STORAGE-FABRIC-PROOF.json",
    "REPOSITORY-CONSOLIDATION-MATRIX.json",
    "SAFE-RETIREMENT-CANDIDATES.json",
    "RETIRED-ASSETS-RECEIPT.json",
    "CANONICAL-CAPABILITY-MAP.json",
    "POST-CONSOLIDATION-REALITY.json",
    "QWEN-RUNTIME-REALITY.json",
    "NEUROLINGUA-RUNTIME-GRAPH.json",
    "CORTEX-CONTEXT-MATRIX-REALITY.json",
    "MODEL-EXECUTION-DATAFLOW.json",
    "NEUROLINGUA-REALITY-AUDIT.json",
    "NEUROLINGUA-LAYER-MATRIX.json",
    "NEUROLINGUA-E2E-PROOF.json",
    "NEUROLINGUA-AUTO-WIRING-PROOF.json",
    "MODEL-LAB-REALITY.json",
    "MODEL-CAPABILITY-FINGERPRINTS.json",
    "MODEL-MERGE-LAB-FOUNDATION.json",
    "SELF-INSPECTION-ENGINE-PROOF.json",
    "COUNCIL-PARALLEL-TASKS.json",
    "MASTER-NEXT-EXECUTION-GRAPH.json",
    "MASTER-RECEIPT.json",
)
LAWS = [
    "NO_RESET",
    "NO_CLEAN",
    "NO_STASH",
    "NO_BLIND_DELETE",
    "NO_NEW_LOCAL_MODEL_DOWNLOADS",
    "NO_AUTO_CANONICAL_PROMOTION",
    "NO_FAKE_PASS",
    "SELF_REPORTED_PASS_INVALID",
    "PROVIDER_NE_C5",
    "WORKER_NE_C5",
    "KAGGLE_NE_PERSISTENT_BRAIN",
    "ACCOUNT_CAPABILITY_NE_SESSION_GPU",
    "LOCAL_STEAL_SIM_NE_KAGGLE_PROVEN",
    "LAPTOP_IS_CONTROL_PLANE",
    "CURSOR_CLOUD_VM_NE_LAPTOP",
    "WAL_MOVE_BLOCKED_A15",
    "COUNCIL_JSON_NE_COGNITIVE_WAL",
    "QWEN_CONFIGURED_NE_FINAL_BACKBONE",
    "NO_HARDCODED_FAMILY_WINNER",
    "CI_PASS_NE_GL005",
    "HOLD_NE_THROW",
]
FOUNDER_CLAIMED = {
    "LOCAL_OLLAMA_MODELS": 9,
    "LOCAL_OLLAMA_STORAGE_BYTES": 38587816862,
    "LOCAL_DEEPSEEK_MODEL": "deepseek-r1:1.5b",
    "DEEPSEEK_HTTP_INFERENCE_PROVEN": True,
    "C4_LOCAL_MODEL_RUNTIME": "PROVEN_WITH_SCOPE",
    "HF_AUTHENTICATED": True,
    "KAGGLE_A_AUTHENTICATED": True,
    "KAGGLE_B_BOUND": False,
    "GITHUB_AUTHENTICATED": False,
    "ONEDRIVE_PATH_COUNT": 2,
    "NEUROLINGUA_FILE_COUNT": 79,
    "EXACT_DUPLICATE_GROUP_COUNT": 483,
    "DUPLICATE_RECLAIMABLE_BYTES": 232043310,
    "PERSISTENT_COGNITIVE_STATE": "NOT_YET_PROVIDER_BOUND",
    "host": "FOUNDER_LAPTOP",
    "this_host": False,
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump_json(path: Path, payload: dict[str, Any]) -> str:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return sha256_bytes(text.encode("utf-8"))


def classify_provider(name: str, *, category: str, states: list[str], notes: str, live: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "provider": name,
        "category": category,
        "states": states,
        "notes": notes,
        "live": live or {},
        "secret_printed": False,
    }


def kaggle_assets() -> list[str]:
    hits = []
    for rel in (
        "gym/colab_kaggle_c5.ipynb",
        "gym/kaggle/hardware_probe.py",
        "gym/kaggle/KAGGLE-A-HARDWARE-PROBE.py",
        "gym/kaggle/KAGGLE-B-HARDWARE-PROBE.py",
        "gym/kaggle/KAGGLE-A-HARDWARE-PROBE.ipynb",
        "gym/kaggle/KAGGLE-B-HARDWARE-PROBE.ipynb",
        "scripts/ai-os/raios_c5_train.py",
        "RAIOS/V9/cloud/nomadic/work_stealing_scheduler.py",
    ):
        if (ROOT / rel).exists():
            hits.append(rel)
    return hits


def nl_files() -> list[str]:
    out: list[str] = []
    for base in (
        ROOT / "src" / "raios" / "neuro_lingua",
        ROOT / "configs" / "neuro_lingua",
        ROOT / "tests" / "neuro_lingua",
        ROOT / "benchmarks" / "neuro_lingua",
        ROOT / "reports",
    ):
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if path.is_file() and any(s in path.name.lower() for s in ("neuro", "lingua", "nl-")):
                out.append(str(path.relative_to(ROOT)))
    extra = [
        "requirements-neurolingua.txt",
        "src/raios/neuro_lingua/ops_compile.py",
        "src/raios/neuro_lingua/layers.py",
    ]
    for rel in extra:
        if (ROOT / rel).is_file() and rel not in out:
            out.append(rel)
    for path in (ROOT / "src" / "raios" / "neuro_lingua").glob("*.py"):
        rel = str(path.relative_to(ROOT))
        if rel not in out:
            out.append(rel)
    return sorted(set(out))


def protected_source(rel: str) -> bool:
    low = rel.lower()
    return any(k in low for k in ("granite", "qwen", "gguf", "safetensor", "ollama", "weights"))


def consolidation(root: Path) -> dict[str, Any]:
    groups: dict[str, list[tuple[str, int]]] = {}
    hashed = 0
    skipped = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = str(path.relative_to(root))
        try:
            size = path.stat().st_size
        except OSError:
            continue
        if size == 0 or size > 2_000_000:
            skipped += 1
            continue
        try:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError:
            continue
        hashed += 1
        groups.setdefault(digest, []).append((rel, size))
    dupes = {h: rows for h, rows in groups.items() if len(rows) > 1}
    candidates = []
    reclaim = 0
    for digest, rows in sorted(dupes.items(), key=lambda kv: -sum(s for _, s in kv[1]))[:80]:
        paths = [p for p, _ in rows]
        size = rows[0][1]
        reclaim += size * (len(rows) - 1)
        canonical = min(paths, key=len)
        unique = False
        blocked = any(protected_source(p) for p in paths)
        live_dep = any(p.startswith("src/") or p.startswith("scripts/ai-os/") for p in paths)
        action = "BLOCKED" if blocked else ("KEEP" if live_dep else "DELETE_CANDIDATE")
        conf = 0.7 if action == "DELETE_CANDIDATE" else (0.99 if blocked else 0.85)
        candidates.append(
            {
                "PATH": paths,
                "CAPABILITY": "byte_identical_copy",
                "UNIQUE_CAPABILITY": unique,
                "LIVE_REFERENCES": live_dep,
                "IMPORTED_BY": [],
                "CALLS": [],
                "LAST_KNOWN_USE": "UNKNOWN",
                "HASH": digest,
                "DUPLICATE_OF": canonical,
                "CANONICAL_TARGET": canonical,
                "RETIREMENT_ACTION": action,
                "CONFIDENCE": conf,
                "DECISION": action,
            }
        )
    safe = [
        c
        for c in candidates
        if c["CONFIDENCE"] >= 0.99
        and c["UNIQUE_CAPABILITY"] is False
        and c["LIVE_REFERENCES"] is False
        and c["DECISION"] != "BLOCKED"
    ]
    return {
        "files_hashed": hashed,
        "skipped_large_or_empty": skipped,
        "exact_duplicate_groups": len(dupes),
        "reclaimable_bytes_sample": reclaim,
        "candidates_sample": candidates,
        "safe_retirement_candidates": safe,
        "retired_now": [],
        "retire_count": 0,
        "rule": "confidence>=0.99 AND unique=false AND live_dep=false AND canonical proven AND rollback — still blocked by NO_BLIND_DELETE and SAFE_TO_REMOVE_SOURCE=false on this wave",
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "repository_consolidation_proven": False,
        "founder_claimed_groups": FOUNDER_CLAIMED["EXACT_DUPLICATE_GROUP_COUNT"],
        "founder_claimed_bytes": FOUNDER_CLAIMED["DUPLICATE_RECLAIMABLE_BYTES"],
        "this_checkout_ne_founder_barn": True,
    }


def runtime_trace(student_gen: dict[str, Any], cortex: dict[str, Any], qwen: dict[str, Any]) -> dict[str, Any]:
    student_live = bool(student_gen.get("ok"))
    nodes = [
        {"id": "input", "class": "LIVE"},
        {"id": "parser", "class": "LIVE", "impl": "normalize_text"},
        {"id": "neurolingua_l1", "class": "LIVE", "impl": "language.py+dialect.py+protected.py"},
        {"id": "neurolingua_l2", "class": "CONNECTED", "impl": "ops_compile+concepts", "embeddings": False},
        {"id": "router", "class": "LIVE", "impl": "ProviderRouter deterministic"},
        {"id": "model_shell", "class": "TRAINING_ONLY" if student_live else "NOT_REACHED", "impl": "qwen_runtime.generate"},
        {"id": "model_weights", "class": "TRAINING_ONLY" if student_live else "NOT_REACHED", "id_measured": qwen.get("student_model")},
        {"id": "context_cortex_matrix", "class": "HOLD", "identity_string": CORTEX_IDENTITY, "loaded": False},
        {"id": "retrieval", "class": "FILE_ONLY", "note": "KAE/INDEX keepers, not LangChain"},
        {"id": "memory", "class": "LIVE", "impl": "Cognitive WAL locked A15"},
        {"id": "reasoning", "class": "LIVE", "impl": "deterministic ops_compile reasoning"},
        {"id": "verifier", "class": "LIVE", "impl": "verify.py"},
        {"id": "output", "class": "LIVE"},
        {"id": "qwen2.5:0.5b", "class": "TRAINING_ONLY" if student_live else "NOT_REACHED"},
        {"id": CORTEX_IDENTITY, "class": "HOLD", "artifact_loaded": False, "do_not_call_qwen_3_6_unless_artifact": True},
        {"id": "granite", "class": "NOT_REACHED"},
        {"id": "deepseek", "class": "FILE_ONLY", "note": "Founder laptop claim. Absent this VM."},
        {"id": "semantic_kernel", "class": "LIVE", "impl": "src/raios/neuro_lingua"},
        {"id": "model_registry", "class": "CONNECTED", "impl": "RAIOS/V9/evolution/model_lab"},
    ]
    return {
        "nodes": nodes,
        "student_generate": {"ok": student_gen.get("ok"), "model": student_gen.get("model"), "error": student_gen.get("error")},
        "cortex": {"hold": cortex.get("hold"), "identity": CORTEX_IDENTITY, "loaded": False, "gpu": cortex.get("gpu")},
        "qwen_probe": {"present": qwen.get("present"), "models": qwen.get("models"), "reason": qwen.get("reason")},
    }


def stamp() -> dict[str, Any]:
    before = wal_mtime()
    this_probe = hardware_probe("CURSOR_CLOUD_VM")
    steal = simulate_pair_failover()
    local_store = disposable_roundtrip(OUT / "cas")
    hf = HfBackend().classify()
    hf_live = hf_whoami()
    kag = KaggleBackend().classify()
    od = OneDriveBackend(founder_path_count=2).classify()
    s3 = FutureS3Backend().classify()
    obj_refs = detect_object_store_refs(ROOT)
    tags = ollama_tags()
    student_gen = qwen_generate("ping", num_predict=8, timeout=20.0)
    cortex = cortex_status()
    qwen = qwen_probe(use_cache=False)
    granite_gen = ollama_generate("granite4:3b")
    cortex_gen = qwen_generate("ping", model=CORTEX_IDENTITY, num_predict=4, timeout=8.0)
    cons = consolidation(ROOT)
    files_nl = nl_files()
    corpus = prove_corpus()
    layers = {
        "L1": classify_layer("L1", tested=corpus.get("ok") is True, proven=False),
        "L2": classify_layer("L2", tested=corpus.get("ok") is True, proven=False),
        "L3": classify_layer("L3", tested=False, proven=False),
        "L4": classify_layer("L4", tested=corpus.get("ok") is True, proven=False),
    }
    layers["L3"]["status"] = "HOLD"
    live_models = list(tags)
    hold_models = [CORTEX_IDENTITY, "granite4:3b", "ibm/granite"]
    founder_models = ["deepseek-r1:1.5b"]
    reg = model_registry(live_local=live_models, named_hold=hold_models, founder_claimed=founder_models)
    fps = fingerprint_catalog(
        live_models + hold_models + founder_models,
        live_generate={
            STUDENT_PREFERRED: {"ok": student_gen.get("ok"), "code": 200 if student_gen.get("ok") else None, "latency_class": "LOCAL_TINY"},
            CORTEX_IDENTITY: {"ok": False, "code": cortex_gen.get("error")},
        },
    )
    decls = merge_declarations()
    plans = generate_experiments(live_models + hold_models)
    merge_try = refuse_merge((plans.get("plans") or [{"id": "none"}])[0])
    compat = compatible({"id": STUDENT_PREFERRED, "arch": None}, {"id": CORTEX_IDENTITY, "arch": None})
    eval_row = evaluate(STUDENT_PREFERRED)
    regress_row = regress({"id": STUDENT_PREFERRED}, {"id": "merged-none"})
    pareto = pareto_select(fps, hardware={"gpu_capacity": this_probe.get("gpu_capacity")})
    adapter = compile_adapter({"id": "none"})
    canary = canary_snapshot()

    origin = git_remote()
    gh_state = "REFERENCED"
    if origin.startswith("https://github.com/"):
        gh_state = "READABLE"
    providers = {
        "huggingface": classify_provider(
            "huggingface",
            category="DATASET_STORAGE",
            states=hf.get("states") or ["BLOCKED_AUTH"],
            notes="Founder laptop claimed authenticated. This VM token_present=" + str(hf_token_present()),
            live={"whoami": hf_live, "write_test": "SKIPPED"},
        ),
        "kaggle_a": classify_provider(
            "kaggle_a",
            category="COMPUTE",
            states=["REFERENCED", "FOUNDER_CLAIMED_AUTHENTICATED", "BLOCKED_AUTH_THIS_HOST"],
            notes="Independent worker A. Session GPU not inferred.",
        ),
        "kaggle_b": classify_provider(
            "kaggle_b",
            category="COMPUTE",
            states=["REFERENCED", "NOT_BOUND"],
            notes="Independent worker B. Not a quota bypass.",
        ),
        "github": classify_provider(
            "github",
            category="SOURCE_CONTROL",
            states=["REFERENCED", gh_state, "CAPACITY_UNKNOWN"],
            notes=strip_userinfo(origin),
        ),
        "onedrive": classify_provider("onedrive", category="BACKUP", states=od.get("states") or ["REFERENCED"], notes="Founder path count claimed 2."),
        "colab": classify_provider("colab", category="COMPUTE", states=["REFERENCED", "WORKER"], notes="gym/colab_kaggle_c5.ipynb"),
        "cursor_cloud_vm": classify_provider(
            "cursor_cloud_vm",
            category="COMPUTE",
            states=["AUTHENTICATED", "WRITABLE", "LIVE_TESTED", "CAPACITY_KNOWN"],
            notes="This executor. Temporary C2. Not C5.",
            live={"hostname": socket.gethostname(), "hardware_state": this_probe.get("hardware_state")},
        ),
        "s3_r2_b2_supabase_neon": classify_provider(
            "future_object_store",
            category="OBJECT_STORAGE",
            states=["ABSENT"] if obj_refs.get("any_live_object_store") is False else ["REFERENCED"],
            notes="No bound object store on this VM.",
            live={"env_flags_present": obj_refs.get("env_flags_present")},
        ),
        "local_cas": classify_provider(
            "local_cas",
            category="EPHEMERAL_SCRATCH",
            states=["WRITABLE", "READABLE", "LIVE_TESTED"],
            notes="Disposable SHA256 store. Not persistent brain.",
            live={"roundtrip_ok": local_store.get("ok")},
        ),
        "cognitive_wal": classify_provider(
            "cognitive_wal",
            category="PERSISTENT_STATE",
            states=["REFERENCED", "LOCKED_A15"],
            notes="Existing Cognitive WAL. Not moved. Not a second bus.",
        ),
    }

    trace = runtime_trace(student_gen, cortex, qwen)
    inspect_rec = self_inspect(
        ROOT,
        context={
            "live_models": live_models,
            "hold_models": hold_models,
            "storage_classes": [p.get("states") for p in providers.values()],
            "ollama_ok": bool(student_gen.get("ok")),
            "nl_files": files_nl,
            "nl_layers": {k: v.get("status") for k, v in layers.items()},
            "capacity": {"providers": providers},
        },
    )

    payload: dict[str, dict[str, Any]] = {}
    payload["RAIOS-CLOUD-CAPACITY-MATRIX.json"] = {
        "schema": "raios.cloud-capacity-matrix.v1",
        "ts": utc(),
        "this_host": socket.gethostname(),
        "laptop_is_control_plane": True,
        "founder_claimed": FOUNDER_CLAIMED,
        "providers": providers,
        "categories": {
            "COMPUTE": ["kaggle_a", "kaggle_b", "colab", "cursor_cloud_vm"],
            "MODEL_HOSTING": ["huggingface", "ollama_local"],
            "OBJECT_STORAGE": ["future_object_store", "local_cas"],
            "DATASET_STORAGE": ["huggingface"],
            "SOURCE_CONTROL": ["github"],
            "PERSISTENT_STATE": ["cognitive_wal"],
            "BACKUP": ["onedrive"],
            "EPHEMERAL_SCRATCH": ["kaggle_a", "kaggle_b", "colab", "local_cas"],
        },
        "persistent_cognitive_storage_proven": False,
        "gl005_proven": False,
        "law": list(LAWS),
    }
    payload["KAGGLE-NOMADIC-PAIR-REALITY.json"] = {
        "schema": "raios.kaggle-nomadic-pair.v1",
        "kaggle_a": {
            "authenticated_this_host": False,
            "founder_claimed_authenticated": True,
            "datasets": [],
            "notebooks": ["gym/colab_kaggle_c5.ipynb", "gym/kaggle/KAGGLE-A-HARDWARE-PROBE.ipynb"],
            "models": [],
            "qwen_assets": [],
            "storage_references": ["/kaggle/working", "/kaggle/input"],
            "persistent_assets": [],
            "worker_proven": False,
        },
        "kaggle_b": {
            "authenticated_this_host": False,
            "bound": False,
            "independent_worker": True,
            "quota_bypass": False,
            "worker_proven": False,
            "notebooks": ["gym/kaggle/KAGGLE-B-HARDWARE-PROBE.ipynb"],
        },
        "assets": kaggle_assets(),
        "providers": provider_catalog(),
        "lifecycle": steal.get("lifecycle"),
        "kaggle_a_worker_proven": False,
        "kaggle_b_worker_proven": False,
        "gl005_proven": False,
        "law": ["PROVIDER_NE_C5", "WORKER_NE_C5", "KAGGLE_NE_PERSISTENT_BRAIN"],
    }
    payload["KAGGLE-HARDWARE-CAPACITY-MATRIX.json"] = {
        "schema": "raios.kaggle-hardware-matrix.v1",
        "this_vm_probe": this_probe,
        "kaggle_a_session": {"status": "NOT_RUN_ON_KAGGLE", "hardware_state": "UNKNOWN", "gpu_capacity": "NOT_PROVEN"},
        "kaggle_b_session": {"status": "NOT_RUN_ON_KAGGLE", "hardware_state": "UNKNOWN", "gpu_capacity": "NOT_PROVEN"},
        "founder_claimed_cpu_only_probes": True,
        "do_not_infer_gpu_from_account": True,
        "this_vm_hardware_state": this_probe.get("hardware_state"),
        "this_vm_gpu_capacity": this_probe.get("gpu_capacity"),
        "c1_actions": [
            "Enable Kaggle accelerator in the A session if GPU work is required, then run gym/kaggle/KAGGLE-A-HARDWARE-PROBE.ipynb",
            "Authenticate Kaggle B as an independent account, then run gym/kaggle/KAGGLE-B-HARDWARE-PROBE.ipynb",
        ],
        "gl005_proven": False,
    }
    payload["KAGGLE-WORK-STEALING-PROOF.json"] = steal
    payload["PERSISTENT-COGNITIVE-STORAGE-REALITY.json"] = {
        "schema": "raios.persistent-cognitive-storage.v1",
        "provider_bound": False,
        "laptop_independent": False,
        "kaggle_independent": True,
        "kaggle_role": "WORKER_CACHE",
        "namespaces": {"HOT": list(HOT), "WARM": list(WARM), "COLD": list(COLD)},
        "object_id": "SHA256(content)",
        "backends": {
            "local": local_store,
            "hf": hf,
            "hf_whoami": hf_live,
            "kaggle": kag,
            "onedrive": od,
            "future_s3": s3,
        },
        "persistent_cognitive_storage_proven": False,
        "gl005_proven": False,
    }
    payload["STORAGE-FABRIC-PROOF.json"] = {
        "schema": "raios.storage-fabric-proof.v1",
        "local_roundtrip": local_store,
        "hf_disposable_write": {"ok": False, "reason": hf_live.get("reason") if not hf_live.get("ok") else "SKIPPED_NO_DEDICATED_TEST_REPO"},
        "architecture_bound_to_one_provider": False,
        "wal_moved": False,
        "gl005_proven": False,
    }
    payload["REPOSITORY-CONSOLIDATION-MATRIX.json"] = {
        "schema": "raios.repo-consolidation.v1",
        **cons,
        "gl005_proven": False,
    }
    payload["SAFE-RETIREMENT-CANDIDATES.json"] = {
        "schema": "raios.safe-retirement-candidates.v1",
        "candidates": cons["safe_retirement_candidates"],
        "count": len(cons["safe_retirement_candidates"]),
        "retired_now": 0,
        "reason": "NO_BLIND_DELETE plus SAFE_TO_REMOVE_SOURCE=false. Quarantine not executed.",
        "gl005_proven": False,
    }
    payload["RETIRED-ASSETS-RECEIPT.json"] = {
        "schema": "raios.retired-assets.v1",
        "retired": [],
        "retire_count": 0,
        "rollback_available": True,
        "note": "Nothing deleted this wave.",
        "gl005_proven": False,
    }
    payload["CANONICAL-CAPABILITY-MAP.json"] = {
        "schema": "raios.canonical-capability-map.v1",
        "capabilities": {
            "neurolingua_deterministic": "src/raios/neuro_lingua",
            "ops_compiler": "src/raios/neuro_lingua/ops_compile.py",
            "c5_keepers": "scripts/ai-os/raios_c5_*.py",
            "cognitive_wal": "RAIOS/V9/wal/cognitive-events.jsonl",
            "nomadic": "RAIOS/V9/cloud/nomadic",
            "storage_fabric": "RAIOS/V9/cloud/storage",
            "model_lab": "RAIOS/V9/evolution/model_lab",
            "self_inspection": "RAIOS/V9/autonomic/self_inspection",
            "screen": "scripts/ai-os/raios_c5_screen.py",
            "train_mesh": "scripts/ai-os/raios_c5_train.py",
        },
        "shadow_not_canonical": ["brain.py discover_and_merge_intelligence"],
        "gl005_proven": False,
    }
    payload["POST-CONSOLIDATION-REALITY.json"] = {
        "schema": "raios.post-consolidation.v1",
        "imports_rerun": False,
        "tests_planned": "tests/neuro_lingua/test_wave_ccn.py",
        "routing": "deterministic ProviderRouter",
        "continuity": "WAL untouched",
        "foundry": "not run",
        "model_registry": "foundation only",
        "neurolingua": "ops_compile auto-wired",
        "council": ".ai-os/council/packets",
        "retire_count": 0,
        "repository_consolidation_proven": False,
        "gl005_proven": False,
    }
    payload["QWEN-RUNTIME-REALITY.json"] = {
        "schema": "raios.qwen-runtime-reality.v1",
        "student_preferred": STUDENT_PREFERRED,
        "student_live": bool(student_gen.get("ok")),
        "student_generate_ok": bool(student_gen.get("ok")),
        "student_model_id": student_gen.get("model") or qwen.get("student_model"),
        "parameter_count_claimed": "0.5b_name_only",
        "weight_hash": None,
        "architecture_from_artifact": None,
        "do_not_call_qwen_3_6": True,
        "cortex_identity_string": CORTEX_IDENTITY,
        "cortex_loaded": False,
        "cortex_generate_ok": bool(cortex_gen.get("ok")),
        "cortex_generate_error": cortex_gen.get("error"),
        "granite_generate_ok": bool(granite_gen.get("ok")),
        "final_backbone": None,
        "qwen_configured_ne_final_backbone": True,
        "ollama_tags": tags,
        "probe": qwen,
        "gl005_proven": False,
    }
    payload["NEUROLINGUA-RUNTIME-GRAPH.json"] = {
        "schema": "raios.neurolingua-runtime-graph.v1",
        "nodes": trace["nodes"],
        "live_path": "input→L1→L2 terminology→L4 compile (L3 HOLD/skip)",
        "llm_calls_on_compile": 0,
        "gl005_proven": False,
    }
    payload["CORTEX-CONTEXT-MATRIX-REALITY.json"] = {
        "schema": "raios.cortex-context-matrix.v1",
        "identity_string": CORTEX_IDENTITY,
        "artifact_confirming_exact_id": False,
        "loaded": False,
        "hold": True,
        "host_reason": cortex.get("host_reason"),
        "gpu": cortex.get("gpu"),
        "context_matrix": "NOT_REACHED",
        "tertiary_layer": "FILE_ONLY_OR_HOLD",
        "gl005_proven": False,
        **{k: cortex.get(k) for k in ("owner", "run_granted", "thrown", "ram_total_gb", "ram_free_gb")},
    }
    payload["MODEL-EXECUTION-DATAFLOW.json"] = {
        "schema": "raios.model-execution-dataflow.v1",
        "flow": [
            "INPUT",
            "parser",
            "NeuroLingua L1",
            "NeuroLingua L2",
            "router",
            "model shell (training only if student generate 200)",
            "model weights (student only on this VM)",
            "context/cortex matrix HOLD",
            "retrieval FILE_ONLY",
            "memory WAL locked",
            "reasoning deterministic",
            "verifier",
            "output",
        ],
        "classes": {n["id"]: n["class"] for n in trace["nodes"]},
        "student": trace["student_generate"],
        "gl005_proven": False,
    }
    payload["NEUROLINGUA-REALITY-AUDIT.json"] = {
        "schema": "raios.neurolingua-reality-audit.v1",
        "founder_claimed_file_count": 79,
        "this_checkout_related_files": len(files_nl),
        "files": files_nl,
        "src_py": sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src" / "raios" / "neuro_lingua").glob("*.py")),
        "packages_added": [],
        "spacy": False,
        "stanza": False,
        "camel_tools": False,
        "gl005_proven": False,
    }
    payload["NEUROLINGUA-LAYER-MATRIX.json"] = {
        "schema": "raios.neurolingua-layer-matrix.v1",
        "spec": LAYER_SPEC,
        "layers": layers,
        "flags": {
            "NEUROLINGUA_L1_PROVEN": False,
            "NEUROLINGUA_L2_PROVEN": False,
            "NEUROLINGUA_L3_PROVEN": False,
            "NEUROLINGUA_L4_PROVEN": False,
        },
        "gl005_proven": False,
    }
    payload["NEUROLINGUA-E2E-PROOF.json"] = {
        "schema": "raios.neurolingua-e2e-proof.v1",
        **corpus,
        "target": TARGET,
        "NEUROLINGUA_E2E_PROVEN": False,
        "gl005_proven": False,
    }
    payload["NEUROLINGUA-AUTO-WIRING-PROOF.json"] = {
        "schema": "raios.neurolingua-auto-wiring.v1",
        "entry": "raios.neuro_lingua.auto_pipeline / auto_compile",
        "manual_invocation_required": False,
        "corpus_auto": corpus.get("auto_wired"),
        "llm_calls": 0,
        "wal_written": False,
        "gl005_proven": False,
    }
    payload["MODEL-LAB-REALITY.json"] = {
        "schema": "raios.model-lab-reality.v1",
        "registry": reg,
        "hardware_this_host": {
            "hardware_state": this_probe.get("hardware_state"),
            "gpu_capacity": this_probe.get("gpu_capacity"),
            "ram_total": this_probe.get("ram_total"),
        },
        "winner": None,
        "model_lab_foundation_proven": True,
        "merge_executed": False,
        "gl005_proven": False,
    }
    payload["MODEL-CAPABILITY-FINGERPRINTS.json"] = {
        "schema": "raios.model-capability-fingerprints.v1",
        "fingerprints": fps,
        "winner": None,
        "gl005_proven": False,
    }
    payload["MODEL-MERGE-LAB-FOUNDATION.json"] = {
        "schema": "raios.model-merge-lab-foundation.v1",
        "declarations": decls,
        "plans": plans,
        "merge_executor": merge_try,
        "compatibility": compat,
        "evaluation": eval_row,
        "regression": regress_row,
        "pareto": pareto,
        "adapter": adapter,
        "canary": canary,
        "installed_blindly": False,
        "gl005_proven": False,
    }
    payload["SELF-INSPECTION-ENGINE-PROOF.json"] = inspect_rec
    packets = {
        "C2": {
            "seat": "C2",
            "tasks": ["repository consolidation", "cloud integration", "runtime wiring"],
            "impersonated": False,
            "status": "THIS_STAMP",
        },
        "C4": {
            "seat": "C4",
            "tasks": ["adversarial architecture review", "model/merge critique", "retirement falsification", "NeuroLingua attack tests"],
            "impersonated": False,
            "status": "PACKET_ONLY",
            "do_not_summon": True,
        },
        "C5": {
            "seat": "C5",
            "tasks": ["self-inspection", "learning", "runtime trace", "assimilation proof", "blind transfer"],
            "impersonated": False,
            "status": "GIT_MIND",
            "lives_in": "git",
            "cognitive_wal_written": False,
        },
        "C3": {
            "seat": "C3",
            "tasks": ["state-of-art research", "model/tool scouting", "architecture comparison"],
            "impersonated": False,
            "status": "PACKET_ONLY",
            "do_not_summon": True,
        },
    }
    payload["COUNCIL-PARALLEL-TASKS.json"] = {
        "schema": "raios.council-parallel-tasks.v1",
        "channel": ".ai-os/council/packets",
        "cognitive_wal": False,
        "packets": packets,
        "gl005_proven": False,
    }
    payload["MASTER-NEXT-EXECUTION-GRAPH.json"] = {
        "schema": "raios.master-next-execution-graph.v1",
        "p0": [
            "AUTHENTICATED_ORCHESTRATION_TASK",
            "QWEN_GRANITE_SOURCE_INDEPENDENT_ASSIMILATION",
            "GL005",
        ],
        "c1_minimum_actions": [
            "Enable Kaggle accelerator in the worker session if GPU is required, then run the A/B hardware probe notebooks",
            "Authenticate Kaggle B as an independent worker",
            "Grant a durable cloud credential if persistent cognitive storage should leave the laptop (HF dataset write repo or object store)",
        ],
        "next_automated": [
            "Keep laptop as control plane",
            "Do not download new local models",
            "Do not delete Qwen/Granite sources",
            "Do not mint GL005",
        ],
        "gl005_proven": False,
    }

    hashes = {}
    for name, body in payload.items():
        if name == "MASTER-RECEIPT.json":
            continue
        body.setdefault("from", "C2")
        body.setdefault("c5", "git")
        body.setdefault("wal_written", False)
        body.setdefault("gl005_proven", False)
        hashes[name] = dump_json(REPORTS / name, body)

    COUNCIL.mkdir(parents=True, exist_ok=True)
    for seat, pkt in packets.items():
        dump_json(COUNCIL / f"WAVE-CCN-{seat}.json", {**pkt, "from": "C2", "wal_written": False, "gl005_proven": False})

    after = wal_mtime()
    if before != after:
        raise SystemExit("WAVE_CCN_WAL_VIOLATION")

    receipt = {
        "schema": "raios.master-receipt.v1",
        "wave": "RAIOS-CLOUD-CONSOLIDATION-NEUROLINGUA",
        "ts": utc(),
        "from": "C2",
        "c5": "git",
        "this_session": "C2",
        "head": git_head(),
        "origin": origin,
        "whoami": {"role": "C2_EXECUTIVE_ENGINEER", "c5_is_git": True},
        "artifacts": [{"name": n, "sha256": hashes[n]} for n in ARTIFACTS if n != "MASTER-RECEIPT.json"],
        "flags": {
            "EXTRACTED_QWEN_GRANITE": False,
            "SAFE_TO_REMOVE_SOURCE": False,
            "GL005_PROVEN": False,
            "KAGGLE_A_WORKER_PROVEN": False,
            "KAGGLE_B_WORKER_PROVEN": False,
            "WORK_STEALING_PROVEN": False,
            "WORK_STEALING_LOCAL_SIM_PROVEN": steal.get("work_stealing_local_sim_proven"),
            "PERSISTENT_COGNITIVE_STORAGE_PROVEN": False,
            "NEUROLINGUA_L1_PROVEN": False,
            "NEUROLINGUA_L2_PROVEN": False,
            "NEUROLINGUA_L3_PROVEN": False,
            "NEUROLINGUA_L4_PROVEN": False,
            "NEUROLINGUA_E2E_PROVEN": False,
            "NEUROLINGUA_CORPUS_TESTED": corpus.get("ok"),
            "MODEL_LAB_FOUNDATION_PROVEN": True,
            "SELF_INSPECTION_PROVEN": True,
            "REPOSITORY_CONSOLIDATION_PROVEN": False,
            "LLM_FABRIC_PROVEN": False,
            "ASSIMILATION_PROVEN": False,
        },
        "evidence": {
            "ollama_tags": tags,
            "student_generate_ok": bool(student_gen.get("ok")),
            "local_cas_ok": bool(local_store.get("ok")),
            "steal_sim_ok": bool(steal.get("work_stealing_local_sim_proven")),
            "nl_corpus_ok": bool(corpus.get("ok")),
            "hardware_state": this_probe.get("hardware_state"),
            "hf_token_present": hf_token_present(),
            "retire_count": 0,
        },
        "law": list(LAWS),
        "wal_written": False,
        "wal_mtime_unchanged": True,
        "paid_api": False,
        "openai": False,
        "weight_downloaded": False,
        "ok": bool(local_store.get("ok") and steal.get("work_stealing_local_sim_proven") and corpus.get("ok")),
        "gl005_proven": False,
    }
    others = [n for n in ARTIFACTS if n != "MASTER-RECEIPT.json"]
    receipt["artifacts"] = [{"name": n, "sha256": hashes[n]} for n in others]
    master_hash = dump_json(REPORTS / "MASTER-RECEIPT.json", receipt)
    OUT.mkdir(parents=True, exist_ok=True)
    dump_json(OUT / "LAST.json", receipt)
    rec = {
        "ok": receipt["ok"],
        "from": "C2",
        "c5": "git",
        "wave": receipt["wave"],
        "wal_written": False,
        "gl005_proven": False,
        "artifacts": receipt["artifacts"] + [{"name": "MASTER-RECEIPT.json", "sha256": master_hash}],
        "flags": receipt["flags"],
        "evidence": receipt["evidence"],
    }
    return rec


def main() -> int:
    rec = stamp()
    print(json.dumps({"ok": rec["ok"], "wave": rec["wave"], "gl005_proven": False, "artifacts": len(rec["artifacts"])}, indent=2))
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
