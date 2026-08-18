from __future__ import annotations

import os
import time
from pathlib import Path

from .identity import FailClosed, sha256_bytes
from .paths import sha256_object_relpath


def fsync_path(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    except OSError:
        # Directory fsync is best-effort; some platforms reject it.
        pass
    finally:
        os.close(fd)


def fsync_file(fd: int) -> None:
    os.fsync(fd)
    if hasattr(os, "fdatasync"):
        try:
            os.fdatasync(fd)
        except OSError:
            pass


class ContentAddressedStore:
    """Application-level immutable CAS.

    Windows chmod/readonly bits are NOT a security boundary. Immutability is:
    exclusive create, refuse overwrite, and verify SHA-256 on every
    authoritative read.
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.objects = self.root / "objects"
        self.tmp = self.root / "tmp"
        self.quarantine = self.root / "quarantine"
        for directory in (self.objects, self.tmp, self.quarantine):
            directory.mkdir(parents=True, exist_ok=True)

    def object_path(self, digest: str) -> Path:
        return self.objects / sha256_object_relpath(digest)

    def quarantine_path(self, digest: str) -> Path:
        return self.quarantine / sha256_object_relpath(digest)

    def ingest(self, data: bytes) -> tuple[str, bool]:
        """Crash-safe ingest: temp write → fsync → verify → exclusive publish.

        Returns (sha256, created). Duplicate concurrent ingestors resolve to
        the same canonical object.
        """
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
        fsync_path(self.tmp)
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
            fsync_path(dest.parent)
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
            fsync_path(dest.parent)
            return True

    def _verify_file(self, path: Path, expected: str) -> None:
        observed = sha256_bytes(path.read_bytes())
        if observed != expected:
            raise FailClosed("OBJECT_HASH_TAMPER_DETECTED")

    def read(self, digest: str) -> bytes:
        path = self.object_path(digest)
        if not path.exists():
            q = self.quarantine_path(digest)
            if q.exists():
                raise FailClosed("OBJECT_QUARANTINED")
            raise FailClosed("METADATA_WITHOUT_OBJECT_DETECTED")
        self._verify_file(path, digest)
        return path.read_bytes()

    def exists(self, digest: str) -> bool:
        return self.object_path(digest).exists()

    def list_object_digests(self) -> set[str]:
        found: set[str] = set()
        if not self.objects.exists():
            return found
        for path in self.objects.rglob("*"):
            if path.is_file() and not path.name.endswith(".part"):
                name = path.name
                if len(name) == 64:
                    found.add(name)
        return found

    def list_temp_parts(self) -> list[Path]:
        return [p for p in self.tmp.glob("*.part") if p.is_file()]

    def quarantine_copy(self, digest: str, data: bytes | None = None) -> Path:
        dest = self.quarantine_path(digest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        payload = data if data is not None else (
            self.object_path(digest).read_bytes() if self.exists(digest) else b""
        )
        if not dest.exists():
            dest.write_bytes(payload)
            fsync_path(dest.parent)
        return dest
