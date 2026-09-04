from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    json.loads(payload)
    tmp = path.with_name(f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(payload, encoding="utf-8")
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(.02 * (2 ** attempt))
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _sha(*parts: Any) -> str:
    raw = "\x1f".join(str(x) for x in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class PresenceChallengeError(RuntimeError):
    pass


class PresenceChallengeStore:
    def __init__(self, runtime: Path) -> None:
        self.runtime = runtime.resolve()
        self.path = self.runtime / "presence-challenges.json"
        self.receipts = self.runtime / "receipts"
        self.receipts.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {"schema": "raios.presence-challenges.v1", "challenges": {}}

    def current_for(self, seat: str) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc)
        data = self._load()
        rows = []
        for row in (data.get("challenges") or {}).values():
            if str(row.get("seat") or "").upper() != seat.upper():
                continue
            if row.get("status") != "PENDING":
                continue
            expiry = _parse(row.get("expires_at"))
            if expiry and expiry > now:
                rows.append(row)
        if not rows:
            return None
        rows.sort(key=lambda r: str(r.get("issued_at") or ""), reverse=True)
        return rows[0]

    def issue(self, seat: str, *, reason: str, issued_by: str = "RAIOS-WORKER",
              ttl_seconds: int = 600) -> dict[str, Any]:
        seat = seat.upper()
        old = self.current_for(seat)
        if old:
            return {"status": "ALREADY_PENDING", **old}
        challenge_id = "PCH-" + secrets.token_hex(8)
        nonce = secrets.token_hex(16)
        at = datetime.now(timezone.utc)
        row = {
            "schema": "raios.presence-challenge.v1",
            "challenge_id": challenge_id,
            "seat": seat,
            "nonce": nonce,
            "issued_by": issued_by,
            "reason": reason,
            "issued_at": at.isoformat(),
            "expires_at": (at + timedelta(seconds=ttl_seconds)).isoformat(),
            "status": "PENDING",
            "message_id": None,
            "response_formula": (
                "Echo challenge_id and nonce exactly; choose a fresh origin_salt and response_word; "
                "return authenticated seat/session/device/origin binding. Delivery ACK alone proves nothing."
            ),
        }
        data = self._load()
        data.setdefault("challenges", {})[challenge_id] = row
        data["updated_at"] = _utc()
        _atomic(self.path, data)
        return {"status": "ISSUED", **row}

    def bind_message(self, challenge_id: str, message_id: str) -> dict[str, Any]:
        data = self._load()
        row = (data.get("challenges") or {}).get(challenge_id)
        if not row:
            raise PresenceChallengeError("CHALLENGE_NOT_FOUND")
        row["message_id"] = message_id
        row["message_bound_at"] = _utc()
        data["updated_at"] = _utc()
        _atomic(self.path, data)
        return row

    def consume(self, *, seat: str, challenge_id: str, nonce: str,
                origin_salt: str, response_word: str, auth: dict[str, Any],
                state: str) -> dict[str, Any]:
        seat = seat.upper()
        state = state.upper()
        if state not in {"AVAILABLE", "BUSY", "OFFLINE"}:
            raise PresenceChallengeError("INVALID_AVAILABILITY_RESPONSE")
        data = self._load()
        row = (data.get("challenges") or {}).get(challenge_id)
        if not row:
            raise PresenceChallengeError("CHALLENGE_NOT_FOUND")
        if row.get("status") != "PENDING":
            raise PresenceChallengeError("CHALLENGE_ALREADY_CONSUMED")
        if str(row.get("seat") or "").upper() != seat:
            raise PresenceChallengeError("CHALLENGE_SEAT_MISMATCH")
        expiry = _parse(row.get("expires_at"))
        if not expiry or expiry <= datetime.now(timezone.utc):
            row["status"] = "EXPIRED"
            data["updated_at"] = _utc()
            _atomic(self.path, data)
            raise PresenceChallengeError("CHALLENGE_EXPIRED")
        if nonce != row.get("nonce"):
            raise PresenceChallengeError("NONCE_MISMATCH")
        if not origin_salt.strip() or not response_word.strip():
            raise PresenceChallengeError("FRESH_RESPONSE_MATERIAL_REQUIRED")
        forbidden = {str(row.get("nonce") or "").lower(), challenge_id.lower(), seat.lower()}
        if origin_salt.lower() in forbidden or response_word.lower() in forbidden:
            raise PresenceChallengeError("PRECOMPUTED_OR_REPLAYED_RESPONSE_MATERIAL")
        actor_id = auth.get("actor_id") or auth.get("principal") or auth.get("PRINCIPAL")
        origin = auth.get("origin_instance") or auth.get("ORIGIN_INSTANCE")
        device = auth.get("device_id") or auth.get("remote_device_id") or auth.get("DEVICE_ID")
        session = auth.get("session_id") or auth.get("remote_session_id") or auth.get("SESSION_ID")
        if state in {"AVAILABLE", "BUSY"} and not all((actor_id, origin, device, session)):
            raise PresenceChallengeError("LIVE_SESSION_BINDING_REQUIRED")
        at = _utc()
        fingerprint = _sha(
            "PRESENCE_CHALLENGE_RESPONSE_V1", seat, state, challenge_id, nonce,
            hashlib.sha256(origin_salt.encode()).hexdigest(),
            hashlib.sha256(response_word.encode()).hexdigest(),
            actor_id or "", origin or "", device or "", session or "", at,
        )
        row.update(
            status="CONSUMED",
            consumed_at=at,
            response_state=state,
            origin_salt_sha256=hashlib.sha256(origin_salt.encode()).hexdigest(),
            response_word_sha256=hashlib.sha256(response_word.encode()).hexdigest(),
            response_fingerprint=fingerprint,
            actor_id=actor_id,
            origin_instance=origin,
            device_id=device,
            session_id=session,
        )
        data["updated_at"] = at
        _atomic(self.path, data)
        receipt = {
            "schema": "raios.presence-challenge-receipt.v1",
            "challenge_id": challenge_id,
            "seat": seat,
            "state": state,
            "response_fingerprint": fingerprint,
            "actor_id": actor_id,
            "origin_instance": origin,
            "device_id": device,
            "session_id": session,
            "at": at,
            "message_id": row.get("message_id"),
            "delivery_ack_ne_presence_proof": True,
            "challenge_response_verified": True,
        }
        _atomic(self.receipts / f"{challenge_id}.{seat}.presence-challenge.receipt.json", receipt)
        return receipt
