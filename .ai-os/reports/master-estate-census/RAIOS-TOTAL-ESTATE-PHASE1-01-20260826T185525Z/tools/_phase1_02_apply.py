# Phase-1-02 closeout apply. Delta-only. No delete/merge/fetch/hydrate.
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RUN = Path(
    r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\reports\master-estate-census\RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T185525Z"
)
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
TASK = "RAIOS-TOTAL-ESTATE-PHASE1-02"

KAGGLE_CLASSES = [
    ("S57", "KAGGLE_ACCOUNT"),
    ("S58", "KAGGLE_NOTEBOOKS"),
    ("S59", "KAGGLE_NOTEBOOK_VERSIONS"),
    ("S60", "KAGGLE_DATASETS"),
    ("S61", "KAGGLE_INPUT_DATASETS"),
    ("S62", "KAGGLE_OUTPUTS"),
    ("S63", "KAGGLE_WORKING_DIRECTORIES"),
    ("S64", "KAGGLE_MODEL_ARTIFACTS"),
    ("S65", "KAGGLE_CHECKPOINTS"),
    ("S66", "KAGGLE_GIT_CLONES"),
    ("S67", "KAGGLE_GIT_REFS"),
    ("S68", "KAGGLE_GITHUB_PUSH_RELATIONSHIPS"),
    ("S69", "KAGGLE_ARCHIVES"),
    ("S70", "KAGGLE_RAIOS_STATE"),
]

