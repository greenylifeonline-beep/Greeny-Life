import inspect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts" / "ai-os"))
from raios_c5_cross_tree import (  # noqa: E402
    LAWS,
    REPORT_NAMES,
    ROOT,
    WAL,
    REPORTS,
    strip_userinfo,
    reconcile,
)
from raios_c5_train import KEEPERS, train  # noqa: E402

TOKEN_MARKERS = ("x-access-token", "ghs_", "ghp_", "github_pat_")


def _no_secrets(payload: object) -> None:
    blob = json.dumps(payload, ensure_ascii=False).lower()
    for marker in TOKEN_MARKERS:
        assert marker not in blob, marker


def test_strip_userinfo_drops_token():
    raw = "https://x-access-token:ghs_exampletoken@github.com/greenylifeonline-beep/greeny-life"
    out = strip_userinfo(raw)
    assert out == "https://github.com/greenylifeonline-beep/greeny-life"
    assert "ghs_" not in out
    assert "x-access-token" not in out


def test_cross_tree_fail_closed_no_wal_no_gl005_no_delete_no_copy():
    before = WAL.stat().st_mtime if WAL.exists() else None
    rec = reconcile()
    after = WAL.stat().st_mtime if WAL.exists() else None
    assert rec["ok"] is True
    assert rec["from"] == "C2"
    assert rec["c5"] == "git"
    assert rec["wave"] == "CROSS-TREE-UNIFICATION"
    assert rec["wal_written"] is False
    assert rec["wal_mtime_unchanged"] is True
    assert rec["gl005_proven"] is False
    assert rec["deleted"] is False
    assert rec["merge_executed"] is False
    assert rec["copied_paths"] == []
    assert before == after
    flags = rec["flags"]
    assert flags["GL005_PROVEN"] is False
    assert flags["EXTRACTED_QWEN_GRANITE"] is False
    assert flags["SAFE_TO_REMOVE_SOURCE"] is False
    assert flags["CROSS_TREE_UNIFICATION_PROVEN"] is False
    assert flags["C3_BOUND_TO_CANONICAL"] is False
    assert flags["C4_BOUND_TO_CANONICAL"] is False
    assert flags["C6_BOUND_TO_CANONICAL"] is False
    assert flags["C2_BOUND_TO_CANONICAL"] is True
    assert flags["C5_BOUND_TO_CANONICAL"] is True
    assert flags["UNIQUE_WORK_PRESERVED"] is True
    assert flags["DELETED_ANY_TREE"] is False
    assert flags["NONCANONICAL_LIVE_PROCESSES"] == 0
    assert rec["canonical_path"] == str(ROOT)
    assert "Greeny-Life-Repair" not in rec["canonical_path"]
    assert "NOT_CHOSEN_BY_PATH_NAME" in LAWS
    _no_secrets(rec)
    for name in REPORT_NAMES:
        path = REPORTS / name
        assert path.is_file(), name
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload.get("gl005_proven") is False
        _no_secrets(payload)
    root_doc = json.loads((REPORTS / "CANONICAL-ROOT.json").read_text(encoding="utf-8"))
    assert root_doc["not_chosen_by_path_name"] is True
    assert root_doc["absolute_path"] == str(ROOT)
    assert root_doc["proof"]["path_name_would_have_chosen_repair"]
    assert "Repair" in root_doc["proof"]["path_name_would_have_chosen_repair"]
    assert root_doc["scope"] == "REACHABLE_TREES_THIS_HOST"
    actors = json.loads((REPORTS / "ACTOR-BINDING-MATRIX.json").read_text(encoding="utf-8"))
    assert actors["actors"]["C3"]["bound"] is False
    assert actors["actors"]["C3"]["impersonated"] is False
    assert actors["actors"]["C4"]["bound"] is False
    assert actors["seat_map_laws_unchanged"] is True
    unique = json.loads((REPORTS / "UNIQUE-ASSET-RECONCILIATION.json").read_text(encoding="utf-8"))
    assert unique["blind_copy_over"] is False
    assert unique["copied_paths"] == []
    if Path("/tmp/c5-clone-v9").exists():
        assert unique["reachable_unique_to_clone_v9_tracked"] == 0
    noncan = json.loads((REPORTS / "NONCANONICAL-TREES.json").read_text(encoding="utf-8"))
    assert noncan["delete_gates"]["any_deleted"] is False
    assert noncan["delete_gates"]["confidence"] < 0.99
    repair = next(t for t in noncan["trees"] if t["id"] == "C3C4_REPAIR")
    assert repair["classification"] == "RETAIN_AS_WORKTREE"
    assert repair["deleted"] is False
    src = inspect.getsource(train)
    assert "cross_tree" not in src
    assert "reconcile" not in src
    assert any(name == "cross-tree" for name, _ in KEEPERS)
