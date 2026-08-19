"""D1 Encoding-Safe Subprocess Kernel.

Bytes-first child execution. stdout/stderr are never None.
UnicodeDecodeError cannot abort returncode capture.

Reuses the A3.1 pattern (PYTHONUTF8 + utf-8 + errors=replace)
and forbids brain.py's errors='ignore' evidence destruction.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from .config import FailClosed, sha256_bytes, utc_now

REPLACEMENT = "\ufffd"
KERNEL_ID = "raios.d1.encoding-safe-subprocess.v1"


def process_env(extra: Mapping[str, str] | None = None) -> dict[str, str]:
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONLEGACYWINDOWSSTDIO"] = "0"
    # LANG is ignored on Windows; set it only as a POSIX hint.
    env.setdefault("LANG", "C.UTF-8")
    env.setdefault("LC_ALL", "C.UTF-8")
    if extra:
        env.update({str(k): str(v) for k, v in extra.items()})
    return env


def env_signature(env: Mapping[str, str] | None = None) -> dict[str, str]:
    src = env or os.environ
    keys = (
        "PYTHONUTF8",
        "PYTHONIOENCODING",
        "PYTHONLEGACYWINDOWSSTDIO",
        "LANG",
        "LC_ALL",
        "OS",
        "PATHEXT",
        "COMSPEC",
    )
    return {
        "platform": sys.platform,
        "preferred_encoding": __import__("locale").getpreferredencoding(False),
        "default_encoding": sys.getdefaultencoding(),
        "fs_encoding": sys.getfilesystemencoding(),
        **{k: str(src.get(k) or "") for k in keys},
    }


def _decode(data: bytes | None) -> tuple[str, bool]:
    raw = b"" if data is None else data
    text = raw.decode("utf-8", errors="replace")
    return text, REPLACEMENT in text


@dataclass
class KernelObservation:
    argv: list[str]
    returncode: int
    stdout: str
    stderr: str
    stdout_sha256: str
    stderr_sha256: str
    combined_sha256: str
    encoding: str = "utf-8"
    errors: str = "replace"
    decode_replaced: bool = False
    timed_out: bool = False
    duration_ms: float = 0.0
    cwd: str = ""
    kernel_id: str = KERNEL_ID
    created_at: str = field(default_factory=utc_now)
    env: dict[str, str] = field(default_factory=env_signature)
    stdout_bytes_len: int = 0
    stderr_bytes_len: int = 0
    integrity: str = "OK"

    def as_completed(self) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(self.argv, self.returncode, self.stdout, self.stderr)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class EncodingSafeProcessKernel:
    """Authoritative child process I/O. No locale decode. No errors='ignore'."""

    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str | Path | None = None,
        timeout: float = 30.0,
        env: Mapping[str, str] | None = None,
        strict_utf8: bool = False,
    ) -> KernelObservation:
        if not argv:
            raise FailClosed("PROCESS_ARGV_EMPTY")
        cmd = [str(part) for part in argv]
        merged = process_env(env)
        started = time.perf_counter()
        timed_out = False
        returncode = 124
        stdout_b = b""
        stderr_b = b""
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(cwd) if cwd else None,
                env=merged,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                text=False,
            )
            returncode = int(completed.returncode)
            stdout_b = completed.stdout or b""
            stderr_b = completed.stderr or b""
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout_b = exc.stdout or b""
            stderr_b = exc.stderr or b""
            returncode = 124
        except OSError as exc:
            raise FailClosed(f"PROCESS_SPAWN_FAILED:{exc}") from exc
        stdout, stdout_replaced = _decode(stdout_b)
        stderr, stderr_replaced = _decode(stderr_b)
        replaced = stdout_replaced or stderr_replaced
        duration_ms = (time.perf_counter() - started) * 1000.0
        integrity = "OK"
        if timed_out:
            integrity = "TIMEOUT"
        elif replaced:
            integrity = "DECODE_REPLACED"
        obs = KernelObservation(
            argv=cmd,
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            stdout_sha256=sha256_bytes(stdout_b),
            stderr_sha256=sha256_bytes(stderr_b),
            combined_sha256=sha256_bytes(stdout_b + b"\0" + stderr_b),
            decode_replaced=replaced,
            timed_out=timed_out,
            duration_ms=round(duration_ms, 3),
            cwd=str(cwd or ""),
            env=env_signature(merged),
            stdout_bytes_len=len(stdout_b),
            stderr_bytes_len=len(stderr_b),
            integrity=integrity,
        )
        if timed_out:
            raise FailClosed("CHILD_TIMEOUT")
        if strict_utf8 and replaced:
            raise FailClosed("ENCODING_INTEGRITY_FAILURE")
        return obs


_KERNEL = EncodingSafeProcessKernel()


def encoding_safe_run(
    argv: Sequence[str],
    *,
    cwd: str | Path | None = None,
    timeout: float = 30.0,
    env: Mapping[str, str] | None = None,
    strict_utf8: bool = False,
) -> KernelObservation:
    return _KERNEL.run(argv, cwd=cwd, timeout=timeout, env=env, strict_utf8=strict_utf8)
