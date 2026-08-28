# HANDOFF — RAIOS-RESOURCE-FACTORY-EXECUTABLE-RESERVOIR-WAVE-05

Seat: C2-KAGGLE-CONTROL
Authority: C1
Base: 24a726a9f6b2757dad5d3881d12dc93368a0f2fa

## Result

Resource Fabric placement is now executable. actory.place() accepts a ResourceRequest, consumes live census/overlay state, enforces Wave-04 policy, and returns a deterministic PlacementDecision. actory.plan_dispatch(dry_run=True) maps that decision onto the existing V9 job ledger, command-fabric lease adapter, TASKS.json, and receipt root without enqueue, acquire, GPU start, or paid create.

## Reuse

Existing placement.decide remains the numeric fit engine. Adapters remain the provider registry. No second scheduler, lease, receipt, task, event bus, or WAL.

## Not claimed

Kaggle live GPU SKU/VRAM, GPU failover, Partner auth, Oracle/Colab reachability, Lightning live GPU, exactly-once, paid entitlement.

## 9Router

Not modified. Not placement authority.
