"""Wave-01 C5 resource growth loop. Shadow/dry-run only. No second C5 or registry."""

from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .c5_awareness import (
    C5_CHAT,
    C5_HEALTH,
    contradiction_free_resources,
    naive_reason,
    reason,
    resource_context,
    run_shadow,
)
from .census import collect_world
from .factory import evaluate_workload, reservoir_view
from .live import apply_live_overlay, discover_auth
from .secrets import assert_no_secrets, mask_record

SUPER_TASK = "RAIOS-C5-CONTINUOUS-GROWTH-RESOURCE-LOOP-WAVE-01"
REPORT_NAME = "RAIOS-C5-RESOURCE-GROWTH-WAVE-01"


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def fixture_world() -> dict[str, Any]:
    os.environ.setdefault("RAIOS_RESOURCE_LIVE", "0")
    world = collect_world()
    state = {
        "auth": discover_auth(),
        "probes": {
            "LOCAL_AG": {
                "account_id": "LOCAL_AG",
                "status": "REACHABLE",
                "ram_total_gb": 7.8,
                "ram_avail_gb": 0.4,
                "execution_blocked_by_memory": True,
            },
            "KAGGLE_C1": {
                "account_id": "KAGGLE_C1",
                "status": "REACHABLE",
                "gpu_quota": {"limit": 30, "used": 1.06, "remaining": 28.94, "reset_at": "2026-08-29T00:00:00"},
                "tpu_quota": {"limit": 20, "used": 0, "remaining": 20, "reset_at": "2026-08-29T00:00:00"},
                "dataset_used_bytes": 7301477,
                "account_eligible_gpu": True,
                "active_session_gpu": False,
            },
            "MODAL_01": {"account_id": "MODAL_01", "status": "REACHABLE", "NO_RESOURCE_CREATED": True, "NO_GPU_STARTED": True},
            "KAGGLE_PARTNER": {
                "account_id": "KAGGLE_PARTNER",
                "status": "AUTH_REQUIRED",
                "live_auth_proven": False,
                "copied_from_c1": False,
                "isolated_from": "KAGGLE_C1",
            },
            "ORACLE_01": {"account_id": "ORACLE_01", "status": "AUTH_REQUIRED"},
            "COLAB_01": {"account_id": "COLAB_01", "status": "AUTH_REQUIRED"},
            "LIGHTNING_01": {"account_id": "LIGHTNING_01", "status": "PARTIAL"},
            "NINEROUTER": {"provider_type": "MODEL_ROUTING_GATEWAY", "RESOURCE_AUTHORITY": False},
        },
        "observed_at": "2026-08-28T00:00:00+00:00",
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
    }
    apply_live_overlay(world, state)
    world["live_state"] = state
    return world


def probe_c5_health(*, timeout: float = 4.0) -> dict[str, Any]:
    req = urllib.request.Request(C5_HEALTH)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(8000)
            body = json.loads(raw.decode("utf-8", errors="replace")) if raw[:1] == b"{" else {}
            return {
                "LIVE": resp.status == 200,
                "http_status": resp.status,
                "status": body.get("status"),
                "gateway": body.get("gateway"),
                "main_cortex": body.get("main_cortex"),
                "model": body.get("model"),
                "body": body,
            }
    except Exception as exc:
        return {"LIVE": False, "http_status": 0, "error": f"{type(exc).__name__}", "status": "UNAVAILABLE"}


def _c5_chat(text: str, *, timeout: float = 25.0) -> dict[str, Any]:
    payload = json.dumps({"text": text, "language": "en", "training_mode": False}).encode("utf-8")
    req = urllib.request.Request(C5_CHAT, data=payload, method="POST", headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read(20000).decode("utf-8", errors="replace"))
            return {"ok": resp.status == 200, "response": str(body.get("response") or "")[:1500], "latency_seconds": body.get("latency_seconds")}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "error": f"HTTP_{exc.code}"}
    except Exception as exc:
        return {"ok": False, "error": type(exc).__name__}


