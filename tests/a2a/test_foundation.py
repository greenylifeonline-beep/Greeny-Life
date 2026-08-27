"""Deterministic offline A2A foundation tests T01-T25. NO_LLM NO_PAID_API NO_GPU NO_PUBLIC_LISTENER."""

from __future__ import annotations

import json
import os
import sys
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("NO_LLM_CALLS", "true")

from raios.a2a.bind import assert_bind_allowed
from raios.a2a.cards import (
    FORBIDDEN_PUBLIC_AGENTS,
    build_extended_card,
    build_public_card,
    card_as_dict,
    reject_seat_as_agent,
)
from raios.a2a.capability import CAPABILITY_NOOP, get_contract
from raios.a2a.failclosed import (
    AUTH_FAILED,
    AUTHORITY_REQUIRED,
    CAPABILITY_UNKNOWN,
    DIRECT_EXECUTION_PATH_FORBIDDEN,
    ISSUER_UNTRUSTED,
    MCP_BYPASS_FORBIDDEN,
    PUBLIC_LISTENER_DISABLED,
    RISK_POLICY_DENIED,
    SECRET_LEAK_REJECTED,
    SEMANTIC_CONTRACT_MISMATCH,
    SEMANTIC_CONTRACT_UNKNOWN,
    SEAT_IDENTITY_NOT_PUBLIC_AGENT,
    FailClosed,
)
from raios.a2a.flags import (
    A2A_PRODUCTION_ACTIVATED,
    A2A_PUBLIC_LISTENER_ENABLED,
    AP2_ACTIVATED,
    AP2_IMPLEMENTED,
    HTTP_FALLBACK_PRESERVED,
    HTTP_PRIMARY,
    NATS_PRIMARY,
    NATS_REPLACED,
)
from raios.a2a.gateway import A2ARequest, Gateway, forbidden_direct_execute
from raios.a2a.secrets_guard import scan_mapping
from raios.a2a.semantic import (
    SEMANTIC_CONTRACT_MATCH,
    SEMANTIC_EXTENSION_URI,
    SemanticRegistry,
    complete_contract,
    default_contract,
    fingerprint,
)
from raios.a2a.trust import sign_bytes


def _sem() -> dict:
    return complete_contract(default_contract())


def _gw(**kw) -> Gateway:
    secrets = kw.pop("hmac_secrets", {"issuer-test": b"test-hmac-secret"})
    trusted = kw.pop("trusted_issuers", ())
    return Gateway(hmac_secrets=secrets, trusted_issuers=trusted, **kw)


