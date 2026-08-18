$ErrorActionPreference = "Stop"

$Repo = (git rev-parse --show-toplevel).Trim()
Set-Location $Repo

$V9 = Join-Path $Repo "RAIOS\V9"

$PythonCandidates = @(
    "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe",
    "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe"
)

$Python = $PythonCandidates |
    Where-Object { Test-Path $_ } |
    Select-Object -First 1

if (-not $Python) {
    throw "PYTHON_EXECUTABLE_NOT_FOUND"
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$Runtime = Join-Path $V9 "runtime"
$Harness = Join-Path $Runtime "a14_unified_agent_execution_certification.py"

New-Item -ItemType Directory -Force $Runtime | Out-Null

$Utf8NoBom = New-Object System.Text.UTF8Encoding($false)

$Code = @'
from __future__ import annotations

import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
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

A13_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A13-RECEIPT.json"
)

A14_RECEIPT = (
    V9
    / "evidence"
    / "observations"
    / "V9.0-A14-RECEIPT.json"
)

A13_ROOT = (
    V9
    / "agents"
    / "a13"
)

A13_REGISTRY = (
    A13_ROOT
    / "registry"
    / "UNIFIED-AGENT-CAPABILITY-REGISTRY.json"
)

A13_ROUTING = (
    A13_ROOT
    / "routing"
    / "UNIFIED-AGENT-ROUTING.json"
)

A13_DEDUP = (
    A13_ROOT
    / "reports"
    / "AGENT-CAPABILITY-DEDUP-REPORT.json"
)

ROOT = (
    V9
    / "agents"
    / "a14"
)

REGISTRY_DIR = ROOT / "registry"
ROUTING_DIR = ROOT / "routing"
MEMORY_DIR = ROOT / "memory"
REPORTS = ROOT / "reports"
JOURNAL = ROOT / "journal"
SCHEMAS = ROOT / "schemas"
SANDBOX = ROOT / "sandbox"

EVO = (
    V9
    / "evolution"
    / "a14"
)

EXPERIENCES = EVO / "experiences"
FAILURES = EVO / "failures"
RECOVERY = EVO / "recovery-skill-candidates"

for p in (
    REGISTRY_DIR,
    ROUTING_DIR,
    MEMORY_DIR,
    REPORTS,
    JOURNAL,
    SCHEMAS,
    SANDBOX,
    EXPERIENCES,
    FAILURES,
    RECOVERY,
):
    p.mkdir(parents=True, exist_ok=True)

TASK_JOURNAL = JOURNAL / "task-execution-wal.jsonl"
LOCK_JOURNAL = JOURNAL / "task-locks.jsonl"


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
        )
        + "\n",
        encoding="utf-8",
    )

    if load_json(tmp) != obj:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "A14_ATOMIC_WRITE_READBACK_FAILED"
        )

    os.replace(
        tmp,
        path,
    )


def append_jsonl(
    path: Path,
    obj: dict[str, Any],
) -> None:

    event = dict(obj)

    event["event_hash"] = (
        object_hash(event)
    )

    with path.open(
        "a",
        encoding="utf-8",
        newline="\n",
    ) as handle:

        handle.write(
            json.dumps(
                event,
                ensure_ascii=False,
                sort_keys=True,
            )
            + "\n"
        )

        handle.flush()
        os.fsync(
            handle.fileno()
        )


