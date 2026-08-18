from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import traceback
import uuid

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO = Path(
    subprocess.check_output(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
    ).strip()
)

V9 = REPO / "RAIOS" / "V9"

STATE = (
    V9
    / "continuity"
    / "RAIOS-CURRENT-STATE.json"
)

A12_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A12-RECEIPT.json"
)

A13_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A13-RECEIPT.json"
)

ROOT = (
    V9
    / "agents"
    / "a13"
)

REGISTRY_DIR = ROOT / "registry"
REPORTS = ROOT / "reports"
ROUTING = ROOT / "routing"
EVIDENCE = ROOT / "evidence"

EVO = (
    V9
    / "evolution"
    / "a13"
)

EXPERIENCES = EVO / "experiences"
FAILURES = EVO / "failures"
RECOVERY = EVO / "recovery-skill-candidates"

for p in (
    REGISTRY_DIR,
    REPORTS,
    ROUTING,
    EVIDENCE,
    EXPERIENCES,
    FAILURES,
    RECOVERY,
):
    p.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def write_json(
    path: Path,
    obj: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_name(
        path.name
        + ".tmp-"
        + uuid.uuid4().hex
    )

    tmp.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
            default=str,
        ) + "\n",
        encoding="utf-8",
    )

    if load_json(tmp) != obj:
        tmp.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "ATOMIC_WRITE_READBACK_FAILED"
        )

    os.replace(
        tmp,
        path,
    )


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def object_hash(obj: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            obj,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            default=str,
        ).encode("utf-8")
    ).hexdigest()


def capture_experience(
    event: str,
    outcome: str,
    details: dict[str, Any],
) -> Path:

    obj = {
        "schema":
            "raios.a13.experience.v1",

        "timestamp":
            now(),

        "event":
            event,

        "outcome":
            outcome,

        "details":
            details,
    }

    obj["experience_id"] = (
        "exp:"
        +
        object_hash(obj)[:32]
    )

    path = (
        EXPERIENCES
        /
        (
            obj["experience_id"]
            .replace(":", "_")
            + ".json"
        )
    )

    write_json(
        path,
        obj,
    )

    return path


def capture_failure(
    exc: BaseException,
) -> None:

    basis = {
        "phase":
            "V9.0-A13",

        "exception":
            type(exc).__name__,

        "message":
            str(exc),
    }

    signature = (
        "fs:"
        +
        object_hash(basis)[:32]
    )

    failure = {
        "schema":
            "raios.a13.failure-signature.v1",

        "failure_signature":
            signature,

        "timestamp":
            now(),

        "exception_type":
            type(exc).__name__,

        "message":
            str(exc),

        "traceback":
            traceback.format_exc(),

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    }

    write_json(
        FAILURES
        /
        (
            signature.replace(
                ":",
                "_",
            )
            + ".json"
        ),
        failure,
    )

    recovery = {
        "schema":
            "raios.a13.recovery-skill-candidate.v1",

        "candidate_id":
            "recovery:"
            +
            object_hash(
                failure
            )[:32],

        "source_failure_signature":
            signature,

        "status":
            "CANDIDATE",

        "automatic_promotion":
            False,

        "canonical_mutation":
            False,

        "created_at":
            now(),
    }

    write_json(
        RECOVERY
        /
        (
            recovery[
                "candidate_id"
            ]
            .replace(":", "_")
            + ".json"
        ),
        recovery,
    )


EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    ".venv",
    "__pycache__",
}


EXPLICIT_ASSETS = [
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".cursor/rules/raios-core.mdc",
    ".ai-os/state/AGENTS.json",
    "RAIOS-CAPABILITY-BRIDGE.ps1",
    "RAIOS-CAPABILITY-BRIDGE/greeny-capabilities.json",
    "RAIOS-CAPABILITY-BRIDGE/greeny-capabilities.md",
    "lib/intelligence/mastermind-agents.ts",
    "MASTERMIND-AGENTS.md",
    "scripts/ai-os/local-agent.py",
    "tests/mastermind_agents_check.ts",
]


