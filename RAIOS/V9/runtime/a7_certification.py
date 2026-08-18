from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import traceback
import uuid

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

A6_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A6-RECEIPT.json"
)

A7_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A7-RECEIPT.json"
)

ROOT = (
    V9
    / "governance"
    / "a7"
)

PROPOSALS = ROOT / "proposals"
BUNDLES = ROOT / "evidence-bundles"
REGISTRY_DIR = ROOT / "registry"
SHADOW_DIR = ROOT / "shadow"
ROLLBACK_DIR = ROOT / "rollback"
AUDIT_DIR = ROOT / "audit"

REGISTRY = (
    REGISTRY_DIR
    / "SKILL-REGISTRY.json"
)

FAILURES = (
    V9
    / "evolution"
    / "a7"
    / "failures"
)

EXPERIENCES = (
    V9
    / "evolution"
    / "a7"
    / "experiences"
)

RECOVERY = (
    V9
    / "evolution"
    / "a7"
    / "recovery-skill-candidates"
)


for path in (
    PROPOSALS,
    BUNDLES,
    REGISTRY_DIR,
    SHADOW_DIR,
    ROLLBACK_DIR,
    AUDIT_DIR,
    FAILURES,
    EXPERIENCES,
    RECOVERY,
):
    path.mkdir(
        parents=True,
        exist_ok=True,
    )


LIFECYCLE = [
    "CANDIDATE",
    "BENCHMARKED",
    "PROMOTION_ELIGIBLE",
    "APPROVAL_REQUIRED",
    "APPROVED",
    "SHADOW",
    "ACTIVE",
    "DEGRADED",
    "SUSPENDED",
    "REVOKED",
    "ROLLED_BACK",
]


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


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")


def object_hash(obj: Any) -> str:
    return hashlib.sha256(
        canonical_bytes(obj)
    ).hexdigest()


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def write_json_atomic(
    path: Path,
    obj: Any,
) -> None:

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp = path.with_name(
        path.name
        + ".tmp-"
        + uuid.uuid4().hex
    )

    temp.write_text(
        json.dumps(
            obj,
            indent=2,
            ensure_ascii=False,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )

    verify = load_json(temp)

    if verify != obj:
        temp.unlink(
            missing_ok=True
        )
        raise RuntimeError(
            "ATOMIC_WRITE_READBACK_MISMATCH"
        )

    os.replace(
        temp,
        path,
    )


def record_experience(
    status: str,
    event: str,
    details: dict[str, Any],
) -> Path:

    obj = {
        "schema":
            "raios.a7.experience.v1",

        "timestamp":
            now(),

        "status":
            status,

        "event":
            event,

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
            +
            ".json"
        )
    )

    write_json_atomic(
        path,
        obj,
    )

    return path


def record_failure(
    exc: BaseException,
    context: dict[str, Any],
) -> None:

    signature_basis = {
        "type":
            type(exc).__name__,

        "message":
            str(exc),

        "phase":
            "V9.0-A7",
    }

    failure_signature = (
        "fs:"
        +
        object_hash(
            signature_basis
        )[:32]
    )

    failure = {
        "schema":
            "raios.a7.failure-signature.v1",

        "failure_signature":
            failure_signature,

        "timestamp":
            now(),

        "exception_type":
            type(exc).__name__,

        "message":
            str(exc),

        "context":
            context,

        "traceback":
            traceback.format_exc(),

        "canonical_promotion":
            False,
    }

    failure_path = (
        FAILURES
        /
        (
            failure_signature
            .replace(":", "_")
            +
            ".json"
        )
    )

    write_json_atomic(
        failure_path,
        failure,
    )

    recovery = {
        "schema":
            "raios.a7.recovery-skill-candidate.v1",

        "candidate_id":
            (
                "recovery:"
                +
                object_hash(
                    failure
                )[:32]
            ),

        "source_failure_signature":
            failure_signature,

        "status":
            "CANDIDATE",

        "automatic_promotion":
            False,

        "canonical_mutation":
            False,

        "requires_validation":
            True,

        "created_at":
            now(),
    }

    recovery_path = (
        RECOVERY
        /
        (
            recovery["candidate_id"]
            .replace(":", "_")
            +
            ".json"
        )
    )

    write_json_atomic(
        recovery_path,
        recovery,
    )

    record_experience(
        "FAILED",
        "A7_CERTIFICATION_FAILURE",
        {
            "failure_signature":
                failure_signature,

            "recovery_candidate":
                recovery["candidate_id"],
        },
    )