class FoundationTests(unittest.TestCase):
    def test_T01_PUBLIC_AGENT_CARD_VALID(self):
        d = card_as_dict(build_public_card())
        self.assertEqual(d["name"], "RAIOS Foundation Agent")
        self.assertTrue(d["skills"])
        scan_mapping(d)

    def test_T02_EXTENDED_CARD_REQUIRES_AUTH(self):
        gw = _gw()
        with self.assertRaises(FailClosed) as ctx:
            gw.extended_agent_card()
        self.assertEqual(ctx.exception.code, AUTH_FAILED)
        sig = sign_bytes(b"peer.alpha:extended-card", b"test-hmac-secret")
        ext = gw.extended_agent_card(
            agent_id="peer.alpha",
            signature=sig,
            issuer="issuer-test",
            granted_scopes=("raios.a2a.task",),
        )
        self.assertTrue(any(s["id"] == "raios.foundation.high_risk_mutate" for s in ext["skills"]))

    def test_T03_AGENT_CARD_SECRET_LEAK_REJECTED(self):
        d = card_as_dict(build_public_card())
        d["api_key"] = "REDACTED_SHOULD_REJECT"
        with self.assertRaises(FailClosed) as ctx:
            scan_mapping(d)
        self.assertEqual(ctx.exception.code, SECRET_LEAK_REJECTED)

    def test_T04_CAPABILITY_CONTRACT_VALID(self):
        c = get_contract(CAPABILITY_NOOP)
        for k in (
            "CAPABILITY_ID",
            "SEMANTIC_VERSION",
            "INPUT_SCHEMA",
            "OUTPUT_SCHEMA",
            "AUTHORITY_CLASS",
            "RISK_CLASS",
            "DATA_DOMAINS",
            "TOOLS_REQUIRED",
            "MODEL_REQUIRED",
            "OFFLINE_CAPABLE",
            "SIDE_EFFECTS",
            "REVERSIBLE",
            "COST_CLASS",
            "EVIDENCE_REQUIREMENTS",
            "TIMEOUT",
            "IDEMPOTENCY_SUPPORTED",
        ):
            self.assertIn(k, c)

    def test_T05_UNKNOWN_CAPABILITY_REJECTED(self):
        payload = b"peer.alpha:t5:t5"
        sig = sign_bytes(payload, b"test-hmac-secret")
        with self.assertRaises(FailClosed) as ctx:
            _gw().handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id="no.such.capability",
                    a2a_task_id="t5",
                    a2a_context_id="c5",
                    desired_state={},
                    idempotency_key="t5",
                    semantic_contract=_sem(),
                    signature=sig,
                    issuer="issuer-test",
                    granted_scopes=("raios.a2a.task",),
                )
            )
        self.assertEqual(ctx.exception.code, CAPABILITY_UNKNOWN)

    def test_T06_SEMANTIC_FINGERPRINT_DETERMINISTIC(self):
        a = fingerprint(default_contract())
        b = fingerprint(default_contract())
        self.assertEqual(a, b)

    def test_T07_SEMANTIC_ORDER_NORMALIZATION(self):
        c1 = default_contract()
        c2 = {k: c1[k] for k in reversed(list(c1))}
        self.assertEqual(fingerprint(c1), fingerprint(c2))

    def test_T08_SEMANTIC_CHANGE_CHANGES_FINGERPRINT(self):
        c = default_contract()
        d = dict(c)
        d["tenant"] = "other-tenant"
        self.assertNotEqual(fingerprint(c), fingerprint(d))

    def test_T09_SEMANTIC_MISMATCH_BLOCKED(self):
        bad = dict(_sem())
        bad["tenant"] = "mismatch-tenant"
        with self.assertRaises(FailClosed) as ctx:
            _gw().handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id=CAPABILITY_NOOP,
                    a2a_task_id="t9",
                    a2a_context_id="c9",
                    desired_state={"n": 1},
                    idempotency_key="t9",
                    semantic_contract=bad,
                )
            )
        self.assertEqual(ctx.exception.code, SEMANTIC_CONTRACT_MISMATCH)

    def test_T10_UNKNOWN_SEMANTIC_CONTRACT_BLOCKED(self):
        unknown = dict(_sem())
        unknown["semantic_contract_id"] = "urn:other:unknown"
        with self.assertRaises(FailClosed) as ctx:
            _gw().handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id=CAPABILITY_NOOP,
                    a2a_task_id="t10",
                    a2a_context_id="c10",
                    desired_state={"n": 1},
                    idempotency_key="t10",
                    semantic_contract=unknown,
                )
            )
        self.assertEqual(ctx.exception.code, SEMANTIC_CONTRACT_UNKNOWN)

    def test_T11_A2A_TASK_TO_RAIOS_INTENT(self):
        out = _gw().handle(
            A2ARequest(
                agent_id="peer.alpha",
                capability_id=CAPABILITY_NOOP,
                a2a_task_id="task-11",
                a2a_context_id="ctx-11",
                desired_state={"marker": "alpha"},
                idempotency_key="id-11",
                semantic_contract=_sem(),
            )
        )
        intent = out["intent"]
        self.assertTrue(intent["COMMAND_ID"].startswith("CMD-A2A-"))
        self.assertEqual(intent["CORRELATION_ID"], "ctx-11")
        self.assertEqual(intent["A2A_TASK_ID"], "task-11")
        self.assertIsNone(intent["secrets"])

    def test_T12_DIRECT_EXECUTION_PATH_FORBIDDEN(self):
        with self.assertRaises(FailClosed) as ctx:
            forbidden_direct_execute(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id=CAPABILITY_NOOP,
                    a2a_task_id="t12",
                    a2a_context_id="c12",
                    desired_state={},
                    idempotency_key="t12",
                    semantic_contract=_sem(),
                    direct_execute=True,
                )
            )
        self.assertEqual(ctx.exception.code, DIRECT_EXECUTION_PATH_FORBIDDEN)
        with self.assertRaises(FailClosed) as ctx2:
            _gw().handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id=CAPABILITY_NOOP,
                    a2a_task_id="t12b",
                    a2a_context_id="c12b",
                    desired_state={},
                    idempotency_key="t12b",
                    semantic_contract=_sem(),
                    direct_execute=True,
                )
            )
        self.assertEqual(ctx2.exception.code, DIRECT_EXECUTION_PATH_FORBIDDEN)

    def test_T13_LOW_RISK_POLICY_PATH(self):
        out = _gw().handle(
            A2ARequest(
                agent_id="peer.alpha",
                capability_id=CAPABILITY_NOOP,
                a2a_task_id="t13",
                a2a_context_id="c13",
                desired_state={"ok": True},
                idempotency_key="t13",
                semantic_contract=_sem(),
                risk="LOW",
            )
        )
        self.assertEqual(out["receipt"]["RISK_CLASS"], "LOW")
        self.assertEqual(out["receipt"]["POLICY_RESULT"], "ALLOW")
        self.assertFalse(out["EXECUTED"])

    def test_T14_HIGH_RISK_AUTHORITY_REQUIRED(self):
        payload = b"peer.alpha:t14:t14"
        sig = sign_bytes(payload, b"test-hmac-secret")
        with self.assertRaises(FailClosed) as ctx:
            _gw().handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id="raios.foundation.high_risk_mutate",
                    a2a_task_id="t14",
                    a2a_context_id="c14",
                    desired_state={"mutate": True},
                    idempotency_key="t14",
                    semantic_contract=_sem(),
                    action="MUTATE",
                    risk="HIGH",
                    signature=sig,
                    issuer="issuer-test",
                    granted_scopes=("raios.a2a.task",),
                    authority_present=False,
                )
            )
        self.assertEqual(ctx.exception.code, AUTHORITY_REQUIRED)

    def test_T15_CRITICAL_MUTATION_DENIED_WITHOUT_AUTHORITY(self):
        payload = b"peer.alpha:t15:t15"
        sig = sign_bytes(payload, b"test-hmac-secret")
        with self.assertRaises(FailClosed) as ctx:
            _gw().handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id="raios.foundation.critical_delete",
                    a2a_task_id="t15",
                    a2a_context_id="c15",
                    desired_state={"delete": True},
                    idempotency_key="t15",
                    semantic_contract=_sem(),
                    action="DELETE",
                    risk="CRITICAL",
                    signature=sig,
                    issuer="issuer-test",
                    granted_scopes=("raios.a2a.task",),
                    authority_present=False,
                )
            )
        self.assertIn(ctx.exception.code, {AUTHORITY_REQUIRED, RISK_POLICY_DENIED})

    def test_T16_IDEMPOTENCY_FIRST_APPLY(self):
        out = _gw().handle(
            A2ARequest(
                agent_id="peer.alpha",
                capability_id=CAPABILITY_NOOP,
                a2a_task_id="t16",
                a2a_context_id="c16",
                desired_state={"v": 1},
                idempotency_key="same-key",
                semantic_contract=_sem(),
            )
        )
        self.assertFalse(out["NO_OP"])
        self.assertEqual(out["A2A_RESULT"], "ACCEPTED_DRY_RUN")

    def test_T17_IDEMPOTENCY_SECOND_NO_OP(self):
        gw = _gw()
        req = dict(
            agent_id="peer.alpha",
            capability_id=CAPABILITY_NOOP,
            a2a_task_id="t17",
            a2a_context_id="c17",
            desired_state={"v": 1},
            idempotency_key="dup-key",
            semantic_contract=_sem(),
        )
        first = gw.handle(A2ARequest(**req))
        second = gw.handle(A2ARequest(**req))
        self.assertFalse(first["NO_OP"])
        self.assertTrue(second["NO_OP"])
        self.assertEqual(second["A2A_RESULT"], "ALREADY_APPLIED")

    def test_T18_RECEIPT_CORRELATION_COMPLETE(self):
        out = _gw().handle(
            A2ARequest(
                agent_id="peer.alpha",
                capability_id=CAPABILITY_NOOP,
                a2a_task_id="t18",
                a2a_context_id="c18",
                desired_state={"v": 1},
                idempotency_key="t18",
                semantic_contract=_sem(),
            )
        )
        r = out["receipt"]
        for k in (
            "A2A_TASK_ID",
            "A2A_CONTEXT_ID",
            "COMMAND_ID",
            "CHANGE_ID",
            "CORRELATION_ID",
            "ACTOR",
            "AGENT_ID",
            "CAPABILITY_ID",
            "SEMANTIC_CONTRACT_ID",
            "SEMANTIC_FINGERPRINT",
            "AUTH_RESULT",
            "POLICY_RESULT",
            "RISK_CLASS",
            "TARGET",
            "PRE_STATE_HASH",
            "ACTION",
            "POST_STATE_HASH",
            "STATUS",
            "TIMESTAMP",
            "EVIDENCE_REFS",
            "ROLLBACK_AVAILABLE",
        ):
            self.assertIn(k, r)
        self.assertEqual(r["PRE_STATE_HASH"], "NOT_APPLICABLE")
        self.assertEqual(r["A2A_TASK_ID"], "t18")
        self.assertEqual(r["CORRELATION_ID"], "c18")

    def test_T19_SIGNATURE_VALID_NOT_EQUAL_TRUSTED(self):
        payload = b"peer.alpha:t19:t19"
        sig = sign_bytes(payload, b"test-hmac-secret")
        out = _gw(trusted_issuers=()).handle(
            A2ARequest(
                agent_id="peer.alpha",
                capability_id=CAPABILITY_NOOP,
                a2a_task_id="t19",
                a2a_context_id="c19",
                desired_state={"v": 1},
                idempotency_key="t19",
                semantic_contract=_sem(),
                signature=sig,
                issuer="issuer-test",
                granted_scopes=("raios.a2a.task",),
            )
        )
        auth = out["receipt"]["AUTH_RESULT"]
        self.assertTrue(auth["SIGNATURE_VALID"])
        self.assertFalse(auth["ISSUER_TRUSTED"])
        self.assertFalse(auth["TRUSTED_ORGANIZATION"])

    def test_T20_UNTRUSTED_ISSUER_BLOCKED(self):
        payload = b"peer.alpha:t20:t20"
        sig = sign_bytes(payload, b"test-hmac-secret")
        with self.assertRaises(FailClosed) as ctx:
            _gw(trusted_issuers=()).handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id=CAPABILITY_NOOP,
                    a2a_task_id="t20",
                    a2a_context_id="c20",
                    desired_state={"v": 1},
                    idempotency_key="t20",
                    semantic_contract=_sem(),
                    signature=sig,
                    issuer="issuer-test",
                    granted_scopes=("raios.a2a.task",),
                    require_trusted_issuer=True,
                )
            )
        self.assertEqual(ctx.exception.code, ISSUER_UNTRUSTED)

    def test_T21_MCP_BYPASS_FORBIDDEN(self):
        with self.assertRaises(FailClosed) as ctx:
            _gw().handle(
                A2ARequest(
                    agent_id="peer.alpha",
                    capability_id=CAPABILITY_NOOP,
                    a2a_task_id="t21",
                    a2a_context_id="c21",
                    desired_state={},
                    idempotency_key="t21",
                    semantic_contract=_sem(),
                    mcp_direct=True,
                )
            )
        self.assertEqual(ctx.exception.code, MCP_BYPASS_FORBIDDEN)

    def test_T22_NATS_NOT_REPLACED(self):
        self.assertFalse(NATS_REPLACED)
        self.assertFalse(NATS_PRIMARY)
        out = _gw().handle(
            A2ARequest(
                agent_id="peer.alpha",
                capability_id=CAPABILITY_NOOP,
                a2a_task_id="t22",
                a2a_context_id="c22",
                desired_state={},
                idempotency_key="t22",
                semantic_contract=_sem(),
            )
        )
        self.assertFalse(out["NATS_REPLACED"])

    def test_T23_HTTP_FALLBACK_PRESERVED(self):
        self.assertTrue(HTTP_PRIMARY)
        self.assertTrue(HTTP_FALLBACK_PRESERVED)

    def test_T24_PUBLIC_LISTENER_DISABLED(self):
        self.assertFalse(A2A_PUBLIC_LISTENER_ENABLED)
        self.assertFalse(A2A_PRODUCTION_ACTIVATED)
        assert_bind_allowed("127.0.0.1")
        with self.assertRaises(FailClosed) as ctx:
            assert_bind_allowed("0.0.0.0")
        self.assertEqual(ctx.exception.code, PUBLIC_LISTENER_DISABLED)

    def test_T25_AP2_NOT_ACTIVATED(self):
        self.assertFalse(AP2_IMPLEMENTED)
        self.assertFalse(AP2_ACTIVATED)

    def test_seats_are_not_public_agents(self):
        for seat in FORBIDDEN_PUBLIC_AGENTS:
            with self.assertRaises(FailClosed) as ctx:
                reject_seat_as_agent(seat)
            self.assertEqual(ctx.exception.code, SEAT_IDENTITY_NOT_PUBLIC_AGENT)

    def test_prototype_local_noop_idempotency(self):
        gw = _gw()
        req = A2ARequest(
            agent_id="TEST_REMOTE_AGENT",
            capability_id=CAPABILITY_NOOP,
            a2a_task_id="proto-1",
            a2a_context_id="proto-ctx",
            desired_state={"fixture": True},
            idempotency_key="proto-idem",
            semantic_contract=_sem(),
            a2a_message_id="msg-proto-1",
            a2a_artifact_id="art-proto-1",
        )
        first = gw.handle(req)
        second = gw.handle(req)
        self.assertEqual(first["A2A_RESULT"], "ACCEPTED_DRY_RUN")
        self.assertFalse(first["EXECUTED"])
        self.assertFalse(first["NO_OP"])
        self.assertTrue(second["NO_OP"])
        self.assertEqual(second["A2A_RESULT"], "ALREADY_APPLIED")
        self.assertFalse(second["EXECUTED"])
        disc = gw.discovery()
        self.assertFalse(disc["public_listener"])
        self.assertTrue(disc["in_process_only"])


if __name__ == "__main__":
    unittest.main()
