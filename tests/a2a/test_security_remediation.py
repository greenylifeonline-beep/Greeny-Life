"""A2A security remediation tests T28-T35. Deterministic. No LLM/GPU/paid/public listener."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("NO_LLM_CALLS", "true")

from raios.a2a.cards import FORBIDDEN_PUBLIC_AGENTS, build_extended_card, build_public_card, card_as_dict, reject_seat_as_agent
from raios.a2a.capability import CAPABILITY_NOOP
from raios.a2a.failclosed import (
    AUTH_SCOPE_MISSING,
    AUTHORITY_REQUIRED,
    CAPABILITY_NOT_AUTHORIZED,
    ISSUER_UNTRUSTED,
    SEAT_IDENTITY_NOT_PUBLIC_AGENT,
    FailClosed,
)
from raios.a2a.gateway import A2ARequest, Gateway
from raios.a2a.semantic import complete_contract, default_contract
from raios.a2a.trust import sign_bytes

DENIED = {
    AUTH_SCOPE_MISSING,
    AUTHORITY_REQUIRED,
    CAPABILITY_NOT_AUTHORIZED,
    ISSUER_UNTRUSTED,
    SEAT_IDENTITY_NOT_PUBLIC_AGENT,
}


def _sem() -> dict:
    return complete_contract(default_contract())


def _signed(agent: str, task: str, key: str, secret: bytes = b"test-hmac-secret") -> str:
    return sign_bytes(f"{agent}:{task}:{key}".encode(), secret)


class SecurityRemediationTests(unittest.TestCase):
    def test_T28_VALID_SIGNATURE_UNTRUSTED_ISSUER_DENIED(self):
        sig = _signed("peer.alpha", "t28", "t28")
        with self.assertRaises(FailClosed) as ctx:
            Gateway(hmac_secrets={"issuer-test": b"test-hmac-secret"}, trusted_issuers=()).handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id="raios.foundation.high_risk_mutate",
                    a2a_task_id="t28",
                    a2a_context_id="c28",
                    desired_state={"mutate": True},
                    idempotency_key="t28",
                    semantic_contract=_sem(),
                    action="MUTATE",
                    risk="HIGH",
                    signature=sig,
                    issuer="issuer-test",
                    granted_scopes=("raios.a2a.high_risk", "ADMIN", "C1"),
                    authority_present=True,
                    requested_authority="C1",
                    requested_role="ADMIN",
                )
            )
        self.assertIn(ctx.exception.code, DENIED)
        self.assertNotEqual(ctx.exception.code, "ALLOW")

    def test_T29_TRUSTED_ISSUER_NO_SCOPE_DENIED(self):
        sig = _signed("peer.alpha", "t29", "t29")
        gw = Gateway(
            hmac_secrets={"issuer-trusted": b"test-hmac-secret"},
            trusted_issuers=("issuer-trusted",),
            principal_by_issuer={"issuer-trusted": "principal-t29"},
            scopes_by_principal={},
        )
        with self.assertRaises(FailClosed) as ctx:
            gw.handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id="raios.foundation.high_risk_mutate",
                    a2a_task_id="t29",
                    a2a_context_id="c29",
                    desired_state={"mutate": True},
                    idempotency_key="t29",
                    semantic_contract=_sem(),
                    action="MUTATE",
                    risk="HIGH",
                    signature=sig,
                    issuer="issuer-trusted",
                    granted_scopes=("raios.a2a.high_risk",),
                    authority_present=True,
                    requested_authority="OWNER",
                )
            )
        self.assertEqual(ctx.exception.code, AUTH_SCOPE_MISSING)

    def test_T30_CALLER_SELF_ASSERTED_ADMIN_DENIED(self):
        sig = sign_bytes(b"peer.alpha:t30:t30", b"test-hmac-secret")
        with self.assertRaises(FailClosed) as ctx:
            Gateway(hmac_secrets={"issuer-test": b"test-hmac-secret"}).handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id="raios.foundation.high_risk_mutate",
                    a2a_task_id="t30",
                    a2a_context_id="c30",
                    desired_state={"mutate": True},
                    idempotency_key="t30",
                    semantic_contract=_sem(),
                    action="MUTATE",
                    risk="HIGH",
                    signature=sig,
                    issuer="issuer-test",
                    authority_present=True,
                    requested_role="admin",
                    requested_authority="C1",
                    granted_scopes=("ADMIN", "OWNER", "C1", "SYSTEM", "TRUSTED"),
                )
            )
        self.assertIn(ctx.exception.code, DENIED)

    def test_T31_SCOPE_DOES_NOT_COVER_CAPABILITY_DENIED(self):
        gw = Gateway(
            hmac_secrets={"issuer-trusted": b"test-hmac-secret"},
            trusted_issuers=("issuer-trusted",),
            principal_by_issuer={"issuer-trusted": "principal-t31"},
            scopes_by_principal={"principal-t31": ("raios.a2a.task",)},
        )
        sig = sign_bytes(b"peer.alpha:t31:t31", b"test-hmac-secret")
        with self.assertRaises(FailClosed) as ctx:
            gw.handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id="raios.foundation.high_risk_mutate",
                    a2a_task_id="t31",
                    a2a_context_id="c31",
                    desired_state={"mutate": True},
                    idempotency_key="t31",
                    semantic_contract=_sem(),
                    action="MUTATE",
                    risk="HIGH",
                    signature=sig,
                    issuer="issuer-trusted",
                    granted_scopes=("raios.a2a.high_risk",),
                    authority_present=True,
                )
            )
        self.assertEqual(ctx.exception.code, CAPABILITY_NOT_AUTHORIZED)

    def test_T32_TRUSTED_SCOPED_LOW_RISK_ALLOWED(self):
        gw = Gateway(
            hmac_secrets={"issuer-trusted": b"test-hmac-secret"},
            trusted_issuers=("issuer-trusted",),
            principal_by_issuer={"issuer-trusted": "principal-t32"},
            scopes_by_principal={"principal-t32": ("raios.a2a.task",)},
        )
        sig = sign_bytes(b"peer.alpha:t32:t32", b"test-hmac-secret")
        out = gw.handle(
            A2ARequest(
                agent_id="peer.alpha",
                capability_id=CAPABILITY_NOOP,
                a2a_task_id="t32",
                a2a_context_id="c32",
                desired_state={"ok": True},
                idempotency_key="t32",
                semantic_contract=_sem(),
                signature=sig,
                issuer="issuer-trusted",
            )
        )
        self.assertEqual(out["A2A_RESULT"], "ACCEPTED_DRY_RUN")
        self.assertFalse(out["EXECUTED"])
        self.assertFalse(out["EFFECTIVE_AUTHORITY_GRANTED"])
        ev = out["policy_evidence"]
        for key in ("AUTH_INPUT", "TRUST_RESULT", "SCOPE_RESULT", "CAPABILITY_RESULT", "RISK_RESULT", "AUTHORITY_RESULT", "DENIAL_REASON"):
            self.assertIn(key, ev)
        self.assertTrue(ev["TRUST_RESULT"]["ISSUER_TRUSTED"])
        self.assertTrue(ev["AUTHORITY_RESULT"]["PRINCIPAL_BOUND"])

    def test_T33_HIGH_RISK_CALLER_AUTHORITY_DENIED(self):
        gw = Gateway(
            hmac_secrets={"issuer-trusted": b"test-hmac-secret"},
            trusted_issuers=("issuer-trusted",),
            principal_by_issuer={"issuer-trusted": "principal-t33"},
            scopes_by_principal={"principal-t33": ("raios.a2a.high_risk",)},
            high_risk_principals=(),
        )
        sig = sign_bytes(b"peer.alpha:t33:t33", b"test-hmac-secret")
        with self.assertRaises(FailClosed) as ctx:
            gw.handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id="raios.foundation.high_risk_mutate",
                    a2a_task_id="t33",
                    a2a_context_id="c33",
                    desired_state={"mutate": True},
                    idempotency_key="t33",
                    semantic_contract=_sem(),
                    action="MUTATE",
                    risk="HIGH",
                    signature=sig,
                    issuer="issuer-trusted",
                    authority_present=True,
                    requested_authority="CRITICAL_AUTHORITY",
                    requested_role="OWNER",
                )
            )
        self.assertEqual(ctx.exception.code, AUTHORITY_REQUIRED)

    def test_T34_OPERATIONAL_SEAT_C7_NOT_PUBLISHABLE(self):
        with self.assertRaises(FailClosed) as ctx:
            reject_seat_as_agent("C7-CLOUD-SANDBOX")
        self.assertEqual(ctx.exception.code, SEAT_IDENTITY_NOT_PUBLIC_AGENT)
        with self.assertRaises(FailClosed) as ctx2:
            Gateway().handle(
                A2ARequest(
                    agent_id="C7-CLOUD-SANDBOX",
                    capability_id=CAPABILITY_NOOP,
                    a2a_task_id="t34",
                    a2a_context_id="c34",
                    desired_state={},
                    idempotency_key="t34",
                    semantic_contract=_sem(),
                )
            )
        self.assertEqual(ctx2.exception.code, SEAT_IDENTITY_NOT_PUBLIC_AGENT)

    def test_T35_ALL_OPERATIONAL_SEATS_DENIED(self):
        required = {
            "C1",
            "C2-KAGGLE-CONTROL",
            "C2-PRIMARY-EXECUTOR",
            "C2-ESTATE-RECON",
            "C6-AG-REMOTE-RECON",
            "C7-CLOUD-SANDBOX",
        }
        self.assertTrue(required.issubset(FORBIDDEN_PUBLIC_AGENTS))
        for seat in FORBIDDEN_PUBLIC_AGENTS:
            with self.assertRaises(FailClosed) as ctx:
                reject_seat_as_agent(seat)
            self.assertEqual(ctx.exception.code, SEAT_IDENTITY_NOT_PUBLIC_AGENT)
        pub = card_as_dict(build_public_card())
        self.assertEqual(pub["name"], "RAIOS Foundation Agent")
        skill_ids = [s["id"] for s in pub["skills"]]
        self.assertEqual(skill_ids, ["raios.foundation.noop_intent"])
        blob = str(pub)
        for seat in required:
            self.assertNotIn(seat, blob)
        with self.assertRaises(FailClosed):
            Gateway().extended_agent_card()
        sig = sign_bytes(b"peer.alpha:extended-card", b"test-hmac-secret")
        ext = Gateway(hmac_secrets={"issuer-test": b"test-hmac-secret"}).extended_agent_card(
            agent_id="peer.alpha",
            signature=sig,
            issuer="issuer-test",
        )
        self.assertTrue(any(s["id"] == "raios.foundation.high_risk_mutate" for s in ext["skills"]))
        ext_blob = str(ext)
        for seat in required:
            self.assertNotIn(seat, ext_blob)


if __name__ == "__main__":
    unittest.main()
