# Durable Decisions

## D-001 Provider-neutral truth
Repository evidence and shared RAIOS state are authoritative.

## D-002 Parallel work requires scope separation
No overlapping write scopes.

## D-003 Handoff is mandatory
Meaningful work must end with status, files, validation, evidence, and next step.

## D-004 Prefer large safe batches
Use independently verifiable work packages.

## D-005 Branch unification without octopus merge
Canonical working checkout is `phase2a/class-a-20260822-232109`. Canonical cloud product line is `origin/v9-neurolingua-semantic-kernel`. Do not merge `origin/main` or other no-common-base cursor branches into Repair. Collapse cursor agent branches to tip `origin/cursor/raios-live-assimilation-147d`. Do not merge origin/v9 into this working tree while V9-A15/V9-NL0 locks are ACTIVE or the tree is dirty. Unique unlocked GL-002 docs live under `migration/strong-validation/`. Origin branches are not deleted. Ledger: `archive/repair-leftovers/branch-filter-20260824.json`.

## D-006 9Router vs 9Remote keys are different domains
A key created in RAIOS or in 9Router dashboard **Create Key** is for `http://127.0.0.1:20128/v1` only (`Authorization: Bearer`). It is **not** valid on `https://9remote.cc/login`. 9Remote Access Keys come from the separate 9Remote product (Get 9Remote / one-time ABC123). 9Remote would expose shell, desktop, and files through a third-party cloud; it stays **NOT_ACTIVATED** unless C1 explicitly authorizes remote terminal access. Registry: `.ai-os/reports/9router/RAIOS-9ROUTER-DISCOVER-AUDIT-INSTALL-RUN-WAVE-01/KEY-REGISTRY.json`. Secrets are never stored in git (`credential_ref` only).

## D-007 Live Resource Fabric overlay does not invent a second registry
Wave-02 binds owned accounts onto the existing Resource Fabric adapters. Catalog GPU/storage remains catalog. Live quota and credits overlay live observations. Missing `~/.kaggle/kaggle.json` does not mean KAGGLE_C1 is absent; current auth is Kaggle CLI OAuth (`credentials.json`). KAGGLE_C1 and KAGGLE_PARTNER stay isolated. 9Router on `127.0.0.1:20128` is a MODEL_ROUTING_GATEWAY only, never resource authority. No paid activation and no model-weight migration in this wave.