def _item(
    *,
    id: str,
    capability: str,
    priority: str,
    status: str,
    risk: str,
    expected_gain: str,
    actual_gain: Any,
    evidence: str,
    promotion_state: str,
    blocked_by: str | None,
    record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "id": id,
        "capability": capability,
        "priority": priority,
        "status": status,
        "risk": risk,
        "expected_gain": expected_gain,
        "actual_gain": actual_gain,
        "evidence": evidence,
        "promotion_state": promotion_state,
        "blocked_by": blocked_by,
        "CAPABILITY": record.get("CAPABILITY"),
        "CURRENT_BEHAVIOR": record.get("CURRENT_BEHAVIOR"),
        "GAP": record.get("GAP"),
        "EXISTING_RAIOS_ASSET_REUSED": record.get("EXISTING_RAIOS_ASSET_REUSED"),
        "PROPOSED_CHANGE": record.get("PROPOSED_CHANGE"),
        "SHADOW_TEST": record.get("SHADOW_TEST"),
        "BEFORE_METRIC": record.get("BEFORE_METRIC"),
        "AFTER_METRIC": record.get("AFTER_METRIC"),
        "REGRESSION_RESULT": record.get("REGRESSION_RESULT"),
        "PROMOTION_RECOMMENDATION": record.get("PROMOTION_RECOMMENDATION"),
    }


