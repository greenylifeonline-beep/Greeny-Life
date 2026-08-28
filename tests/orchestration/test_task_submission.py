from pathlib import Path

import pytest

from raios.orchestration.task_submission import (
    OrchestrationTask,
    TaskSubmissionError,
    authorize_task_capability,
    get_registered_task,
    task_is_registered,
)


def _task() -> OrchestrationTask:
    return OrchestrationTask(
        task_id="GL-005",
        correlation_id="COR-GL005-ORCH-01",
        idempotency_key="idem-gl005-orch-01",
        target="C5",
        requested_capability="c5.self_inspect.health",
        authenticated_principal_ref="C1@AG",
        authority_context_reference="HMAC_FOUNDER_SESSION",
        submitting_agent="chatgpt-main-brain",
    )


def test_registered_gl005_exists() -> None:
    assert task_is_registered("GL-005") is True

    record = get_registered_task("GL-005")

    assert record is not None
    assert record["title"] == "Unified orchestrator"
    assert record["status"] == "READY"


def test_gl005_authorizes_read_only_c5_health() -> None:
    auth = authorize_task_capability(_task())

    assert auth["AUTHORIZED"] is True
    assert auth["TASK_ID"] == "GL-005"
    assert auth["TARGET"] == "C5"
    assert auth["CAPABILITY"] == "c5.self_inspect.health"
    assert auth["RISK_CLASS"] == "LOW"
    assert auth["MODE"] == "READ_ONLY"
    assert auth["MATCHED_SCOPE"]


def test_unregistered_task_fails_closed() -> None:
    task = OrchestrationTask(
        task_id="NOT-REGISTERED",
        correlation_id="COR-X",
        idempotency_key="IDEM-X",
        target="C5",
        requested_capability="c5.self_inspect.health",
        authenticated_principal_ref="C1@AG",
        authority_context_reference="HMAC_FOUNDER_SESSION",
        submitting_agent="chatgpt-main-brain",
    )

    with pytest.raises(
        TaskSubmissionError,
        match="TASK_NOT_REGISTERED",
    ):
        authorize_task_capability(task)


def test_unrelated_capability_fails_closed() -> None:
    task = OrchestrationTask(
        task_id="GL-005",
        correlation_id="COR-X",
        idempotency_key="IDEM-X",
        target="C5",
        requested_capability="c5.unspecified.mutation",
        authenticated_principal_ref="C1@AG",
        authority_context_reference="HMAC_FOUNDER_SESSION",
        submitting_agent="chatgpt-main-brain",
    )

    with pytest.raises(
        TaskSubmissionError,
        match="TASK_CAPABILITY_BINDING_NOT_DEFINED",
    ):
        authorize_task_capability(task)


def test_unapproved_agent_fails_closed() -> None:
    task = OrchestrationTask(
        task_id="GL-005",
        correlation_id="COR-X",
        idempotency_key="IDEM-X",
        target="C5",
        requested_capability="c5.self_inspect.health",
        authenticated_principal_ref="C1@AG",
        authority_context_reference="HMAC_FOUNDER_SESSION",
        submitting_agent="unknown-agent",
    )

    with pytest.raises(
        TaskSubmissionError,
        match="SUBMITTING_AGENT_NOT_ALLOWED",
    ):
        authorize_task_capability(task)

def test_submission_delegates_exact_command_fabric_contract(monkeypatch) -> None:
    import raios.orchestration.task_submission as mod

    captured = {}

    class DummyLeases:
        pass

    class DummyUCP:
        pass

    def fake_executor(
        *,
        env,
        session,
        leases,
        transport=None,
        ucp=None,
        health=None,
        nats_available=True,
        force_duplicate_delivery=False,
        ttl_seconds=120,
    ):
        captured["env"] = env
        captured["session"] = session
        captured["leases"] = leases
        captured["transport"] = transport
        captured["ucp"] = ucp
        captured["health"] = health
        captured["nats_available"] = nats_available
        captured["force_duplicate_delivery"] = force_duplicate_delivery
        captured["ttl_seconds"] = ttl_seconds

        return {
            "STATUS": "COMPLETED",
            "COMMAND_FABRIC_E2E_PROVEN": True,
        }

    task = _task()
    leases = DummyLeases()
    ucp = DummyUCP()
    session = {
        "principal": "C1@AG",
        "authority_source": "HMAC_FOUNDER_SESSION",
    }

    result = mod.submit_authenticated_task(
        task,
        session=session,
        leases=leases,
        transport="TEST_TRANSPORT",
        ucp=ucp,
        health=lambda: {"LIVE": True},
        nats_available=True,
        force_duplicate_delivery=False,
        ttl_seconds=120,
        executor=fake_executor,
    )

    assert captured["env"]["task_id"] == "GL-005"
    assert captured["session"] == session
    assert captured["leases"] is leases
    assert captured["transport"] == "TEST_TRANSPORT"
    assert captured["ucp"] is ucp
    assert captured["nats_available"] is True
    assert captured["force_duplicate_delivery"] is False
    assert captured["ttl_seconds"] == 120

    assert result["registered_task"] is True
    assert result["authenticated_submission"] is True
    assert result["delegated_to_command_fabric"] is True
    assert result["result"]["STATUS"] == "COMPLETED"


def test_submission_requires_authenticated_session() -> None:
    import raios.orchestration.task_submission as mod

    class DummyLeases:
        pass

    with pytest.raises(
        TaskSubmissionError,
        match="AUTHENTICATED_SESSION_REQUIRED",
    ):
        mod.submit_authenticated_task(
            _task(),
            session={},
            leases=DummyLeases(),
            executor=lambda **kwargs: {},
        )
