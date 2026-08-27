"""Server-side founder/session bind. Envelope actor string is request data only."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SESSION = ROOT / ".ai-os" / "control" / "C1-C5-SESSION.json"

AUTH_FAILED = "AUTH_FAILED"
AUTHORITY_REQUIRED = "AUTHORITY_REQUIRED"
STATIC_C1_REF = "raios.identity.C1.ACTIVE_CANONICAL"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def new_founder_secret() -> str:
    return secrets.token_hex(32)


def ensure_founder_secret(session: dict[str, Any]) -> str:
    secret = session.get("founder_secret")
    if not isinstance(secret, str) or len(secret) < 32:
        secret = new_founder_secret()
        session["founder_secret"] = secret
    return secret


def founder_binding(*, secret: str, session_id: str, task_id: str, idempotency_key: str, correlation_id: str) -> str:
    msg = f"{session_id}\n{task_id}\n{idempotency_key}\n{correlation_id}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def trusted_session_ids(*, session: dict[str, Any] | None = None) -> frozenset[str]:
    sess = session if session is not None else load_json(SESSION)
    refs = set()
    for key in ("session_id", "correlation_id"):
        val = sess.get(key)
        if isinstance(val, str) and val.strip():
            refs.add(val.strip())
    return frozenset(refs)


def trusted_founder_contexts(*, session: dict[str, Any] | None = None) -> frozenset[str]:
    """Session ids only. Static identity strings are never grants."""
    return trusted_session_ids(session=session)


def bind_founder(
    *,
    actor: str,
    authority_context_reference: str,
    env: dict[str, Any] | None = None,
    session: dict[str, Any] | None = None,
    channel_attested: bool = False,
    founder_binding_hex: str | None = None,
) -> dict[str, Any]:
    """ACTOR=C1 never grants. Static C1 identity strings never grant."""
    _ = actor
    sess = session if session is not None else load_json(SESSION)
    env = env or {}
    task_id = str(env.get("task_id") or "")
    idem = str(env.get("idempotency_key") or "")
    corr = str(env.get("correlation_id") or "")
    if channel_attested:
        live_id = str(sess.get("session_id") or sess.get("correlation_id") or "").strip()
        if not live_id:
            raise PermissionError(AUTH_FAILED)
        ensure_founder_secret(sess)
        return {
            "PRINCIPAL": "C1@AG",
            "AUTHORITY_SOURCE": "CHANNEL_ATTESTED_FOUNDER_SESSION",
            "authority_context_reference": live_id,
            "REQUESTED_ACTOR": actor,
            "TASK_SCOPED": True,
            "task_id": task_id,
            "NOTE": "REQUESTED_ACTOR and envelope authority_context_reference are request data only; grant is live founder channel attestation",
        }
    refs = trusted_session_ids(session=sess)
    ref = (authority_context_reference or "").strip()
    if not ref or ref == STATIC_C1_REF or ref not in refs:
        raise PermissionError(AUTH_FAILED)
    secret = sess.get("founder_secret")
    if not isinstance(secret, str) or len(secret) < 32:
        raise PermissionError(AUTH_FAILED)
    expected = founder_binding(secret=secret, session_id=ref, task_id=task_id, idempotency_key=idem, correlation_id=corr)
    provided = (founder_binding_hex or "").strip()
    if not provided or not hmac.compare_digest(expected, provided):
        raise PermissionError(AUTH_FAILED)
    return {
        "PRINCIPAL": "C1@AG",
        "AUTHORITY_SOURCE": "HMAC_FOUNDER_SESSION",
        "authority_context_reference": ref,
        "REQUESTED_ACTOR": actor,
        "TASK_SCOPED": True,
        "task_id": task_id,
        "NOTE": "REQUESTED_ACTOR is request data only; grant is HMAC over session+task+idempotency",
    }