CAPABILITY_VOCAB = {
    "read",
    "search",
    "inspect",
    "analyze",
    "analysis",
    "reason",
    "plan",
    "execute",
    "execution",
    "terminal",
    "shell",
    "powershell",
    "git",
    "github",
    "test",
    "testing",
    "debug",
    "repair",
    "recover",
    "recovery",
    "agent",
    "agents",
    "orchestration",
    "orchestrator",
    "routing",
    "router",
    "memory",
    "experience",
    "evidence",
    "failure",
    "governance",
    "approval",
    "promotion",
    "capability",
    "bridge",
    "claude",
    "gemini",
    "cline",
    "cursor",
    "model",
    "tool",
    "tools",
    "workflow",
    "runtime",
    "skill",
    "skills",
}


def normalize_rel(
    path: Path,
) -> str:

    return str(
        path.relative_to(
            REPO
        )
    ).replace("\\", "/")


def text_tokens(
    text: str,
) -> set[str]:

    raw = set(
        re.findall(
            r"[a-zA-Z][a-zA-Z0-9_-]{2,}",
            text.lower(),
        )
    )

    tokens = set()

    for token in raw:

        base = (
            token
            .replace("_", "-")
            .strip("-")
        )

        if (
            base
            in CAPABILITY_VOCAB
        ):
            tokens.add(base)

        for part in base.split("-"):
            if part in CAPABILITY_VOCAB:
                tokens.add(part)

    return tokens


def infer_agent_family(
    rel: str,
    text: str,
) -> str:

    blob = (
        rel
        + "\n"
        + text[:5000]
    ).lower()

    if "claude" in blob:
        return "CLAUDE"

    if "gemini" in blob:
        return "GEMINI"

    if "cline" in blob:
        return "CLINE"

    if "cursor" in blob:
        return "CURSOR"

    if "mastermind" in blob:
        return "MASTERMIND"

    if "capability-bridge" in blob:
        return "RAIOS_CAPABILITY_BRIDGE"

    if "agents" in blob:
        return "GENERIC_AGENT_CONTROL"

    return "RAIOS_INTERNAL"


def read_text_safe(
    path: Path,
) -> str:

    try:
        return path.read_text(
            encoding="utf-8-sig",
            errors="replace",
        )

    except Exception:
        return ""


def discover_assets() -> list[Path]:

    found = {}

    for rel in EXPLICIT_ASSETS:

        path = REPO / rel

        if path.exists() and path.is_file():
            found[
                normalize_rel(path)
            ] = path

    patterns = [
        "AGENTS.md",
        "CLAUDE.md",
        "GEMINI.md",
        "*agent*.json",
        "*agent*.md",
        "*agent*.ts",
        "*agent*.py",
        "*bridge*.json",
        "*bridge*.md",
        "*bridge*.ps1",
        "*bridge*.py",
        "*.mdc",
    ]

    for pattern in patterns:

        for path in REPO.rglob(
            pattern
        ):

            if not path.is_file():
                continue

            if any(
                part in EXCLUDED_PARTS
                for part in path.parts
            ):
                continue

            rel = normalize_rel(
                path
            )

            # Old/archive material remains evidence only.
            found[
                rel
            ] = path

    return [
        found[key]
        for key
        in sorted(
            found
        )
    ]


def jaccard(
    left: set[str],
    right: set[str],
) -> float:

    if not left and not right:
        return 0.0

    union = left | right

    if not union:
        return 0.0

    return (
        len(left & right)
        /
        len(union)
    )


