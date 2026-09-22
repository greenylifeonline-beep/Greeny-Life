from __future__ import annotations

import json
import hashlib
import subprocess
import zipfile
from pathlib import Path

SCRIPT = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life\scripts\runtime\Migrate-RAIOS-Cognitive-Store.ps1")


def _seed(repo: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        path = repo / "RAIOS" / "V9" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def _run(repo: Path, store: Path, archive: Path, run_id: str, *extra: str) -> subprocess.CompletedProcess[str]:
    cmd = [
        "powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(SCRIPT),
        "-Repo", str(repo), "-Store", str(store), "-ArchiveBase", str(archive),
        "-RunId", run_id, *extra,
    ]
    return subprocess.run(cmd, text=True, capture_output=True, timeout=60)


def test_bounded_migration_resumes_then_promotes(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    store = tmp_path / "store"
    archive = tmp_path / "archive"
    repo.mkdir()
    _seed(repo, {
        "wal/events.jsonl": "one\n",
        "experience/automatic-a4/a.json": '{"a":1}',
        "experience/automatic-a4/b.json": '{"b":2}',
    })
    first = _run(repo, store, archive, "resume-case", "-BatchSize", "1", "-MaxSeconds", "30")
    assert first.returncode == 0, first.stderr
    report = json.loads((archive / "resume-case" / "MIGRATION-REPORT.json").read_text(encoding="utf-8-sig"))
    assert report["status"] == "IN_PROGRESS"
    assert report["cleanup_executed"] is False
    assert report["promotion_executed"] is False
    assert not (archive / "resume-case" / "repo-cognitive-store-before-migration.zip").exists()

    second = _run(repo, store, archive, "resume-case", "-Resume", "-BatchSize", "10", "-MaxSeconds", "30")
    assert second.returncode == 0, second.stderr
    report = json.loads((archive / "resume-case" / "MIGRATION-REPORT.json").read_text(encoding="utf-8-sig"))
    assert report["status"] == "PASS"
    assert report["promotion_verified"] is True
    assert report["bounded_snapshot"] is True
    assert report["resumable"] is True
    assert (archive / "resume-case" / "repo-cognitive-store-before-migration.zip").is_file()
    assert (archive / "resume-case" / "repo-cognitive-store-before-migration.zip.sha256").is_file()
    assert (store / "wal" / "events.jsonl").read_text(encoding="utf-8") == "one\n"
    assert (store / "experience" / "automatic-a4" / "b.json").read_text(encoding="utf-8") == '{"b":2}'


def test_source_drift_fails_closed_without_archive_or_promotion(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    store = tmp_path / "store"
    archive = tmp_path / "archive"
    repo.mkdir()
    _seed(repo, {
        "experience/automatic-a4/a.json": "stable-a",
        "experience/automatic-a4/b.json": "stable-b",
    })
    first = _run(repo, store, archive, "drift-case", "-BatchSize", "1", "-MaxSeconds", "30")
    assert first.returncode == 0, first.stderr
    changed = repo / "RAIOS" / "V9" / "experience" / "automatic-a4" / "b.json"
    changed.write_text("changed-after-snapshot", encoding="utf-8")

    second = _run(repo, store, archive, "drift-case", "-Resume", "-BatchSize", "10", "-MaxSeconds", "30")
    assert second.returncode != 0
    report = json.loads((archive / "drift-case" / "MIGRATION-REPORT.json").read_text(encoding="utf-8-sig"))
    assert report["status"] == "SOURCE_DRIFT_OR_VERIFY_FAILURE"
    assert report["cleanup_executed"] is False
    assert report["promotion_executed"] is False
    assert report["archive_created"] is False
    assert not (archive / "drift-case" / "repo-cognitive-store-before-migration.zip").exists()
    assert not (store / "experience" / "automatic-a4" / "a.json").exists()


def test_prior_verified_archive_is_reused_instead_of_rearchived(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    store = tmp_path / "store"
    archive = tmp_path / "archive"
    repo.mkdir()
    prior_text = "already-preserved"
    rel = "experience/automatic-a4/prior.json"
    _seed(repo, {rel: prior_text, "experience/automatic-a4/new.json": "new-value"})
    prior_dir = archive / "prior-pass"
    prior_dir.mkdir(parents=True)
    prior_zip = prior_dir / "repo-cognitive-store-before-migration.zip"
    with zipfile.ZipFile(prior_zip, "w") as zf:
        zf.writestr(rel, prior_text)
    archive_sha = hashlib.sha256(prior_zip.read_bytes()).hexdigest()
    source_sha = hashlib.sha256(prior_text.encode()).hexdigest()
    (prior_dir / "source-manifest.json").write_text(
        json.dumps([{"relative_path": rel, "bytes": len(prior_text.encode()), "sha256": source_sha}]), encoding="utf-8"
    )
    (prior_dir / "MIGRATION-REPORT.json").write_text(
        json.dumps({"schema": "raios.cognitive-store-migration.v1", "status": "PASS",
                    "archive": str(prior_zip), "archive_sha256": archive_sha}), encoding="utf-8"
    )
    prior_target = store / rel
    prior_target.parent.mkdir(parents=True, exist_ok=True)
    prior_target.write_text(prior_text, encoding="utf-8")
    result = _run(repo, store, archive, "incremental-case", "-BatchSize", "10", "-MaxSeconds", "30")
    assert result.returncode == 0, result.stderr
    report = json.loads((archive / "incremental-case" / "MIGRATION-REPORT.json").read_text(encoding="utf-8-sig"))
    assert report["status"] == "PASS"
    assert report["prior_archive_reused"] == 1
    assert report["delta_files"] == 1
    assert report["prior_archive_sha256"] == archive_sha
    assert not (archive / "incremental-case" / "snapshot-stage" / rel).exists()
    assert (store / "experience" / "automatic-a4" / "new.json").read_text(encoding="utf-8") == "new-value"
