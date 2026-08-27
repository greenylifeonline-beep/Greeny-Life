# Handoff

- Agent: cursor
- Seat: C2-KAGGLE-CONTROL
- Task: RAIOS-RESOURCE-FABRIC-GIT-DELIVERY-REPAIR-WAVE-01
- Status: IN_PROGRESS
- Isolation: git worktree `rf-wave02-clean-delivery` at `C:\Users\Ghanam\Documents\Codex\Greeny-Life-Worktrees\RF-WAVE02-CLEAN-DELIVERY` (cone sparse-checkout; no full-tree copy)
- Files: Wave-02 Resource Fabric source, tests, live-account evidence, and this delivery-repair package
- Validation: `python -m unittest tests.resource_fabric.test_live_binding tests.resource_fabric.test_resource_fabric` → 131/131 OK on clean materialization from `50f243a` + `b0491b5` blobs
- Evidence: `TEST-RESULTS.json`; oversized archives classified LOCAL_PROVENANCE_ONLY and not in this lineage
- Next: commit clean delivery, write `RESOURCE-FABRIC-DELIVERY-PROVENANCE.json`, fast-forward push to `origin/ai-evolution-202608051809` without rewriting local `7f3c4672`/`b0491b5`
- ORIGINAL_LOCAL_LINEAGE_REWRITTEN: false
