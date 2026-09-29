import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))
sys.path.insert(0, str(ROOT / "RAIOS" / "V9"))

from raios_c5_grind import DOMAINS  # noqa: E402
from raios_c5_train import COMMAND  # noqa: E402


def test_self_inspection_package_exports_engine_inspect():
    from autonomic.self_inspection import inspect as pkg_inspect
    from autonomic.self_inspection.engine import inspect as eng_inspect

    assert pkg_inspect is eng_inspect


def test_marketing_domain_mills_architecture_keeper_not_duplicate_brand_copy():
    marketing = next(row for row in DOMAINS if row["id"] == "marketing")
    assert marketing["keepers"] == ("canonical/docs/architecture/SYSTEM_ARCHITECTURE.md",)
    assert (ROOT / marketing["keepers"][0]).is_file()


def test_run_all_ps1_refuses_brain_and_points_at_train_mesh():
    text = (ROOT / "run_all.ps1").read_text(encoding="utf-8")
    assert "DO_NOT_RUN" in text
    assert "raios_c5_train.py" in text
    assert "brain.py" in text
    assert COMMAND.endswith("raios_c5_train.py")
    assert "brain_fixed.py" not in text


def test_legacy_brain_launchers_fail_closed_onto_train_keeper(tmp_path):
    import subprocess

    for name in ("fix_brain.py", "run_audit_hack.py"):
        proc = subprocess.run(
            [sys.executable, str(ROOT / name)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 2, name
        err = proc.stderr + proc.stdout
        assert "DO_NOT_RUN" in err, name
        assert "raios_c5_train.py" in err, name
        assert not (tmp_path / "brain_fixed.py").exists()


def test_same_function_bind_report_does_not_merge_specialized_jobs():
    import json

    rec = json.loads((ROOT / ".ai-os" / "reports" / "SAME-FUNCTION-BIND.json").read_text(encoding="utf-8"))
    assert rec["new_engine_created"] is False
    assert rec["new_bus_created"] is False
    assert rec["wal_written"] is False
    assert rec["gl005_proven"] is False
    whys = {row["why"] for row in rec["specialized_not_merged"]}
    assert "COGNITIVE_EVENT_WAL_NE_JOB_LEDGER" in whys
    assert "COMPUTE_HOST_NE_LANGUAGE_PROVIDER" in whys
    keepers = {row["keeper"] for row in rec["bound"]}
    assert "scripts/ai-os/raios_c5_train.py" in keepers
    assert "RAIOS/V9/autonomic/self_inspection/engine.py" in keepers
