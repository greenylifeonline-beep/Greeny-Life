"""A2A auth evidence consistency tests T36-T40. Deterministic. No LLM/GPU/paid/public listener."""

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

from raios.a2a.authority import (
    AUTHORITY_SOURCE_C1_TASK_GATE,
    derive,
)
from raios.a2a.failclosed import AUTH_SCOPE_MISSING, FailClosed
from raios.a2a.gateway import A2ARequest, Gateway
from raios.neuro_lingua.schema import RiskLevel
from raios.a2a.semantic import complete_contract, default_contract
from raios.a2a.trust import sign_bytes

PROTECTED = "raios.foundation.high_risk_mutate"


def _sem() -> dict:
    return complete_contract(default_contract())


def _protected_gw() -> Gateway:
    return Gateway(
        hmac_secrets={"issuer-trusted": b"test-hmac-secret"},
        trusted_issuers=("issuer-trusted",),
        principal_by_issuer={"issuer-trusted": "principal-c1"},
        scopes_by_principal={"principal-c1": ("raios.a2a.high_risk",)},
        high_risk_principals=("principal-c1",),
    )


def _protected_req(**kw) -> A2ARequest:
    defaults = dict(
        agent_id="peer.alpha",
        capability_id=PROTECTED,
        a2a_task_id="t36",
        a2a_context_id="c36",
        desired_state={"mutate": True},
        idempotency_key="t36",
        semantic_contract=_sem(),
        action="MUTATE",
        risk="HIGH",
        signature=sign_bytes(b"peer.alpha:t36:t36", b"test-hmac-secret"),
        issuer="issuer-trusted",
        granted_scopes=("ADMIN", "C1", "OWNER"),
        authority_present=True,
        requested_authority="C1",
        requested_role="admin",
    )
    defaults.update(kw)
    return A2ARequest(**defaults)


