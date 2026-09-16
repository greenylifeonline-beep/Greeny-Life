import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / ".ai-os" / "reports" / "architecture" / "RAIOS-CANONICAL-CONVERGENCE-001"


def _json(name):
    return json.loads((PACK / name).read_text(encoding="utf-8"))


def test_wave01_files_exist():
    for name in (
        "INDEX.json",
        "CLASSIFICATION.json",
        "WAVE-01.json",
        "WAVE-01.md",
        "P0-OBSERVED.json",
        "FORBIDDEN.json",
        "GATES.json",
    ):
        assert (PACK / name).is_file(), name


def test_wave01_excludes_mutation_and_gitignore_only():
    wave = _json("WAVE-01.json")
    assert wave["wave"] == "P1"
    assert wave["C1_FULL_EXECUTE"] is False
    assert wave["C1_MUTATION_AUTHORIZED"] is False
    for banned in (
        "moving or deleting files",
        "gitignore-only mutable-state fix",
        "stop services",
        "C6 live rebind",
        "LOCKS.json mutation",
        "cursor branch extraction",
    ):
        assert banned in wave["excludes"]


def test_eight_kinds_and_no_relocation():
    row = _json("CLASSIFICATION.json")
    kinds = [item["id"] for item in row["kinds"]]
    assert kinds == [
        "LEGAL_SOURCE",
        "GOVERNANCE",
        "DURABLE_EVIDENCE",
        "RUNTIME_STATE",
        "VOLATILE_TELEMETRY",
        "WAL",
        "TEMPORARY",
        "RECOVERY_ARTIFACT",
    ]
    assert row["this_slice_relocated"] == []
    assert row["this_slice_deleted"] == []
    assert row["gitignore_used_as_sole_fix"] is False
    assert "gitignore-only is not the mutable-state solution" in row["law"]
    examples = {item["path"]: item["kind"] for item in row["observed_examples_not_moved"]}
    assert examples[".ai-os/state/command-fabric/WORKER-REGISTRY.json"] == "RUNTIME_STATE"
    assert examples[".ai-os/state/LOCKS.json"] == "GOVERNANCE"


def test_p0_observation_keeps_mutation_blocked():
    obs = _json("P0-OBSERVED.json")
    wave = _json("WAVE-01.json")
    assert obs["C6_LIVE_BOUND_CONSUMER"] is False
    assert obs["TASK_LEASE_ACTIVE"] is False
    assert obs["C1_MUTATION_AUTHORIZED"] is False
    assert obs["mutation_allowed"] is False
    assert obs["locks_mutated"] is False
    assert obs["c6_rebound"] is False
    assert obs["worker_kind"] == "MESSAGE_PICKUP"
    assert wave["observed_this_slice"]["mutation_allowed"] is False
    assert wave["required_before_p1_mutation"]["P0_mutation_allowed"] is True


def test_phase1_campaign_is_files_only():
    campaign = {row["id"]: row for row in _json("PHASES.json")["campaign"]}
    index = _json("INDEX.json")
    gates = _json("GATES.json")
    assert campaign["P0"]["mutation"] == "BLOCKED_NO_C6_LIVE_BINDING"
    assert campaign["P1"]["status"] == "FILES_AND_TESTS_EMITTED"
    assert campaign["P1"]["mutation"] == "BLOCKED_UNTIL_P0_MUTATION_ALLOWED"
    assert campaign["P2"]["status"] == "FILES_AND_TESTS_EMITTED"
    assert campaign["P2"]["mutation"] == "BLOCKED_UNTIL_P0_MUTATION_ALLOWED"
    assert campaign["P3"]["status"] == "QUEUED"
    assert index["IMPLEMENTATION"] == "NOT_STARTED"
    assert index["C1_ACCEPTANCE"] is False
    assert index["C1_MUTATION_AUTHORIZED"] is False
    assert index["C1_PHASE1_FILES_AUTHORIZED"] is True
    assert gates["phase1_this_slice"]["mutation_allowed"] is False
    assert gates["phase1_this_slice"]["files_moved"] is False
    assert "gitignore-only as the mutable-state solution" in _json("FORBIDDEN.json")["forbidden"]
