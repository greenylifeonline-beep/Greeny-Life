from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "runtime" / "Migrate-RAIOS-Cognitive-Store.ps1"


def test_bounded_migration_contract() -> None:
    text = SCRIPT.read_text(encoding="utf-8-sig")
    for token in (
        "BatchSize", "MaxSeconds", "Resume", "snapshot.json", "ledger.jsonl",
        "IN_PROGRESS", "bounded_snapshot", "resumable", "promotion_verified",
        "cleanup_executed", "ExecuteCleanup",
    ):
        assert token in text


def test_source_drift_is_fail_closed() -> None:
    text = SCRIPT.read_text(encoding="utf-8-sig")
    for token in (
        "MISSING_AFTER_SNAPSHOT", "METADATA_CHANGED_AFTER_SNAPSHOT",
        "CHANGED_DURING_HASH", "CHANGED_DURING_COPY",
        "SOURCE_DRIFT_OR_VERIFY_FAILURE", "COGNITIVE_MIGRATION_FAIL_CLOSED",
        'promotion_executed=$false', 'archive_created=$false',
    ):
        assert token in text