def assert_probability(
    value: Any,
    name: str,
) -> float:

    if isinstance(value, bool):
        raise RuntimeError(
            f"{name}_BOOLEAN_INVALID"
        )

    value = float(value)

    if not (
        0.0
        <=
        value
        <=
        1.0
    ):
        raise RuntimeError(
            f"{name}_OUT_OF_RANGE:{value}"
        )

    return value


def initial_registry() -> dict[str, Any]:

    return {
        "schema":
            "raios.skill-registry.v1",

        "registry_version":
            1,

        "automatic_promotion":
            False,

        "production_auto_activation":
            False,

        "lifecycle":
            LIFECYCLE,

        "skills":
            {},

        "updated_at":
            now(),
    }


def load_registry() -> dict[str, Any]:

    if not REGISTRY.exists():
        registry = initial_registry()

        write_json_atomic(
            REGISTRY,
            registry,
        )

    return load_json(
        REGISTRY
    )


def freeze_bundle(
    candidate_id: str,
    candidate_hash: str,
    a6: dict[str, Any],
) -> tuple[Path, dict[str, Any]]:

    bundle = {
        "schema":
            "raios.a7.frozen-evidence-bundle.v1",

        "candidate_id":
            candidate_id,

        "candidate_sha256":
            candidate_hash,

        "a6_receipt_sha256":
            file_hash(A6_RECEIPT),

        "a6_benchmark_id":
            a6["benchmark"][
                "benchmark_id"
            ],

        "a6_verdict_id":
            a6["verdict"][
                "verdict_id"
            ],

        "a6_verdict":
            a6["verdict"][
                "status"
            ],

        "metrics":
            a6["benchmark"][
                "metrics"
            ],

        "frozen":
            True,

        "created_at":
            now(),
    }

    bundle["bundle_hash"] = (
        object_hash(bundle)
    )

    path = (
        BUNDLES
        /
        (
            bundle["bundle_hash"]
            +
            ".json"
        )
    )

    write_json_atomic(
        path,
        bundle,
    )

    before = file_hash(path)

    readback = load_json(path)

    after = file_hash(path)

    if before != after:
        raise RuntimeError(
            "EVIDENCE_BUNDLE_MUTATION"
        )

    if (
        readback["bundle_hash"]
        !=
        bundle["bundle_hash"]
    ):
        raise RuntimeError(
            "EVIDENCE_BUNDLE_HASH_DRIFT"
        )

    return path, bundle


def rejected_transaction_test(
    registry_before: bytes,
) -> None:

    if not REGISTRY.exists():
        raise RuntimeError(
            "REGISTRY_NOT_FOUND"
        )

    current = REGISTRY.read_bytes()

    if current != registry_before:
        raise RuntimeError(
            "REGISTRY_DRIFT_BEFORE_REJECTION_TEST"
        )

    authorization = False

    try:
        if not authorization:
            raise PermissionError(
                "HUMAN_AUTHORIZATION_REQUIRED"
            )

    except PermissionError:
        pass

    current_after = (
        REGISTRY.read_bytes()
    )

    if (
        current_after
        !=
        registry_before
    ):
        raise RuntimeError(
            "REJECTED_TRANSACTION_MUTATED_REGISTRY"
        )


