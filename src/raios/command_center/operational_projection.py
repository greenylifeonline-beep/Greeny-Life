"""Read-only operational projections over existing Command Center sources.

Not a second registry, scheduler, bus, MCP, or program ledger.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CORE_RUNTIME_IDS = {
    "command-center",
    "c5-runtime",
    "universal-mcp",
    "message-worker",
    "nats",
}
MAX_ATTENTION_SCAN = 256
MAX_ATTENTION_ITEMS = 64
MAX_CAPABILITY_PROVIDERS = 64


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default


def _mtime_iso(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _norm_head(value: Any) -> str:
    text = str(value or "").strip()
    if not text or text.upper() in {"UNKNOWN", "NONE", "NULL"}:
        return "UNKNOWN"
    return text


def head_truth(
    *,
    canonical_head: Any = None,
    deployed_head: Any = None,
    runtime_head: Any = None,
    actor_observed_head: Any = None,
    remote_head: Any = None,
) -> dict[str, Any]:
    canonical = _norm_head(canonical_head)
    deployed = _norm_head(deployed_head)
    runtime = _norm_head(runtime_head)
    actor = _norm_head(actor_observed_head)
    remote = _norm_head(remote_head)
    drift: list[str] = []
    known = {
        "CANONICAL_HEAD": canonical,
        "DEPLOYED_HEAD": deployed,
        "RUNTIME_HEAD": runtime,
        "ACTOR_OBSERVED_HEAD": actor,
    }
    present = {k: v for k, v in known.items() if v != "UNKNOWN"}
    values = set(present.values())
    if len(values) > 1:
        if canonical != "UNKNOWN" and deployed != "UNKNOWN" and canonical != deployed:
            drift.append("CANONICAL_NE_DEPLOYED")
        if canonical != "UNKNOWN" and runtime != "UNKNOWN" and canonical != runtime:
            drift.append("CANONICAL_NE_RUNTIME")
        if runtime != "UNKNOWN" and actor != "UNKNOWN" and runtime != actor:
            drift.append("RUNTIME_NE_ACTOR_OBSERVED")
        if canonical != "UNKNOWN" and actor != "UNKNOWN" and canonical != actor:
            drift.append("CANONICAL_NE_ACTOR_OBSERVED")
    return {
        "schema": "raios.head-truth.v1",
        "CANONICAL_HEAD": canonical,
        "DEPLOYED_HEAD": deployed,
        "RUNTIME_HEAD": runtime,
        "ACTOR_OBSERVED_HEAD": actor,
        "REMOTE_HEAD": remote,
        "generic_head_omitted": True,
        "drift": drift,
        "drift_ne_corruption": True,
        "corruption": False,
        "auto_approval": False,
        "auto_commit": False,
        "auto_push": False,
    }


def capability_projection(repo: Path) -> dict[str, Any]:
    repo = Path(repo).resolve()
    gateway_path = repo / ".ai-os" / "mcp" / "AI-GATEWAY.json"
    hermes_path = repo / ".ai-os" / "mcp" / "HERMES-PROVIDER.json"
    channel_path = repo / ".ai-os" / "mcp" / "EXECUTION-CHANNEL.json"
    gateway = _load(gateway_path, {})
    hermes = _load(hermes_path, {})
    channel = _load(channel_path, {})
    observed_at = datetime.now(timezone.utc).isoformat()
    by_capability: dict[str, list[dict[str, Any]]] = {}
    providers: list[dict[str, Any]] = []

    def _add(capability: str, row: dict[str, Any]) -> None:
        if len(providers) >= MAX_CAPABILITY_PROVIDERS:
            return
        cap = capability or "UNKNOWN"
        item = dict(row)
        item["CAPABILITY"] = cap
        providers.append(item)
        by_capability.setdefault(cap, []).append(item)

    for row in gateway.get("providers") or []:
        if not isinstance(row, dict):
            continue
        pid = str(row.get("provider_id") or row.get("model_id") or "").strip()
        if not pid:
            continue
        caps = [str(x) for x in (row.get("capabilities") or []) if str(x).strip()]
        if not caps:
            caps = ["UNKNOWN"]
        payload = {
            "PROVIDER": pid,
            "IMPLEMENTATION": row.get("model_id") or pid,
            "HEALTH": "UNKNOWN",
            "CERTIFICATION": row.get("availability") or "UNKNOWN",
            "LAST_PROBE": None,
            "FRESHNESS": "UNKNOWN",
            "FAILURE": None,
            "local": row.get("local") is True,
            "enabled": row.get("enabled") is not False,
            "source": "AI-GATEWAY.json",
            "source_observed_at": _mtime_iso(gateway_path),
            "raios_core": False,
            "live_probe": False,
        }
        for cap in caps[:8]:
            _add(cap, payload)

    if hermes:
        _add(
            str(hermes.get("capability") or "KnowledgeIngest"),
            {
                "PROVIDER": hermes.get("provider_id") or "hermes-knowledge-ingest",
                "IMPLEMENTATION": "provider-adapter",
                "HEALTH": "UNKNOWN",
                "CERTIFICATION": "DECLARED" if hermes.get("enabled") is True else "UNKNOWN",
                "LAST_PROBE": None,
                "FRESHNESS": "UNKNOWN",
                "FAILURE": None,
                "not_core": hermes.get("not_core") is True,
                "ninth_mcp": hermes.get("ninth_mcp") is True,
                "hermes_is_scheduler": False,
                "hermes_is_mcp": False,
                "hermes_is_governance": False,
                "hermes_is_memory_core": False,
                "hermes_is_task_queue": False,
                "hermes_is_command_plane": False,
                "source": "HERMES-PROVIDER.json",
                "source_observed_at": _mtime_iso(hermes_path),
                "raios_core": False,
                "live_probe": False,
            },
        )

    for row in channel.get("runtimes") or []:
        if not isinstance(row, dict) or row.get("adapter") is not True:
            continue
        rid = str(row.get("id") or "").strip()
        if not rid or rid in CORE_RUNTIME_IDS:
            continue
        caps = [str(x) for x in (row.get("capabilities") or []) if str(x).strip()]
        if not caps:
            caps = [str(row.get("role") or "RemoteCapability")]
        stamp = row.get("health")
        payload = {
            "PROVIDER": rid,
            "IMPLEMENTATION": row.get("transport") or rid,
            "HEALTH": "UNKNOWN",
            "CERTIFICATION": "ADAPTER_DECLARED",
            "LAST_PROBE": None,
            "FRESHNESS": "STALE" if stamp else "UNKNOWN",
            "FAILURE": row.get("failure"),
            "declared_health_stamp": stamp,
            "declared_health_freshness": "STALE",
            "remote_capability": True,
            "raios_core": False,
            "source": "EXECUTION-CHANNEL.json",
            "source_observed_at": _mtime_iso(channel_path),
            "live_probe": False,
        }
        for cap in caps[:8]:
            _add(cap, payload)

    return {
        "schema": "raios.capability-provider-map.v1",
        "observed_at": observed_at,
        "capability_first": True,
        "provider_ne_core": True,
        "second_provider_registry": False,
        "ollama_tags_called": False,
        "live_probe_on_dashboard_refresh": False,
        "model_count": None,
        "timeout_ne_empty_inventory": True,
        "capabilities": [
            {"CAPABILITY": cap, "providers": rows}
            for cap, rows in list(by_capability.items())[:64]
        ],
        "providers": providers,
        "count": len(providers),
        "law": [
            "CAPABILITY_THEN_PROVIDER",
            "PROVIDERS_NEVER_CORE",
            "HERMES_IS_PROVIDER_ADAPTER",
            "REMOTE_ADAPTER_NE_RAIOS_CORE",
            "DECLARED_HEALTH_STAMP_NE_LIVE",
        ],
    }


def operational_attention(
    *,
    tasks: list[dict[str, Any]] | None = None,
    mcp: dict[str, Any] | None = None,
    engine: dict[str, Any] | None = None,
    heads: dict[str, Any] | None = None,
    c5_runtime: dict[str, Any] | None = None,
    c8_route: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    observed_at = datetime.now(timezone.utc).isoformat()

    def _item(category: str, **fields: Any) -> None:
        if len(items) >= MAX_ATTENTION_ITEMS:
            return
        row = {"category": category, "fabricated_score": False}
        prio = fields.get("priority")
        if prio not in (None, "", "UNKNOWN"):
            row["priority"] = prio
        row.update({k: v for k, v in fields.items() if k != "priority" or prio not in (None, "", "UNKNOWN")})
        items.append(row)

    for task in (tasks or [])[:MAX_ATTENTION_SCAN]:
        if not isinstance(task, dict):
            continue
        tid = task.get("id")
        blocker = str(task.get("blocker") or "")
        blocker_u = blocker.upper()
        status = str(task.get("status") or "").upper()
        dispatch = str(task.get("dispatch_status") or "").upper()
        prio = task.get("scheduler_priority") or task.get("priority")
        claimed = str(task.get("claimed_by") or task.get("assigned_to") or "").upper()
        if "AWAITING_C1" in blocker_u or dispatch in {"AWAITING_C1", "C1_APPROVAL_REQUIRED"}:
            _item("C1_APPROVAL_REQUIRED", task_id=tid, priority=prio, blocker=blocker or None)
        if "ACK" in blocker_u and "PENDING" in blocker_u:
            _item("ACTOR_ACK_PENDING", task_id=tid, priority=prio, blocker=blocker)
        if status == "BLOCKED" and "TEST" in blocker_u:
            _item("TEST_FAILURE", task_id=tid, priority=prio, blocker=blocker or status, ledger_status=status)
        if "READY_FOR_REVIEW" in dispatch or str(task.get("review_state") or "").upper() == "READY_FOR_REVIEW":
            _item("REVIEW_REQUIRED", task_id=tid, priority=prio)
        if claimed.startswith("C8"):
            _item("C8_ACTIVATION_PENDING", task_id=tid, priority=prio, seat="C8", activate=False, ack=False)
        if status == "IN_PROGRESS":
            _item("TASK_HANGING", task_id=tid, priority=prio, ledger_status=status, claimed_by=claimed or None)
        elif status == "BLOCKED":
            _item("TASK_BLOCKED", task_id=tid, priority=prio, blocker=blocker or status)

    if mcp:
        live = mcp.get("live")
        http = mcp.get("http")
        if live is True:
            pass
        elif http == 0:
            _item("MCP_STATE_UNCERTAINTY", observation_class="UNKNOWN", http=http)
        elif live is False:
            _item("MCP_STATE_UNCERTAINTY", observation_class="CURRENT", http=http, live=False)

    if engine:
        for row in (engine.get("engines") or [])[:32]:
            if row.get("STATE") == "DEGRADED" or row.get("DEGRADED_REASON"):
                _item(
                    "RUNTIME_DEGRADED",
                    engine=row.get("id"),
                    reason=row.get("DEGRADED_REASON"),
                    freshness=row.get("FRESHNESS"),
                )
            if row.get("FRESHNESS") == "UNKNOWN" and row.get("live_keeper") is True:
                _item("PROVIDER_UNKNOWN", engine=row.get("id"), freshness="UNKNOWN")

    if heads and heads.get("drift"):
        _item("HEAD_DRIFT", drift=list(heads.get("drift") or []), corruption=False)

    if c5_runtime:
        state = str(c5_runtime.get("state") or c5_runtime.get("probe_state") or "").upper()
        if state in {"TIMEOUT", "UNKNOWN", "DEGRADED", "UNAVAILABLE"}:
            _item("RUNTIME_DEGRADED", surface="C5_RUNTIME", state=state)

    if c8_route and c8_route.get("present") is not True:
        _item("SEAT_STALE", seat="C8", present=False, activate=False)

    # Deduplicate category+task_id while preserving order.
    seen: set[tuple[Any, Any]] = set()
    unique: list[dict[str, Any]] = []
    for row in items:
        key = (row.get("category"), row.get("task_id") or row.get("engine") or row.get("surface") or row.get("seat"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)

    return {
        "schema": "raios.operational-attention.v1",
        "observed_at": observed_at,
        "fabric_attention_ne_operational": True,
        "fabricated_score": False,
        "c8_activated": False,
        "c8_acked": False,
        "items": unique[:MAX_ATTENTION_ITEMS],
        "count": min(len(unique), MAX_ATTENTION_ITEMS),
        "law": [
            "NO_FABRICATED_SEVERITY_SCORE",
            "DELIVERY_ACK_NE_ACTOR_ACK",
            "C8_FOREIGN_ACTIVE_NO_ACK",
            "C2_EDITING_NE_SEAT_ONLINE",
        ],
    }


COMMAND_INTENTS = frozenset({"NOTICE", "REQUEST", "COMMAND", "REVIEW_REQUEST"})
PERSISTED_MESSAGE_KIND = "COMMAND"
MAX_BLOCKERS = 48

QWEN_REGISTRY_BLOCKER = {
    "BLOCKER_ID": "C2-QWEN-REGISTRY-001",
    "TYPE": "EXTERNAL_NETWORK",
    "TARGET": "qwen3:0.6b",
    "PROVIDER": "registry.ollama.ai",
    "STATUS": "OPEN_EXTERNAL",
    "IMPACT_COMMAND_CENTER": "NONE",
    "RETRY_POLICY": "DO_NOT_BUSY_RETRY",
    "CLASSIFICATION": "EXTERNAL_PROVIDER_NETWORK_FAILURE",
    "QWEN_PULL_STATUS": "BLOCKED_EXTERNAL_NETWORK",
    "QWEN_PULL_BLOCKS_COMMAND_CENTER": False,
    "code": "EXTERNAL_NETWORK",
}

_INTENT_PREFIX = {
    "NOTICE": (
        "COUNCIL_NOTICE_ONLY\nWORK_AUTHORITY=false\n"
        "EXECUTION_REQUIRES=RAIOS_WORKER_TASK_ASSIGNMENT_AND_EXPLICIT_ACCEPTANCE\n"
        "INTENT=NOTICE\nPERSISTED_KIND=COMMAND\n\n"
    ),
    "REQUEST": (
        "COUNCIL_REQUEST_NO_WORK_AUTHORITY\nWORK_AUTHORITY=false\n"
        "EXECUTION_REQUIRES=RAIOS_WORKER_TASK_ASSIGNMENT_AND_EXPLICIT_ACCEPTANCE\n"
        "INTENT=REQUEST\nPERSISTED_KIND=COMMAND\n\n"
    ),
    "COMMAND": (
        "COUNCIL_COMMAND_NOTICE_ONLY\nWORK_AUTHORITY=false\n"
        "EXECUTION_REQUIRES=RAIOS_WORKER_TASK_ASSIGNMENT_AND_EXPLICIT_ACCEPTANCE\n"
        "INTENT=COMMAND\nPERSISTED_KIND=COMMAND\n"
        "COMMAND_INTENT_NE_WORK_AUTHORITY=true\n\n"
    ),
    "REVIEW_REQUEST": (
        "COUNCIL_REVIEW_REQUEST\nWORK_AUTHORITY=false\n"
        "EXECUTION_REQUIRES=RAIOS_WORKER_TASK_ASSIGNMENT_AND_EXPLICIT_ACCEPTANCE\n"
        "INTENT=REVIEW_REQUEST\nPERSISTED_KIND=COMMAND\n\n"
    ),
}


def _norm_state(value: Any, *, default: str = "UNKNOWN") -> str:
    text = str(value if value is not None else "").strip().upper()
    if text in {"", "NONE", "NULL"}:
        return default
    if text == "OFFLINE" and default == "UNKNOWN":
        return text
    return text or default


def classify_model_fabric(
    model: dict[str, Any] | None,
    *,
    ollama_listening: bool | None = None,
    recorded_remote_registry: bool = False,
) -> dict[str, Any]:
    """TIMEOUT inventory stays UNKNOWN. Remote registry failure is not local Ollama down."""
    src = dict(model or {})
    probe = _norm_state(src.get("probe_state"), default="UNKNOWN")
    err = str(src.get("model_fabric_error") or "")
    err_l = err.lower()
    timeout = probe == "TIMEOUT" or "timeout" in err_l
    registry_hit = (
        recorded_remote_registry
        or "registry.ollama.ai" in err_l
        or "remote_registry" in err_l
    )
    count = src.get("count")
    if timeout:
        inventory_state = "UNKNOWN"
        count = None
        probe = "TIMEOUT"
    elif count is None and not src.get("models"):
        inventory_state = "UNKNOWN"
    else:
        inventory_state = "CURRENT" if src.get("fabric_ready") is True else (
            "DEGRADED" if src.get("fabric_ready") is False else "UNKNOWN"
        )
    if ollama_listening is True:
        local_ollama_state = "ONLINE"
    elif ollama_listening is False:
        local_ollama_state = "UNAVAILABLE"
    else:
        local_ollama_state = "UNKNOWN"
    remote_registry_state = "REMOTE_REGISTRY_UNAVAILABLE" if registry_hit else "UNKNOWN"
    src.update({
        "probe_state": probe,
        "inventory_state": inventory_state,
        "count": count,
        "timeout_ne_empty_inventory": True,
        "local_ollama_state": local_ollama_state,
        "remote_registry_state": remote_registry_state,
        "LOCAL_OLLAMA_DOWN": False if local_ollama_state != "UNAVAILABLE" else True,
        "REMOTE_REGISTRY_NE_LOCAL_OLLAMA": True,
        "qwen_pull_blocks_command_center": False,
        "models_zero_on_timeout": False,
    })
    if timeout:
        src["ollama_online"] = local_ollama_state == "ONLINE"
        src["fabric_ready"] = None
    return src


def command_intent_envelope(text: str, intent: str | None = None) -> dict[str, Any]:
    chosen = str(intent or "NOTICE").strip().upper()
    if chosen not in COMMAND_INTENTS:
        return {
            "ok": False,
            "error": "INTENT_UNSUPPORTED",
            "allowed": sorted(COMMAND_INTENTS),
            "intent": chosen,
            "persisted_kind": PERSISTED_MESSAGE_KIND,
            "work_authority": False,
            "notice_only": True,
        }
    body = str(text or "")
    prefix = _INTENT_PREFIX[chosen]
    if body.startswith("COUNCIL_") and "WORK_AUTHORITY=false" in body:
        notice = body
    else:
        notice = prefix + body
    return {
        "ok": True,
        "intent": chosen,
        "persisted_kind": PERSISTED_MESSAGE_KIND,
        "work_authority": False,
        "notice_only": True,
        "new_persisted_message_type": False,
        "notice": notice,
    }


def attach_communication_lifecycle(trace: dict[str, Any] | None) -> dict[str, Any]:
    """Add CREATED/ROUTED/DELIVERED/DELIVERY_ACK/ACTOR_ACK/FAILED/DEAD_LETTER. Never infer ACTOR_ACK."""
    payload = dict(trace or {})
    targets = [t for t in (payload.get("targets") or []) if isinstance(t, dict)]
    created = payload.get("MESSAGE_CREATED") is True or bool(payload.get("RECEIPT"))
    routed = payload.get("MESSAGE_ROUTED") is True
    delivery_ack = payload.get("DELIVERY_ACK") is True or any(t.get("delivery_ack") is True for t in targets)
    actor_ack = payload.get("ACTOR_ACK") is True
    if actor_ack and payload.get("actor_ack_synthesized") is True:
        actor_ack = False
        payload["ACTOR_ACK"] = False
    actor_acks = []
    for row in targets:
        if row.get("actor_ack") is True and row.get("synthetic") is not True:
            actor_acks.append({
                "message_id": row.get("message_id") or payload.get("message_id"),
                "actor_id": row.get("actor_id") or row.get("target_actor"),
                "session_id": row.get("session_id") or "UNKNOWN",
                "seat": row.get("target_seat") or row.get("seat") or "UNKNOWN",
                "timestamp": row.get("timestamp") or "UNKNOWN",
            })
        elif row.get("synthetic") is True:
            row["actor_ack"] = False
            row["phase"] = "DELIVERY_ACK" if row.get("delivery_ack") else row.get("phase")
    actor_ack = bool(actor_acks)
    payload["ACTOR_ACK"] = actor_ack
    dead = payload.get("DEAD_LETTER") is True
    failed = dead or str(payload.get("FAILURE") or "").upper() in {"FAILED", "DEAD_LETTER", "ROUTING_FAILURE"}
    lifecycle: list[str] = []
    if created:
        lifecycle.append("CREATED")
    if routed:
        lifecycle.append("ROUTED")
    if delivery_ack:
        lifecycle.append("DELIVERED")
        lifecycle.append("DELIVERY_ACK")
    if actor_ack:
        lifecycle.append("ACTOR_ACK")
    if failed:
        lifecycle.append("FAILED")
    if dead:
        lifecycle.append("DEAD_LETTER")
    payload.update({
        "LIFECYCLE": lifecycle,
        "CREATED": created,
        "ROUTED": routed,
        "DELIVERED": delivery_ack,
        "DELIVERY_ACK": delivery_ack,
        "FAILED": failed,
        "actor_acks": actor_acks,
        "delivery_ack_ne_actor_ack": True,
        "actor_ack_synthesized": False,
        "WHO_SENT": payload.get("SOURCE_ACTOR") or "UNKNOWN",
        "TO_SEATS": [t.get("target_seat") for t in targets if t.get("target_seat")] or payload.get("TO_SEATS") or [],
        "WHICH_SESSION": payload.get("SOURCE_SESSION") or "UNKNOWN",
        "HTTP_200_NE_ACTOR_ACK": True,
    })
    return payload


def _component(name: str, state: Any, **fields: Any) -> dict[str, Any]:
    raw = _norm_state(state, default="UNKNOWN")
    if raw in {"OFFLINE", "DOWN"}:
        normalized = "UNAVAILABLE" if raw == "DOWN" else "OFFLINE"
    elif raw in {"ONLINE", "DEGRADED", "UNKNOWN", "UNAVAILABLE", "STALE", "TIMEOUT"}:
        normalized = "UNKNOWN" if raw == "TIMEOUT" else raw
    elif raw in {"HEALTHY", "CURRENT", "PASS", "OK"}:
        normalized = "ONLINE"
    elif raw in {"FAIL", "BROKEN", "ERROR"}:
        normalized = "DEGRADED"
    else:
        normalized = "UNKNOWN"
    row = {"name": name, "state": normalized, "unknown_ne_offline": True}
    row.update(fields)
    return row


def runtime_health_view(
    *,
    services: list[dict[str, Any]] | None = None,
    worker: dict[str, Any] | None = None,
    models: dict[str, Any] | None = None,
    continuity: dict[str, Any] | None = None,
    ollama_listening: bool | None = None,
    command_center_state: str = "ONLINE",
) -> dict[str, Any]:
    """Independent health for C5 / CC / MCP / Fabric / Model Fabric / Providers / Continuity."""
    by = {str(s.get("name") or ""): s for s in (services or []) if isinstance(s, dict)}
    c5 = by.get("C5") or {}
    mcp = by.get("UniversalMCP") or {}
    models = models or {}
    worker = worker or {}
    continuity = continuity or {}
    c5_state = c5.get("state") or "UNKNOWN"
    if c5.get("probe_state") == "TIMEOUT":
        c5_state = "UNKNOWN"
    mcp_state = mcp.get("state") or "UNKNOWN"
    if worker.get("healthy") is True:
        fabric_state = "ONLINE"
    elif worker.get("healthy") is False:
        fabric_state = "DEGRADED"
    else:
        fabric_state = "UNKNOWN"
    probe = str(models.get("probe_state") or "UNKNOWN").upper()
    if probe == "TIMEOUT":
        fabric_models = "UNKNOWN"
    elif models.get("fabric_ready") is True:
        fabric_models = "ONLINE"
    elif models.get("fabric_ready") is False:
        fabric_models = "DEGRADED"
    else:
        fabric_models = str(models.get("inventory_state") or "UNKNOWN").upper() or "UNKNOWN"
        if fabric_models == "CURRENT":
            fabric_models = "ONLINE"
    if ollama_listening is True:
        provider_ollama = "ONLINE"
    elif ollama_listening is False:
        provider_ollama = "UNAVAILABLE"
    else:
        provider_ollama = str(models.get("local_ollama_state") or "UNKNOWN")
    cont_raw = str(continuity.get("status") or continuity.get("state") or "UNKNOWN").upper()
    if cont_raw in {"ONLINE", "HEALTHY", "PASS"}:
        cont_state = "ONLINE"
    elif cont_raw in {"DEGRADED"}:
        cont_state = "DEGRADED"
    elif cont_raw in {"STALE"}:
        cont_state = "STALE"
    elif cont_raw in {"OFFLINE", "UNAVAILABLE"}:
        cont_state = "UNAVAILABLE"
    else:
        cont_state = "UNKNOWN"
    components = [
        _component("C5", c5_state, kind="RUNTIME", seat_presence_independent=True, probe_state=c5.get("probe_state")),
        _component("Command Center", command_center_state, kind="RUNTIME", source="/health"),
        _component("Universal MCP", mcp_state, kind="RUNTIME", port=mcp.get("port") or 8788),
        _component("Command Fabric", fabric_state, kind="BUS", source="MESSAGE_WORKER.status", synthetic_ack=False),
        _component("Model Fabric", fabric_models, kind="INVENTORY", probe_state=probe, inventory_state=models.get("inventory_state")),
        _component("Providers.Ollama", provider_ollama, kind="PROVIDER", remote_registry_state=models.get("remote_registry_state")),
        _component("Continuity", cont_state, kind="CONTINUITY", source="continuity/status.json"),
    ]
    return {
        "schema": "raios.runtime-health.v1",
        "C5_RUNTIME_NE_SEAT_PRESENCE": True,
        "UNKNOWN_NE_OFFLINE": True,
        "REMOTE_REGISTRY_NE_LOCAL_OLLAMA": True,
        "components": components,
        "by_name": {c["name"]: c for c in components},
    }


def operational_blockers(
    *,
    members: list[dict[str, Any]] | None = None,
    models: dict[str, Any] | None = None,
    heads: dict[str, Any] | None = None,
    change_authority: dict[str, Any] | None = None,
    worker: dict[str, Any] | None = None,
    recorded_qwen: bool = True,
) -> dict[str, Any]:
    """Surface only evidenced blockers. Do not invent incidents."""
    items: list[dict[str, Any]] = []

    def _add(code: str, **fields: Any) -> None:
        if len(items) >= MAX_BLOCKERS:
            return
        row = {"code": code, "invented": False}
        row.update(fields)
        items.append(row)

    if recorded_qwen:
        _add(
            "EXTERNAL_NETWORK",
            **{k: v for k, v in QWEN_REGISTRY_BLOCKER.items() if k != "code"},
        )
    models = models or {}
    if str(models.get("probe_state") or "").upper() == "TIMEOUT":
        _add(
            "PROVIDER_TIMEOUT",
            surface="MODEL_FABRIC",
            inventory_state=models.get("inventory_state") or "UNKNOWN",
            count=models.get("count"),
        )
    if str(models.get("remote_registry_state") or "") == "REMOTE_REGISTRY_UNAVAILABLE":
        existing = {i.get("BLOCKER_ID") for i in items}
        if "C2-QWEN-REGISTRY-001" not in existing:
            _add("EXTERNAL_NETWORK", PROVIDER="registry.ollama.ai", STATUS="OPEN_EXTERNAL")
    for member in members or []:
        if not isinstance(member, dict):
            continue
        seat = member.get("seat") or member.get("seat_id")
        task = member.get("current_task")
        if member.get("presence_state") == "EXPIRED" or member.get("lease_state") == "EXPIRED":
            _add("EXPIRED_LEASE", seat=seat, lease_state=member.get("lease_state"))
        if member.get("heartbeat_state") == "STALE" or member.get("presence_state") == "STALE":
            _add("STALE_SESSION", seat=seat, heartbeat_state=member.get("heartbeat_state"))
        unbound = member.get("presentation_state") == "UNBOUND" or member.get("binding_state") == "UNBOUND"
        if unbound and task:
            _add("UNBOUND_SEAT", seat=seat, current_task=task)
        last_ack = member.get("last_actor_ack")
        if member.get("actor_ack_state") in {"NO_ACTOR_ACK", "ACK_PENDING", "SYNTHETIC_NOT_ACTOR_ACK"} and last_ack:
            _add("NO_ACTOR_ACK", seat=seat, actor_ack_state=member.get("actor_ack_state"))
        if member.get("last_error"):
            err = str(member.get("last_error"))
            if "ROUTING" in err.upper():
                _add("ROUTING_FAILURE", seat=seat, last_error=err)
    if heads:
        drift = list(heads.get("drift") or [])
        if any("NE" in str(x) for x in drift) or "HEAD_MISMATCH" in drift:
            _add("HEAD_MISMATCH", drift=drift, corruption=False)
    authority = change_authority or {}
    pending = str(authority.get("approval_state") or "").upper()
    if pending in {"PENDING", "APPROVAL_REQUIRED", "RECEIPT_REQUIRED"} and authority.get("proposal_present") is True:
        _add(
            "APPROVAL_REQUIRED",
            task_id=authority.get("task_id") or "UNKNOWN",
            approval_state=pending,
        )
    worker = worker or {}
    last_error = str(worker.get("last_error") or "")
    if "DEAD_LETTER" in last_error.upper():
        _add("DEAD_LETTER", surface="COMMAND_FABRIC", last_error=last_error)
    if "ROUTING" in last_error.upper():
        _add("ROUTING_FAILURE", surface="COMMAND_FABRIC", last_error=last_error)
    seen: set[tuple[Any, Any]] = set()
    unique: list[dict[str, Any]] = []
    for row in items:
        key = (row.get("code"), row.get("BLOCKER_ID") or row.get("seat") or row.get("surface") or row.get("task_id"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return {
        "schema": "raios.operational-blockers.v1",
        "invented": False,
        "qwen_pull_blocks_command_center": False,
        "items": unique[:MAX_BLOCKERS],
        "count": min(len(unique), MAX_BLOCKERS),
    }


def enrich_change_authority(
    doc: dict[str, Any] | None,
    *,
    heads: dict[str, Any] | None = None,
    approval_receipt: dict[str, Any] | None = None,
    canonical_head: Any = None,
) -> dict[str, Any]:
    """Read-only change-authority view. Missing optional sources stay UNKNOWN."""
    base = dict(doc or {})
    receipt = approval_receipt if isinstance(approval_receipt, dict) else {}
    heads = heads if isinstance(heads, dict) else {}
    missing = not base and not receipt
    task_id = receipt.get("task_id") or base.get("task_id") or "UNKNOWN"
    base_head = receipt.get("base_head") or base.get("base_head") or "UNKNOWN"
    staged = receipt.get("staged_diff_sha256") or base.get("staged_diff_sha256") or "UNKNOWN"
    lease = receipt.get("lease") or base.get("lease") or "UNKNOWN"
    expiry = receipt.get("expiry") or receipt.get("expires_at") or base.get("expiry") or "UNKNOWN"
    if missing:
        approval_state = "UNKNOWN"
        source_missing = True
        proposal_present = False
    elif receipt:
        approval_state = str(receipt.get("approval_state") or receipt.get("state") or "RECEIPT_PRESENT").upper()
        source_missing = False
        proposal_present = True
    elif base.get("approval_receipt_required") is True:
        approval_state = "RECEIPT_REQUIRED"
        source_missing = False
        proposal_present = False
    else:
        approval_state = str(base.get("state") or "CURRENT").upper()
        source_missing = False
        proposal_present = False
    promotion_state = "READ_ONLY_NO_AUTO_PROMOTE"
    return {
        **base,
        "schema": base.get("schema") or "raios.change-authority-view.v1",
        "state": "UNKNOWN" if missing else (base.get("state") or "CURRENT"),
        "source_missing": missing or base.get("source_missing") is True,
        "canonical_head": canonical_head or base.get("canonical_head") or heads.get("CANONICAL_HEAD") or "UNKNOWN",
        "heads": heads or base.get("heads") or {},
        "task_id": task_id,
        "base_head": base_head,
        "staged_diff_sha256": staged,
        "lease": lease,
        "expiry": expiry,
        "approval_state": approval_state,
        "promotion_state": promotion_state,
        "proposal_present": proposal_present,
        "promotion": False,
        "auto_approval": False,
        "auto_commit": False,
        "auto_push": False,
        "silent_promote": False,
    }
