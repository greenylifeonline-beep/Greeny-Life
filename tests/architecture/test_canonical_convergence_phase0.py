import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
PACK = REPO / ".ai-os" / "reports" / "architecture" / "RAIOS-CANONICAL-CONVERGENCE-001"


def _json(name):
    return json.loads((PACK / name).read_text(encoding="utf-8"))


def test_wave00_files_exist():
    for name in ("INDEX.json", "GATES.json", "FORBIDDEN.json", "WAVE-00.json", "WAVE-00.md", "DESIGN.md"):
        assert (PACK / name).is_file(), name


def test_wave00_excludes_extraction_and_cleanup():
    wave = _json("WAVE-00.json")
    assert wave["wave"] == "P0"
    assert wave["C1_FULL_EXECUTE"] is False
    assert wave["authorized_by_c1"] == "PHASE0_FILES_AND_TESTS_ONLY"
    for banned in (
        "cursor branch extraction",
        "tree cleanup",
        "C6 live rebind",
        "LOCKS.json mutation",
        "merge",
        "delete",
    ):
        assert banned in wave["excludes"]


def test_canonical_branch_matches_authority_file():
    authority = json.loads((REPO / ".ai-os" / "mcp" / "CANONICAL-CHANGE-AUTHORITY.json").read_text(encoding="utf-8"))
    wave = _json("WAVE-00.json")
    gates = _json("GATES.json")
    assert authority["canonical_branch"] == "ai-evolution-202608051809"
    assert wave["required_before_mutation"]["CANONICAL_BRANCH"] == authority["canonical_branch"]
    assert gates["phase0_before_any_mutation"]["CANONICAL_BRANCH"] == authority["canonical_branch"]
    assert authority["workers_may_promote_without_c1_approval"] is False
    assert authority["noncanonical_branch_commit_allowed"] is False
    assert authority["new_worktree_allowed"] is False


def test_lock_owner_is_system_not_a_seat():
    wave = _json("WAVE-00.json")
    seats = json.loads((REPO / ".ai-os" / "mcp" / "SEAT-MAP.json").read_text(encoding="utf-8"))
    assert wave["required_before_mutation"]["LOCK_OWNER"] == "RAIOS_SYSTEM"
    assert seats["owner"] == "RAIOS_SYSTEM"
    assert "permanent_ownership" in seats["seats"]["C6"]["deny"]
    assert "permanent_lock" in seats["seats"]["C6"]["deny"]


def test_mutation_blocked_while_c6_binding_unproven():
    wave = _json("WAVE-00.json")
    obs = wave["observed_this_slice"]
    req = wave["required_before_mutation"]
    assert obs["C6_LIVE_BOUND_CONSUMER"] is False
    assert obs["TASK_LEASE_ACTIVE"] is False
    assert obs["C1_MUTATION_AUTHORIZED"] is False
    assert obs["mutation_allowed"] is False
    assert req["C6_LIVE_BOUND_CONSUMER"] is True
    assert req["TASK_LEASE_ACTIVE"] is True


def test_forbidden_operations_cover_merge_and_rebuild():
    forbidden = set(_json("FORBIDDEN.json")["forbidden"])
    assert "git merge origin/cursor/*" in forbidden
    assert "git rebase whole-branch" in forbidden
    assert "branch deletion before extraction closure" in forbidden
    assert "clean-tree rebuild as primary path" in forbidden
    assert "TASKS.json / LOCKS.json mutation by C2 this slice" in forbidden


def derived_mutation_allowed(wave):
    req = wave["required_before_mutation"]
    obs = wave["observed_this_slice"]
    if obs.get("CANONICAL_BRANCH") != req["CANONICAL_BRANCH"]:
        return False
    if obs.get("CANONICAL_HEAD_PROVEN") is not True:
        return False
    if obs.get("C6_LIVE_BOUND_CONSUMER") is not True:
        return False
    if obs.get("TASK_LEASE_ACTIVE") is not True:
        return False
    if obs.get("LOCK_OWNER_LAW") != req["LOCK_OWNER"]:
        return False
    if obs.get("SCOPE_CONFLICTS") != 0:
        return False
    if obs.get("C1_MUTATION_AUTHORIZED") is not True:
        return False
    return True


def test_index_does_not_claim_full_implementation():
    index = _json("INDEX.json")
    gates = _json("GATES.json")
    assert index["IMPLEMENTATION"] == "NOT_STARTED"
    assert index["C1_ACCEPTANCE"] is False
    assert index["C1_PHASE0_FILES_AUTHORIZED"] is True
    assert index["C1_MUTATION_AUTHORIZED"] is False
    assert index["official_00_12_rewritten"] is False
    assert index["FOUNDATION_BOOTSTRAP_CERTIFIED"] is False
    assert index["this_slice_merged"] is False
    assert index["this_slice_deleted"] is False
    assert index["locks_mutated"] is False
    assert gates["phase0_this_slice"]["C1_PHASE0_FILES_AUTHORIZED"] is True
    assert gates["phase0_this_slice"]["C1_MUTATION_AUTHORIZED"] is False
    assert gates["phase0_this_slice"]["mutation_allowed"] is False


def test_derived_mutation_gate_is_fail_closed():
    wave = _json("WAVE-00.json")
    assert derived_mutation_allowed(wave) is False
    assert wave["observed_this_slice"]["mutation_allowed"] is False
    assert wave["observed_this_slice"]["mutation_allowed"] == derived_mutation_allowed(wave)


def test_later_waves_remain_queued_no_extraction():
    campaign = {row["id"]: row for row in _json("PHASES.json")["campaign"]}
    assert campaign["P0"]["status"] == "FILES_AND_TESTS_EMITTED"
    assert campaign["P0"]["mutation"] == "BLOCKED_NO_C6_LIVE_BINDING"
    assert campaign["P5"]["status"] == "QUEUED"
    assert campaign["P10"]["status"] == "QUEUED"