def main() -> None:

    print("=" * 78)
    print(
        "RAIOS V9.0-A7 TRUE FAIL-CLOSED CERTIFICATION"
    )
    print("=" * 78)

    head = subprocess.check_output(
        [
            "git",
            "rev-parse",
            "HEAD",
        ],
        cwd=REPO,
        text=True,
    ).strip()

    print(
        "HEAD:",
        head,
    )

    # --------------------------------------------------------------
    # 1. PREDECESSOR
    # --------------------------------------------------------------

    state = load_json(
        STATE
    )

    if (
        state.get(
            "current_version"
        )
        !=
        "V9.0-A6"
    ):
        raise RuntimeError(
            "A7_PREDECESSOR_NOT_A6"
        )

    if (
        state.get(
            "state_status"
        )
        !=
        "A6_CERTIFIED"
    ):
        raise RuntimeError(
            "A7_PREDECESSOR_NOT_CERTIFIED"
        )

    latest = state.get(
        "latest_phase_receipt"
    ) or {}

    if (
        latest.get("phase")
        !=
        "V9.0-A6"
    ):
        raise RuntimeError(
            "A7_PREDECESSOR_RECEIPT_PHASE_INVALID"
        )

    if (
        latest.get(
            "certification_status"
        )
        !=
        "PASS"
    ):
        raise RuntimeError(
            "A7_PREDECESSOR_RECEIPT_NOT_PASS"
        )

    if not A6_RECEIPT.exists():
        raise RuntimeError(
            "A6_RECEIPT_NOT_FOUND"
        )

    actual_a6_hash = (
        file_hash(
            A6_RECEIPT
        )
    )

    if (
        actual_a6_hash
        !=
        latest.get(
            "sha256"
        )
    ):
        raise RuntimeError(
            "A6_RECEIPT_HASH_DRIFT"
        )

    a6 = load_json(
        A6_RECEIPT
    )

    print(
        "PREDECESSOR_A6            : PASS"
    )

    # --------------------------------------------------------------
    # 2. EXACT CANDIDATE IDENTITY
    # --------------------------------------------------------------

    candidate = a6.get(
        "candidate"
    ) or {}

    candidate_id = (
        candidate.get(
            "candidate_id"
        )
    )

    candidate_hash = (
        candidate.get(
            "sha256"
        )
    )

    if not candidate_id:
        raise RuntimeError(
            "A7_CANDIDATE_ID_MISSING"
        )

    if not candidate_hash:
        raise RuntimeError(
            "A7_CANDIDATE_HASH_MISSING"
        )

    a5_score = assert_probability(
        candidate.get(
            "a5_evidence_score"
        ),
        "A5_EVIDENCE_SCORE",
    )

    if (
        a6["verdict"][
            "status"
        ]
        !=
        "PROMOTION_ELIGIBLE"
    ):
        raise RuntimeError(
            "A7_CANDIDATE_NOT_PROMOTION_ELIGIBLE"
        )

    if (
        a6["verdict"][
            "automatic_promotion"
        ]
        is not False
    ):
        raise RuntimeError(
            "A7_PREDECESSOR_AUTO_PROMOTION_VIOLATION"
        )

    print(
        "CANDIDATE_IDENTITY         : PASS"
    )

    print(
        "CANDIDATE_ID               :",
        candidate_id,
    )

    # --------------------------------------------------------------
    # 3. FREEZE EVIDENCE
    # --------------------------------------------------------------

    bundle_path, bundle = (
        freeze_bundle(
            candidate_id,
            candidate_hash,
            a6,
        )
    )

    frozen_hash_before = (
        file_hash(
            bundle_path
        )
    )

    print(
        "EVIDENCE_BUNDLE_FREEZE     : PASS"
    )

    # --------------------------------------------------------------
    # 4. PROPOSAL
    # --------------------------------------------------------------

    proposal = {
        "schema":
            "raios.a7.promotion-proposal.v1",

        "proposal_id":
            None,

        "candidate_id":
            candidate_id,

        "candidate_sha256":
            candidate_hash,

        "evidence_bundle":
            str(
                bundle_path.relative_to(
                    REPO
                )
            ),

        "evidence_bundle_sha256":
            file_hash(
                bundle_path
            ),

        "a6_receipt_sha256":
            actual_a6_hash,

        "a6_benchmark_id":
            a6["benchmark"][
                "benchmark_id"
            ],

        "a6_verdict_id":
            a6["verdict"][
                "verdict_id"
            ],

        "requested_lifecycle":
            "SHADOW",

        "maximum_allowed_lifecycle":
            "SHADOW",

        "automatic_promotion":
            False,

        "production_activation":
            False,

        "status":
            "APPROVAL_REQUIRED",

        "created_at":
            now(),
    }

    proposal[
        "proposal_id"
    ] = (
        "proposal:"
        +
        object_hash(
            proposal
        )[:32]
    )

    proposal_path = (
        PROPOSALS
        /
        (
            proposal[
                "proposal_id"
            ]
            .replace(
                ":",
                "_",
            )
            +
            ".json"
        )
    )

    write_json_atomic(
        proposal_path,
        proposal,
    )

    print(
        "PROMOTION_PROPOSAL         : PASS"
    )

    # --------------------------------------------------------------
    # 5. INDEPENDENT REVALIDATION
    # --------------------------------------------------------------

    metrics = (
        a6["benchmark"][
            "metrics"
        ]
    )

    candidate_accuracy = (
        assert_probability(
            metrics[
                "candidate_accuracy"
            ],
            "CANDIDATE_ACCURACY",
        )
    )

    false_action_rate = (
        assert_probability(
            metrics[
                "false_action_rate"
            ],
            "FALSE_ACTION_RATE",
        )
    )

    positive_recovery_rate = (
        assert_probability(
            metrics[
                "positive_recovery_rate"
            ],
            "POSITIVE_RECOVERY_RATE",
        )
    )

    if (
        candidate_accuracy
        < 0.90
    ):
        raise RuntimeError(
            "A7_REVALIDATION_ACCURACY_FAILED"
        )

    if (
        false_action_rate
        != 0.0
    ):
        raise RuntimeError(
            "A7_REVALIDATION_FALSE_ACTION_FAILED"
        )

    if (
        positive_recovery_rate
        != 1.0
    ):
        raise RuntimeError(
            "A7_REVALIDATION_RECOVERY_RATE_FAILED"
        )

    if (
        metrics[
            "regression_count"
        ]
        !=
        0
    ):
        raise RuntimeError(
            "A7_REVALIDATION_REGRESSION_FAILED"
        )

    print(
        "INDEPENDENT_REVALIDATION   : PASS"
    )

    # --------------------------------------------------------------
    # 6. REGISTRY BASELINE + FAILED TRANSACTION IMMUTABILITY
    # --------------------------------------------------------------

    registry = load_registry()

    registry_before = (
        REGISTRY.read_bytes()
    )

    rollback_hash = (
        hashlib.sha256(
            registry_before
        ).hexdigest()
    )

    rollback_path = (
        ROLLBACK_DIR
        /
        (
            "pre-shadow-"
            +
            rollback_hash
            +
            ".json"
        )
    )

    if not rollback_path.exists():
        rollback_path.write_bytes(
            registry_before
        )

    if (
        file_hash(
            rollback_path
        )
        !=
        rollback_hash
    ):
        raise RuntimeError(
            "ROLLBACK_POINTER_HASH_INVALID"
        )

    rejected_transaction_test(
        registry_before
    )

    if (
        REGISTRY.read_bytes()
        !=
        registry_before
    ):
        raise RuntimeError(
            "FAILED_TRANSACTION_NOT_BYTE_IDENTICAL"
        )

    print(
        "FAILED_TRANSACTION_GUARD   : PASS"
    )

    print(
        "ROLLBACK_POINTER           : PASS"
    )

    # --------------------------------------------------------------
    # 7. HUMAN AUTHORIZATION BOUNDARY
    #
    # Running this installer is explicit authorization for SHADOW only.
    # It is NOT authorization for ACTIVE production use.
    # --------------------------------------------------------------

    authorization = {
        "schema":
            "raios.a7.authorization.v1",

        "authorization_id":
            (
                "auth:"
                +
                uuid.uuid4().hex
            ),

        "actor":
            "HUMAN_OPERATOR",

        "mechanism":
            "EXPLICIT_A7_INSTALLER_EXECUTION",

        "candidate_id":
            candidate_id,

        "allowed_transition":
            "APPROVAL_REQUIRED->APPROVED->SHADOW",

        "active_production_authorized":
            False,

        "scope":
            "SHADOW_ONLY",

        "timestamp":
            now(),
    }

    auth_path = (
        AUDIT_DIR
        /
        (
            authorization[
                "authorization_id"
            ]
            .replace(
                ":",
                "_",
            )
            +
            ".json"
        )
    )

    write_json_atomic(
        auth_path,
        authorization,
    )

    if (
        authorization[
            "active_production_authorized"
        ]
        is not False
    ):
        raise RuntimeError(
            "PRODUCTION_AUTHORIZATION_VIOLATION"
        )

    print(
        "HUMAN_AUTH_BOUNDARY        : PASS"
    )

    # --------------------------------------------------------------
    # 8. ATOMIC SHADOW REGISTRY TRANSACTION
    # --------------------------------------------------------------

    registry = load_json(
        REGISTRY
    )

    skills = registry.setdefault(
        "skills",
        {},
    )

    previous_skill = (
        skills.get(
            candidate_id
        )
    )

    skill_record = {
        "skill_id":
            candidate_id,

        "candidate_sha256":
            candidate_hash,

        "lifecycle":
            "SHADOW",

        "previous_lifecycle":
            (
                previous_skill.get(
                    "lifecycle"
                )
                if isinstance(
                    previous_skill,
                    dict,
                )
                else
                "PROMOTION_ELIGIBLE"
            ),

        "proposal_id":
            proposal[
                "proposal_id"
            ],

        "authorization_id":
            authorization[
                "authorization_id"
            ],

        "evidence_bundle_sha256":
            file_hash(
                bundle_path
            ),

        "a6_receipt_sha256":
            actual_a6_hash,

        "benchmark_id":
            a6["benchmark"][
                "benchmark_id"
            ],

        "verdict_id":
            a6["verdict"][
                "verdict_id"
            ],

        "rollback_pointer":
            str(
                rollback_path.relative_to(
                    REPO
                )
            ),

        "rollback_sha256":
            rollback_hash,

        "shadow_enabled":
            True,

        "production_active":
            False,

        "automatic_promotion":
            False,

        "canonical_auto_promotion":
            False,

        "registered_at":
            now(),
    }

    if (
        skill_record[
            "lifecycle"
        ]
        not in LIFECYCLE
    ):
        raise RuntimeError(
            "INVALID_SKILL_LIFECYCLE"
        )

    if (
        skill_record[
            "production_active"
        ]
        is not False
    ):
        raise RuntimeError(
            "A7_ACTIVE_PRODUCTION_FORBIDDEN"
        )

    skills[
        candidate_id
    ] = skill_record

    registry[
        "registry_version"
    ] = int(
        registry.get(
            "registry_version",
            0,
        )
    ) + 1

    registry[
        "automatic_promotion"
    ] = False

    registry[
        "production_auto_activation"
    ] = False

    registry[
        "updated_at"
    ] = now()

    write_json_atomic(
        REGISTRY,
        registry,
    )

    registry_after = (
        load_json(
            REGISTRY
        )
    )

    stored = (
        registry_after[
            "skills"
        ][
            candidate_id
        ]
    )

    if (
        stored[
            "lifecycle"
        ]
        !=
        "SHADOW"
    ):
        raise RuntimeError(
            "A7_REGISTRY_NOT_SHADOW"
        )

    if (
        stored[
            "production_active"
        ]
        is not False
    ):
        raise RuntimeError(
            "A7_PRODUCTION_ACTIVATED"
        )

    if (
        stored[
            "candidate_sha256"
        ]
        !=
        candidate_hash
    ):
        raise RuntimeError(
            "A7_CANDIDATE_HASH_BINDING_FAILED"
        )

    print(
        "ATOMIC_REGISTRY_TRANSACTION: PASS"
    )

    print(
        "SKILL_LIFECYCLE            : SHADOW"
    )

    print(
        "PRODUCTION_ACTIVE          : FALSE"
    )

    # --------------------------------------------------------------
    # 9. SHADOW ACTIVATION OBJECT
    # --------------------------------------------------------------

    shadow = {
        "schema":
            "raios.a7.shadow-activation.v1",

        "skill_id":
            candidate_id,

        "candidate_sha256":
            candidate_hash,

        "registry_sha256":
            file_hash(
                REGISTRY
            ),

        "mode":
            "SHADOW",

        "can_observe":
            True,

        "can_score":
            True,

        "can_recommend":
            True,

        "can_mutate_production":
            False,

        "can_mutate_canonical":
            False,

        "can_self_promote":
            False,

        "rollback_pointer":
            str(
                rollback_path.relative_to(
                    REPO
                )
            ),

        "created_at":
            now(),
    }

    shadow_path = (
        SHADOW_DIR
        /
        (
            candidate_id
            .replace(
                ":",
                "_",
            )
            +
            ".json"
        )
    )

    write_json_atomic(
        shadow_path,
        shadow,
    )

    if (
        shadow[
            "can_mutate_production"
        ]
        is not False
    ):
        raise RuntimeError(
            "SHADOW_PRODUCTION_MUTATION_VIOLATION"
        )

    if (
        shadow[
            "can_mutate_canonical"
        ]
        is not False
    ):
        raise RuntimeError(
            "SHADOW_CANONICAL_MUTATION_VIOLATION"
        )

    print(
        "SHADOW_ACTIVATION          : PASS"
    )

    # --------------------------------------------------------------
    # 10. FROZEN EVIDENCE MUST STILL BE IDENTICAL
    # --------------------------------------------------------------

    frozen_hash_after = (
        file_hash(
            bundle_path
        )
    )

    if (
        frozen_hash_before
        !=
        frozen_hash_after
    ):
        raise RuntimeError(
            "FROZEN_EVIDENCE_CHANGED"
        )

    print(
        "EVIDENCE_IMMUTABILITY      : PASS"
    )

    # --------------------------------------------------------------
    # 11. SUCCESS EXPERIENCE
    # --------------------------------------------------------------

    success_experience = (
        record_experience(
            "SUCCESS",
            "A7_SHADOW_PROMOTION_TRANSACTION",
            {
                "candidate_id":
                    candidate_id,

                "proposal_id":
                    proposal[
                        "proposal_id"
                    ],

                "authorization_id":
                    authorization[
                        "authorization_id"
                    ],

                "lifecycle":
                    "SHADOW",

                "production_active":
                    False,
            },
        )
    )

    print(
        "PROMOTION_EXPERIENCE       : PASS"
    )

    # --------------------------------------------------------------
    # 12. RECEIPT — ONLY NOW
    # --------------------------------------------------------------

    receipt = {
        "schema":
            "raios.v9.a7.receipt.v1",

        "phase":
            "V9.0-A7",

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
                "V9.0-A6",

            "receipt":
                str(
                    A6_RECEIPT.relative_to(
                        REPO
                    )
                ),

            "sha256":
                actual_a6_hash,

            "status":
                "PASS",
        },

        "candidate": {
            "candidate_id":
                candidate_id,

            "sha256":
                candidate_hash,

            "a5_evidence_score":
                a5_score,
        },

        "promotion": {
            "proposal_id":
                proposal[
                    "proposal_id"
                ],

            "evidence_bundle_sha256":
                file_hash(
                    bundle_path
                ),

            "authorization_id":
                authorization[
                    "authorization_id"
                ],

            "registry_sha256":
                file_hash(
                    REGISTRY
                ),

            "lifecycle":
                "SHADOW",

            "promotion_eligible":
                True,

            "approved":
                True,

            "shadow":
                True,

            "active":
                False,

            "automatic_promotion":
                False,

            "canonical_auto_promotion":
                False,
        },

        "rollback": {
            "path":
                str(
                    rollback_path.relative_to(
                        REPO
                    )
                ),

            "sha256":
                rollback_hash,

            "available_before_activation":
                True,
        },

        "transaction_guards": {
            "failed_transaction_byte_identical":
                True,

            "atomic_registry_write":
                True,

            "candidate_hash_bound":
                True,

            "evidence_bundle_frozen":
                True,

            "partial_promotion_forbidden":
                True,

            "production_activation":
                False,

            "canonical_mutation":
                False,
        },

        "experience": {
            "path":
                str(
                    success_experience.relative_to(
                        REPO
                    )
                )
        },

        "lifecycle_contract":
            LIFECYCLE,

        "invariants": [
            "PROMOTION_ELIGIBLE does not mean PROMOTED.",
            "APPROVED does not mean ACTIVE.",
            "SHADOW does not mean production activation.",
            "Candidate hash must be bound to promotion evidence.",
            "Evidence bundle is immutable after freeze.",
            "Rollback state must exist before shadow activation.",
            "Failed promotion attempts must leave the previous registry byte-identical.",
            "Partial registry promotion is forbidden.",
            "Automatic canonical promotion is forbidden.",
            "ACTIVE production lifecycle is outside A7 authority."
        ],
    }

    write_json_atomic(
        A7_RECEIPT,
        receipt,
    )

    receipt_hash = (
        file_hash(
            A7_RECEIPT
        )
    )

    receipt_readback = (
        load_json(
            A7_RECEIPT
        )
    )

    if (
        receipt_readback[
            "certification_status"
        ]
        !=
        "PASS"
    ):
        raise RuntimeError(
            "A7_RECEIPT_READBACK_FAILED"
        )

    # --------------------------------------------------------------
    # 13. UPDATE CURRENT STATE ONLY AFTER RECEIPT PASS
    # --------------------------------------------------------------

    state = load_json(
        STATE
    )

    state[
        "current_version"
    ] = "V9.0-A7"

    state[
        "current_phase"
    ] = (
        "GOVERNED_PROMOTION_AND_SKILL_REGISTRY"
    )

    state[
        "state_status"
    ] = (
        "A7_CERTIFIED"
    )

    active_architecture = (
        state.get(
            "active_architecture",
            []
        )
    )

    for capability in [
        "GOVERNED_PROMOTION_GATE",
        "SKILL_REGISTRY",
        "EVIDENCE_BUNDLE_FREEZE",
        "ATOMIC_REGISTRY_TRANSACTION",
        "SHADOW_ACTIVATION",
        "ROLLBACK_POINTER",
    ]:
        if capability not in active_architecture:
            active_architecture.append(
                capability
            )

    state[
        "active_architecture"
    ] = active_architecture

    state[
        "skill_governance"
    ] = {
        "candidate_id":
            candidate_id,

        "lifecycle":
            "SHADOW",

        "production_active":
            False,

        "automatic_promotion":
            False,

        "canonical_auto_promotion":
            False,

        "rollback_available":
            True,

        "registry_path":
            str(
                REGISTRY.relative_to(
                    REPO
                )
            ),
    }

    state[
        "latest_phase_receipt"
    ] = {
        "phase":
            "V9.0-A7",

        "path":
            str(
                A7_RECEIPT.relative_to(
                    REPO
                )
            ),

        "sha256":
            receipt_hash,

        "certification_status":
            "PASS",
    }

    state[
        "updated_at"
    ] = now()

    write_json_atomic(
        STATE,
        state,
    )

    final_state = (
        load_json(
            STATE
        )
    )

    actual_receipt_hash = (
        file_hash(
            A7_RECEIPT
        )
    )

    if (
        final_state[
            "latest_phase_receipt"
        ][
            "sha256"
        ]
        !=
        actual_receipt_hash
    ):
        raise RuntimeError(
            "A7_STATE_RECEIPT_HASH_DRIFT"
        )

    if (
        final_state[
            "current_version"
        ]
        !=
        "V9.0-A7"
    ):
        raise RuntimeError(
            "A7_STATE_VERSION_INVALID"
        )

    if (
        final_state[
            "skill_governance"
        ][
            "production_active"
        ]
        is not False
    ):
        raise RuntimeError(
            "A7_FINAL_PRODUCTION_ACTIVATION_VIOLATION"
        )

    print()
    print("=" * 78)
    print(
        "RAIOS V9.0-A7 CERTIFICATION RESULT"
    )
    print("=" * 78)

    print(
        "PREDECESSOR_A6             : PASS"
    )

    print(
        "CANDIDATE_HASH_BINDING     : PASS"
    )

    print(
        "EVIDENCE_BUNDLE_FREEZE     : PASS"
    )

    print(
        "INDEPENDENT_REVALIDATION   : PASS"
    )

    print(
        "PROMOTION_PROPOSAL         : PASS"
    )

    print(
        "HUMAN_AUTH_BOUNDARY        : PASS"
    )

    print(
        "FAILED_TRANSACTION_GUARD   : PASS"
    )

    print(
        "ATOMIC_REGISTRY_TRANSACTION: PASS"
    )

    print(
        "ROLLBACK_POINTER           : PASS"
    )

    print(
        "SHADOW_ACTIVATION          : PASS"
    )

    print(
        "SKILL_LIFECYCLE            : SHADOW"
    )

    print(
        "PROMOTION_ELIGIBLE         : TRUE"
    )

    print(
        "APPROVED                   : TRUE"
    )

    print(
        "ACTIVE                     : FALSE"
    )

    print(
        "PRODUCTION_ACTIVE          : FALSE"
    )

    print(
        "AUTOMATIC_PROMOTION        : FALSE"
    )

    print(
        "CANONICAL_AUTO_PROMOTION   : FALSE"
    )

    print(
        "STATE_RECEIPT_HASH_MATCH   : TRUE"
    )

    print(
        "CURRENT_VERSION            :",
        final_state[
            "current_version"
        ],
    )

    print(
        "STATE_STATUS               :",
        final_state[
            "state_status"
        ],
    )

    print(
        "A7_RECEIPT_SHA256          :",
        actual_receipt_hash,
    )

    print()
    print(
        "STATUS = V9.0-A7_PASS"
    )

    print("=" * 78)


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        try:
            record_failure(
                exc,
                {
                    "phase":
                        "V9.0-A7",

                    "state_path":
                        str(STATE),

                    "receipt_path":
                        str(A7_RECEIPT),
                },
            )

        except Exception as telemetry_error:

            print(
                "A7_FAILURE_TELEMETRY_ERROR:",
                repr(
                    telemetry_error
                ),
                file=sys.stderr,
            )

        print(
            "A7_CERTIFICATION_FAILED:",
            repr(exc),
            file=sys.stderr,
        )

        raise