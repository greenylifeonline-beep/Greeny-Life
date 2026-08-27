"""Server-side founder/session bind. Envelope actor string is request data only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
SESSION = ROOT / ".ai-os" / "control" / "C1-C5-SESSION.json"
IDENTITY = ROOT / ".ai-os" / "control" / "C2-IDENTITY-BINDING.json"

AUTH_FAILED = "AUTH_FAILED"
AUTHORITY_REQUIRED = "AUTHORITY_REQUIRED"


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def trusted_founder_contexts(*, session: dict[str, Any] | None = None) -> frozenset[str]:
    sess = session if session is not None else load_json(SESSION)
    refs = set()
    for key in ("session_id", "correlation_id"):
        val = sess.get(key)
        if isinstance(val, str) and val.strip():
            refs.add(val.strip())
    ident = load_json(IDENTITY)
    if ident.get("identity_authority") == "C1" and ident.get("operational_status") == "ACTIVE_CANONICAL":
        refs.add("raios.identity.C1.ACTIVE_CANONICAL")
    return frozenset(refs)


def bind_founder(*, actor: str, authority_context_reference: str, session: dict[str, Any] | None = None) -> dict[str, Any]:
    """ACTOR=C1 never grants. Reference must match live session/identity files."""
    _ = actor
    refs = trusted_founder_contexts(session=session)
    ref = (authority_context_reference or "").strip()
    if not ref:
        raise PermissionError(AUTH_FAILED)
    if ref not in refs:
        raise PermissionError(AUTH_FAILED)
    return {
        "PRINCIPAL": "C1@AG",
        "AUTHORITY_SOURCE": "SERVER_SIDE_FOUNDER_SESSION",
        "authority_context_reference": ref,
        "REQUESTED_ACTOR": actor,
        "NOTE": "REQUESTED_ACTOR is request data only",
    }