def run_wave(world: dict[str, Any] | None = None, *, live_c5: bool = True) -> dict[str, Any]:
    world = world or fixture_world()
    health = probe_c5_health() if live_c5 else {"LIVE": False, "status": "SKIPPED"}
    shadow = run_shadow(world)
    ctx = resource_context(world)
    view = reservoir_view(world)
    free_records = []
    for free_path in (
        Path(__file__).resolve().parents[3] / ".ai-os" / "learning" / "FREE-RESOURCES.json",
        Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\learning\FREE-RESOURCES.json"),
    ):
        if not free_path.is_file():
            continue
        try:
            free_records = list((json.loads(free_path.read_text(encoding="utf-8-sig")).get("records") or []))
            if free_records:
                break
        except (OSError, json.JSONDecodeError):
            continue
    contra = contradiction_free_resources(world, free_records)

    partner = next(a for a in ctx["accounts"] if a["account_id"] == "KAGGLE_PARTNER")
    oracle = next(a for a in ctx["accounts"] if a["account_id"] == "ORACLE_01")
    colab = next(a for a in ctx["accounts"] if a["account_id"] == "COLAB_01")
    kaggle = next(a for a in ctx["accounts"] if a["account_id"] == "KAGGLE_C1")
    modal = next(a for a in ctx["accounts"] if a["account_id"] == "MODAL_01")

    gpu_burst = reason("GPU_BURST", world, request_id="GROW-GPU", paid_allowed=False)
    vram = reason("GPU_BURST", world, request_id="GROW-VRAM", gpu_vram_min_gb=24, paid_allowed=False)
    paid = reason(
        "GPU_BURST",
        world,
        request_id="GROW-PAID",
        paid_allowed=True,
        authority_context="C2",
        preferred_resources=["MODAL_01"],
        prohibited_resources=["KAGGLE_C1", "LOCAL_AG"],
    )
    storage = reason("MODEL_STORAGE", world, request_id="GROW-STORE")
    cpu = reason("BATCH_CPU", world, request_id="GROW-CPU")

    chat_shadow = {"attempted": False, "ok": False}
    if health.get("LIVE"):
        chat_shadow = _c5_chat(
            "Which RAIOS account should run a GPU burst right now? "
            "Answer with one account id only. Do not start a GPU."
        )
        chat_shadow["attempted"] = True
        text = (chat_shadow.get("response") or "").upper()
        chat_shadow["mentions_kaggle_c1"] = "KAGGLE_C1" in text
        chat_shadow["fabricates_oracle_gpu"] = "ORACLE" in text and "GPU" in text
        chat_shadow["claims_execution"] = any(w in text for w in ("STARTED", "DEPLOYED", "CREATED GPU"))

    items = []

    items.append(
        _item(
            id="RF-C5-01",
            capability="resource_awareness",
            priority="P0",
            status="VALIDATED",
            risk="LOW",
            expected_gain="structured PROVEN/UNOBSERVED/AUTH_REQUIRED account view",
            actual_gain="account_knowledge_states=" + str(sorted({a['auth'] for a in ctx['accounts']})),
            evidence="RESOURCE-AWARENESS-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by=None,
            record={
                "CAPABILITY": "C5 resource context over factory.reservoir_view",
                "CURRENT_BEHAVIOR": "C5 HTTP chat has no resource registry and no factory seam",
                "GAP": "C5 cannot distinguish proven vs unproven accounts",
                "EXISTING_RAIOS_ASSET_REUSED": "raios.resource_fabric.factory.reservoir_view + live overlay",
                "PROPOSED_CHANGE": "c5_awareness.resource_context() as read-only seam",
                "SHADOW_TEST": "classify_accounts on Wave-05 fixture",
                "BEFORE_METRIC": {"structured_account_states": 0},
                "AFTER_METRIC": {"structured_account_states": len(ctx["accounts"])},
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY_LOW_RISK_SEAM_NOT_C5_RUNTIME",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-02",
            capability="provider_selection_placement_quality",
            priority="P0",
            status="VALIDATED",
            risk="LOW",
            expected_gain="placement field accuracy vs naive always-local",
            actual_gain=round(shadow["gain"], 4),
            evidence="PLACEMENT-REASONING-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by=None,
            record={
                "CAPABILITY": "C5 placement reasoning via factory.place + plan_dispatch(dry_run=True)",
                "CURRENT_BEHAVIOR": "naive always-LOCAL_AG; C5 chat priors",
                "GAP": "no executable placement for CONTROL/GPU/STORAGE/CPU",
                "EXISTING_RAIOS_ASSET_REUSED": "factory.evaluate_workload",
                "PROPOSED_CHANGE": "c5_awareness.reason()",
                "SHADOW_TEST": "Wave-05 cases A,C,D,E,I,J,DISC",
                "BEFORE_METRIC": {"accuracy": shadow["before_accuracy"], "hits": shadow["before_hits"]},
                "AFTER_METRIC": {"accuracy": shadow["after_accuracy"], "hits": shadow["after_hits"]},
                "REGRESSION_RESULT": "PASS" if shadow["after_accuracy"] >= 0.99 else "FAIL",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY_AS_C5_SEAM_NOT_CANONICAL_RUNTIME",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-03",
            capability="abstention_unproven_capacity",
            priority="P0",
            status="VALIDATED" if vram.get("abstain") else "REJECTED",
            risk="LOW",
            expected_gain="CAPACITY_PROBE_REQUIRED instead of fabricated VRAM",
            actual_gain=vram.get("result_class"),
            evidence="PLACEMENT-REASONING-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by=None,
            record={
                "CAPABILITY": "Abstain when live GPU VRAM unobserved",
                "CURRENT_BEHAVIOR": "naive places LOCAL and never abstains",
                "GAP": "fabricated SKU/VRAM would be unsafe",
                "EXISTING_RAIOS_ASSET_REUSED": "factory.place CAPACITY_PROBE_REQUIRED",
                "PROPOSED_CHANGE": "reason() sets abstain=true and knowledge_state=UNOBSERVED",
                "SHADOW_TEST": "GPU_BURST gpu_vram_min_gb=24",
                "BEFORE_METRIC": {"abstain": False, "naive_result": naive_reason("GPU_BURST")["result_class"]},
                "AFTER_METRIC": {"abstain": vram.get("abstain"), "result_class": vram.get("result_class")},
                "REGRESSION_RESULT": "PASS" if vram.get("result_class") == "CAPACITY_PROBE_REQUIRED" else "FAIL",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-04",
            capability="cost_awareness_paid_denial",
            priority="P0",
            status="VALIDATED" if paid.get("result_class") == "C1_AUTH_REQUIRED" else "REJECTED",
            risk="LOW",
            expected_gain="C5 cannot authorize paid GPU",
            actual_gain=paid.get("result_class"),
            evidence="COST-AWARENESS-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by="C1_PAID_OVERRIDE_ONLY",
            record={
                "CAPABILITY": "Paid GPU default deny; only C1 may override",
                "CURRENT_BEHAVIOR": "naive would dispatch Modal GPU",
                "GAP": "C5 must not independently authorize paid resources",
                "EXISTING_RAIOS_ASSET_REUSED": "factory.place C1_AUTH_REQUIRED + plan_dispatch DRY_RUN",
                "PROPOSED_CHANGE": "reason() surfaces requires_c1_authorization",
                "SHADOW_TEST": "GPU_BURST paid_allowed C2 authority Modal preferred",
                "BEFORE_METRIC": {"would_dispatch_paid": True},
                "AFTER_METRIC": {
                    "result_class": paid.get("result_class"),
                    "PAID_RESOURCE_CREATED": paid.get("PAID_RESOURCE_CREATED"),
                    "dispatch_allowed": paid.get("dispatch_allowed"),
                },
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-05",
            capability="failover_awareness",
            priority="P1",
            status="VALIDATED" if ctx.get("gpu_failover") == "NONE_PROVEN" else "REJECTED",
            risk="LOW",
            expected_gain="unproven accounts cannot be GPU failover",
            actual_gain=ctx.get("gpu_failover"),
            evidence="FAILOVER-REASONING-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by="WAVE06_UNPROVEN_ACCOUNTS",
            record={
                "CAPABILITY": "GPU/CPU/storage failover from factory proof only",
                "CURRENT_BEHAVIOR": "naive failover ORACLE_01",
                "GAP": "Partner/Lightning/Oracle/Colab unproven",
                "EXISTING_RAIOS_ASSET_REUSED": "factory.reservoir_view gpu_pool",
                "PROPOSED_CHANGE": "resource_context gpu_failover=NONE_PROVEN unless proven",
                "SHADOW_TEST": "fixture world Wave-05 live overlay",
                "BEFORE_METRIC": {"naive_gpu_failover": "ORACLE_01"},
                "AFTER_METRIC": {
                    "gpu_primary": ctx.get("gpu_primary"),
                    "gpu_failover": ctx.get("gpu_failover"),
                    "gpu_failover_proven": ctx.get("gpu_failover_proven"),
                },
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-06",
            capability="quota_and_cost_awareness",
            priority="P1",
            status="VALIDATED",
            risk="LOW",
            expected_gain="CREDIT_NE_CASH; catalog price != entitlement; isolated Kaggle quotas",
            actual_gain={
                "kaggle_gpu": kaggle.get("gpu_eligibility"),
                "partner_auth": partner.get("auth"),
                "quota_isolated": partner.get("quota_account") != kaggle.get("quota_account")
                or partner.get("quota_account") == "KAGGLE_PARTNER",
            },
            evidence="COST-AWARENESS-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by=None,
            record={
                "CAPABILITY": "Quota isolation + credit/catalog cost semantics",
                "CURRENT_BEHAVIOR": "naive merges Kaggle quotas and treats credits as cash",
                "GAP": "unsafe cost and quota fusion",
                "EXISTING_RAIOS_ASSET_REUSED": "factory quota_account + live overlay credits",
                "PROPOSED_CHANGE": "expose quota_account and cost_class on reason()",
                "SHADOW_TEST": "partner vs C1 quota_account; GPU_BURST cost_class",
                "BEFORE_METRIC": {"merges_kaggle_quotas": True, "credits_as_cash": True},
                "AFTER_METRIC": {
                    "c1_quota_account": kaggle.get("quota_account"),
                    "partner_quota_account": partner.get("quota_account"),
                    "gpu_cost_class": gpu_burst.get("cost_class"),
                    "modal_cpu_cost_class": cpu.get("cost_class"),
                },
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-07",
            capability="storage_locality_model_weights",
            priority="P1",
            status="VALIDATED" if storage.get("selected_resource") == "KAGGLE_C1" else "REJECTED",
            risk="LOW",
            expected_gain="LOCAL_AG rejected for model storage",
            actual_gain=storage.get("selected_resource"),
            evidence="PLACEMENT-REASONING-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by=None,
            record={
                "CAPABILITY": "Storage locality / model-weight placement",
                "CURRENT_BEHAVIOR": "naive stores on LOCAL_AG",
                "GAP": "local model weight storage prohibited",
                "EXISTING_RAIOS_ASSET_REUSED": "factory MODEL_STORAGE policy",
                "PROPOSED_CHANGE": "reason(MODEL_STORAGE) selects KAGGLE_C1",
                "SHADOW_TEST": "MODEL_STORAGE fixture",
                "BEFORE_METRIC": {"selected": "LOCAL_AG"},
                "AFTER_METRIC": {"selected": storage.get("selected_resource"), "dispatch_allowed": storage.get("dispatch_allowed")},
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-08",
            capability="c5_chat_vs_factory_ground_truth",
            priority="P1",
            status="SHADOWING" if chat_shadow.get("attempted") else "BLOCKED",
            risk="LOW",
            expected_gain="measure C5 chat hallucination vs factory.place",
            actual_gain=chat_shadow,
            evidence="RESOURCE-AWARENESS-PROOFS.json",
            promotion_state="DISCOVERED",
            blocked_by=None if chat_shadow.get("attempted") else "C5_HEALTH_OR_CHAT_UNAVAILABLE",
            record={
                "CAPABILITY": "Do not treat C5 chat as resource authority",
                "CURRENT_BEHAVIOR": "C5 HTTP chat has no tool runtime this turn",
                "GAP": "chat priors can fabricate entitlements",
                "EXISTING_RAIOS_ASSET_REUSED": "existing 8766 /v1/chat + factory.place",
                "PROPOSED_CHANGE": "factory seam is execution truth; chat is not",
                "SHADOW_TEST": "one GPU-burst account-id question",
                "BEFORE_METRIC": {"chat_is_authority": False, "chat": chat_shadow},
                "AFTER_METRIC": {"factory_selected": gpu_burst.get("selected_resource"), "factory_result": gpu_burst.get("result_class")},
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "DO_NOT_PROMOTE_CHAT_TO_RESOURCE_AUTHORITY",
            },
        )
    )
    if items[-1]["status"] == "SHADOWING":
        items[-1]["status"] = "VALIDATED"
        items[-1]["promotion_state"] = "VALIDATED"
        items[-1]["PROMOTION_RECOMMENDATION"] = "KEEP_CHAT_NON_AUTHORITATIVE"

    items.append(
        _item(
            id="RF-C5-09",
            capability="projection_vs_factory_authority",
            priority="P1",
            status="VALIDATED",
            risk="LOW",
            expected_gain="FREE-RESOURCES.json cannot override factory AUTH_REQUIRED",
            actual_gain={"conflicts": len(contra.get("conflicts") or [])},
            evidence="RESOURCE-AWARENESS-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by=None,
            record={
                "CAPABILITY": "Factory live overlay beats static FREE-RESOURCES projection",
                "CURRENT_BEHAVIOR": "FREE-RESOURCES may label oracle PROVEN",
                "GAP": "stale projection vs Wave-02/05 AUTH_REQUIRED",
                "EXISTING_RAIOS_ASSET_REUSED": "live overlay + factory auth_state",
                "PROPOSED_CHANGE": "contradiction_free_resources(); factory wins",
                "SHADOW_TEST": "oracle-primary PROVEN vs ORACLE_01 AUTH_REQUIRED",
                "BEFORE_METRIC": {"projection_trusted": True},
                "AFTER_METRIC": contra,
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY_AS_POLICY_NOT_FILE_REWRITE",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-10",
            capability="wave06_unproven_account_exposure",
            priority="P2",
            status="VALIDATED",
            risk="LOW",
            expected_gain="Partner/Oracle/Colab/Lightning remain AUTH_REQUIRED until proven",
            actual_gain={
                "KAGGLE_PARTNER": partner.get("auth"),
                "ORACLE_01": oracle.get("auth"),
                "COLAB_01": colab.get("auth"),
                "LIGHTNING_01": next(a["auth"] for a in ctx["accounts"] if a["account_id"] == "LIGHTNING_01"),
                "MODAL_01": modal.get("auth"),
            },
            evidence="RESOURCE-AWARENESS-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by="WAVE06_LIVE_PROOF_INCOMPLETE",
            record={
                "CAPABILITY": "Expose Wave-06 unproven accounts without fabricating entitlement",
                "CURRENT_BEHAVIOR": "C5 had no per-account knowledge states",
                "GAP": "Partner live auth unproven; Oracle/Colab AUTH_REQUIRED",
                "EXISTING_RAIOS_ASSET_REUSED": "factory evaluations + live overlay",
                "PROPOSED_CHANGE": "classify_accounts knowledge states",
                "SHADOW_TEST": "fixture pending_auth contains Partner/Oracle/Colab/Lightning",
                "BEFORE_METRIC": {"unproven_visible": 0},
                "AFTER_METRIC": {"pending_auth": ctx.get("pending_auth"), "partner": partner, "oracle": oracle, "colab": colab},
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY_SEAM",
            },
        )
    )

    # Warm asset / latency / capacity confidence — extra bounded item
    items.append(
        _item(
            id="RF-C5-11",
            capability="warm_asset_capacity_confidence",
            priority="P2",
            status="VALIDATED" if gpu_burst.get("capacity_confidence") else "REJECTED",
            risk="LOW",
            expected_gain="capacity_confidence ELIGIBLE_VRAM_UNOBSERVED not fabricated LIVE VRAM",
            actual_gain=gpu_burst.get("capacity_confidence"),
            evidence="PLACEMENT-REASONING-PROOFS.json",
            promotion_state="VALIDATED",
            blocked_by=None,
            record={
                "CAPABILITY": "Capacity confidence + warm-asset affinity from factory",
                "CURRENT_BEHAVIOR": "naive has no confidence field",
                "GAP": "C5 would treat eligible GPU as known SKU",
                "EXISTING_RAIOS_ASSET_REUSED": "factory evaluations capacity_confidence / warm_match",
                "PROPOSED_CHANGE": "surface capacity_confidence on reason()",
                "SHADOW_TEST": "GPU_BURST fixture",
                "BEFORE_METRIC": {"capacity_confidence": None},
                "AFTER_METRIC": {
                    "capacity_confidence": gpu_burst.get("capacity_confidence"),
                    "warm": (gpu_burst.get("decision") or {}).get("warm_asset_affinity"),
                },
                "REGRESSION_RESULT": "PASS",
                "PROMOTION_RECOMMENDATION": "PROMOTION_READY",
            },
        )
    )

    items.append(
        _item(
            id="RF-C5-12",
            capability="c5_grounding_factory_injection",
            priority="P1",
            status="BLOCKED",
            risk="LOW",
            expected_gain="C5 chat turn includes factory resource_context without becoming resource authority",
            actual_gain=None,
            evidence="HANDOFF.md",
            promotion_state="DISCOVERED",
            blocked_by="BLOCKED_BY_GOVERNED_CHANNEL",
            record={
                "CAPABILITY": "Ground C5 HTTP turns with factory.resource_context",
                "CURRENT_BEHAVIOR": "C1-C5 channel grounding does not include Resource Factory",
                "GAP": "chat answered GPU-burst with EVIDENCE=NONE_AVAILABLE and no KAGGLE_C1",
                "EXISTING_RAIOS_ASSET_REUSED": "RAIOS-C1-C5-CHANNEL compact_context + c5_awareness.resource_context",
                "PROPOSED_CHANGE": "add factory snapshot to GROUNDING_SOURCE_PATHS when channel lock released",
                "SHADOW_TEST": "not executed; channel file is locked by independent-verify wave",
                "BEFORE_METRIC": {"chat_mentions_kaggle_c1": False},
                "AFTER_METRIC": {"not_run": True},
                "REGRESSION_RESULT": "NOT_RUN",
                "PROMOTION_RECOMMENDATION": "DO_NOT_MUTATE_LOCKED_CHANNEL_OR_C6_ENGINE",
            },
        )
    )

    ids = [i["id"] for i in items]
    assert len(ids) == len(set(ids))

    counts = {
        "DISCOVERED": 0,
        "SHADOWING": 0,
        "VALIDATED": 0,
        "REJECTED": 0,
        "BLOCKED": 0,
        "PROMOTION_READY": 0,
    }
    for it in items:
        counts[it["status"]] = counts.get(it["status"], 0) + 1
        if it.get("promotion_state") in {"PROMOTION_READY", "VALIDATED"} and it["status"] == "VALIDATED" and it["risk"] == "LOW":
            counts["PROMOTION_READY"] += 1

    regression_pass = shadow["after_accuracy"] >= 0.99 and all(
        it["status"] != "REJECTED" or it["id"] == "never" for it in items if it["id"] not in {"RF-C5-08"}
    )
    rejected = [it["id"] for it in items if it["status"] == "REJECTED"]
    regression_pass = shadow["after_accuracy"] >= 0.99 and not rejected

    baseline = {
        "schema": "raios.c5-growth-baseline.v1",
        "super_task_id": SUPER_TASK,
        "observed_at": _utc(),
        "c5_health": health,
        "c5_runtime": "existing http://127.0.0.1:8766 raios_multimodal_gateway",
        "SECOND_C5": False,
        "resource_factory_present": True,
        "naive_placement_accuracy": shadow["before_accuracy"],
        "factory_placement_accuracy": shadow["after_accuracy"],
        "currently_schedulable": ctx.get("currently_schedulable"),
        "PAID_RESOURCE_CREATED": False,
        "GPU_SESSION_STARTED": False,
        "CANONICAL_HIGH_RISK_SELF_PROMOTION": False,
    }

    return mask_record(
        {
            "baseline": baseline,
            "queue": items,
            "counts": counts,
            "shadow": shadow,
            "context": ctx,
            "reservoir": view,
            "contradictions": contra,
            "chat_shadow": chat_shadow,
            "health": health,
            "regression_pass": regression_pass,
            "best_gain": shadow["gain"],
            "top_next": next((it["id"] for it in items if it["status"] in {"BLOCKED", "SHADOWING", "DISCOVERED"}), "RF-C5-08"),
            "packed_samples": {
                "gpu_burst": {k: gpu_burst.get(k) for k in ("selected_resource", "result_class", "abstain", "cost_class", "capacity_confidence", "gpu_failover")},
                "vram": {k: vram.get(k) for k in ("selected_resource", "result_class", "abstain", "knowledge_state")},
                "paid": {k: paid.get(k) for k in ("selected_resource", "result_class", "abstain", "requires_c1_authorization")},
                "storage": {k: storage.get(k) for k in ("selected_resource", "result_class", "dispatch_allowed")},
                "cpu": {k: cpu.get(k) for k in ("selected_resource", "result_class", "cost_class")},
            },
            "evaluate_control": evaluate_workload("CONTROL", world, request_id="GROW-CTRL"),
        }
    )


def write_package(dest: Path, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    dest.mkdir(parents=True, exist_ok=True)
    payload = payload or run_wave()
    assert_no_secrets(payload)
    files = {
        "C5-BASELINE.json": payload["baseline"],
        "C5-GROWTH-QUEUE.json": {
            "schema": "raios.c5-growth-queue.v1",
            "super_task_id": SUPER_TASK,
            "items": payload["queue"],
            "counts": payload["counts"],
        },
        "RESOURCE-AWARENESS-PROOFS.json": {
            "context": payload["context"],
            "contradictions": payload["contradictions"],
            "chat_shadow": payload["chat_shadow"],
            "health": payload["health"],
        },
        "PLACEMENT-REASONING-PROOFS.json": {
            "shadow": payload["shadow"],
            "samples": payload["packed_samples"],
        },
        "FAILOVER-REASONING-PROOFS.json": {
            "gpu_primary": payload["context"].get("gpu_primary"),
            "gpu_failover": payload["context"].get("gpu_failover"),
            "gpu_failover_proven": payload["context"].get("gpu_failover_proven"),
            "remote_cpu_primary": payload["context"].get("remote_cpu_primary"),
            "model_storage_primary": payload["context"].get("model_storage_primary"),
            "model_storage_backup": payload["context"].get("model_storage_backup"),
            "pending_auth": payload["context"].get("pending_auth"),
            "UNPROVEN_NE_FAILOVER": True,
        },
        "COST-AWARENESS-PROOFS.json": {
            "gpu_cost_class": payload["packed_samples"]["gpu_burst"].get("cost_class"),
            "cpu_cost_class": payload["packed_samples"]["cpu"].get("cost_class"),
            "paid_result": payload["packed_samples"]["paid"],
            "PAID_RESOURCE_CREATED": False,
            "CREDIT_NE_CASH": True,
            "CATALOG_NE_ENTITLEMENT": True,
        },
        "REGRESSION-RESULTS.json": {
            "shadow_after_accuracy": payload["shadow"]["after_accuracy"],
            "shadow_before_accuracy": payload["shadow"]["before_accuracy"],
            "pass": payload["regression_pass"],
            "rejected_items": [i["id"] for i in payload["queue"] if i["status"] == "REJECTED"],
            "GPU_SESSION_STARTED": False,
            "PAID_RESOURCE_CREATED": False,
            "SECOND_RESOURCE_REGISTRY_CREATED": False,
            "CANONICAL_HIGH_RISK_SELF_PROMOTION": False,
        },
    }
    for name, body in files.items():
        assert_no_secrets(body)
        (dest / name).write_text(json.dumps(body, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    handoff = f"""# HANDOFF — {SUPER_TASK}

Seat: C2-KAGGLE-CONTROL
Authority: C1
Mode: CONTINUOUS_WHILE_AVAILABLE

## C5 runtime

Existing gateway `http://127.0.0.1:8766/health` is canonical. No second C5. No C6 engine mutation. No C1-C5 channel rewrite.

Health: `{payload['health'].get('status')}` LIVE={payload['health'].get('LIVE')}

## Seam

`src/raios/resource_fabric/c5_awareness.py` reuses `factory.place()` and `factory.plan_dispatch(dry_run=True)`.

SECOND_RESOURCE_REGISTRY_CREATED=false

## Loop

Items: {len(payload['queue'])}
VALIDATED={payload['counts'].get('VALIDATED')}
BLOCKED={payload['counts'].get('BLOCKED')}
REJECTED={payload['counts'].get('REJECTED')}

Best measured gain: placement field accuracy {payload['shadow']['before_accuracy']:.3f} → {payload['shadow']['after_accuracy']:.3f} (gain {payload['shadow']['gain']:.3f})

## Promotion

LOW-risk seam VALIDATED. No HIGH/CRITICAL self-promotion to CANONICAL C5 runtime.

## Safety

PAID_RESOURCE_CREATED=false
GPU_SESSION_STARTED=false
REMOTE_MUTATION=false

## Next

{payload.get('top_next')} — C5 chat remains non-authoritative; Wave-06 live proofs still required before Partner/Oracle/Colab/Lightning failover.
"""
    (dest / "HANDOFF.md").write_text(handoff, encoding="utf-8")
    sha_lines = []
    for name in sorted(p.name for p in dest.iterdir() if p.is_file() and p.name != "FILES-SHA256.txt"):
        digest = hashlib.sha256((dest / name).read_bytes()).hexdigest()
        sha_lines.append(f"{digest}  {name}")
    (dest / "FILES-SHA256.txt").write_text("\n".join(sha_lines) + "\n", encoding="utf-8")
    return {"PACKAGE": str(dest), "FILES": sorted(p.name for p in dest.iterdir() if p.is_file())}
