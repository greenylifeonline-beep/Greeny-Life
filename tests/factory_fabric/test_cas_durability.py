from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from raios.factory_fabric.cas_durability import (
    CASIntegrityError,
    publish_verified_copy,
    reconcile_publish_residue,
    verify_object,
)


def test_publish_is_durable_content_addressed_and_idempotent(tmp_path):
    source = tmp_path / "source.jsonl"
    source.write_bytes(b'{"event":"one"}\n')
    before = source.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    destination = tmp_path / "objects" / f"{digest}.jsonl"

    assert publish_verified_copy(source, destination, expected_sha256=digest) is True
    assert publish_verified_copy(source, destination, expected_sha256=digest) is False
    verify_object(destination, digest)
    assert destination.read_bytes() == before
    assert source.read_bytes() == before


def test_existing_corrupt_object_fails_closed(tmp_path):
    source = tmp_path / "source.bin"
    source.write_bytes(b"correct")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = tmp_path / "objects" / f"{digest}.bin"
    destination.parent.mkdir()
    destination.write_bytes(b"tampered")

    with pytest.raises(CASIntegrityError, match="CAS_OBJECT_HASH_MISMATCH"):
        publish_verified_copy(source, destination, expected_sha256=digest)


def test_reconcile_removes_only_publish_residue(tmp_path):
    objects = tmp_path / "objects"
    tmp = objects / ".tmp"
    tmp.mkdir(parents=True)
    stable = objects / ("a" * 64 + ".bin")
    stable.write_bytes(b"stable")
    (tmp / "stale.1.2.part").write_bytes(b"partial")
    (objects / ".candidate.publish.lock").write_bytes(b"")

    result = reconcile_publish_residue(objects)

    assert result == {
        "removed_temp_parts": 1,
        "removed_publish_locks": 1,
    }
    assert stable.read_bytes() == b"stable"
    assert not list(tmp.glob("*.part"))
    assert not list(objects.glob(".*.publish.lock"))


def test_hardlink_failure_uses_exclusive_lock_fallback(tmp_path, monkeypatch):
    source = tmp_path / "source.bin"
    source.write_bytes(b"fallback")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    destination = tmp_path / "objects" / f"{digest}.bin"

    def _no_link(*args, **kwargs):
        raise OSError("hard links unavailable")

    monkeypatch.setattr(os, "link", _no_link)

    assert publish_verified_copy(source, destination, expected_sha256=digest) is True
    verify_object(destination, digest)
    assert not list(destination.parent.glob(".*.publish.lock"))
