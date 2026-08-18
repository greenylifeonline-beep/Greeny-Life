"""Filesystem content-addressed store adapted from Shared Cognitive Exchange V2.

Raw blobs live on disk. SQLite stores metadata only. SHA-256 identity is
verified on every authoritative read. This store is owned by the integration
wave and must never write into live A17.4 harvest paths.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

from .identity import FailClosed, assert_not_protected_live_writer, sha256_bytes

DIGEST_RE = re.compile(r"^[0-9a-f]{64}$")


def fsync_file(fd: int) -> None:
    os.fsync(fd)
    if hasattr(os, "fdatasync"):
        try:
            os.fdatasync(fd)
        except OSError:
            pass


def fsync_path(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def object_relpath(digest: str) -> str:
    if not DIGEST_RE.fullmatch(digest):
        raise FailClosed("INVALID_CONTENT_DIGEST")
    return f"{digest[:2]}/{digest[2:4]}/{digest}"


class ContentAddressedStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        assert_not_protected_live_writer(self.root)
        self.objects = self.root / "objects"
        self.tmp = self.root / "tmp"
        self.quarantine_root = self.root / "quarantine"
        for directory in (self.objects, self.tmp, self.quarantine_root):
            directory.mkdir(parents=True, exist_ok=True)

    def object_path(self, digest: str) -> Path:
        return self.objects / object_relpath(digest)

    def quarantine_path(self, digest: str) -> Path:
        return self.quarantine_root / object_relpath(digest)

    def ingest(self, data: bytes) -> tuple[str, bool]:
        digest = sha256_bytes(data)
        dest = self.object_path(digest)
        if dest.exists():
            self._verify_file(dest, digest)
            return digest, False
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.tmp / f"{digest}.{os.getpid()}.{time.time_ns()}.part"
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        fd = os.open(str(tmp), flags, 0o600)
        try:
            os.write(fd, data)
            fsync_file(fd)
        finally:
            os.close(fd)
        self._verify_file(tmp, digest)
        created = self._exclusive_publish(tmp, dest)
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        self._verify_file(dest, digest)
        return digest, created

    def _exclusive_publish(self, tmp: Path, dest: Path) -> bool:
        if dest.exists():
            return False
        try:
            os.link(tmp, dest)
            return True
        except FileExistsError:
            return False
        except OSError:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            try:
                lock_fd = os.open(str(dest), flags, 0o600)
                os.close(lock_fd)
            except FileExistsError:
                return False
            os.replace(tmp, dest)
            return True

    def _verify_file(self, path: Path, expected: str) -> None:
        observed = sha256_bytes(path.read_bytes())
        if observed != expected:
            raise FailClosed("OBJECT_HASH_TAMPER_DETECTED")

    def read(self, digest: str) -> bytes:
        path = self.object_path(digest)
        if not path.exists():
            if self.quarantine_path(digest).exists():
                raise FailClosed("OBJECT_QUARANTINED")
            raise FailClosed("OBJECT_MISSING")
        self._verify_file(path, digest)
        return path.read_bytes()

    def exists(self, digest: str) -> bool:
        return self.object_path(digest).exists()

    def quarantine(self, data: bytes, reason: str) -> str:
        digest = sha256_bytes(data)
        dest = self.quarantine_path(digest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        meta = dest.with_suffix(".reason.json")
        if not dest.exists():
            dest.write_bytes(data)
        meta.write_text(
            '{"reason":"%s","sha256":"%s"}' % (reason.replace('"', ""), digest),
            encoding="utf-8",
        )
        return digest
