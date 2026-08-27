"""Timeout-bounded, failure-isolated, read-only probes. Probe failure is not absence."""

from __future__ import annotations

import os
import socket
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any, Callable

from .observations import observation
from .schema import UNKNOWN

PROBE_FAIL_NE_ABSENT = True


def _tcp(host: str, port: int, timeout: float) -> str:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, port))
        return "SUCCESS"
    except OSError:
        return "OFFLINE"
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _env_present(name: str) -> bool:
    val = os.environ.get(name)
    return bool(val) and len(str(val)) > 0


def _file_exists_no_read(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


class ResourceProbeRunner:
    def __init__(self, *, timeout_seconds: float = 3.0) -> None:
        self.timeout_seconds = timeout_seconds

    def run(
        self,
        *,
        provider: str,
        account: str,
        fn: Callable[[], dict[str, Any]],
        probe_id: str,
    ) -> dict[str, Any]:
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(fn)
                raw = fut.result(timeout=self.timeout_seconds)
        except FuturesTimeout:
            raw = {"status": "UNAVAILABLE", "reason": "TIMEOUT"}
        except Exception as exc:
            raw = {"status": "UNAVAILABLE", "reason": type(exc).__name__}
        status = str(raw.get("status") or "UNKNOWN")
        rec = observation(
            provider=provider,
            account=account,
            resource_or_service=f"probe:{probe_id}",
            value={"status": status, "detail": raw, "UNOBSERVED_NE_ABSENT": True},
            source="ResourceProbeRunner",
            probe_id=probe_id,
            confidence="LOW" if status not in {"SUCCESS", "PARTIAL"} else "MEDIUM",
        )
        rec["PROBE_FAIL_NE_ABSENT"] = True
        rec["status"] = status
        return rec

    def probe_local_control(self) -> dict[str, Any]:
        def _fn() -> dict[str, Any]:
            st = _tcp("127.0.0.1", 8766, min(2.0, self.timeout_seconds))
            return {"status": st, "target": "127.0.0.1:8766", "mode": "TCP"}

        return self.run(provider="GENERIC_HTTP_INFERENCE", account="LOCAL_AG", fn=_fn, probe_id="local-http-8766")

    def probe_credential_presence(self, *, provider: str, account: str, env_name: str | None, file_ref: Path | None) -> dict[str, Any]:
        def _fn() -> dict[str, Any]:
            env_ok = _env_present(env_name) if env_name else False
            file_ok = _file_exists_no_read(file_ref) if file_ref else False
            if env_ok or file_ok:
                return {"status": "PARTIAL", "credential_present": True, "read_secret": False}
            return {"status": "AUTH_REQUIRED", "credential_present": False}

        return self.run(provider=provider, account=account, fn=_fn, probe_id=f"cred-{account}")
