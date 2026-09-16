import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / ".ai-os" / "reports" / "architecture" / "RAIOS-CANONICAL-CONVERGENCE-001"
ALLOWED_CLASS = {"OBSERVED", "STALE", "CONFLICTING", "UNPROVEN", "HISTORICAL"}
STAMP_KEYS = ("observed_at", "source", "proof_hash", "class")
FIELDS = (
    "repository_head",
    "evidence_commit",
    "deployed_source_head",
    "runtime_reported_head",
    "state_projection_head",
    "upstream_head",
)
HISTORICAL = {
    "2efd08184614749dee999be7a2456c6bf1387c2e",
    "96a1e7ef9cbbe15176a83c9b65d5efea9239b747",
}


def _json(name):
    return json.loads((PACK / name).read_text(encoding="utf-8"))


def test_wave02_files_exist():
    for name in (
        "HEAD-TRUTH-MODEL.json",
        "HEAD-SNAPSHOT.json",
        "WAVE-02.json",
        "WAVE-02.md",
        "GATES.json",
        "FORBIDDEN.json",
    ):
        assert (PACK / name).is_file(), name


def test_wave02_excludes_cutover_and_projection_rewrite():
    wave = _json("WAVE-02.json")
    assert wave["wave"] == "P2"
    assert wave["C1_FULL_EXECUTE"] is False
    assert wave["C1_MUTATION_AUTHORIZED"] is False
    for banned in (
        "rewriting EXECUTIVE-PROGRAM.json head as current",
        "C5 cutover",
        "C6 live rebind",
        "LOCKS.json mutation",
        "file relocation",
    ):
        assert banned in wave["excludes"]


def test_snapshot_has_named_stamps_not_bare_head():
    snap = _json("HEAD-SNAPSHOT.json")
    model = _json("HEAD-TRUTH-MODEL.json")
    assert snap["stamps"].keys() == set(FIELDS)
    assert model["fields"] == list(FIELDS)
    assert "head" not in snap["stamps"]
    for name in FIELDS:
        row = snap["stamps"][name]
        for key in STAMP_KEYS:
            assert row.get(key), f"{name}.{key}"
        assert row["class"] in ALLOWED_CLASS
        assert row["proof_hash"] in ("sha256:value", "sha256:last_known")


def test_git_refs_match_repository_and_upstream():
    snap = _json("HEAD-SNAPSHOT.json")
    branch = (REPO / ".git" / "refs" / "heads" / "ai-evolution-202608051809").read_text(encoding="utf-8").strip()
    upstream = (REPO / ".git" / "refs" / "remotes" / "origin" / "ai-evolution-202608051809").read_text(encoding="utf-8").strip()
    assert snap["stamps"]["repository_head"]["value"] == branch
    assert snap["stamps"]["upstream_head"]["value"] == upstream
    assert snap["stamps"]["repository_head"]["class"] == "OBSERVED"
    assert snap["stamps"]["upstream_head"]["class"] == "OBSERVED"


def test_historical_heads_are_not_current():
    snap = _json("HEAD-SNAPSHOT.json")
    assert snap["stamps"]["runtime_reported_head"]["class"] == "CONFLICTING"
    assert snap["stamps"]["state_projection_head"]["class"] == "CONFLICTING"
    assert snap["stamps"]["deployed_source_head"]["class"] == "UNPROVEN"
    assert snap["stamps"]["deployed_source_head"]["last_known_class"] == "STALE"
    for sha in HISTORICAL:
        assert sha in snap["historical_unless_live_proves_use"]
        assert snap["stamps"]["repository_head"]["value"] != sha
    exec_prog = json.loads((REPO / ".ai-os" / "state" / "EXECUTIVE-PROGRAM.json").read_text(encoding="utf-8"))
    channel = json.loads((REPO / ".ai-os" / "mcp" / "EXECUTION-CHANNEL.json").read_text(encoding="utf-8"))
    assert exec_prog["head"] == snap["stamps"]["state_projection_head"]["value"]
    assert channel["head"] in snap["stamps"]["state_projection_head"]["also_seen"]
    assert exec_prog["head"] != snap["stamps"]["repository_head"]["value"]
    assert channel["head"] != snap["stamps"]["repository_head"]["value"]


def test_projection_is_not_authority_and_cutover_forbidden():
    snap = _json("HEAD-SNAPSHOT.json")
    wave = _json("WAVE-02.json")
    model = _json("HEAD-TRUTH-MODEL.json")
    gates = _json("GATES.json")
    campaign = {row["id"]: row for row in _json("PHASES.json")["campaign"]}
    index = _json("INDEX.json")
    assert snap["executive_program_is_authority"] is False
    assert wave["observed_this_slice"]["executive_program_treated_as_authority"] is False
    assert snap["c5_cutover_this_slice"] is False
    assert snap["c5_cutover_before_delta_and_rollback_test"] == "FORBIDDEN"
    assert model["snapshot_at_design"]["c5_cutover_before_delta_and_rollback_test"] == "FORBIDDEN"
    assert snap["conflicts"]
    assert wave["observed_this_slice"]["conflicts_present"] is True
    assert gates["phase2_this_slice"]["stale_marked_as_current"] is False
    assert gates["phase2_this_slice"]["mutation_allowed"] is False
    assert gates["phase2_success"]["CANONICAL_HEAD_CONFLICTS"] == 0
    assert campaign["P2"]["status"] == "FILES_AND_TESTS_EMITTED"
    assert campaign["P2"]["mutation"] == "BLOCKED_UNTIL_P0_MUTATION_ALLOWED"
    assert campaign["P3"]["status"] == "QUEUED"
    assert index["C1_PHASE2_FILES_AUTHORIZED"] is True
    assert index["C1_MUTATION_AUTHORIZED"] is False
    assert index["IMPLEMENTATION"] == "NOT_STARTED"
    assert snap["locks_mutated"] is False
    assert snap["mutation_allowed"] is False
