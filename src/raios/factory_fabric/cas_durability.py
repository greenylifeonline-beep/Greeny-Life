from __future__ import annotations

import hashlib
import os
import shutil
import time
from pathlib import Path


class CASIntegrityError(RuntimeError):
    """Fail-closed durability/integrity error for Factory Fabric CAS publishing."""


def sha256_path(path: str | Path) -> str:
    path = Path(path)
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        # Directory fsync is best-effort on platforms that reject it.
        pass
    finally:
        os.close(fd)


def verify_object(path: str | Path, expected_sha256: str) -> None:
    path = Path(path)
    if not path.is_file():
        raise CASIntegrityError("CAS_OBJECT_MISSING")
    if sha256_path(path) != expected_sha256:
        raise CASIntegrityError("CAS_OBJECT_HASH_MISMATCH")


def publish_verified_copy(
    source: str | Path,
    destination: str | Path,
    *,
    expected_sha256: str | None = None,
) -> bool:
    """Durably publish one immutable object without overwriting an existing object.

    The source is never mutated. Publication is:
    temp write -> fsync -> SHA-256 verify -> exclusive publish -> verify.
    Returns True only when this call created the destination.
    """

    source = Path(source)
    destination = Path(destination)
    digest = expected_sha256 or sha256_path(source)

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        verify_object(destination, digest)
        return False

    tmp_dir = destination.parent / ".tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    tmp = tmp_dir / f"{destination.name}.{os.getpid()}.{time.time_ns()}.part"
    lock = destination.parent / f".{destination.name}.publish.lock"

    with source.open("rb") as src, tmp.open("xb") as out:
        shutil.copyfileobj(src, out, length=1024 * 1024)
        out.flush()
        os.fsync(out.fileno())
    _fsync_dir(tmp_dir)
    verify_object(tmp, digest)

    created = False
    try:
        try:
            os.link(tmp, destination)
            created = True
            _fsync_dir(destination.parent)
        except FileExistsError:
            verify_object(destination, digest)
        except OSError:
            # Some Windows/filesystem combinations reject hard-link publication.
            # Use an exclusive sidecar lock, never an empty destination placeholder.
            try:
                lock_fd = os.open(
                    str(lock),
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError as exc:
                if destination.exists():
                    verify_object(destination, digest)
                    return False
                raise CASIntegrityError("CAS_PUBLISH_LOCKED") from exc
            else:
                os.close(lock_fd)
                try:
                    if destination.exists():
                        verify_object(destination, digest)
                    else:
                        os.replace(tmp, destination)
                        created = True
                        _fsync_dir(destination.parent)
                finally:
                    try:
                        lock.unlink()
                    except FileNotFoundError:
                        pass
                    _fsync_dir(destination.parent)

        verify_object(destination, digest)
        return created
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def reconcile_publish_residue(objects_dir: str | Path) -> dict[str, int]:
    """Remove only crash residue left before an object became authoritative.

    Objects are never deleted or promoted here. A later estate import can safely
    retry publication from the donor/source if a crash occurred before publish.
    """

    objects_dir = Path(objects_dir)
    tmp_dir = objects_dir / ".tmp"
    removed_parts = 0
    removed_locks = 0

    if tmp_dir.is_dir():
        for part in tmp_dir.glob("*.part"):
            try:
                part.unlink()
                removed_parts += 1
            except OSError:
                pass
        _fsync_dir(tmp_dir)

    for lock in objects_dir.glob(".*.publish.lock"):
        try:
            lock.unlink()
            removed_locks += 1
        except OSError:
            pass

    _fsync_dir(objects_dir)
    return {
        "removed_temp_parts": removed_parts,
        "removed_publish_locks": removed_locks,
    }
