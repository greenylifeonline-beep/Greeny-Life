"""A2A identity/trust. Signature validity is not organization trust."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from typing import Any

from .failclosed import AUTH_FAILED, ISSUER_UNTRUSTED, UNKNOWN_AGENT, FailClosed

PRODUCTION_TRUSTED_ISSUERS: tuple[str, ...] = ()  # do not fabricate org trust
PRODUCTION_DENYLIST: frozenset[str] = frozenset()
# Official JWS lives in a2a.utils.signing (optional extra a2a-sdk[signing]).
OFFICIAL_JWS_MODULE = "a2a.utils.signing"


@dataclass(frozen=True)
class TrustResult:
    SIGNATURE_VALID: bool
    ISSUER_IDENTIFIED: bool
    ISSUER_TRUSTED: bool
    SCOPE_AUTHORIZED: bool
    issuer: str | None
    TRUSTED_ORGANIZATION: bool = False


@dataclass
class TrustPolicy:
    trusted_issuers: tuple[str, ...] = ()
    denylist: frozenset[str] = PRODUCTION_DENYLIST
    key_ids: dict[str, str] = field(default_factory=dict)
    rotation_epoch: int = 0
    jws_required_for_production: bool = True
    self_signed_is_production_trust: bool = False


def jws_architecture_available() -> bool:
    try:
        import a2a.utils.signing  # noqa: F401

        return True
    except ImportError:
        return False


def sign_bytes(payload: bytes, secret: bytes) -> str:
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()


def verify(
    *,
    agent_id: str,
    payload: bytes,
    signature: str | None,
    issuer: str | None,
    trusted_issuers: tuple[str, ...],
    hmac_secrets: dict[str, bytes],
    required_scope: str,
    authorized_scopes: tuple[str, ...],
    allow_unauthenticated_public: bool,
    denylist: frozenset[str] = PRODUCTION_DENYLIST,
) -> TrustResult:
    if not agent_id:
        raise FailClosed(UNKNOWN_AGENT)
    if agent_id in denylist or (issuer and issuer in denylist):
        raise FailClosed(ISSUER_UNTRUSTED, "denylist")
    if allow_unauthenticated_public and not signature:
        return TrustResult(False, False, False, False, None, False)
    if not signature or not issuer:
        raise FailClosed(AUTH_FAILED)
    secret = hmac_secrets.get(issuer)
    if secret is None:
        raise FailClosed(AUTH_FAILED, "unknown-issuer-key")
    expected = sign_bytes(payload, secret)
    sig_ok = hmac.compare_digest(expected, signature)
    if not sig_ok:
        raise FailClosed(AUTH_FAILED, "bad-signature")
    identified = True
    trusted = issuer in trusted_issuers
    # Scopes are server-side only. Caller-claimed scopes must not be passed in.
    scope_ok = bool(trusted and required_scope in authorized_scopes)
    if not trusted:
        return TrustResult(True, identified, False, False, issuer, False)
    return TrustResult(True, True, True, scope_ok, issuer, False)


def require_trusted(result: TrustResult) -> None:
    if not result.ISSUER_TRUSTED:
        raise FailClosed(ISSUER_UNTRUSTED)


def card_payload(card_dict: dict[str, Any]) -> bytes:
    return json.dumps(card_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")


def as_auth_result(result: TrustResult) -> dict[str, Any]:
    return {
        "SIGNATURE_VALID": result.SIGNATURE_VALID,
        "ISSUER_IDENTIFIED": result.ISSUER_IDENTIFIED,
        "ISSUER_TRUSTED": result.ISSUER_TRUSTED,
        "SCOPE_AUTHORIZED": result.SCOPE_AUTHORIZED,
        "TRUSTED_ORGANIZATION": result.TRUSTED_ORGANIZATION,
        "PRINCIPAL_BOUND": False,
        "AUTHORIZED_SCOPES": [],
        "CAPABILITY_AUTHORIZED": False,
        "EFFECTIVE_AUTHORITY": False,
    }