class AuthEvidenceConsistencyTests(unittest.TestCase):
    def test_T36_EFFECTIVE_AUTHORITY_IMPLIES_SCOPE_AUTHORIZED(self):
        out = _protected_gw().handle(_protected_req())
        auth = out["auth_result"]
        self.assertTrue(auth["EFFECTIVE_AUTHORITY"])
        self.assertTrue(auth["SCOPE_AUTHORIZED"])
        self.assertTrue(auth["CAPABILITY_AUTHORIZED"])
        self.assertFalse(out["EXECUTED"])
        self.assertEqual(out["A2A_RESULT"], "ACCEPTED_DRY_RUN")

    def test_T37_SCOPE_FALSE_CANNOT_EFFECTIVE_TRUE(self):
        decision = derive(
            capability_id=PROTECTED,
            action="MUTATE",
            risk=RiskLevel.HIGH,
            side_effects=True,
            signature_valid=True,
            issuer_identified=True,
            issuer_trusted=True,
            issuer="issuer-trusted",
            principal="principal-c1",
            authorized_scopes=(),
            high_risk_principals=frozenset({"principal-c1"}),
            requested={"authority_present": True, "requested_authority": "C1"},
            task_id="t37",
        )
        self.assertFalse(decision.SCOPE_AUTHORIZED)
        self.assertFalse(decision.EFFECTIVE_AUTHORITY)
        self.assertFalse(decision.EFFECTIVE_AUTHORITY_GRANTED)
        gw = Gateway(
            hmac_secrets={"issuer-trusted": b"test-hmac-secret"},
            trusted_issuers=("issuer-trusted",),
            principal_by_issuer={"issuer-trusted": "principal-c1"},
            scopes_by_principal={},
            high_risk_principals=("principal-c1",),
        )
        with self.assertRaises(FailClosed) as ctx:
            gw.handle(
                _protected_req(
                    a2a_task_id="t37",
                    idempotency_key="t37",
                    signature=sign_bytes(b"peer.alpha:t37:t37", b"test-hmac-secret"),
                )
            )
        self.assertEqual(ctx.exception.code, AUTH_SCOPE_MISSING)

    def test_T38_EXPLICIT_C1_GATE_SERVER_SIDE_PROVENANCE(self):
        out = _protected_gw().handle(
            _protected_req(
                a2a_task_id="t38",
                idempotency_key="t38",
                signature=sign_bytes(b"peer.alpha:t38:t38", b"test-hmac-secret"),
            )
        )
        auth = out["auth_result"]
        requested = out["policy_evidence"]["AUTH_INPUT"]["REQUESTED_AUTHORITY"]
        self.assertEqual(requested["requested_authority"], "C1")
        self.assertEqual(requested["requested_role"], "admin")
        self.assertIn("REQUEST_DATA_ONLY", requested["NOTE"])
        self.assertNotIn("ADMIN", auth["AUTHORIZED_SCOPES"])
        self.assertNotIn("C1", auth["AUTHORIZED_SCOPES"])
        self.assertEqual(auth["AUTHORIZED_SCOPES"], ["raios.a2a.high_risk"])
        self.assertEqual(auth["AUTHORITY_SOURCE"], AUTHORITY_SOURCE_C1_TASK_GATE)
        self.assertTrue(auth["AUTHORITY_SOURCE_PROVENANCE"]["c1_task_gate"])
        self.assertEqual(auth["AUTHORITY_SOURCE_PROVENANCE"]["principal"], "principal-c1")
        self.assertTrue(auth["SCOPE_AUTHORIZED"])
        self.assertTrue(auth["CAPABILITY_AUTHORIZED"])
        self.assertTrue(auth["EFFECTIVE_AUTHORITY"])
        self.assertFalse(out["EXECUTED"])

    def test_T39_AUTH_RESULT_MATCHES_POLICY_DECISION(self):
        out = _protected_gw().handle(
            _protected_req(
                a2a_task_id="t39",
                idempotency_key="t39",
                signature=sign_bytes(b"peer.alpha:t39:t39", b"test-hmac-secret"),
            )
        )
        auth = out["auth_result"]
        ev = out["policy_evidence"]
        self.assertIs(ev["AUTH_RESULT"], auth)
        self.assertEqual(ev["SCOPE_RESULT"]["SCOPE_AUTHORIZED"], auth["SCOPE_AUTHORIZED"])
        self.assertEqual(ev["CAPABILITY_RESULT"]["CAPABILITY_AUTHORIZED"], auth["CAPABILITY_AUTHORIZED"])
        self.assertEqual(ev["AUTHORITY_RESULT"]["EFFECTIVE_AUTHORITY"], auth["EFFECTIVE_AUTHORITY"])
        self.assertEqual(ev["AUTHORITY_RESULT"]["AUTHORITY_SOURCE"], auth["AUTHORITY_SOURCE"])
        self.assertEqual(ev["TRUST_RESULT"]["SIGNATURE_VALID"], auth["SIGNATURE_VALID"])
        self.assertEqual(ev["TRUST_RESULT"]["ISSUER_TRUSTED"], auth["ISSUER_TRUSTED"])
        self.assertNotEqual(auth["SCOPE_AUTHORIZED"], False)
        self.assertTrue(auth["EFFECTIVE_AUTHORITY"])

    def test_T40_RECEIPT_MATCHES_AUTH_RESULT(self):
        out = _protected_gw().handle(
            _protected_req(
                a2a_task_id="t40",
                idempotency_key="t40",
                signature=sign_bytes(b"peer.alpha:t40:t40", b"test-hmac-secret"),
            )
        )
        self.assertIs(out["receipt"]["AUTH_RESULT"], out["auth_result"])
        self.assertEqual(out["receipt"]["AUTH_RESULT"], out["auth_result"])
        self.assertEqual(out["receipt"]["POLICY_RESULT"], "ALLOW")
        self.assertFalse(out["EXECUTED"])


if __name__ == "__main__":
    unittest.main()