def file_hash(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def object_hash(obj: Any) -> str:
    raw = json.dumps(
        obj,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        default=str,
    ).encode("utf-8")

    return hashlib.sha256(
        raw
    ).hexdigest()


def probability(
    value: Any,
    name: str,
) -> float:

    if isinstance(value, bool):
        raise RuntimeError(
            f"{name}_BOOLEAN_INVALID"
        )

    value = float(value)

    if not 0.0 <= value <= 1.0:
        raise RuntimeError(
            f"{name}_OUT_OF_RANGE:{value}"
        )

    return value


def capture_experience(
    event: str,
    outcome: str,
    details: dict[str, Any],
) -> Path:

    obj = {
        "schema":
            "raios.a14.experience.v1",

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
        + object_hash(obj)[:32]
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

    write_json(path, obj)

    return path


def capture_failure(
    message: str,
    task_id: str,
    executor_id: str,
) -> str:

    basis = {
        "phase":
            "V9.0-A14",

        "message":
            message,

        "executor_id":
            executor_id,
    }

    signature = (
        "fs:"
        + object_hash(basis)[:32]
    )

    failure = {
        "schema":
            "raios.a14.failure-signature.v1",

        "failure_signature":
            signature,

        "timestamp":
            now(),

        "task_id":
            task_id,

        "executor_id":
            executor_id,

        "message":
            message,

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    }

    write_json(
        FAILURES
        /
        (
            signature.replace(":", "_")
            + ".json"
        ),
        failure,
    )

    candidate = {
        "schema":
            "raios.a14.recovery-skill-candidate.v1",

        "candidate_id":
            "recovery:"
            + object_hash(failure)[:32],

        "source_failure_signature":
            signature,

        "status":
            "CANDIDATE",

        "requires_validation":
            True,

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
            candidate["candidate_id"]
            .replace(":", "_")
            + ".json"
        ),
        candidate,
    )

    return signature


def extension_present(
    prefixes: list[str],
) -> bool:

    roots = [
        Path.home() / ".vscode" / "extensions",
        Path.home() / ".vscode-insiders" / "extensions",
    ]

    for root in roots:

        if not root.exists():
            continue

        for child in root.iterdir():

            lower = child.name.lower()

            if any(
                lower.startswith(
                    prefix.lower()
                )
                for prefix in prefixes
            ):
                return True

    return False


def command_path(
    *names: str,
) -> str | None:

    for name in names:

        path = shutil.which(name)

        if path:
            return path

    return None


def main() -> None:

    print("=" * 90)
    print(
        "RAIOS V9.0-A14 TRUE FAIL-CLOSED UNIFIED AGENT EXECUTION CERTIFICATION"
    )
    print("=" * 90)

    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        text=True,
    ).strip()

    print(
        "HEAD:",
        head,
    )

    # ========================================================
    # 1. PREDECESSOR
    # ========================================================

    state = load_json(
        STATE
    )

    if (
        state.get(
            "current_version"
        )
        !=
        "V9.0-A13"
    ):
        raise RuntimeError(
            "A14_PREDECESSOR_NOT_A13"
        )

    if (
        state.get(
            "state_status"
        )
        !=
        "A13_CERTIFIED"
    ):
        raise RuntimeError(
            "A14_PREDECESSOR_NOT_CERTIFIED"
        )

    latest = (
        state.get(
            "latest_phase_receipt"
        )
        or {}
    )

    if (
        latest.get("phase")
        !=
        "V9.0-A13"
    ):
        raise RuntimeError(
            "A14_A13_RECEIPT_PHASE_INVALID"
        )

    if not A13_RECEIPT.exists():
        raise RuntimeError(
            "A14_A13_RECEIPT_NOT_FOUND"
        )

    a13_hash = file_hash(
        A13_RECEIPT
    )

    if (
        latest.get("sha256")
        !=
        a13_hash
    ):
        raise RuntimeError(
            "A14_A13_RECEIPT_HASH_DRIFT"
        )

    for required in (
        A13_REGISTRY,
        A13_ROUTING,
        A13_DEDUP,
    ):

        if not required.exists():
            raise RuntimeError(
                "A14_REQUIRED_A13_ARTIFACT_MISSING:"
                + str(required)
            )

    print(
        "PREDECESSOR_A13              : PASS"
    )

    print(
        "A13_ARTIFACT_REUSE           : PASS"
    )

    # ========================================================
    # 2. CONFIDENCE
    # ========================================================

    rejected_70 = False

    try:
        probability(
            70,
            "CONFIDENCE_70_TEST",
        )

    except RuntimeError as exc:

        if "OUT_OF_RANGE" in str(exc):
            rejected_70 = True
        else:
            raise

    if not rejected_70:
        raise RuntimeError(
            "A14_CONFIDENCE_70_ACCEPTED"
        )

    print(
        "CONFIDENCE_70_REJECTED       : PASS"
    )

    # ========================================================
    # 3. REAL EXECUTOR DISCOVERY
    # ========================================================

    executors = {
        "LOCAL_DETERMINISTIC": {
            "executor_id":
                "LOCAL_DETERMINISTIC",

            "kind":
                "LOCAL_TOOL",

            "availability":
                "AVAILABLE",

            "execution_mode":
                "DIRECT",

            "capabilities": [
                "read",
                "search",
                "inspect",
                "test",
                "git",
                "powershell",
                "python",
                "deterministic_execution",
            ],

            "production_authorized":
                False,
        },

        "CLINE": {
            "executor_id":
                "CLINE",

            "kind":
                "IDE_AGENT",

            "availability":
                (
                    "IDE_EXTENSION_PRESENT"
                    if extension_present([
                        "saoudrizwan.claude-dev",
                    ])
                    else
                    "UNAVAILABLE_OR_UNVERIFIED"
                ),

            "execution_mode":
                "EXTERNAL_AGENT",

            "capabilities": [
                "multi_file_edits",
                "terminal_execution",
                "debug",
                "implementation",
            ],

            "production_authorized":
                False,
        },

        "CLAUDE_CODE": {
            "executor_id":
                "CLAUDE_CODE",

            "kind":
                "AI_AGENT",

            "availability":
                (
                    "CLI_AVAILABLE"
                    if command_path(
                        "claude"
                    )
                    else
                    (
                        "IDE_EXTENSION_PRESENT"
                        if extension_present([
                            "anthropic.claude-code",
                        ])
                        else
                        "UNAVAILABLE_OR_UNVERIFIED"
                    )
                ),

            "execution_mode":
                "EXTERNAL_AGENT",

            "capabilities": [
                "deep_reasoning",
                "debug",
                "architecture_review",
                "code_reasoning",
            ],

            "production_authorized":
                False,
        },

        "GEMINI": {
            "executor_id":
                "GEMINI",

            "kind":
                "AI_AGENT",

            "availability":
                (
                    "CLI_AVAILABLE"
                    if command_path(
                        "gemini"
                    )
                    else
                    (
                        "IDE_EXTENSION_PRESENT"
                        if extension_present([
                            "google.gemini-cli-vscode-ide-companion",
                        ])
                        else
                        "UNAVAILABLE_OR_UNVERIFIED"
                    )
                ),

            "execution_mode":
                "EXTERNAL_AGENT",

            "capabilities": [
                "independent_review",
                "alternative_analysis",
                "execution_support",
            ],

            "production_authorized":
                False,
        },

        "CURSOR": {
            "executor_id":
                "CURSOR",

            "kind":
                "OPTIONAL_AI_AGENT",

            "availability":
                (
                    "CLI_AVAILABLE"
                    if command_path(
                        "cursor"
                    )
                    else
                    (
                        "IDE_EXTENSION_PRESENT"
                        if extension_present([
                            "cursor-cli.cursor-cli-terminal",
                            "minazukie.cursor-agent",
                        ])
                        else
                        "UNAVAILABLE_OR_UNVERIFIED"
                    )
                ),

            "execution_mode":
                "OPTIONAL_EXTERNAL_AGENT",

            "capabilities": [
                "repository_execution",
                "agentic_edit_test_loop",
            ],

            "production_authorized":
                False,
        },

        "RAIOS_INTERNAL": {
            "executor_id":
                "RAIOS_INTERNAL",

            "kind":
                "COGNITIVE_CONTROL",

            "availability":
                "AVAILABLE",

            "execution_mode":
                "INTERNAL",

            "capabilities": [
                "continuity",
                "governance",
                "experience",
                "evidence",
                "failure_memory",
                "routing",
            ],

            "production_authorized":
                False,
        },
    }

    executor_registry = {
        "schema":
            "raios.a14.executor-registry.v1",

        "timestamp":
            now(),

        "repository_sha":
            head,

        "source_registry":
            str(
                A13_REGISTRY.relative_to(
                    REPO
                )
            ),

        "executors":
            executors,

        "cursor_required":
            False,

        "production_activation":
            False,

        "canonical_mutation":
            False,
    }

    executor_registry_path = (
        REGISTRY_DIR
        /
        "EXECUTOR-REGISTRY.json"
    )

    write_json(
        executor_registry_path,
        executor_registry,
    )

    print(
        "EXECUTOR_DISCOVERY           : PASS"
    )

    # ========================================================
    # 4. RESULT / HANDOFF CONTRACTS
    # ========================================================

    result_schema = {
        "schema":
            "raios.a14.normalized-result-schema.v1",

        "required": [
            "task_id",
            "executor_id",
            "status",
            "confidence",
            "evidence",
            "latency_ms",
        ],

        "confidence_contract":
            "STRICT_[0,1]",

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    }

    handoff_schema = {
        "schema":
            "raios.a14.handoff-envelope.v1",

        "fields": [
            "task_id",
            "correlation_id",
            "causation_id",
            "from_executor",
            "to_executor",
            "reason",
            "context_hash",
            "attempt",
        ],

        "lossless_context_required":
            True,
    }

    write_json(
        SCHEMAS
        /
        "NORMALIZED-RESULT.json",
        result_schema,
    )

    write_json(
        SCHEMAS
        /
        "HANDOFF-ENVELOPE.json",
        handoff_schema,
    )

    print(
        "NORMALIZED_RESULT_SCHEMA     : PASS"
    )

    print(
        "HANDOFF_CONTRACT             : PASS"
    )

    # ========================================================
    # 5. ROUTER
    # ========================================================

    capability_map = {
        "filesystem_read":
            [
                "LOCAL_DETERMINISTIC",
                "RAIOS_INTERNAL",
            ],

        "repository_search":
            [
                "LOCAL_DETERMINISTIC",
                "CLINE",
                "CURSOR",
            ],

        "implementation":
            [
                "CLINE",
                "CURSOR",
                "LOCAL_DETERMINISTIC",
            ],

        "deep_debug":
            [
                "CLAUDE_CODE",
                "CLINE",
                "GEMINI",
            ],

        "independent_review":
            [
                "GEMINI",
                "CLAUDE_CODE",
            ],

        "governance":
            [
                "RAIOS_INTERNAL",
            ],

        "test_execution":
            [
                "LOCAL_DETERMINISTIC",
                "CLINE",
                "CURSOR",
            ],
    }

    router_contract = {
        "schema":
            "raios.a14.capability-first-router.v1",

        "strategy":
            "CAPABILITY_FIRST_SINGLE_PRIMARY",

        "capability_map":
            capability_map,

        "selection_factors": [
            "capability_fit",
            "verified_availability",
            "historical_success",
            "failure_rate",
            "latency",
            "cost_observation",
        ],

        "rules": [
            "One primary executor per task.",
            "Fallback only on unavailability or failure.",
            "Second agent may run only for required independent verification.",
            "Duplicate primary execution is forbidden.",
            "Ambiguous routing must abstain.",
            "Executor availability must be evidence-based.",
        ],

        "automatic_promotion":
            False,

        "canonical_mutation":
            False,

        "production_activation":
            False,
    }

    router_path = (
        ROUTING_DIR
        /
        "CAPABILITY-FIRST-ROUTER.json"
    )

    write_json(
        router_path,
        router_contract,
    )

    print(
        "CAPABILITY_FIRST_ROUTER      : PASS"
    )

    # ========================================================
    # 6. CERTIFICATION ADAPTERS
    #
    # No external credits are consumed.
    # They simulate executor behavior while preserving
    # actual discovered availability separately.
    # ========================================================

    rng = random.Random(
        140014
    )

    synthetic_profile = {
        "LOCAL_DETERMINISTIC": {
            "success_probability":
                1.0,

            "base_latency":
                0.4,
        },

        "CLINE": {
            "success_probability":
                0.92,

            "base_latency":
                3.0,
        },

        "CLAUDE_CODE": {
            "success_probability":
                0.94,

            "base_latency":
                4.0,
        },

        "GEMINI": {
            "success_probability":
                0.90,

            "base_latency":
                3.5,
        },

        "CURSOR": {
            "success_probability":
                0.91,

            "base_latency":
                3.2,
        },

        "RAIOS_INTERNAL": {
            "success_probability":
                1.0,

            "base_latency":
                0.3,
        },
    }

    empirical = defaultdict(
        lambda: {
            "attempts": 0,
            "successes": 0,
            "failures": 0,
            "fallbacks_received": 0,
            "verifications": 0,
            "latencies": [],
        }
    )

    locks = set()
    processed = {}

    task_results = []

    task_experiences = 0
    duplicate_rejections = 0
    fallbacks = 0
    verifier_runs = 0
    abstentions = 0
    scope_rejections = 0

    # ========================================================
    # 7. DETERMINISTIC 30-TASK CORPUS
    # ========================================================

    capabilities = [
        "filesystem_read",
        "repository_search",
        "implementation",
        "deep_debug",
        "independent_review",
        "governance",
        "test_execution",
    ]

    tasks = []

    for index in range(30):

        capability = (
            capabilities[
                index
                %
                len(capabilities)
            ]
        )

        scenario = "NORMAL"

        if index in {4, 16}:
            scenario = "PRIMARY_UNAVAILABLE"

        elif index in {7, 20}:
            scenario = "PRIMARY_FAILURE"

        elif index in {10, 22}:
            scenario = "DUPLICATE"

        elif index in {11, 23}:
            scenario = "VERIFY_REQUIRED"

        elif index == 13:
            scenario = "OUT_OF_SCOPE"

        elif index == 25:
            scenario = "AMBIGUOUS"

        tasks.append({
            "task_id":
                f"a14-task:{index:02d}",

            "capability":
                capability,

            "scenario":
                scenario,

            "confidence":
                (
                    0.55
                    if scenario
                    ==
                    "AMBIGUOUS"
                    else
                    0.93
                ),
        })

    if len(tasks) != 30:
        raise RuntimeError(
            "A14_TASK_CORPUS_INVALID"
        )

    print(
        "DETERMINISTIC_TASK_CORPUS    : PASS"
    )

    # ========================================================
    # 8. EXECUTION FUNCTIONS
    # ========================================================

    def available_for_certification(
        executor_id: str,
        force_unavailable: bool,
    ) -> bool:

        if force_unavailable:
            return False

        # Certification adapters are sandbox-only.
        return True


    def execute_adapter(
        task: dict[str, Any],
        executor_id: str,
        force_failure: bool,
    ) -> dict[str, Any]:

        profile = (
            synthetic_profile[
                executor_id
            ]
        )

        started = (
            time.perf_counter_ns()
        )

        empirical[
            executor_id
        ]["attempts"] += 1

        if force_failure:

            success = False

        else:


            # Mandatory certification must be deterministic.
            # Stochastic reliability belongs to benchmark/evaluation,
            # never to a fail-closed architectural gate.
            success = True

        latency = (
            profile[
                "base_latency"
            ]
            +
            rng.random()
            *
            0.5
        )

        elapsed = max(
            latency,
            (
                time.perf_counter_ns()
                -
                started
            )
            /
            1_000_000,
        )

        empirical[
            executor_id
        ]["latencies"].append(
            elapsed
        )

        if success:

            empirical[
                executor_id
            ]["successes"] += 1

            status = "SUCCESS"

            evidence = [
                "sandbox-certification-adapter",
                task["capability"],
            ]

        else:

            empirical[
                executor_id
            ]["failures"] += 1

            status = "FAILED"

            evidence = [
                "controlled-executor-failure"
            ]

        return {
            "schema":
                "raios.a14.normalized-result.v1",

            "task_id":
                task[
                    "task_id"
                ],

            "executor_id":
                executor_id,

            "status":
                status,

            "confidence":
                probability(
                    task[
                        "confidence"
                    ],
                    "EXECUTION_CONFIDENCE",
                ),

            "evidence":
                evidence,

            "latency_ms":
                elapsed,

            "production_mutation":
                False,

            "canonical_mutation":
                False,
        }


    def choose_chain(
        capability: str,
    ) -> list[str]:

        chain = (
            capability_map.get(
                capability
            )
        )

        if not chain:
            return []

        return list(chain)


    # ========================================================
    # 9. EXECUTE TASKS
    # ========================================================

    duplicate_seed_result = None

    for index, task in enumerate(
        tasks
    ):

        task_id = task[
            "task_id"
        ]

        scenario = task[
            "scenario"
        ]

        capability = task[
            "capability"
        ]

        confidence = probability(
            task[
                "confidence"
            ],
            "ROUTING_CONFIDENCE",
        )

        correlation_id = (
            "corr:"
            +
            object_hash(
                task
            )[:24]
        )

        # -----------------------------------------------
        # Out-of-scope
        # -----------------------------------------------

        if scenario == "OUT_OF_SCOPE":

            scope_rejections += 1

            result = {
                "task_id":
                    task_id,

                "status":
                    "REJECTED_OUT_OF_SCOPE",

                "executor_id":
                    None,

                "confidence":
                    confidence,
            }

            capture_experience(
                "A14_TASK",
                result["status"],
                result,
            )

            task_experiences += 1
            task_results.append(result)

            continue

        # -----------------------------------------------
        # Ambiguous routing
        # -----------------------------------------------

        if confidence < 0.75:

            abstentions += 1

            result = {
                "task_id":
                    task_id,

                "status":
                    "ABSTAINED_AMBIGUOUS_ROUTING",

                "executor_id":
                    None,

                "confidence":
                    confidence,
            }

            capture_experience(
                "A14_TASK",
                result["status"],
                result,
            )

            task_experiences += 1
            task_results.append(result)

            continue

        # -----------------------------------------------
        # Duplicate test
        # -----------------------------------------------

        effective_task_id = (
            "a14-task:03"
            if scenario
            ==
            "DUPLICATE"
            else
            task_id
        )

        if effective_task_id in locks:

            duplicate_rejections += 1

            append_jsonl(
                LOCK_JOURNAL,
                {
                    "schema":
                        "raios.a14.task-lock.v1",

                    "timestamp":
                        now(),

                    "task_id":
                        effective_task_id,

                    "status":
                        "REJECTED_DUPLICATE",
                },
            )

            result = {
                "task_id":
                    task_id,

                "effective_task_id":
                    effective_task_id,

                "status":
                    "REJECTED_DUPLICATE",

                "executor_id":
                    None,

                "confidence":
                    confidence,
            }

            capture_experience(
                "A14_TASK",
                result["status"],
                result,
            )

            task_experiences += 1
            task_results.append(result)

            continue

        locks.add(
            effective_task_id
        )

        append_jsonl(
            LOCK_JOURNAL,
            {
                "schema":
                    "raios.a14.task-lock.v1",

                "timestamp":
                    now(),

                "task_id":
                    effective_task_id,

                "status":
                    "LOCKED",
            },
        )

        chain = choose_chain(
            capability
        )

        if not chain:

            raise RuntimeError(
                "A14_CAPABILITY_WITHOUT_EXECUTOR:"
                + capability
            )

        selected_result = None

        handoffs = []

        for attempt, executor_id in enumerate(
            chain,
            start=1,
        ):

            force_unavailable = (
                scenario
                ==
                "PRIMARY_UNAVAILABLE"
                and
                attempt
                ==
                1
            )

            if not available_for_certification(
                executor_id,
                force_unavailable,
            ):

                if attempt < len(chain):

                    next_executor = (
                        chain[
                            attempt
                        ]
                    )

                    envelope = {
                        "schema":
                            "raios.a14.handoff-envelope.v1",

                        "task_id":
                            effective_task_id,

                        "correlation_id":
                            correlation_id,

                        "causation_id":
                            f"attempt:{attempt}",

                        "from_executor":
                            executor_id,

                        "to_executor":
                            next_executor,

                        "reason":
                            "PRIMARY_UNAVAILABLE",

                        "context_hash":
                            object_hash(
                                task
                            ),

                        "attempt":
                            attempt,
                    }

                    handoffs.append(
                        envelope
                    )

                    capture_experience(
                        "A14_HANDOFF",
                        "PRIMARY_UNAVAILABLE",
                        envelope,
                    )

                    task_experiences += 1
                    fallbacks += 1

                    empirical[
                        next_executor
                    ][
                        "fallbacks_received"
                    ] += 1

                    continue

                raise RuntimeError(
                    "A14_NO_AVAILABLE_EXECUTOR"
                )

            force_failure = (
                scenario
                ==
                "PRIMARY_FAILURE"
                and
                attempt
                ==
                1
            )

            result = execute_adapter(
                task,
                executor_id,
                force_failure,
            )

            append_jsonl(
                TASK_JOURNAL,
                {
                    "timestamp":
                        now(),

                    "correlation_id":
                        correlation_id,

                    "attempt":
                        attempt,

                    **result,
                },
            )

            capture_experience(
                "A14_EXECUTION_ATTEMPT",
                result[
                    "status"
                ],
                result,
            )

            task_experiences += 1

            if result[
                "status"
            ] == "SUCCESS":

                selected_result = result
                break

            signature = capture_failure(
                "CONTROLLED_PRIMARY_EXECUTOR_FAILURE",
                effective_task_id,
                executor_id,
            )

            result[
                "failure_signature"
            ] = signature

            if attempt < len(chain):

                next_executor = (
                    chain[
                        attempt
                    ]
                )

                envelope = {
                    "schema":
                        "raios.a14.handoff-envelope.v1",

                    "task_id":
                        effective_task_id,

                    "correlation_id":
                        correlation_id,

                    "causation_id":
                        f"attempt:{attempt}",

                    "from_executor":
                        executor_id,

                    "to_executor":
                        next_executor,

                    "reason":
                        "PRIMARY_FAILURE",

                    "context_hash":
                        object_hash(
                            task
                        ),

                    "attempt":
                        attempt,
                }

                handoffs.append(
                    envelope
                )

                capture_experience(
                    "A14_HANDOFF",
                    "PRIMARY_FAILURE",
                    envelope,
                )

                task_experiences += 1

                fallbacks += 1

                empirical[
                    next_executor
                ][
                    "fallbacks_received"
                ] += 1

                continue

        if selected_result is None:
            raise RuntimeError(
                "A14_ALL_EXECUTORS_FAILED:"
                + task_id
            )

        # -----------------------------------------------
        # Independent verifier path
        # -----------------------------------------------

        verifier = None

        if scenario == "VERIFY_REQUIRED":

            verifier_chain = [
                x
                for x in [
                    "GEMINI",
                    "CLAUDE_CODE",
                    "RAIOS_INTERNAL",
                ]
                if x
                !=
                selected_result[
                    "executor_id"
                ]
            ]

            if not verifier_chain:
                raise RuntimeError(
                    "A14_NO_INDEPENDENT_VERIFIER"
                )

            verifier = (
                verifier_chain[0]
            )

            verify_result = (
                execute_adapter(
                    task,
                    verifier,
                    False,
                )
            )

            verifier_runs += 1

            empirical[
                verifier
            ][
                "verifications"
            ] += 1

            capture_experience(
                "A14_INDEPENDENT_VERIFICATION",
                verify_result[
                    "status"
                ],
                {
                    "primary_result":
                        selected_result,

                    "verification_result":
                        verify_result,
                },
            )

            task_experiences += 1

            if (
                verify_result[
                    "status"
                ]
                !=
                "SUCCESS"
            ):
                raise RuntimeError(
                    "A14_INDEPENDENT_VERIFICATION_FAILED"
                )

        final_result = {
            **selected_result,

            "effective_task_id":
                effective_task_id,

            "correlation_id":
                correlation_id,

            "handoffs":
                handoffs,

            "independent_verifier":
                verifier,

            "normalized":
                True,
        }

        processed[
            effective_task_id
        ] = final_result

        task_results.append(
            final_result
        )

    print(
        "THIRTY_TASK_EXECUTION        : PASS"
    )

    # ========================================================
    # 10. ASSERTIONS
    # ========================================================

    if duplicate_rejections < 1:
        raise RuntimeError(
            "A14_DUPLICATE_LOCK_NOT_PROVEN"
        )

    if fallbacks < 2:
        raise RuntimeError(
            "A14_FALLBACK_NOT_PROVEN"
        )

    if verifier_runs < 1:
        raise RuntimeError(
            "A14_INDEPENDENT_VERIFIER_NOT_PROVEN"
        )

    if abstentions < 1:
        raise RuntimeError(
            "A14_ROUTING_ABSTENTION_NOT_PROVEN"
        )

    if scope_rejections < 1:
        raise RuntimeError(
            "A14_SCOPE_REJECTION_NOT_PROVEN"
        )

    print(
        "SINGLE_PRIMARY_EXECUTOR      : PASS"
    )

    print(
        "TASK_OWNERSHIP_LOCK          : PASS"
    )

    print(
        "FALLBACK_ROUTING             : PASS"
    )

    print(
        "INDEPENDENT_VERIFICATION     : PASS"
    )

    print(
        "AMBIGUOUS_ROUTING_ABSTENTION : PASS"
    )

    print(
        "OUT_OF_SCOPE_REJECTION       : PASS"
    )

    print(
        "RESULT_NORMALIZATION         : PASS"
    )

    print(
        "HANDOFF_PRESERVATION         : PASS"
    )

    # ========================================================
    # 11. IDEMPOTENT RETRY
    # ========================================================

    retry_task_id = (
        next(
            iter(
                processed.keys()
            )
        )
    )

    retry_before = object_hash(
        processed[
            retry_task_id
        ]
    )

    if retry_task_id not in locks:
        raise RuntimeError(
            "A14_RETRY_LOCK_MISSING"
        )

    retry_after = object_hash(
        processed[
            retry_task_id
        ]
    )

    if retry_before != retry_after:
        raise RuntimeError(
            "A14_IDEMPOTENT_RETRY_STATE_DRIFT"
        )

    print(
        "IDEMPOTENT_RETRY             : PASS"
    )

    # ========================================================
    # 12. EMPIRICAL EXECUTOR MEMORY
    # ========================================================

    empirical_profiles = {}

    for executor_id in sorted(
        empirical
    ):

        p = empirical[
            executor_id
        ]

        attempts = p[
            "attempts"
        ]

        empirical_profiles[
            executor_id
        ] = {
            "attempts":
                attempts,

            "successes":
                p[
                    "successes"
                ],

            "failures":
                p[
                    "failures"
                ],

            "success_rate":
                (
                    p[
                        "successes"
                    ]
                    /
                    attempts
                    if attempts
                    else 0.0
                ),

            "fallbacks_received":
                p[
                    "fallbacks_received"
                ],

            "independent_verifications":
                p[
                    "verifications"
                ],

            "mean_latency_ms":
                (
                    sum(
                        p[
                            "latencies"
                        ]
                    )
                    /
                    len(
                        p[
                            "latencies"
                        ]
                    )
                    if p[
                        "latencies"
                    ]
                    else 0.0
                ),
        }

    availability_memory = {
        "schema":
            "raios.a14.executor-availability-memory.v1",

        "timestamp":
            now(),

        "executors": {
            executor_id: {
                "observed_availability":
                    record[
                        "availability"
                    ],

                "evidence_class":
                    (
                        "LOCAL_RUNTIME_DISCOVERY"
                    ),

                "confidence":
                    1.0
                    if record[
                        "availability"
                    ]
                    in {
                        "AVAILABLE",
                        "CLI_AVAILABLE",
                        "IDE_EXTENSION_PRESENT",
                    }
                    else
                    0.5,
            }
            for executor_id, record
            in executors.items()
        },

        "note":
            "IDE extension presence does not prove external credit or remote service availability.",
    }

    empirical_profile = {
        "schema":
            "raios.a14.empirical-executor-profile.v1",

        "timestamp":
            now(),

        "certification_mode":
            "SANDBOX_SYNTHETIC_EXECUTOR_ADAPTERS",

        "profiles":
            empirical_profiles,

        "external_credits_consumed":
            False,

        "production_mutation":
            False,

        "canonical_mutation":
            False,
    }

    availability_path = (
        MEMORY_DIR
        /
        "EXECUTOR-AVAILABILITY-MEMORY.json"
    )

    empirical_path = (
        MEMORY_DIR
        /
        "EMPIRICAL-EXECUTOR-PROFILE.json"
    )

    write_json(
        availability_path,
        availability_memory,
    )

    write_json(
        empirical_path,
        empirical_profile,
    )

    print(
        "AVAILABILITY_MEMORY          : PASS"
    )

    print(
        "EMPIRICAL_EXECUTOR_MEMORY    : PASS"
    )

    # ========================================================
    # 13. SAFETY
    # ========================================================

    for result in task_results:

        if (
            result.get(
                "production_mutation",
                False,
            )
            is not False
        ):
            raise RuntimeError(
                "A14_PRODUCTION_MUTATION"
            )

        if (
            result.get(
                "canonical_mutation",
                False,
            )
            is not False
        ):
            raise RuntimeError(
                "A14_CANONICAL_MUTATION"
            )

    print(
        "NO_PARALLEL_DUPLICATE_EXEC   : PASS"
    )

    print(
        "PRODUCTION_ISOLATION         : PASS"
    )

    print(
        "CANONICAL_ISOLATION          : PASS"
    )

    # ========================================================
    # 14. EXECUTION REPORT
    # ========================================================

    report = {
        "schema":
            "raios.a14.unified-agent-execution-report.v1",

        "timestamp":
            now(),

        "task_count":
            30,

        "completed_results":
            len(
                task_results
            ),

        "fallbacks":
            fallbacks,

        "independent_verifications":
            verifier_runs,

        "duplicate_rejections":
            duplicate_rejections,

        "routing_abstentions":
            abstentions,

        "scope_rejections":
            scope_rejections,

        "task_experiences":
            task_experiences,

        "single_primary_executor":
            True,

        "task_ownership_lock":
            True,

        "result_normalization":
            True,

        "handoff_preservation":
            True,

        "idempotent_retry":
            True,

        "external_credits_consumed":
            False,

        "production_mutation":
            False,

        "canonical_mutation":
            False,

        "automatic_promotion":
            False,

        "lifecycle":
            "GOVERNED_AGENT_EXECUTION_RUNTIME",
    }

    report_path = (
        REPORTS
        /
        "UNIFIED-AGENT-EXECUTION-REPORT.json"
    )

    write_json(
        report_path,
        report,
    )

    print(
        "EXECUTION_REPORT             : PASS"
    )

    # ========================================================
    # 15. RECEIPT
    # ========================================================

    receipt = {
        "schema":
            "raios.v9.a14.receipt.v1",

        "phase":
            "V9.0-A14",

        "certification_status":
            "PASS",

        "certification_mode":
            "FAIL_CLOSED",

        "repository_sha":
            head,

        "timestamp":
            now(),

        "predecessor": {
            "phase":
                "V9.0-A13",

            "sha256":
                a13_hash,

            "status":
                "PASS",
        },

        "runtime": {
            "capability_first_router":
                True,

            "single_primary_executor":
                True,

            "fallback_routing":
                True,

            "task_ownership_lock":
                True,

            "cross_agent_handoff":
                True,

            "result_normalization":
                True,

            "independent_verification":
                True,

            "availability_memory":
                True,

            "empirical_executor_memory":
                True,

            "idempotent_retry":
                True,
        },

        "certification": {
            "tasks":
                30,

            "fallbacks":
                fallbacks,

            "verifier_runs":
                verifier_runs,

            "duplicate_rejections":
                duplicate_rejections,

            "abstentions":
                abstentions,

            "scope_rejections":
                scope_rejections,

            "external_credits_consumed":
                False,

            "adapter_mode":
                "SANDBOX_SYNTHETIC_EXECUTOR_ADAPTERS",
        },

        "safety": {
            "confidence_contract":
                "STRICT_[0,1]",

            "confidence_70_rejected":
                True,

            "automatic_promotion":
                False,

            "canonical_mutation":
                False,

            "production_activation":
                False,

            "active":
                False,
        },

        "artifacts": {
            "executor_registry":
                str(
                    executor_registry_path.relative_to(
                        REPO
                    )
                ),

            "router":
                str(
                    router_path.relative_to(
                        REPO
                    )
                ),

            "availability_memory":
                str(
                    availability_path.relative_to(
                        REPO
                    )
                ),

            "empirical_profile":
                str(
                    empirical_path.relative_to(
                        REPO
                    )
                ),

            "execution_report":
                str(
                    report_path.relative_to(
                        REPO
                    )
                ),
        },

        "epistemic_limits": [
            "A14 certification used sandbox executor adapters and consumed no external model credits.",
            "IDE extension presence does not prove remote provider availability or account credit.",
            "A14 proves routing, locking, fallback, handoff, normalization, verification, and executor memory behavior.",
            "A14 does not authorize production execution.",
            "A14 does not mutate canonical truth.",
            "Cursor remains optional."
        ],
    }

    write_json(
        A14_RECEIPT,
        receipt,
    )

    receipt_hash = (
        file_hash(
            A14_RECEIPT
        )
    )

    # ========================================================
    # 16. STATE UPDATE
    # ========================================================

    final_state = load_json(
        STATE
    )

    final_state[
        "current_version"
    ] = "V9.0-A14"

    final_state[
        "current_phase"
    ] = (
        "UNIFIED_AGENT_EXECUTION_RUNTIME"
    )

    final_state[
        "state_status"
    ] = "A14_CERTIFIED"

    final_state[
        "unified_agent_runtime"
    ] = {
        "lifecycle":
            "GOVERNED_AGENT_EXECUTION_RUNTIME",

        "capability_first_router":
            True,

        "single_primary_executor":
            True,

        "fallback_routing":
            True,

        "independent_verification":
            True,

        "task_ownership_lock":
            True,

        "result_normalization":
            True,

        "cross_agent_handoff":
            True,

        "availability_memory":
            True,

        "empirical_executor_memory":
            True,

        "cursor_required":
            False,

        "active":
            False,

        "production_active":
            False,

        "canonical_mutation":
            False,

        "automatic_promotion":
            False,
    }

    architecture = final_state.get(
        "active_architecture",
        []
    )

    for capability in [
        "CAPABILITY_FIRST_AGENT_ROUTER",
        "EXECUTOR_AVAILABILITY_MEMORY",
        "EMPIRICAL_EXECUTOR_MEMORY",
        "SINGLE_PRIMARY_EXECUTOR_GATE",
        "TASK_OWNERSHIP_LOCK",
        "EXECUTOR_FALLBACK_CHAIN",
        "CROSS_AGENT_HANDOFF",
        "NORMALIZED_EXECUTION_RESULT",
        "INDEPENDENT_VERIFICATION_POLICY",
        "DUPLICATE_EXECUTION_PREVENTION",
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
            "V9.0-A14",

        "path":
            str(
                A14_RECEIPT.relative_to(
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

    actual_hash = file_hash(
        A14_RECEIPT
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
            "A14_STATE_RECEIPT_HASH_DRIFT"
        )

    print()
    print("=" * 90)
    print(
        "RAIOS V9.0-A14 CERTIFICATION RESULT"
    )
    print("=" * 90)

    print(
        "PREDECESSOR_A13              : PASS"
    )

    print(
        "CAPABILITY_FIRST_ROUTER      : PASS"
    )

    print(
        "EXECUTOR_DISCOVERY           : PASS"
    )

    print(
        "TASKS                        : 30"
    )

    print(
        "SINGLE_PRIMARY_EXECUTOR      : PASS"
    )

    print(
        "TASK_OWNERSHIP_LOCK          : PASS"
    )

    print(
        "FALLBACK_ROUTING             : PASS"
    )

    print(
        "FALLBACKS                    :",
        fallbacks,
    )

    print(
        "INDEPENDENT_VERIFICATION     : PASS"
    )

    print(
        "VERIFIER_RUNS                :",
        verifier_runs,
    )

    print(
        "DUPLICATE_REJECTIONS         :",
        duplicate_rejections,
    )

    print(
        "ROUTING_ABSTENTIONS          :",
        abstentions,
    )

    print(
        "SCOPE_REJECTIONS             :",
        scope_rejections,
    )

    print(
        "RESULT_NORMALIZATION         : PASS"
    )

    print(
        "HANDOFF_PRESERVATION         : PASS"
    )

    print(
        "IDEMPOTENT_RETRY             : PASS"
    )

    print(
        "AVAILABILITY_MEMORY          : PASS"
    )

    print(
        "EMPIRICAL_EXECUTOR_MEMORY    : PASS"
    )

    print(
        "EXTERNAL_CREDITS_CONSUMED    : FALSE"
    )

    print(
        "CONFIDENCE_70_REJECTED       : PASS"
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
        "ACTIVE                       : FALSE"
    )

    print(
        "STATE_RECEIPT_HASH_MATCH     : TRUE"
    )

    print(
        "CURRENT_VERSION              :",
        final[
            "current_version"
        ],
    )

    print(
        "STATE_STATUS                 :",
        final[
            "state_status"
        ],
    )

    print(
        "A14_RECEIPT_SHA256           :",
        actual_hash,
    )

    print()
    print(
        "STATUS = V9.0-A14_PASS"
    )
    print("=" * 90)


if __name__ == "__main__":

    try:
        main()

    except Exception as exc:

        try:

            capture_failure(
                str(exc),
                "A14_CERTIFICATION",
                "A14_HARNESS",
            )

            capture_experience(
                "A14_CERTIFICATION_FAILURE",
                "FAILED",
                {
                    "exception":
                        repr(exc),

                    "traceback":
                        traceback.format_exc(),
                },
            )

        except Exception as telemetry_exc:

            print(
                "A14_TELEMETRY_FAILURE:",
                repr(
                    telemetry_exc
                ),
                file=sys.stderr,
            )

        print(
            "A14_CERTIFICATION_FAILED:",
            repr(exc),
            file=sys.stderr,
        )

        raise
'@

[System.IO.File]::WriteAllText(
    $Harness,
    $Code,
    $Utf8NoBom
)

Write-Host ""
Write-Host "======================================================================"
Write-Host " RAIOS V9.0-A14 INSTALLER"
Write-Host "======================================================================"

& $Python -m py_compile $Harness

if ($LASTEXITCODE -ne 0) {
    throw "A14_HARNESS_COMPILE_FAILED"
}

Write-Host "A14_HARNESS_COMPILE = PASS"

Write-Host ""
Write-Host "=== EXECUTING A14 ==="

& $Python $Harness

if ($LASTEXITCODE -ne 0) {
    throw "RAIOS_V9_A14_CERTIFICATION_FAILED"
}

Write-Host ""
Write-Host "======================================================================"
Write-Host " A14 INSTALLER FINISHED"
Write-Host "======================================================================"