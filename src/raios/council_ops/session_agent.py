from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.request

try:
    import msvcrt
except ImportError:
    msvcrt = None
try:
    import fcntl
except ImportError:
    fcntl = None
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .operations import CouncilOperations


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def _atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode()
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(raw)
    os.replace(tmp, path)


def _current(expiry: str | None) -> bool:
    if not expiry:
        return False
    try:
        return datetime.fromisoformat(expiry.replace("Z", "+00:00")) > datetime.now(timezone.utc)
    except (TypeError, ValueError):
        return False


class SeatSessionAgent:
    def __init__(self, repo: Path, runtime: Path, seat: str, auth_path: Path,
                 actor_id: str, origin_instance: str, device_id: str, session_id: str) -> None:
        self.repo = repo.resolve()
        self.runtime = runtime.resolve()
        self.seat = seat.upper()
        self.auth_path = auth_path.resolve()
        self.actor_id = actor_id
        self.origin_instance = origin_instance
        self.device_id = device_id
        self.session_id = session_id
        self.ops = CouncilOperations(self.repo, self.runtime)
        self.deliveries = self.repo / ".ai-os" / "state" / "command-fabric" / "deliveries" / self.seat
        self.receipts = self.repo / ".ai-os" / "receipts" / "command-fabric"
        self.heartbeat_path = self.runtime / "consumers" / f"{self.seat}.json"
        self.singleton_path = self.runtime / "consumers" / f"{self.seat}.agent.lock"
        self._singleton_handle = None
        self.started_at = datetime.now(timezone.utc)
        self.command_center = os.getenv("RAIOS_COMMAND_CENTER_URL", "http://127.0.0.1:8770").rstrip("/")

    def _acquire_singleton(self) -> None:
        self.singleton_path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.singleton_path.open("a+b")
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if msvcrt is not None:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            elif fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                raise RuntimeError("NO_PROCESS_LOCK_PRIMITIVE")
        except Exception:
            handle.close()
            raise RuntimeError(f"SEAT_SESSION_SINGLETON_ALREADY_RUNNING::{self.seat}")
        self._singleton_handle = handle
        handle.seek(0)
        handle.write(str(os.getpid()).encode()[:32].ljust(32,b" "))
        handle.flush()

    def _auth(self) -> dict[str, Any]:
        auth = _load(self.auth_path, {})
        auth.update({
            "actor_id": self.actor_id,
            "origin_instance": self.origin_instance,
            "device_id": self.device_id,
            "session_id": self.session_id,
        })
        return auth

    def _binding(self) -> dict[str, Any]:
        data = _load(self.runtime / "actor-bindings.json", {"bindings": {}})
        return (data.get("bindings") or {}).get(self.seat) or {}
    def refresh_presence(self) -> dict[str, Any]:
        auth = self._auth()
        idem = f"{self.seat.lower()}-session-{int(time.time() * 1000)}"
        try:
            return self.ops.prove_presence(seat=self.seat, auth=auth, idem=idem)
        except Exception:
            return self.ops.check_in(seat=self.seat, auth=auth, idem=f"{idem}-in")

    def _binding_live(self) -> bool:
        row = self._binding()
        return bool(
            row.get("actor_id") == self.actor_id
            and row.get("session_id") == self.session_id
            and row.get("device_id") == self.device_id
            and _current(row.get("lease_expires_at"))
        )

    def heartbeat(self) -> None:
        expiry = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        _atomic(self.heartbeat_path, {
            "schema": "raios.seat-consumer-heartbeat.v1",
            "seat": self.seat,
            "actor_id": self.actor_id,
            "origin_instance": self.origin_instance,
            "device_id": self.device_id,
            "session_id": self.session_id,
            "state": "ONLINE",
            "at": utc(),
            "lease_expires_at": expiry,
            "synthetic": False,
        })

    def _eligible_delivery(self, path: Path) -> bool:
        try:
            msg = _load(path, {})
            created = datetime.fromisoformat(str(msg.get("created_at") or "").replace("Z", "+00:00"))
        except Exception:
            return False
        return created >= self.started_at

    @staticmethod
    def _message_fields(text: str) -> dict[str, str]:
        fields: dict[str, str] = {}
        for line in str(text or "").splitlines():
            if "=" in line:
                key, value = line.split("=", 1)
                fields[key.strip().upper()] = value.strip()
        return fields

    def _actor_proof(self) -> dict[str, Any]:
        binding = self._binding()
        presence = _load(self.runtime / "presence.json", {"seats": {}})
        p = (presence.get("seats") or {}).get(self.seat) or {}
        fingerprint = str(p.get("attendance_fingerprint") or "")
        if not fingerprint:
            raise RuntimeError("ATTENDANCE_FINGERPRINT_REQUIRED")
        expected = {
            "actor_id": self.actor_id,
            "session_id": self.session_id,
            "device_id": self.device_id,
            "attendance_fingerprint": fingerprint,
        }
        if binding.get("actor_id") != self.actor_id:
            raise RuntimeError("ACTOR_BINDING_MISMATCH")
        if binding.get("session_id") != self.session_id:
            raise RuntimeError("SESSION_BINDING_MISMATCH")
        if binding.get("device_id") != self.device_id:
            raise RuntimeError("DEVICE_BINDING_MISMATCH")
        return expected

    def _http_json(self, path: str, *, method: str = "GET",
                   payload: dict[str, Any] | None = None,
                   csrf: str | None = None) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if csrf:
            headers["x-raios-csrf"] = csrf
        request = urllib.request.Request(
            self.command_center + path, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=8) as response:
                raw = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"COMMAND_CENTER_HTTP_{exc.code}::{detail[:500]}") from exc
        return json.loads(raw or "{}")

    def _accept_task_assignment(self, msg: dict[str, Any]) -> dict[str, Any] | None:
        text = str((msg.get("payload") or {}).get("text") or "")
        if "TASK_ASSIGNMENT" not in text:
            return None
        fields = self._message_fields(text)
        target = str(fields.get("TARGET") or "").upper()
        if target != self.seat:
            return {"status": "TARGET_MISMATCH", "target": target, "seat": self.seat}
        task_id = fields.get("TASK_ID")
        dispatch_id = fields.get("DISPATCH_ID")
        if not task_id or not dispatch_id:
            return {"status": "MALFORMED_ASSIGNMENT"}
        proof = self._actor_proof()
        csrf_state = self._http_json("/api/csrf")
        csrf = str(csrf_state.get("csrf") or "")
        if not csrf:
            raise RuntimeError("COMMAND_CENTER_CSRF_MISSING")
        result = self._http_json(
            "/api/task-accept",
            method="POST",
            csrf=csrf,
            payload={
                "task_id": task_id,
                "actor": self.seat,
                "dispatch_id": dispatch_id,
                "actor_proof": proof,
            },
        )
        return {
            "status": result.get("status"),
            "task_id": task_id,
            "dispatch_id": dispatch_id,
            "acceptance_fingerprint": result.get("acceptance_fingerprint"),
            "signature_mode": result.get("signature_mode"),
        }

    def _respond_presence_probe(self,msg:dict[str,Any])->dict[str,Any]|None:
        text=str((msg.get("payload") or {}).get("text") or "")
        if "PRESENCE_PROBE" not in text:return None
        fields=self._message_fields(text)
        challenge_id=fields.get("CHALLENGE_ID");nonce=fields.get("NONCE")
        if not challenge_id or not nonce:return None
        auth=self._auth()
        return self.ops.respond_presence_challenge(
            seat=self.seat,challenge_id=challenge_id,nonce=nonce,
            origin_salt=secrets.token_hex(16),response_word=secrets.token_hex(12),
            availability="AVAILABLE",auth=auth,
            idem=f"{self.seat.lower()}-probe-{challenge_id}")
    def consume_once(self) -> int:
        if not self._binding_live():
            return 0
        consumed = 0
        for path in sorted(self.deliveries.glob("MSG-*.json")):
            if not self._eligible_delivery(path):
                continue
            msg = _load(path, {})
            mid = str(msg.get("message_id") or "")
            if not mid:
                continue
            ack = self.receipts / f"{mid}.{self.seat}.actor.ack.receipt.json"
            if ack.exists():
                continue
            raw = path.read_bytes()
            challenge_result=self._respond_presence_probe(msg)
            acceptance_result = None
            acceptance_error = None
            try:
                acceptance_result = self._accept_task_assignment(msg)
            except Exception as exc:
                acceptance_error = f"{type(exc).__name__}:{exc}"
            binding = self._binding()
            presence = _load(self.runtime / "presence.json", {"seats": {}})
            p = (presence.get("seats") or {}).get(self.seat) or {}
            row = {
                "schema": "raios.actor-ack.v1",
                "message_id": mid,
                "actor": self.actor_id,
                "seat": self.seat,
                "target": self.seat,
                "ack_type": "ACTOR_ACK",
                "status": "READ",
                "at": utc(),
                "delivery_sha256": hashlib.sha256(raw).hexdigest(),
                "presence_receipt": p.get("receipt"),
                "source_delivery": str(path),
                "authority": binding.get("auth_evidence"),
                "device_id": self.device_id,
                "session_id": self.session_id,
                "origin_instance": self.origin_instance,
                "synthetic": False,
                "canonical_mutation": False,
                "task_id": (msg.get("payload") or {}).get("task_id"),
                "presence_challenge_verified": bool(challenge_result),
                "presence_challenge_id": (challenge_result or {}).get("challenge_id"),
                "attendance_fingerprint": (challenge_result or {}).get("attendance_fingerprint"),
                "task_acceptance_signed": bool(
                    acceptance_result and acceptance_result.get("status") == "ACCEPTED"),
                "task_acceptance": acceptance_result,
                "task_acceptance_error": acceptance_error,
            }
            _atomic(ack, row)
            consumed += 1
        return consumed

    def run(self) -> None:
        self._acquire_singleton()
        next_presence = 0.0
        while True:
            now = time.time()
            if now >= next_presence:
                self.refresh_presence()
                next_presence = now + 60
            self.heartbeat()
            self.consume_once()
            time.sleep(3)


def main() -> int:
    p = argparse.ArgumentParser(prog="raios-seat-session")
    p.add_argument("--repo", required=True)
    p.add_argument("--runtime", required=True)
    p.add_argument("--seat", required=True)
    p.add_argument("--auth-evidence", required=True)
    p.add_argument("--actor-id", required=True)
    p.add_argument("--origin-instance", required=True)
    p.add_argument("--device-id", required=True)
    p.add_argument("--session-id", required=True)
    args = p.parse_args()
    agent = SeatSessionAgent(
        Path(args.repo), Path(args.runtime), args.seat, Path(args.auth_evidence),
        args.actor_id, args.origin_instance, args.device_id, args.session_id,
    )
    agent.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