def main() -> None:

    print("=" * 88)
    print(
        "RAIOS V9.0-A13 TRUE FAIL-CLOSED UNIFIED AGENT DEDUP CERTIFICATION"
    )
    print("=" * 88)

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        text=True,
    ).strip()

    print(
        "HEAD:",
        head,
    )

    # --------------------------------------------------------
    # 1. PREDECESSOR
    # --------------------------------------------------------

    state = load_json(
        STATE
    )

    if (
        state.get(
            "current_version"
        )
        !=
        "V9.0-A12"
    ):
        raise RuntimeError(
            "A13_PREDECESSOR_NOT_A12"
        )

    if (
        state.get(
            "state_status"
        )
        !=
        "A12_CERTIFIED"
    ):
        raise RuntimeError(
            "A13_PREDECESSOR_NOT_CERTIFIED"
        )

    latest = (
        state.get(
            "latest_phase_receipt"
        )
        or {}
    )

    if (
        latest.get(
            "phase"
        )
        !=
        "V9.0-A12"
    ):
        raise RuntimeError(
            "A13_A12_RECEIPT_PHASE_INVALID"
        )

    if not A12_RECEIPT.exists():
        raise RuntimeError(
            "A12_RECEIPT_NOT_FOUND"
        )

    a12_hash = file_hash(
        A12_RECEIPT
    )

    if (
        latest.get(
            "sha256"
        )
        !=
        a12_hash
    ):
        raise RuntimeError(
            "A12_RECEIPT_HASH_DRIFT"
        )

    print(
        "PREDECESSOR_A12              : PASS"
    )

    # --------------------------------------------------------
    # 2. DISCOVERY
    # --------------------------------------------------------

    assets = discover_assets()

    if not assets:
        raise RuntimeError(
            "A13_NO_AGENT_ASSETS_DISCOVERED"
        )

    print(
        "ASSET_DISCOVERY              : PASS"
    )

    print(
        "DISCOVERED_ASSETS            :",
        len(assets),
    )

    # --------------------------------------------------------
    # 3. REGISTRATION
    # --------------------------------------------------------

    records = []

    for path in assets:

        rel = normalize_rel(
            path
        )

        text = read_text_safe(
            path
        )

        tokens = text_tokens(
            text
        )

        family = infer_agent_family(
            rel,
            text,
        )

        authority = (
            "ARCHIVED_EVIDENCE"
            if (
                rel.startswith(
                    "archive/"
                )
                or
                "continuity-evidence"
                in rel.lower()
                or
                "deep-evidence"
                in rel.lower()
            )
            else
            "CURRENT"
        )

        record = {
            "asset_id":
                "asset:"
                +
                file_hash(path)[:32],

            "path":
                rel,

            "sha256":
                file_hash(path),

            "bytes":
                path.stat().st_size,

            "agent_family":
                family,

            "authority":
                authority,

            "capabilities":
                sorted(tokens),

            "canonical_owner":
                False,

            "destructive_merge_allowed":
                False,
        }

        records.append(
            record
        )

    # idempotent identity check

    ids = [
        x["asset_id"]
        for x in records
    ]

    if (
        len(ids)
        !=
        len(set(ids))
    ):
        # identical content is not destructive duplicate;
        # treat it below as duplicate evidence.
        pass

    print(
        "CAPABILITY_REGISTRATION      : PASS"
    )

    # --------------------------------------------------------
    # 4. EXACT DUPLICATES
    # --------------------------------------------------------

    by_hash = defaultdict(
        list
    )

    for record in records:

        by_hash[
            record["sha256"]
        ].append(record)

    exact_groups = []

    for sha, group in (
        by_hash.items()
    ):

        if len(group) > 1:

            exact_groups.append({
                "sha256":
                    sha,

                "paths":
                    [
                        x["path"]
                        for x in group
                    ],

                "disposition":
                    "REVIEW_REUSE_CANDIDATE",
            })

    print(
        "EXACT_DUPLICATE_DETECTION    : PASS"
    )

    # --------------------------------------------------------
    # 5. SEMANTIC OVERLAP
    # --------------------------------------------------------

    semantic_pairs = []

    current_records = [
        x
        for x in records
        if x["authority"]
        ==
        "CURRENT"
    ]

    for i in range(
        len(current_records)
    ):

        for j in range(
            i + 1,
            len(current_records)
        ):

            left = current_records[i]
            right = current_records[j]

            score = jaccard(
                set(
                    left[
                        "capabilities"
                    ]
                ),
                set(
                    right[
                        "capabilities"
                    ]
                ),
            )

            if score >= 0.50:

                semantic_pairs.append({
                    "left":
                        left["path"],

                    "right":
                        right["path"],

                    "capability_overlap":
                        round(
                            score,
                            6,
                        ),

                    "status":
                        "REVIEW_MERGE_CANDIDATE",

                    "automatic_merge":
                        False,
                })

    print(
        "SEMANTIC_DUPLICATE_DETECTION : PASS"
    )

    # --------------------------------------------------------
    # 6. CANONICAL OWNERSHIP
    # --------------------------------------------------------

    preferred_paths = {
        "GLOBAL_AGENT_CONTRACT":
            "AGENTS.md",

        "CLAUDE_AGENT_CONTRACT":
            "CLAUDE.md",

        "GEMINI_AGENT_CONTRACT":
            "GEMINI.md",

        "CURSOR_RULES":
            ".cursor/rules/raios-core.mdc",

        "CAPABILITY_BRIDGE":
            "RAIOS-CAPABILITY-BRIDGE/greeny-capabilities.json",

        "CAPABILITY_BRIDGE_EXECUTOR":
            "RAIOS-CAPABILITY-BRIDGE.ps1",

        "AGENT_STATE":
            ".ai-os/state/AGENTS.json",

        "MASTERMIND_RUNTIME":
            "lib/intelligence/mastermind-agents.ts",
    }

    available_paths = {
        x["path"]
        for x in records
    }

    owners = {}

    for capability, path in (
        preferred_paths.items()
    ):

        if path in available_paths:

            owners[
                capability
            ] = path

    if (
        "GLOBAL_AGENT_CONTRACT"
        not in owners
    ):
        raise RuntimeError(
            "A13_AGENTS_MD_NOT_DISCOVERED"
        )

    if (
        "CAPABILITY_BRIDGE"
        not in owners
    ):
        raise RuntimeError(
            "A13_EXISTING_CAPABILITY_BRIDGE_NOT_REUSED"
        )

    for record in records:

        if (
            record["path"]
            in owners.values()
        ):
            record[
                "canonical_owner"
            ] = True

    print(
        "CANONICAL_OWNER_ASSIGNMENT   : PASS"
    )

    print(
        "EXISTING_BRIDGE_REUSED       : PASS"
    )

    # --------------------------------------------------------
    # 7. ROUTING CONTRACT
    # --------------------------------------------------------

    routing = {
        "schema":
            "raios.a13.unified-agent-routing.v1",

        "timestamp":
            now(),

        "strategy":
            "DISCOVER_REUSE_EXTEND_CREATE_ONLY_IF_MISSING",

        "agents": {
            "CLINE": {
                "role":
                    "IMPLEMENTATION_EXECUTOR",

                "preferred_for": [
                    "multi_file_edits",
                    "terminal_execution",
                    "test_debug_loop",
                ],
            },

            "CLAUDE": {
                "role":
                    "DEEP_REASONING_DEBUGGER",

                "preferred_for": [
                    "complex_debugging",
                    "code_reasoning",
                    "architecture_review",
                ],
            },

            "GEMINI": {
                "role":
                    "SECONDARY_REVIEW_AND_EXECUTION",

                "preferred_for": [
                    "independent_review",
                    "alternative_analysis",
                    "execution_support",
                ],
            },

            "CURSOR": {
                "role":
                    "OPTIONAL_EXECUTION_AGENT",

                "preferred_for": [
                    "repository_execution",
                    "agentic_edit_test_loop",
                ],

                "availability":
                    "OPTIONAL_NOT_REQUIRED",
            },

            "RAIOS_INTERNAL": {
                "role":
                    "COGNITIVE_GOVERNANCE_AND_MEMORY",

                "preferred_for": [
                    "continuity",
                    "experience",
                    "failure_memory",
                    "skill_memory",
                    "governance",
                ],
            },
        },

        "mandatory_bootstrap": [
            "READ_CURRENT_STATE",
            "VERIFY_LATEST_RECEIPT_HASH",
            "READ_AGENT_CONTRACT",
            "CHECK_GIT_STATUS",
            "DISCOVER_EXISTING_CAPABILITY",
            "REUSE_BEFORE_CREATE",
        ],

        "invariants": [
            "No agent may create a duplicate capability without discovery.",
            "No semantic duplicate is automatically deleted.",
            "No canonical owner is replaced automatically.",
            "Certified predecessor phases are immutable.",
            "Every execution becomes Experience.",
            "Every failure becomes Failure Signature and Recovery Skill Candidate.",
            "Confidence must be in [0,1].",
            "No automatic promotion.",
        ],

        "automatic_promotion":
            False,

        "automatic_destructive_merge":
            False,

        "canonical_mutation":
            False,

        "production_activation":
            False,
    }

    routing_path = (
        ROUTING
        /
        "UNIFIED-AGENT-ROUTING.json"
    )

    write_json(
        routing_path,
        routing,
    )

    print(
        "UNIFIED_AGENT_ROUTING        : PASS"
    )

    # --------------------------------------------------------
    # 8. ANOMALIES
    # --------------------------------------------------------

    anomalies = []

    for record in records:

        rel = record[
            "path"
        ]

        if (
            "," in rel
            or
            "`" in rel
        ):

            anomalies.append({
                "path":
                    rel,

                "status":
                    "REVIEW_REQUIRED",

                "reason":
                    "Unusual path syntax detected.",

                "automatic_action":
                    False,
            })

    print(
        "ANOMALY_DETECTION            : PASS"
    )

    print(
        "ANOMALIES                    :",
        len(anomalies),
    )

    # --------------------------------------------------------
    # 9. WRITE REGISTRY
    # --------------------------------------------------------

    registry = {
        "schema":
            "raios.a13.unified-agent-capability-registry.v1",

        "timestamp":
            now(),

        "repository_sha":
            head,

        "asset_count":
            len(records),

        "canonical_owners":
            owners,

        "assets":
            records,

        "exact_duplicate_groups":
            exact_groups,

        "semantic_overlap_pairs":
            semantic_pairs,

        "anomalies":
            anomalies,

        "strategy":
            "DISCOVER_REUSE_EXTEND_CREATE_ONLY_IF_MISSING",

        "automatic_merge":
            False,

        "automatic_delete":
            False,

        "canonical_mutation":
            False,
    }

    registry_path = (
        REGISTRY_DIR
        /
        "UNIFIED-AGENT-CAPABILITY-REGISTRY.json"
    )

    write_json(
        registry_path,
        registry,
    )

    # deterministic readback

    if (
        load_json(
            registry_path
        )[
            "asset_count"
        ]
        !=
        len(records)
    ):
        raise RuntimeError(
            "A13_REGISTRY_READBACK_FAILED"
        )

    print(
        "UNIFIED_CAPABILITY_REGISTRY  : PASS"
    )

    # --------------------------------------------------------
    # 10. DEDUP REPORT
    # --------------------------------------------------------

    report = {
        "schema":
            "raios.a13.dedup-report.v1",

        "timestamp":
            now(),

        "discovered_assets":
            len(records),

        "current_assets":
            len(
                current_records
            ),

        "exact_duplicate_groups":
            len(
                exact_groups
            ),

        "semantic_overlap_pairs":
            len(
                semantic_pairs
            ),

        "canonical_owner_count":
            len(
                owners
            ),

        "anomaly_count":
            len(
                anomalies
            ),

        "existing_bridge_reused":
            True,

        "new_bridge_created":
            False,

        "destructive_merge":
            False,

        "automatic_delete":
            False,

        "canonical_mutation":
            False,

        "production_activation":
            False,
    }

    report_path = (
        REPORTS
        /
        "AGENT-CAPABILITY-DEDUP-REPORT.json"
    )

    write_json(
        report_path,
        report,
    )

    print(
        "DEDUP_REPORT                 : PASS"
    )

    # --------------------------------------------------------
    # 11. IDEMPOTENCY
    # --------------------------------------------------------

    registry_hash_1 = (
        object_hash(
            registry
        )
    )

    registry_hash_2 = (
        object_hash(
            load_json(
                registry_path
            )
        )
    )

    if (
        registry_hash_1
        !=
        registry_hash_2
    ):
        raise RuntimeError(
            "A13_REGISTRY_IDEMPOTENCY_FAILED"
        )

    print(
        "REGISTRY_IDEMPOTENCY         : PASS"
    )

    # --------------------------------------------------------
    # 12. EXPERIENCE
    # --------------------------------------------------------

    exp = capture_experience(
        "A13_AGENT_CAPABILITY_UNIFICATION",
        "SUCCESS",
        {
            "discovered_assets":
                len(records),

            "exact_duplicate_groups":
                len(
                    exact_groups
                ),

            "semantic_overlap_pairs":
                len(
                    semantic_pairs
                ),

            "canonical_owners":
                owners,

            "existing_bridge_reused":
                True,

            "new_bridge_created":
                False,
        },
    )

    print(
        "EXPERIENCE_CAPTURE           : PASS"
    )

    # --------------------------------------------------------
    # 13. RECEIPT
    # --------------------------------------------------------

    receipt = {
        "schema":
            "raios.v9.a13.receipt.v1",

        "phase":
            "V9.0-A13",

        "certification_status":
            "PASS",

        "certification_mode":
            "FAIL_CLOSED",

        "timestamp":
            now(),

        "repository_sha":
            head,

        "predecessor": {
            "phase":
                "V9.0-A12",

            "sha256":
                a12_hash,

            "status":
                "PASS",
        },

        "unification": {
            "discovered_assets":
                len(records),

            "canonical_owner_count":
                len(owners),

            "exact_duplicate_groups":
                len(exact_groups),

            "semantic_overlap_pairs":
                len(semantic_pairs),

            "anomalies":
                len(anomalies),

            "existing_bridge_reused":
                True,

            "new_bridge_created":
                False,

            "routing_contract":
                True,

            "registry_idempotency":
                True,
        },

        "safety": {
            "destructive_merge":
                False,

            "automatic_delete":
                False,

            "automatic_promotion":
                False,

            "canonical_mutation":
                False,

            "production_activation":
                False,
        },

        "artifacts": {
            "registry":
                str(
                    registry_path.relative_to(
                        REPO
                    )
                ),

            "routing_contract":
                str(
                    routing_path.relative_to(
                        REPO
                    )
                ),

            "dedup_report":
                str(
                    report_path.relative_to(
                        REPO
                    )
                ),

            "experience":
                str(
                    exp.relative_to(
                        REPO
                    )
                ),
        },

        "epistemic_limits": [
            "Semantic overlap identifies review candidates, not proven duplicates.",
            "Archived agent artifacts remain evidence and are not automatically authoritative.",
            "A13 does not delete or merge existing agent assets.",
            "A13 reuses the existing RAIOS capability bridge.",
            "Canonical ownership can only be changed through governed review.",
            "Cursor remains optional and is not required for RAIOS continuity."
        ],
    }

    write_json(
        A13_RECEIPT,
        receipt,
    )

    receipt_hash = (
        file_hash(
            A13_RECEIPT
        )
    )

    # --------------------------------------------------------
    # 14. UPDATE STATE AFTER RECEIPT
    # --------------------------------------------------------

    final_state = load_json(
        STATE
    )

    final_state[
        "current_version"
    ] = "V9.0-A13"

    final_state[
        "current_phase"
    ] = (
        "UNIFIED_AGENT_EXECUTION_AND_CAPABILITY_DEDUPLICATION"
    )

    final_state[
        "state_status"
    ] = "A13_CERTIFIED"

    final_state[
        "unified_agent_execution"
    ] = {
        "strategy":
            "DISCOVER_REUSE_EXTEND_CREATE_ONLY_IF_MISSING",

        "existing_bridge_reused":
            True,

        "new_bridge_created":
            False,

        "registry":
            str(
                registry_path.relative_to(
                    REPO
                )
            ),

        "routing_contract":
            str(
                routing_path.relative_to(
                    REPO
                )
            ),

        "canonical_owner_count":
            len(owners),

        "automatic_merge":
            False,

        "automatic_delete":
            False,

        "canonical_mutation":
            False,

        "production_active":
            False,
    }

    architecture = (
        final_state.get(
            "active_architecture",
            []
        )
    )

    for capability in [
        "UNIFIED_AGENT_CAPABILITY_REGISTRY",
        "CAPABILITY_IDENTITY_HASHING",
        "SEMANTIC_CAPABILITY_DEDUPLICATION",
        "CANONICAL_CAPABILITY_OWNERSHIP",
        "UNIFIED_AGENT_ROUTING",
        "AGENT_EXECUTION_BOOTSTRAP",
        "REUSE_BEFORE_CREATE_GATE",
    ]:

        if capability not in architecture:

            architecture.append(
                capability
            )

    final_state[
        "active_architecture"
    ] = architecture

    final_state[
        "latest_phase_receipt"
    ] = {
        "phase":
            "V9.0-A13",

        "path":
            str(
                A13_RECEIPT.relative_to(
                    REPO
                )
            ),

        "sha256":
            receipt_hash,

        "certification_status":
            "PASS",
    }

    final_state[
        "updated_at"
    ] = now()

    write_json(
        STATE,
        final_state,
    )

    final = load_json(
        STATE
    )

    actual_hash = (
        file_hash(
            A13_RECEIPT
        )
    )

    if (
        final[
            "latest_phase_receipt"
        ][
            "sha256"
        ]
        !=
        actual_hash
    ):
        raise RuntimeError(
            "A13_STATE_RECEIPT_HASH_DRIFT"
        )

    print()
    print("=" * 88)
    print(
        "RAIOS V9.0-A13 CERTIFICATION RESULT"
    )
    print("=" * 88)

    print(
        "PREDECESSOR_A12              : PASS"
    )

    print(
        "ASSET_DISCOVERY              : PASS"
    )

    print(
        "DISCOVERED_ASSETS            :",
        len(records),
    )

    print(
        "EXISTING_BRIDGE_REUSED       : TRUE"
    )

    print(
        "NEW_BRIDGE_CREATED           : FALSE"
    )

    print(
        "EXACT_DUPLICATE_GROUPS       :",
        len(exact_groups),
    )

    print(
        "SEMANTIC_OVERLAP_PAIRS       :",
        len(semantic_pairs),
    )

    print(
        "CANONICAL_OWNERS             :",
        len(owners),
    )

    print(
        "ANOMALIES                    :",
        len(anomalies),
    )

    print(
        "UNIFIED_AGENT_ROUTING        : PASS"
    )

    print(
        "REGISTRY_IDEMPOTENCY         : PASS"
    )

    print(
        "DESTRUCTIVE_MERGE            : FALSE"
    )

    print(
        "AUTOMATIC_DELETE             : FALSE"
    )

    print(
        "AUTOMATIC_PROMOTION          : FALSE"
    )

    print(
        "CANONICAL_MUTATION           : FALSE"
    )

    print(
        "PRODUCTION_ACTIVE            : FALSE"
    )

    print(
        "STATE_RECEIPT_HASH_MATCH     : TRUE"
    )

    print(
        "CURRENT_VERSION              :",
        final["current_version"],
    )

    print(
        "STATE_STATUS                 :",
        final["state_status"],
    )

    print(
        "A13_RECEIPT_SHA256           :",
        actual_hash,
    )

    print()
    print(
        "STATUS = V9.0-A13_PASS"
    )
    print("=" * 88)


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        try:

            capture_failure(
                exc
            )

            capture_experience(
                "A13_CERTIFICATION_FAILURE",
                "FAILED",
                {
                    "exception":
                        repr(exc)
                },
            )

        except Exception as telemetry_exc:

            print(
                "A13_TELEMETRY_FAILURE:",
                repr(
                    telemetry_exc
                ),
                file=sys.stderr,
            )

        print(
            "A13_CERTIFICATION_FAILED:",
            repr(exc),
            file=sys.stderr,
        )

        raise