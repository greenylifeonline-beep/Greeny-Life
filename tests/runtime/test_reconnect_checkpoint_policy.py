import importlib.util
from pathlib import Path

MODULE = Path(__file__).parents[2] / "scripts" / "runtime" / "continuity" / "raios_reconnect_checkpoint.py"
spec = importlib.util.spec_from_file_location("raios_reconnect_checkpoint", MODULE)
checkpoint = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checkpoint)

def test_probe_failure_is_pending_not_drift():
    base = {"canonical_branch":"b","branch":"b","local_head":"a","dirty_tracked_sha256":"x","remote_tracking_head":"r"}
    new = dict(base, remote_probe_ok=False, remote_probe_error="TIMEOUT", status_error="WORKTREE_PROBE_TIMEOUT", comparable=False)
    assert checkpoint.compare(base, new) == {}
    pending = checkpoint.verification_pending(base, new)
    assert pending["remote_probe"] == "TIMEOUT"
    assert pending["working_tree_probe"] == "WORKTREE_PROBE_TIMEOUT"

def test_real_head_change_is_drift():
    base = {"canonical_branch":"b","branch":"b","local_head":"a","dirty_tracked_sha256":"x","remote_tracking_head":"r"}
    new = dict(base, local_head="c", remote_probe_ok=True, status_error=None, comparable=True)
    assert checkpoint.compare(base, new)["local_head"] == {"before":"a","after":"c"}

def test_missing_field_is_pending_not_drift():
    base = {"canonical_branch":"b","branch":"b","local_head":None,"dirty_tracked_sha256":"x","remote_tracking_head":"r"}
    new = dict(base, local_head="a", remote_probe_ok=True, status_error=None, comparable=True)
    assert checkpoint.compare(base, new) == {}
    assert "local_head" in checkpoint.verification_pending(base, new)["missing_comparable_fields"]

def test_index_metadata_fingerprint_change_is_not_source_drift():
    base = {"canonical_branch":"b","branch":"b","local_head":"a","dirty_tracked_sha256":"old","remote_tracking_head":"r","working_tree_clean":False}
    new = dict(base, dirty_tracked_sha256="new", remote_probe_ok=True, status_error=None, comparable=True)
    assert checkpoint.compare(base, new) == {}

def test_cleanliness_transition_is_real_workspace_drift():
    base = {"canonical_branch":"b","branch":"b","local_head":"a","dirty_tracked_sha256":"x","remote_tracking_head":"r","working_tree_clean":True}
    new = dict(base, working_tree_clean=False, remote_probe_ok=True, status_error=None, comparable=True)
    assert checkpoint.compare(base, new)["working_tree_clean"] == {"before":True,"after":False}

if __name__ == "__main__":
    test_probe_failure_is_pending_not_drift()
    test_real_head_change_is_drift()
    test_missing_field_is_pending_not_drift()
    test_index_metadata_fingerprint_change_is_not_source_drift()
    test_cleanliness_transition_is_real_workspace_drift()
    print("CHECKPOINT_POLICY_PASS")