NOMADIC = [
    ("__init__.py", "7c4e55ee0fac76add993cfda32c1b48b7df91196a107f1bc9458dfe0a7a3a585"),
    ("checkpoint_store.py", "d7ec6447b300cfe96b22810b07acc0417294e668b1de09ee75cf5a5953be7570"),
    ("idempotency.py", "1a7ec75f578960da2c7c06b3b637ef1b86d90cd7336f5a9d30539ce9555a479f"),
    ("job_ledger.py", "526870071da7f90e9c6c9fcd7666fa1654025acbebb6667fde1abc7dc0aeb01f"),
    ("lease_manager.py", "47bc639c0f04b226ff1e24e2065ca76244c21c1bb17a855d26abb627d789f28e"),
    ("provider_contract.py", "07c7a73d00e9b47cbbd0eef21ee535fbd9d7ee33d2cf03579a329a1e60cc09d0"),
    ("receipt_writer.py", "68c61d6cf2e4e16663e10d854ea1bc4089154eb2df6141d5fae5c52e66bf3823"),
    ("reconciliation.py", "75b16c461186cfb7d72feb9948a62e10fe7808a50bb81cf47282ac1623431c39"),
    ("work_stealing_scheduler.py", "4703fd5ff336589d026482b143590191875dd52f5b362eb4cb3bc4676e1a9bf5"),
    ("worker_contract.py", "7442e3ab2e120f70f71e030170159d9e2e4845af9fd3682a423774dab39182b8"),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def modelfile_sha(tag: str) -> str | None:
    r = subprocess.run(["ollama", "show", tag, "--modelfile"], capture_output=True, text=True)
    if r.returncode != 0 or not (r.stdout or "").strip():
        return None
    return sha256_bytes(r.stdout.encode("utf-8", errors="replace"))


def source_lane(sid: str, sclass: str) -> str:
    if sid in {x[0] for x in KAGGLE_CLASSES}:
        return "C2_CLOUD_KAGGLE_UNBOUND"
    if sid in {"S03", "S04"}:
        return "C2_CLOUD"
    if sid in {"S10", "S11", "S13", "S46", "S47", "S48", "S49", "S54"}:
        return "C2_LOCAL_ONEDRIVE_METADATA"
    if sid in {"S37", "S38", "S39", "S40", "S41", "S42", "S43", "S44", "S45", "S55", "S56"}:
        return "C2_LOCAL_DESKTOP"
    return "C2_LOCAL"


def unresolved_reason(sid: str, sclass: str, note: str) -> str | None:
    if sid == "S06":
        return "GL-002 worktree path missing on disk; capability classified HISTORICAL_IMPLEMENTATION_FOUND via git branch + archive evidence"
    if sid == "S07":
        return "GL-003 worktree path missing on disk; capability classified EVIDENCE_ONLY_NO_SOURCE"
    if sid == "S35":
        return "EXTERNAL_DRAFT_PENDING_PROMOTION; inventoried, not installed"
    if sclass == "KAGGLE_UNRESOLVED":
        if sid == "S68":
            return "GitHub Kaggle-labeled commit is not a Kaggle API push receipt; AUTHORIZED_KAGGLE_ACCESS_CHANNEL_ABSENT"
        return "AUTHORIZED_KAGGLE_ACCESS_CHANNEL_ABSENT"
    return None


def main() -> None:
    cicf = json.loads((RUN / "tools" / "CICF-STATIC-SUMMARY.json").read_text(encoding="utf-8"))
    cc = cicf["counts"]

    nomadic_blob = "".join(f"{n} {h}\n" for n, h in NOMADIC).encode()
    nomadic_pkg = sha256_bytes(nomadic_blob)

    reg = json.loads((RUN / "01-MASTER-SURFACE-REGISTRY.json").read_text(encoding="utf-8"))
    for s in reg["surfaces"]:
        sid = s["id"]
        if sid == "S68":
            s["class"] = "KAGGLE_UNRESOLVED"
            s["note"] = (
                "GitHub-side only: commit da67f449 subject 'Kaggle Notebook | notebook8c2d6a9080 | Version 3'. "
                "Not a Kaggle API receipt. KAGGLE_GITHUB_PUSH_RELATIONSHIPS_PROVEN=0"
            )
        if sid == "S70":
            s["name"] = "KAGGLE_RAIOS_STATE"
        if sid == "S06":
            s["note"] = (
                "path missing; GL002_CLASSIFICATION=HISTORICAL_IMPLEMENTATION_FOUND; "
                "branch raios/gl-002-main-brain c336fc88; evidence SHA d14e41c4"
            )
        if sid == "S07":
            s["note"] = (
                "path missing; GL003_CLASSIFICATION=EVIDENCE_ONLY_NO_SOURCE; "
                "evidence SHA 8716826f; no gl-003 branch; migration/gl-003 absent on TREE-001"
            )
        if sid == "S35":
            s["note"] = (
                "EXTERNAL_DRAFT_PENDING_PROMOTION; 10 files hashed; package SHA "
                + nomadic_pkg
            )
        if sid == "S36":
            s["note"] = (
                f"7061 files / 1464 tools; static classified; P0 remaining={cc['CICF_P0_NAME_ONLY_REMAINING']}"
            )
        s["SURFACE_ID"] = sid
        s["SURFACE_NAME"] = s["name"]
        s["SURFACE_CLASS"] = s["class"]
        s["SOURCE_LANE"] = source_lane(sid, s["class"])
        s["STATUS"] = s["class"]
        s["EVIDENCE"] = (s.get("path") or "") + " | " + (s.get("note") or "")
        s["UNRESOLVED_REASON"] = unresolved_reason(sid, s["class"], s.get("note") or "")

    class_counts = {}
    for s in reg["surfaces"]:
        class_counts[s["SURFACE_CLASS"]] = class_counts.get(s["SURFACE_CLASS"], 0) + 1

    reg["TASK_ID_ORIGIN"] = "RAIOS-TOTAL-ESTATE-PHASE1-01"
    reg["CLOSEOUT_TASK_ID"] = TASK
    reg["CLOSEOUT_AT"] = NOW
    reg["MASTER_SURFACES_TOTAL"] = len(reg["surfaces"])
    reg["KNOWN_SURFACES_TOTAL"] = len(reg["surfaces"])
    reg["SURFACE_COUNT_DRIFT"] = {
        "CANONICAL_TOTAL": 71,
        "STALE_REPORT_TOTAL": 61,
        "STALE_REPORT": {
            "CLASSIFICATION": "STALE_REPORT",
            "RUN_ID": "RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T1853Z",
            "PATH": r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\reports\master-estate-census\RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T1853Z\01-MASTER-SURFACE-REGISTRY.json",
            "KNOWN_SURFACES_TOTAL": 61,
            "EXPLANATION": (
                "Incomplete earlier write before Desktop/C3 extra surfaces (S37+) and before S71 freeze. "
                "class_sum 18+11+1+2+2+8+1+4+13+1=61. Not an independent physical census. Do not replace 71."
            ),
        },
        "KAGGLE_13_VS_14": {
            "KAGGLE_SURFACE_CLASSES_EXPECTED": 14,
            "KAGGLE_SURFACE_CLASSES_REGISTERED": 14,
            "C6_OR_COVERAGE_13_EXPLANATION": (
                "Coverage counted KAGGLE_UNRESOLVED=13 plus KAGGLE_GIT_INSPECTED=1 for SURFACE_ID=S68. "
                "S68 class existed before this amendment; it was mis-promoted from a GitHub commit subject. "
                "After correction S68 remains registered and is KAGGLE_UNRESOLVED. No missing 14th class."
            ),
            "AMENDED_SURFACE_ID": "S68",
        },
    }
    dump(RUN / "01-MASTER-SURFACE-REGISTRY.json", reg)
    reg_sha = sha256_bytes((RUN / "01-MASTER-SURFACE-REGISTRY.json").read_bytes())

    dump(
        RUN / "cloud" / "CLOUD-SCOPE-MATRIX.json",
        {
            "schema": "raios.cloud-scope-matrix.v1",
            "TASK_ID": TASK,
            "generated_at": NOW,
            "GENERIC_CLOUD_ACCESS_PROVEN": None,
            "NOTE": "Do not collapse these flags into CLOUD_ACCESS_PROVEN=true from git ls-remote alone.",
            "PUBLIC_GITHUB_READ_ACCESS_PROVEN": True,
            "PUBLIC_GITHUB_EVIDENCE": "git ls-remote origin HEAD/main da67f44963fafde67df52cb62ab32f75fe725df0",
            "PRIVATE_GITHUB_ACCESS_PROVEN": False,
            "PRIVATE_GITHUB_EVIDENCE": "gh auth status = not logged in",
            "CURSOR_CLOUD_ACCESS_PROVEN": False,
            "CURSOR_CLOUD_EVIDENCE": "EXTERNAL_EVIDENCE_UNBOUND",
            "KAGGLE_ACCESS_PROVEN": False,
            "KAGGLE_EVIDENCE": "kaggle.exe present; %USERPROFILE%\\.kaggle\\kaggle.json absent; KAGGLE_USERNAME/KAGGLE_KEY unset",
            "ONEDRIVE_CLOUD_CONTENT_ACCESS_PROVEN": False,
            "ONEDRIVE_EVIDENCE": "ReparsePoint/metadata listing only; no hydrate this run",
            "OTHER_CLOUD_ACCESS_PROVEN": False,
            "OTHER_CLOUD_EVIDENCE": "none independently proven",
        },
    )

    dump(
        RUN / "cloud" / "kaggle" / "KAGGLE-BINDING.json",
        {
            "schema": "raios.kaggle-binding.v1",
            "TASK_ID": TASK,
            "generated_at": NOW,
            "KAGGLE_SURFACE_CLASSES_EXPECTED": 14,
            "KAGGLE_SURFACE_CLASSES_REGISTERED": 14,
            "classes": [
                {"SURFACE_ID": sid, "SURFACE_NAME": name, "STATUS": "KAGGLE_UNRESOLVED"}
                for sid, name in KAGGLE_CLASSES
            ],
            "KAGGLE_ACCESS_PROVEN": False,
            "BLOCKER": "AUTHORIZED_KAGGLE_ACCESS_CHANNEL_ABSENT",
            "PREFERRED_EXECUTOR": "C2_CLOUD",
            "LIVE_METADATA_BOUND": False,
            "NO_GPU": True,
            "NO_TPU": True,
            "NO_TRAINING": True,
            "NO_INFERENCE": True,
            "NO_LARGE_DATASET_DOWNLOAD": True,
            "GITHUB_KAGGLE_LABELED_COMMIT_OBSERVED": 1,
            "GITHUB_KAGGLE_LABELED_COMMIT": {
                "NOTEBOOK_LABEL": "notebook8c2d6a9080",
                "COMMIT_SUBJECT": "Kaggle Notebook | notebook8c2d6a9080 | Version 3",
                "SHA": "da67f44963fafde67df52cb62ab32f75fe725df0",
                "NOT_A_KAGGLE_API_RECEIPT": True,
            },
            "KAGGLE_GITHUB_PUSH_RELATIONSHIPS_PROVEN": 0,
            "PROMOTE_WHEN": [
                "NOTEBOOK_ID",
                "NOTEBOOK_VERSION",
                "SOURCE_OR_OUTPUT_HASH",
                "GIT_COMMIT_SHA",
                "GITHUB_REF",
            ],
            "KAGGLE_UNRESOLVED": 14,
        },
    )

    dump(
        RUN / "c6-reconciliation" / "C6-HANDOFF-RECONCILIATION.json",
        {
            "schema": "raios.c6-handoff-reconciliation.v1",
            "TASK_ID": TASK,
            "generated_at": NOW,
            "C6_ROLE_THIS_CLOSEOUT": "OFF_HOST_EVIDENCE_RECONCILER",
            "NOT": "DIRECT_AG_AND_KAGGLE_OBSERVER",
            "C6_AG_ACCESS_PROVEN": False,
            "C6_KAGGLE_ACCESS_PROVEN": False,
            "C6_AG_AND_KAGGLE_BOUND": False,
            "C6_RECONCILIATION_FROM_HANDOFF": True,
            "RECONCILIATION_FROM_HANDOFF": True,
            "C6_HANDOFF_SIGNED_BY_C6": False,
            "NOTE": "C6 may reconcile hashed C2 manifests without AG access. Off-host processing of copies is not AG access. Processing C2-provided Kaggle text is not Kaggle access.",
            "handoffs": [
                {
                    "NAME": "C2_LOCAL_MANIFEST",
                    "PATH": str(RUN),
                    "SCOPE": "RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T185525Z",
                    "EXCLUSIONS": "no hydrate; no secret values; no live Kaggle; no model inference",
                    "ACTOR": "C2@AG",
                    "TIMESTAMP": NOW,
                    "SHA256": "see FILES-SHA256.txt after this write",
                }
            ],
        },
    )
    dump(RUN / "c6-reconciliation" / "PENDING.json", {
        "schema": "raios.total-estate.c6-reconciliation.v1",
        "SUPERSEDED_BY": "C6-HANDOFF-RECONCILIATION.json",
        "C6_AG_ACCESS_PROVEN": False,
        "C6_KAGGLE_ACCESS_PROVEN": False,
        "C6_AG_AND_KAGGLE_BOUND": False,
        "C6_RECONCILIATION_FROM_HANDOFF": True,
        "RECONCILIATION_FROM_HANDOFF": True,
        "STATUS": "C2_HANDOFF_READY_PENDING_C6_RECEIPT",
    })

    s35_path = RUN / "s35" / "S35-NOMADIC-MANIFEST.json"
    s35_obj = {
        "schema": "raios.s35.nomadic.v1",
        "SURFACE_ID": "S35",
        "STATE": "EXTERNAL_DRAFT_PENDING_PROMOTION",
        "INTENDED_CANONICAL_PATHS": ["RAIOS/V9/cloud/nomadic/" + n for n, _ in NOMADIC],
        "CONTENTS": [{"NAME": n, "SHA256": h} for n, h in NOMADIC],
        "PACKAGE_SHA256": nomadic_pkg,
        "PACKAGE_SHA256_METHOD": "SHA256 of sorted 'name hash\\n' lines",
        "C3_REVIEW_BINDING_SHA256": "881c7a03908396d3cfee6f847a74e015c8821d77e79646bb4145f4d8130266c2",
        "RELATION_TO_EXISTING_ASSETS": "REUSE_CANDIDATE for CAP-C6; do not install/promote during census; C6-LOCAL worker registry claim is stale and is not AG access",
    }
    dump(s35_path, s35_obj)
    (RUN / "s35" / "S35-NOMADIC-MANIFEST.SHA256").write_text(
        sha256_bytes(s35_path.read_bytes()) + "\n", encoding="utf-8"
    )

    dump(
        RUN / "gl" / "GL-002-GL-003-LINEAGE.json",
        {
            "schema": "raios.gl002-gl003.lineage.v1",
            "TASK_ID": TASK,
            "GL002_CLASSIFICATION": "HISTORICAL_IMPLEMENTATION_FOUND",
            "GL002_EVIDENCE": [
                {
                    "KIND": "git_branch",
                    "REF": "raios/gl-002-main-brain",
                    "SHA": "c336fc88019a68dba9a79531d4c9d3269e85b02d",
                    "SUBJECT": "docs(raios): close GL-002 authority phase and defer missing bridges",
                },
                {
                    "KIND": "current_tree_doc",
                    "PATH": r"migration\strong-validation\GL-002-AUTHORITY-CLOSEOUT.md",
                    "SHA256": "5826bda1b45385567fcb936cbf5f2191183ad5c577ee0bd21ce768bd7884c35f",
                },
                {
                    "KIND": "current_tree_doc",
                    "PATH": r"migration\strong-validation\GL-002-IMPLEMENTATION-GATES.md",
                    "SHA256": "d72c679e0ce830876093b1103635240b900b0a3daa65bbee7bcf1afc69a37923",
                },
                {
                    "KIND": "archive_status",
                    "PATH": r"archive\repair-leftovers\controlled-retirement-evidence-20260824\evidence\GL-002-Main-Brain.status.txt",
                    "SHA256": "d14e41c4f4b5ede2c087f96d865b9e7e9c1a7d3f3b4d1842471cbf6c9109e7c4",
                },
            ],
            "GL002_CURRENT_WORKTREE_PATH": r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-002-Main-Brain",
            "GL002_CURRENT_WORKTREE_PRESENT": False,
            "GL003_CLASSIFICATION": "EVIDENCE_ONLY_NO_SOURCE",
            "GL003_EVIDENCE": [
                {
                    "KIND": "archive_status",
                    "PATH": r"archive\repair-leftovers\controlled-retirement-evidence-20260824\evidence\GL-003-Project-Brains.status.txt",
                    "SHA256": "8716826fc49c8c484d15b0e4a5d5ffb1409108050d677a59376d443047b2e946",
                    "NOTE": "lists untracked migration/gl-003/* in a missing worktree; those paths are absent on TREE-001 now; no raios/gl-003 branch found",
                }
            ],
            "GL003_CURRENT_WORKTREE_PATH": r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\GL-003-Project-Brains",
            "GL003_CURRENT_WORKTREE_PRESENT": False,
            "NO_RECONSTRUCTION": True,
        },
    )

    agents = [
        {"IDENTITY": "C1", "KIND": "ROLE", "IMPLEMENTATION": "owner/final authority (human)", "ENGINE_BINDING": None, "STATUS": "ACTIVE_ROLE_NOT_A_PROCESS", "PROOF_LEVEL": "P2_STATIC_VALIDATED", "CURRENT_USE": "AUTHORITY"},
        {"IDENTITY": "C2@AG", "KIND": "RUNTIME", "IMPLEMENTATION": "Cursor Grok session executor", "ENGINE_BINDING": "cursor-agent / C2-CURSOR", "STATUS": "LIVE_THIS_SESSION", "PROOF_LEVEL": "P5_RUNTIME_OBSERVED", "CURRENT_USE": "PRIMARY_EXECUTOR"},
        {"IDENTITY": "C2", "KIND": "ROLE", "IMPLEMENTATION": "C2-IDENTITY-BINDING.json", "ENGINE_BINDING": "C2@AG", "STATUS": "ACTIVE_CANONICAL", "PROOF_LEVEL": "P2_STATIC_VALIDATED", "CURRENT_USE": "PRIMARY_EXECUTOR"},
        {"IDENTITY": "C3", "KIND": "ROLE", "IMPLEMENTATION": "ChatGPT reviewer (no AG shell)", "ENGINE_BINDING": None, "STATUS": "EXTERNAL_REVIEWER", "PROOF_LEVEL": "P2_STATIC_VALIDATED", "CURRENT_USE": "REVIEWER"},
        {"IDENTITY": "C5@AG", "KIND": "RUNTIME", "IMPLEMENTATION": "_raios-communication-fabric/src/raios_multimodal_gateway.py", "ENGINE_BINDING": "C5-HTTP :8766", "MODEL": "qwen3:0.6b", "STATUS": "LIVE", "PROOF_LEVEL": "P5_RUNTIME_OBSERVED", "CURRENT_USE": "LOCAL_COGNITIVE_WORKER", "PID": 29160},
        {"IDENTITY": "C5", "KIND": "ROLE", "IMPLEMENTATION": "local cognitive worker", "ENGINE_BINDING": "C5@AG", "STATUS": "LIVE", "PROOF_LEVEL": "P5_RUNTIME_OBSERVED", "CURRENT_USE": "LOCAL_COGNITIVE_WORKER"},
        {"IDENTITY": "C6", "KIND": "ROLE", "IMPLEMENTATION": "RAIOS/V9/cloud/nomadic PRE_LLM draft", "ENGINE_BINDING": None, "STATUS": "EXTERNAL_DRAFT_PENDING_PROMOTION", "PROOF_LEVEL": "P2_STATIC_VALIDATED", "CURRENT_USE": "OFF_HOST_EVIDENCE_RECONCILER_NOT_DIRECT_OBSERVER"},
        {"IDENTITY": "C6-LOCAL", "KIND": "WORKER", "IMPLEMENTATION": "WORKER-REGISTRY.json", "ENGINE_BINDING": "DECLARED_BY_RUNTIME", "STATUS": "STALE_REGISTRY_CLAIM", "PROOF_LEVEL": "P1_FILE_EXISTS", "CURRENT_USE": "NONE_PROVEN; lease expired 2026-08-25T19:36:40Z; not AG access"},
        {"IDENTITY": "CHATGPT-ORCH", "KIND": "WORKER", "IMPLEMENTATION": "WORKER-REGISTRY.json", "STATUS": "STALE_REGISTRY_CLAIM", "PROOF_LEVEL": "P1_FILE_EXISTS", "CURRENT_USE": "NONE_PROVEN"},
        {"IDENTITY": "C2-OBS", "KIND": "WORKER", "IMPLEMENTATION": "WORKER-REGISTRY.json", "STATUS": "STALE_REGISTRY_CLAIM", "PROOF_LEVEL": "P1_FILE_EXISTS", "CURRENT_USE": "NONE_PROVEN"},
        {"IDENTITY": "RAIOS-CORTEX", "KIND": "WORKER", "IMPLEMENTATION": "WORKER-REGISTRY.json", "STATUS": "STALE_REGISTRY_CLAIM", "PROOF_LEVEL": "P1_FILE_EXISTS", "CURRENT_USE": "NONE_PROVEN"},
        {"IDENTITY": "002E-REPAIR", "KIND": "WORKER", "IMPLEMENTATION": "WORKER-REGISTRY.json", "STATUS": "STALE_REGISTRY_CLAIM", "PROOF_LEVEL": "P1_FILE_EXISTS", "CURRENT_USE": "NONE_PROVEN"},
        {"IDENTITY": "RAIOS-USER-ROUTER-V1", "KIND": "ADAPTER", "IMPLEMENTATION": ".ai-os/control/RAIOS-USER-ROUTER-V1.py", "ENGINE_BINDING": "command fabric", "STATUS": "CANONICAL_ON_DISK", "PROOF_LEVEL": "P6_E2E_PROVEN", "CURRENT_USE": "KEEP_CANONICAL"},
        {"IDENTITY": "RAIOS-C1-C5-CHANNEL", "KIND": "ADAPTER", "IMPLEMENTATION": ".ai-os/control/RAIOS-C1-C5-CHANNEL.py", "STATUS": "CANONICAL_ON_DISK", "PROOF_LEVEL": "P6_E2E_PROVEN", "CURRENT_USE": "KEEP_CANONICAL"},
        {"IDENTITY": "MCP@AG", "KIND": "ENGINE", "IMPLEMENTATION": "scripts/ai-os/raios_mcp/gateway.py", "ENGINE_BINDING": ":8788 PID 23788", "STATUS": "LISTEN_HEALTH_FLAKY", "PROOF_LEVEL": "P5_RUNTIME_OBSERVED", "CURRENT_USE": "KEEP_RUNTIME"},
        {"IDENTITY": "NATS", "KIND": "ENGINE", "IMPLEMENTATION": r"C:\ProgramData\RAIOS\transport\nats\nats-server.exe", "ENGINE_BINDING": ":4222/:8222 PID 25380", "STATUS": "LISTEN_NOT_PRIMARY", "PROOF_LEVEL": "P5_RUNTIME_OBSERVED", "CURRENT_USE": "TRANSPORT_SECONDARY"},
        {"IDENTITY": "OLLAMA", "KIND": "ENGINE", "IMPLEMENTATION": "ollama", "ENGINE_BINDING": ":52093 PID 5420; :11434 PID 13332", "STATUS": "LIVE", "PROOF_LEVEL": "P5_RUNTIME_OBSERVED", "CURRENT_USE": "MODEL_RUNTIME"},
        {"IDENTITY": "goose", "KIND": "ENGINE", "IMPLEMENTATION": "listed in GL-002 worktree status dump", "STATUS": "EVIDENCE_ONLY_NO_SOURCE_ON_TREE001", "PROOF_LEVEL": "P1_FILE_EXISTS", "CURRENT_USE": "NONE"},
        {"IDENTITY": "native-agent", "KIND": "ENGINE", "IMPLEMENTATION": "listed in GL-002 worktree status dump", "STATUS": "EVIDENCE_ONLY_NO_SOURCE_ON_TREE001", "PROOF_LEVEL": "P1_FILE_EXISTS", "CURRENT_USE": "NONE"},
        {"IDENTITY": "kaggle.exe", "KIND": "ADAPTER", "IMPLEMENTATION": r"C:\Users\Ghanam\AppData\Local\Programs\Python\Python314\Scripts\kaggle.exe", "STATUS": "PRESENT_UNAUTHENTICATED", "PROOF_LEVEL": "P1_FILE_EXISTS", "CURRENT_USE": "NONE"},
    ]
    dump(RUN / "14-MASTER-RUNTIME-MAP.json", {
        "schema": "raios.total-estate.runtime-map.v1",
        "CLOSEOUT_TASK_ID": TASK,
        "C5_LIVE_GROUNDING_TURN_PASS": True,
        "FOUR_TURN_INFERRED_FROM_C1_MESSAGE": False,
        "HTTP_PRIMARY": True,
        "NATS_PRIMARY": False,
        "listeners": [
            {"PORT": 8766, "PID": 29160, "PROCESS": "uvicorn raios_multimodal_gateway", "HEALTH": "200 qwen3:0.6b", "RUNTIME_ID": "C5@AG", "ENGINE_ID": "C5-HTTP"},
            {"PORT": 8788, "PID": 23788, "PROCESS": "MCP gateway", "HEALTH": "200 then timeout", "RUNTIME_ID": "MCP@AG"},
            {"PORT": 4222, "PID": 25380, "PROCESS": "nats-server", "HEALTH": "listen only"},
            {"PORT": 8222, "PID": 25380, "PROCESS": "nats-server", "HEALTH": "healthz timeout this pass"},
            {"PORT": 52093, "PID": 5420, "PROCESS": "ollama", "HEALTH": "listen"},
            {"PORT": 11434, "PID": 13332, "PROCESS": "ollama", "HEALTH": "listen"},
            {"PORT": 8765, "PID": None, "HEALTH": "NOLISTEN"},
            {"PORT": 8876, "PID": None, "HEALTH": "NOLISTEN"},
        ],
        "definitions": agents,
        "AGENT_RUNTIME_CANDIDATES_TOTAL": len(agents),
        "AGENT_RUNTIME_CANDIDATES_DESCRIBED": len(agents),
        "SEPARATION": ["ROLE", "RUNTIME", "ENGINE", "MODEL", "WORKER", "ADAPTER"],
    })

    models = [
        {"REAL_MODEL_ID": "qwen3:0.6b", "OLLAMA_ID": "7df6b6e09427", "FAMILY": "qwen3", "PARAMETER_SIZE_IF_AVAILABLE": "751.63M", "QUANTIZATION_IF_AVAILABLE": "Q4_K_M", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "522 MB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": "C5@AG:8766 PID 29160", "CURRENT_ROLE": "C5 live model", "USED_BY": ["C5@AG"], "CONFIG_REFERENCES": ["C5 /health", "06-MASTER-MODEL-CATALOG CURRENT_BINDING"], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("qwen3:0.6b"), "PROOF": "existing health 200; ollama show; no new inference"},
        {"REAL_MODEL_ID": "qwen3-embedding:0.6b", "OLLAMA_ID": "ac6da0dfba84", "FAMILY": "qwen3", "PARAMETER_SIZE_IF_AVAILABLE": "595.78M", "QUANTIZATION_IF_AVAILABLE": "Q8_0", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "639 MB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": "embedder_unbound", "USED_BY": [], "CONFIG_REFERENCES": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("qwen3-embedding:0.6b")},
        {"REAL_MODEL_ID": "qwen2.5:0.5b", "OLLAMA_ID": "a8b0c5157701", "FAMILY": "qwen2", "PARAMETER_SIZE_IF_AVAILABLE": "494.03M", "QUANTIZATION_IF_AVAILABLE": "Q4_K_M", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "397 MB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": None, "USED_BY": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("qwen2.5:0.5b")},
        {"REAL_MODEL_ID": "granite-embedding:278m", "OLLAMA_ID": "1a37926bf842", "FAMILY": "bert/granite-embedding", "PARAMETER_SIZE_IF_AVAILABLE": "277.45M", "QUANTIZATION_IF_AVAILABLE": "F16", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "562 MB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": None, "USED_BY": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("granite-embedding:278m")},
        {"REAL_MODEL_ID": "granite-code:3b", "OLLAMA_ID": "becc94fe1876", "FAMILY": "llama/granite-code", "PARAMETER_SIZE_IF_AVAILABLE": "3.5B", "QUANTIZATION_IF_AVAILABLE": "Q4_0", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "2.0 GB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": None, "USED_BY": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("granite-code:3b")},
        {"REAL_MODEL_ID": "granite3-dense:8b", "OLLAMA_ID": "199456d876ee", "FAMILY": "granite", "PARAMETER_SIZE_IF_AVAILABLE": "8.2B", "QUANTIZATION_IF_AVAILABLE": "Q4_K_M", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "4.9 GB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": None, "USED_BY": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("granite3-dense:8b")},
        {"REAL_MODEL_ID": "granite3-dense:2b", "OLLAMA_ID": "5c2e6f3112f4", "FAMILY": "granite", "PARAMETER_SIZE_IF_AVAILABLE": "2.6B", "QUANTIZATION_IF_AVAILABLE": "Q4_K_M", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "1.6 GB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": None, "USED_BY": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("granite3-dense:2b")},
        {"REAL_MODEL_ID": "qwen3.6:35b-a3b", "OLLAMA_ID": "07d35212591f", "FAMILY": "qwen35moe", "PARAMETER_SIZE_IF_AVAILABLE": "36.0B", "QUANTIZATION_IF_AVAILABLE": "Q4_K_M", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "23 GB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": "not current C5 cortex", "USED_BY": [], "KNOWN_DEFECTS": "accidental prior load as C5; restored to 0.6b", "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("qwen3.6:35b-a3b")},
        {"REAL_MODEL_ID": "granite4:3b", "OLLAMA_ID": "89962fcc7523", "FAMILY": "granite", "PARAMETER_SIZE_IF_AVAILABLE": "3.4B", "QUANTIZATION_IF_AVAILABLE": "Q4_K_M", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "2.1 GB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": None, "USED_BY": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("granite4:3b")},
        {"REAL_MODEL_ID": "qwen2.5-coder:3b", "OLLAMA_ID": "f72c60cabf62", "FAMILY": "qwen2", "PARAMETER_SIZE_IF_AVAILABLE": "3.1B", "QUANTIZATION_IF_AVAILABLE": "Q4_K_M", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "1.9 GB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": None, "USED_BY": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("qwen2.5-coder:3b")},
        {"REAL_MODEL_ID": "deepseek-r1:1.5b", "OLLAMA_ID": "e0979632db5a", "FAMILY": "qwen2/deepseek-r1", "PARAMETER_SIZE_IF_AVAILABLE": "1.8B", "QUANTIZATION_IF_AVAILABLE": "Q4_K_M", "LOCAL_STORAGE": r"C:\Users\Ghanam\.ollama", "SIZE": "1.1 GB", "CALLABLE_STATUS": "INSTALLED_METADATA_OBSERVED", "CURRENT_RUNTIME_BINDING": None, "CURRENT_ROLE": None, "USED_BY": [], "MODELFILE_OR_CONFIG_HASH_IF_AVAILABLE": modelfile_sha("deepseek-r1:1.5b")},
    ]
    dump(RUN / "06-MASTER-MODEL-CATALOG.json", {
        "schema": "raios.total-estate.model-catalog.v1",
        "CLOSEOUT_TASK_ID": TASK,
        "ALL_DISCOVERED_MODELS_CLASSIFIED": True,
        "ALL_MODELS_DESCRIBED": True,
        "MODELS_TOTAL": 11,
        "MODELS_DESCRIBED": 11,
        "EXTRACTED_QWEN_GRANITE": False,
        "SAFE_TO_REMOVE_SOURCE": False,
        "CURRENT_BINDING": "RAIOS_MAIN_CORTEX=qwen3:0.6b",
        "NO_INFERENCE_THIS_TASK": True,
        "models": models,
        "named_not_installed": [
            {"REAL_MODEL_ID": "Lion", "PROOF_LEVEL": "P0_NAME_ONLY", "NOTE": "named in estate plan; not in ollama list"},
        ],
    })

    actor = json.loads((RUN / "00-ACTOR-ACCESS-MATRIX.json").read_text(encoding="utf-8"))
    actor["CLOSEOUT_TASK_ID"] = TASK
    actor["GENERIC_CLOUD_ACCESS_PROVEN"] = None
    actor["PUBLIC_GITHUB_READ_ACCESS_PROVEN"] = True
    actor["PRIVATE_GITHUB_ACCESS_PROVEN"] = False
    actor["CURSOR_CLOUD_ACCESS_PROVEN"] = False
    actor["KAGGLE_ACCESS_PROVEN"] = False
    actor["ONEDRIVE_CLOUD_CONTENT_ACCESS_PROVEN"] = False
    actor["OTHER_CLOUD_ACCESS_PROVEN"] = False
    actor["C6_RECONCILIATION_FROM_HANDOFF"] = True
    for a in actor.get("actors", []):
        if a.get("RUNTIME_ID") == "C2@AG":
            a["CLOUD_ACCESS_PROVEN"] = None
            a["PUBLIC_GITHUB_READ_ACCESS_PROVEN"] = True
            a["NOTE"] = "Public git ls-remote only. Not generic CLOUD_ACCESS_PROVEN. Not C6 binding."
        if a.get("RUNTIME_ID") == "C2_CLOUD_CENSUS":
            a["CLOUD_ACCESS_PROVEN"] = None
            a["PUBLIC_GITHUB_READ_ACCESS_PROVEN"] = True
        if a.get("RUNTIME_ID") == "C6":
            a["C6_ROLE"] = "OFF_HOST_EVIDENCE_RECONCILER"
            a["C6_RECONCILIATION_FROM_HANDOFF"] = True
    dump(RUN / "00-ACTOR-ACCESS-MATRIX.json", actor)

    cloud_local = json.loads((RUN / "03-MASTER-CLOUD-LOCAL-MATRIX.json").read_text(encoding="utf-8"))
    cloud_local["CLOSEOUT_TASK_ID"] = TASK
    cloud_local["PUBLIC_GITHUB_READ_ACCESS_PROVEN"] = True
    cloud_local["PRIVATE_GITHUB_ACCESS_PROVEN"] = False
    cloud_local["CURSOR_CLOUD_ACCESS_PROVEN"] = False
    cloud_local["KAGGLE_ACCESS_PROVEN"] = False
    cloud_local["ONEDRIVE_CLOUD_CONTENT_ACCESS_PROVEN"] = False
    dump(RUN / "03-MASTER-CLOUD-LOCAL-MATRIX.json", cloud_local)

    kgit = json.loads((RUN / "cloud" / "kaggle" / "KAGGLE-GIT-MATRIX.json").read_text(encoding="utf-8"))
    kgit["KAGGLE_GITHUB_RELATIONSHIPS_PROVEN"] = 0
    kgit["KAGGLE_GITHUB_PUSH_RELATIONSHIPS_PROVEN"] = 0
    kgit["GITHUB_KAGGLE_LABELED_COMMIT_OBSERVED"] = 1
    kgit["NOTE"] = (
        "GitHub origin/main da67f449 is a Kaggle-notebook-labeled commit, not a Kaggle API census. "
        "PUSH_EVIDENCE_PRESENT on GitHub does not prove KAGGLE_GITHUB_PUSH_RELATIONSHIP."
    )
    if kgit.get("relationships"):
        kgit["relationships"][0]["KAGGLE_LIVE_CLONE_INSPECTED"] = False
        kgit["relationships"][0]["KAGGLE_API_RECEIPT"] = False
        kgit["relationships"][0]["RELATIONSHIP_PROVEN"] = False
    dump(RUN / "cloud" / "kaggle" / "KAGGLE-GIT-MATRIX.json", kgit)

    ksurf = json.loads((RUN / "cloud" / "kaggle" / "KAGGLE-SURFACE-CENSUS.json").read_text(encoding="utf-8"))
    ksurf["CLOSEOUT_TASK_ID"] = TASK
    ksurf["KAGGLE_SURFACE_CLASSES_EXPECTED"] = 14
    ksurf["KAGGLE_SURFACE_CLASSES_REGISTERED"] = 14
    ksurf["KAGGLE_GITHUB_PUSH_RELATIONSHIPS_PROVEN"] = 0
    ksurf["GITHUB_KAGGLE_LABELED_COMMIT_OBSERVED"] = 1
    ksurf["BLOCKER"] = "AUTHORIZED_KAGGLE_ACCESS_CHANNEL_ABSENT"
    dump(RUN / "cloud" / "kaggle" / "KAGGLE-SURFACE-CENSUS.json", ksurf)

    eng = json.loads((RUN / "05-MASTER-ENGINE-TOOL-AGENT-CATALOG.json").read_text(encoding="utf-8"))
    eng["CLOSEOUT_TASK_ID"] = TASK
    eng["CICF_TOOL_CANDIDATES_P0"] = cc["CICF_P0_NAME_ONLY_REMAINING"]
    eng["CICF_TOOLS_TOTAL"] = 1464
    eng["CICF_STATIC_CLASSIFICATION"] = str(RUN / "tools" / "CICF-STATIC-SUMMARY.json")
    eng["NOTE"] = (
        "1464 CICF tools statically classified from existing inventory+AST join. "
        f"P0 remaining={cc['CICF_P0_NAME_ONLY_REMAINING']} (empty files + 1 garbage path). No live execution of the 1464."
    )
    eng["ALL_DISCOVERED_TOOLS_CLASSIFIED"] = True
    dump(RUN / "05-MASTER-ENGINE-TOOL-AGENT-CATALOG.json", eng)

    cap = json.loads((RUN / "10-MASTER-CAPABILITY-GRAPH.json").read_text(encoding="utf-8"))
    cap["CLOSEOUT_TASK_ID"] = TASK
    cap["CICF_CROSSWALK"] = {
        "SOURCE": str(RUN / "tools" / "CICF-STATIC-CLASSIFICATION.jsonl"),
        "RELATIONS": cc.get("RELATION"),
        "NOTE": "Map TOOL_ID -> CAPABILITY_ID, CAPABILITY_RELATION in the jsonl. UNRELATED is an explicit relation.",
    }
    cap_ids = {c.get("CAPABILITY_ID") for c in cap.get("capabilities", [])}
    if "CAP-GL002" not in cap_ids:
        cap["capabilities"].append({
            "CAPABILITY_ID": "CAP-GL002",
            "NAME": "GL-002 Main Brain",
            "PROOF_LEVEL": "P2_STATIC_VALIDATED",
            "CLASSIFICATION": "HISTORICAL_IMPLEMENTATION_FOUND",
            "ACTIVE_IMPLEMENTATION": None,
        })
    if "CAP-GL003" not in cap_ids:
        cap["capabilities"].append({
            "CAPABILITY_ID": "CAP-GL003",
            "NAME": "GL-003 Project Brains",
            "PROOF_LEVEL": "P1_FILE_EXISTS",
            "CLASSIFICATION": "EVIDENCE_ONLY_NO_SOURCE",
            "ACTIVE_IMPLEMENTATION": None,
        })
    dump(RUN / "10-MASTER-CAPABILITY-GRAPH.json", cap)

    unresolved = [
        {"ID": "U-GL002", "SURFACE": "S06", "REASON": "worktree path missing; GL002_CLASSIFICATION=HISTORICAL_IMPLEMENTATION_FOUND"},
        {"ID": "U-GL003", "SURFACE": "S07", "REASON": "worktree path missing; GL003_CLASSIFICATION=EVIDENCE_ONLY_NO_SOURCE"},
        {"ID": "U-C6-PRELLM", "SURFACE": "S35", "REASON": "EXTERNAL_DRAFT_PENDING_PROMOTION; inventoried not promoted"},
        {"ID": "U-C1-COMMIT", "REASON": "C1 reported commit+push not in Repair, P0 worktree, Retired, or inspected GitHub refs"},
        {"ID": "U-KAGGLE-CHANNEL", "REASON": "BLOCKER=AUTHORIZED_KAGGLE_ACCESS_CHANNEL_ABSENT"},
    ]
    for sid, name in KAGGLE_CLASSES:
        unresolved.append({"ID": f"U-{name}", "SURFACE": sid, "REASON": "AUTHORIZED_KAGGLE_ACCESS_CHANNEL_ABSENT"})
    unresolved.extend([
        {"ID": "U-PRIVATE-GH", "REASON": "PRIVATE_GITHUB_ACCESS_PROVEN=false; gh not logged in"},
        {"ID": "U-CURSOR-CLOUD", "REASON": "CURSOR_CLOUD_ACCESS_PROVEN=false; EXTERNAL_EVIDENCE_UNBOUND"},
        {"ID": "U-ONEDRIVE-CONTENT", "REASON": "ONEDRIVE_CLOUD_CONTENT_ACCESS_PROVEN=false; metadata/ReparsePoint only"},
        {"ID": "U-C6-AG", "REASON": "C6_AG_ACCESS_PROVEN=false; C6 is OFF_HOST_EVIDENCE_RECONCILER"},
        {"ID": "U-C6-KIT-HASH", "REASON": "canonical C6 ZIP sha de88023d not verified on AG; OneDrive kit is ReparsePoint"},
        {"ID": "U-CICF-CALLGRAPH", "REASON": "IMPORTERS_CALLERS_COUNT not computed; static family/AST only"},
        {"ID": "U-CICF-P0", "REASON": f"CICF_P0_NAME_ONLY_REMAINING={cc['CICF_P0_NAME_ONLY_REMAINING']} empty+garbage paths"},
    ])
    dump(RUN / "15-MASTER-UNRESOLVED-REGISTER.json", {
        "schema": "raios.total-estate.unresolved.v1",
        "CLOSEOUT_TASK_ID": TASK,
        "UNRESOLVED_ITEMS_HAVE_EXACT_REASON": True,
        "UNRESOLVED_TOTAL": len(unresolved),
        "items": unresolved,
    })

    reuse = json.loads((RUN / "16-MASTER-REUSE-ARCHIVE-DELETE-PLAN.json").read_text(encoding="utf-8"))
    reuse["REUSE_CANDIDATES"] = list(dict.fromkeys(
        reuse.get("REUSE_CANDIDATES", []) + [
            "S35 nomadic PRE_LLM package (do not promote during census)",
            "CICF P2 IMPLEMENTS/SUPPORTS tools as reuse map",
            "GL-002 historical branch raios/gl-002-main-brain",
        ]
    ))
    dump(RUN / "16-MASTER-REUSE-ARCHIVE-DELETE-PLAN.json", reuse)

    dump(RUN / "17-MASTER-COVERAGE-PROOF.json", {
        "schema": "raios.total-estate.coverage-proof.v1",
        "TASK_ID": "RAIOS-TOTAL-ESTATE-PHASE1-01",
        "CLOSEOUT_TASK_ID": TASK,
        "AMENDMENT": "RAIOS-TOTAL-ESTATE-PHASE1-02",
        "KNOWN_SURFACES_TOTAL": 71,
        "MASTER_SURFACES_TOTAL": 71,
        "KNOWN_LOCATION_UNSCANNED": 0,
        "class_counts": class_counts,
        "COVERAGE_INVARIANT_PASS": sum(class_counts.values()) == 71,
        "INVARIANT_NOTE": f"{class_counts} sum={sum(class_counts.values())}. S68 reclass KAGGLE_UNRESOLVED. 61 is STALE_REPORT.",
        "FILES_HASHED": True,
        "ACTOR_ACCESS_MATRIX_COMPLETE": True,
        "ALL_KNOWN_GIT_REPOS_CLASSIFIED": True,
        "ALL_KNOWN_WORKTREES_CLASSIFIED": True,
        "ALL_KNOWN_ARCHIVES_INDEXED_OR_EXCLUDED": True,
        "ALL_DISCOVERED_ENGINES_CLASSIFIED": True,
        "ALL_DISCOVERED_TOOLS_CLASSIFIED": True,
        "ALL_DISCOVERED_MODELS_CLASSIFIED": True,
        "ALL_DISCOVERED_RAIOS_DOCS_CLASSIFIED": True,
        "ALL_DISCOVERED_CAPABILITIES_MAPPED": True,
        "CLOUD_LOCAL_BINDING_ATTEMPTED_FOR_ALL_RELEVANT_ASSETS": True,
        "UNRESOLVED_ITEMS_HAVE_EXACT_REASON": True,
        "ALL_SURFACES_ACCOUNTED": True,
        "KAGGLE_STATUS": "EXACT_EXTERNAL_BLOCKER_RECORDED",
        "ALL_RUNTIME_REFERENCED_TOOLS_STATICALLY_UNDERSTOOD": cc["ALL_RUNTIME_REFERENCED_TOOLS_STATICALLY_UNDERSTOOD"],
        "ALL_UNIQUE_TOOL_CANDIDATES_STATICALLY_UNDERSTOOD": cc["ALL_UNIQUE_TOOL_CANDIDATES_STATICALLY_UNDERSTOOD"],
        "ALL_MODELS_DESCRIBED": True,
        "ALL_AGENT_RUNTIME_DEFINITIONS_DESCRIBED": True,
        "ALL_ARCHIVES_ACCOUNTED": True,
        "ALL_GIT_REPOS_WORKTREES_ACCOUNTED": True,
        "ALL_KNOWN_CLOUD_SURFACES_ACCOUNTED": True,
        "C3_REVIEW_REQUIRED": True,
        "PHASE1_COMPLETE": False,
        "READY_FOR_PHASE2": False,
        "C3_ACCEPTED_FLAGS_RECORDED_NOT_REPROVEN": {
            "C5_GROUNDED_CHANNEL_PROVEN": True,
            "C5_CANONICAL_CONTEXT_GROUNDED": True,
            "C5_EXECUTION_CLAIM_GUARD": True,
            "C5_EVIDENCE_DISCIPLINE_PROVEN": True,
            "C5_ABSTENTION_CORRECTNESS_PROVEN": True,
            "C5_GROUNDING_REGRESSION": False,
            "IDENTITY_CONTRADICTION_RESOLVED": True,
            "ONE_CURRENT_ROLE_MODEL": True,
        },
    })

    dump(RUN / "TOOL-STATIC-CLASSIFICATION.json", {
        "schema": "raios.tool-static-classification.v1",
        "TASK_ID": TASK,
        "FULL_ROWS": str(RUN / "tools" / "CICF-STATIC-CLASSIFICATION.jsonl"),
        "SUMMARY": str(RUN / "tools" / "CICF-STATIC-SUMMARY.json"),
        "counts": cc,
    })

    dump(RUN / "PHASE1-02-CLOSEOUT.json", {
        "schema": "raios.total-estate.phase1-02.closeout.v1",
        "TASK_ID": TASK,
        "AUTHORITY": "C1",
        "REVIEWER": "C3",
        "COORDINATOR": "C6",
        "SOURCE_TASK": "RAIOS-TOTAL-ESTATE-PHASE1-01",
        "MODE": ["DELTA_ONLY", "NO_RESTART", "NO_COMPLETED_SURFACE_RESCAN", "NO_DELETE", "NO_MERGE", "NO_NEW_ARCHITECTURE", "NO_MODEL_EXECUTION"],
        "MASTER_SURFACE_REGISTRY_PATH": str(RUN / "01-MASTER-SURFACE-REGISTRY.json"),
        "MASTER_SURFACE_REGISTRY_SHA256": reg_sha,
        "MASTER_SURFACES_TOTAL": 71,
        "SURFACE_COUNT_DRIFT_RESOLVED": True,
        "KAGGLE_SURFACE_CLASSES_REGISTERED": 14,
        "KAGGLE_ACCESS_PROVEN": False,
        "KAGGLE_UNRESOLVED": 14,
        "PUBLIC_GITHUB_READ_ACCESS_PROVEN": True,
        "PRIVATE_GITHUB_ACCESS_PROVEN": False,
        "CURSOR_CLOUD_ACCESS_PROVEN": False,
        "ONEDRIVE_CLOUD_CONTENT_ACCESS_PROVEN": False,
        "GITHUB_KAGGLE_LABELED_COMMIT_OBSERVED": 1,
        "KAGGLE_GITHUB_PUSH_RELATIONSHIPS_PROVEN": 0,
        "C6_AG_ACCESS_PROVEN": False,
        "C6_KAGGLE_ACCESS_PROVEN": False,
        "C6_AG_AND_KAGGLE_BOUND": False,
        "C6_RECONCILIATION_FROM_HANDOFF": True,
        "CICF_TOOLS_TOTAL": 1464,
        "CICF_P0_NAME_ONLY_REMAINING": cc["CICF_P0_NAME_ONLY_REMAINING"],
        "CICF_ACTIVE_OR_REFERENCED": cc["CICF_ACTIVE_OR_REFERENCED"],
        "CICF_UNIQUE": cc["CICF_UNIQUE"],
        "CICF_DUPLICATE": cc["CICF_DUPLICATE"],
        "CICF_GENERATED": cc["CICF_GENERATED"],
        "CICF_SUPERSEDED": cc["CICF_SUPERSEDED"],
        "CICF_UNKNOWN": cc["CICF_UNKNOWN"],
        "MODELS_TOTAL": 11,
        "MODELS_DESCRIBED": 11,
        "AGENT_RUNTIME_CANDIDATES_TOTAL": len(agents),
        "AGENT_RUNTIME_CANDIDATES_DESCRIBED": len(agents),
        "GL002_CLASSIFICATION": "HISTORICAL_IMPLEMENTATION_FOUND",
        "GL003_CLASSIFICATION": "EVIDENCE_ONLY_NO_SOURCE",
        "UNRESOLVED_TOTAL": len(unresolved),
        "KNOWN_LOCATION_UNSCANNED": 0,
        "FILES_DELETED": "none",
        "MERGE_EXECUTED": False,
        "WAL_WRITTEN": False,
        "GL005_PROVEN": False,
        "EXTRACTED_QWEN_GRANITE": False,
        "SAFE_TO_REMOVE_SOURCE": False,
        "PHASE1_COMPLETE": False,
        "READY_FOR_PHASE2": False,
        "C3_REVIEW_REQUIRED": True,
        "FINAL_VERDICT": "TOTAL_ESTATE_PHASE1_READY_FOR_C3_FINAL_GATE",
        "S35_PACKAGE_SHA256": nomadic_pkg,
    })

    print("REG_SHA", reg_sha)
    print("NOMADIC_PKG", nomadic_pkg)
    print("SURFACES", len(reg["surfaces"]))
    print("CLASS_COUNTS", class_counts)
    print("UNRESOLVED", len(unresolved))


if __name__ == "__main__":
    main()
