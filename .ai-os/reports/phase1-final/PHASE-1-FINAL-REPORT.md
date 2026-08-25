# Phase-1 final consolidation report (C2-OBS)

`not_complete_phase1_census=true`

This is not a new program. It continues `PHASE1-DEEP-PROJECT-ESTATE-CENSUS-20260825` and `C2-RAIOS-COMMAND-FABRIC-JOIN-REPAIR-EVOLUTION-20260825`.

Every durable claim is bound to HOST + TREE_ID + ROOT + BRANCH/REF + FULL SHA + DATE + STATE.

## A. EXECUTIVE-TRUTH-SUMMARY

Host (this executor):

* HOST=`cursor` ROOT=`/workspace` TREE_ID=`C2-CLOUD` BRANCH=`v9-neurolingua-semantic-kernel` SHA=`ff366772edaa823e154fc53b76f52dd6fdf5ceb5` bcId=`bc-dd60b5cf-95bd-4f24-9237-cc1b2225f013` STATE=`ON_DISK` DATE=`2026-08-25T17:38:17.605088+00:00`

Host (C1/AG, not readable here):

* HOST=`AG` ROOT=`C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair` BRANCH=`phase2a/class-a-20260822-232109` SHA=`12603d02253547c7727bc84ce68c318e8e9258bc` STATE=`EXTERNAL_ATTESTATION_PENDING_CROSS_HOST_BIND`

Cleanup commit `d17335a8a1428acdd0b98849550e4c930c1d9e97` parent `61069d8fbd5914f5104eb3c4e2728cdf8271698c`.
Command Fabric commit `ff366772edaa823e154fc53b76f52dd6fdf5ceb5` is HEAD.

Truth:

1. C2-OBS joined the **guards of this `/workspace` clone** (lease, heartbeat, ACK, isolated channel, MCP 8787, C5 8765, 8 tests). That is `C2_CLOUD_GUARDS_JOINED=true`.
2. That is **not** join to unified RAIOS and **not** a link to the AG Repair tree. `C2_JOIN_PROVEN=false`. `COMMAND_FABRIC_E2E_PROVEN=false`. `CROSS_HOST_ROUND_TRIP_PROVEN=false`.
3. CI govern+c5-week succeeded on `d17335a` and `ff36677`. `CI_PASS_NE_ASSIMILATION`. `GL005_PROVEN=false`.
4. WAL git blob is identical from parent to `d17335a` (and HEAD blob). On-disk WAL is dirty vs HEAD under A15. `WAL_WRITTEN=false`.
5. The 60 deleted files are listed in appendix I. `RESTORE_REQUIRED=0`.
6. C1 AG C5 public chat and the local C5 comparison JSON were **not read** on this VM. They are ingested as external attestation only.
7. OneDrive, Skrivebord, AG ZIPs, donor commit `f7354c24`, retired `fd2775e3`, and TREE-001 remain unread here.
8. Because appendix J is nonempty, this report does not describe the estate as complete.

Machine copies: `.ai-os/reports/phase1-final/*.json`.

## 2. Why the join is not fully proven

1. Isolated Gateway tests used **ephemeral tokens in a temp git repo** (`CHANNEL.json` `tmp=/tmp/c2-obs-fabric-jp8ochpd`, `read_head=5b574e19`), not live `tokens.local.json`. Live health reports `remote_c2_ready=false`. Delivery receipt itself sets `c2_join_proven=false` and `isolated_not_live_mcp_token=true`.
2. Three different acts:
   * Join `/workspace` guards = bind observer onto this clone's existing MCP/mail/lock/lease/watchdog keepers.
   * Join unified RAIOS = authenticated live membership on the five-seat plane (live `send_packet`/`ack_packet`, not paste, not tmp).
   * Connect Repair AG = reach `12603d0` plus that tree's Command Fabric runtime on device AG.
3. Yes. Lease, ACK, and Response circulated inside **one repository** and **one isolated tmp repo** on HOST=`cursor`. Not AG.
4. No. No packet traveled AG → Cursor Cloud without manual paste.
5. No. No automatic Cloud → AG return path exists (`cursor-agent` missing, no public MCP URL, mail inbox missing).
6. Missing live credential: **MCP bearer token** consumed by `Gateway.authenticate()`. File `.ai-os/mcp/tokens.local.json` is absent. Independently, `scripts/ai-os/raios_mcp/server.py` **hardcodes** `remote_c2_ready=false` on `/health`.
7. Issuer: **C1/owner** via scoped local grant (or OAuth when remote MCP is registered). This C2 must not mint secrets.
8. Store at `.ai-os/mcp/tokens.local.json` (gitignored). Receipts may record sha256 only. Never commit values.
9. Minimum for `C2_JOIN_PROVEN=true`: C1-issued grant loaded by the live Gateway process; authenticated live MCP ACK/receipt on 8787 (not tmp). That still would not prove Repair or cross-host E2E.
10. Requires a **documented bridge**, not Actor rebind. SEAT-MAP `C2.instance_role=chatgpt-primary` is not overwritten this phase.

## 3 / K. Communication topology

Paste is not a round trip. Status vocabulary only: PROVEN_E2E, PROVEN_ONE_WAY, LOCAL_ONLY, SESSION_ONLY, BLOCKED_AUTH, BLOCKED_ROUTING, UNPROVEN, ABSENT.

| link | STATUS | evidence |
|------|--------|----------|
| USER → C1/ChatGPT | SESSION_ONLY | founder chat; not MCP |
| USER → C2/Cursor | SESSION_ONLY | this Cloud run |
| USER → C5 Public | LOCAL_ONLY | Cloud GET health/status/history 200; AG POST /api/chat attested not read |
| USER → C5 Founder | BLOCKED_ROUTING | AG 8876 not forwarded; Cloud 8876 is this VM |
| C1 ↔ C2 | SESSION_ONLY | paste + isolated tmp; live MCP BLOCKED_AUTH |
| C1 ↔ C5 | LOCAL_ONLY | per-host loopback |
| C2 ↔ C5 | LOCAL_ONLY | 8765/8787 this VM |
| C2 Cloud ↔ Repair AG | ABSENT | 12603d0 missing; no cursor-agent |
| C5 ↔ MCP | LOCAL_ONLY / tools BLOCKED_AUTH | health 200; 8 tools; no bearer |
| C5 ↔ Mail | LOCAL_ONLY | OUTBOX present; INBOX missing |
| C5 ↔ Nomadic leases | LOCAL_ONLY | C2-OBS FAILOVER_CLAIM |
| C5 ↔ WAL | BLOCKED_AUTH | A15; wal_written=false |
| C5 ↔ Main Cortex | UNPROVEN | ENDPOINT_UNBOUND |
| C5 ↔ NeuroLingua | LOCAL_ONLY | code on HEAD; not E2E cortex |
| C5 ↔ GL-005 | UNPROVEN | GL005_PROVEN=false |

ACK `MSG-1787675796720281-e5058327` status=READ moved=false. Channel receipt sha256 `b56b43e5503b7aeb11020449e983dc12081b2494e11b3b73c41131f235761e06`.

## 4 / L. C5 repair and channels

C2 Cloud (HOST=cursor, ON_DISK, HEAD=`ff366772edaa823e154fc53b76f52dd6fdf5ceb5`):

* `/health` 200, `/api/status` 200, `/api/history` 200
* `/v1/chat` 404 (old path)
* `/api/chat` GET 404 because the keeper is POST-only (`raios_c5_screen.py` `do_POST`)
* POST `/api/chat` **not executed** this turn (WAL hold)
* 8876 `/health` 200 on **this** VM (C1 console here ≠ AG founder channel)
* MCP 8787 `/health` 200, `remote_c2_ready=false`, `gl005_proven=false`
* `.ai-os/control` has `KEEPERS.json` + `c2_obs.py` only — not Repair console runtime
* `raios_multimodal_gateway.py` missing

AG (EXTERNAL_ATTESTATION_PENDING_CROSS_HOST_BIND): C5 via Cursor.exe forward on 8765; `/api/chat` PASS; `response_schema=raios.c5-screen-turn.v1`; lane PUBLIC; wal_written=false; founder 8876 not forwarded; console script switched to `/api/chat` + `text`/`locale`; donor `f7354c24` GIT_ONLY/ORPHAN; recovered three modules under `_raios-communication-fabric/.venv-multimodal`; recovery gateway not bound while live C5 owns 8765; no second C5. Local report sha256 attested `b2dd45a12ef6a9d99f537ed801d12404097014cd13526b576b52a2896be8c1aa` — **not hashed here**.

## 5 / I. Deleted 60 files (`d17335a`)

`git show --stat` and `git diff-tree --name-status` are copied beside this report.

* Parent: `61069d8fbd5914f5104eb3c4e2728cdf8271698c`
* Name-status counts: 60 D, 5 A, 3 M (68 paths in `--stat`)
* Classes: 58 ZERO_BYTE_HUSK, 1 BOM_ONLY_EMPTY_CLI (`run_brain_cli.py` 4 bytes, sha256 `b42f2099187886def637d6aa840022266e05cb6c987a9394e708e23cd505eb46`), 1 POWERSHELL_COMMAND_CAPTURE (16384 bytes)
* `RESTORE_REQUIRED=0`
* Live keepers not in the D list (WAL, C5 screen, MCP, aios.py present at HEAD)
* WAL blob `77f6090cd39a533d0d3facb9471878267382e4d3` identical parent and `d17335a`
* Alternate nonempty **different blobs** on `origin/main` for three `data/*.json` husks — HOLD, do not merge
* `run_brain_cli_backup.py` remains (13725 bytes)
* Several deleted paths still have ACTIVE GL-004 locks (stale); HOLD

| n | path | size | sha256 | class | husk | alt | lock | decision | git_restore |
|---|------|------|--------|-------|------|-----|------|----------|-------------|
| 1 | `ImageInventory.csv` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 2 | `app/js/script.js` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 3 | `app/views/products.html` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 4 | `application/customer/commands/customer-command.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 5 | `application/customer/queries/customer-query.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 6 | `application/customer/workflows/customer-workflow.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 7 | `application/inventory/commands/inventory-command.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 8 | `application/inventory/queries/inventory-query.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 9 | `application/inventory/workflows/inventory-workflow.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 10 | `application/logistics/commands/logistics-command.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 11 | `application/logistics/queries/logistics-query.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 12 | `application/logistics/workflows/logistics-workflow.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 13 | `application/product/commands/product-command.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 14 | `application/product/queries/product-query.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 15 | `application/product/workflows/product-workflow.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 16 | `application/quality/commands/quality-command.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 17 | `application/quality/queries/quality-query.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 18 | `application/quality/workflows/quality-workflow.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 19 | `application/supplier/commands/supplier-command.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 20 | `application/supplier/queries/supplier-query.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 21 | `application/supplier/workflows/supplier-workflow.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 22 | `archive/old_folders/unified-intelligence/scripts/phase-2-capability-discovery.ps1` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 23 | `data/03_packaging_system.json` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | yes | yes | DELETE_CONFIRMED | yes |
| 24 | `data/legacy/packaging.json` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | yes | yes | DELETE_CONFIRMED | yes |
| 25 | `data/migrated_products.json` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | yes | yes | DELETE_CONFIRMED | yes |
| 26 | `database/connections/index.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 27 | `database/indexes/README.md` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 28 | `database/models/entities.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 29 | `database/models/index.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 30 | `database/repositories/index.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 31 | `database/repositories/repository-contracts.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 32 | `database/schemas/core/enterprise-schema.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 33 | `database/schemas/domain/domain-schema.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 34 | `database/schemas/index.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 35 | `domain/customer/entities/customer-entity.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 36 | `domain/customer/rules/customer-rules.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 37 | `domain/customer/services/customer-service.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 38 | `domain/inventory/entities/inventory-entity.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 39 | `domain/inventory/rules/inventory-rules.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 40 | `domain/inventory/services/inventory-service.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 41 | `domain/logistics/entities/logistics-entity.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 42 | `domain/logistics/rules/logistics-rules.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 43 | `domain/logistics/services/logistics-service.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 44 | `domain/product/entities/product-entity.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 45 | `domain/product/rules/product-rules.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 46 | `domain/product/services/product-service.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 47 | `domain/quality/entities/quality-entity.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 48 | `domain/quality/rules/quality-rules.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 49 | `domain/quality/services/quality-service.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 50 | `domain/supplier/entities/supplier-entity.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 51 | `domain/supplier/rules/supplier-rules.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 52 | `domain/supplier/services/supplier-service.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 53 | `eos-core/master-data/master-data/contracts/master-data-contracts.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 54 | `eos-core/master-data/master-data/events/master-data-events.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 55 | `eos-core/master-data/master-data/mapping/entity-mapping.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 56 | `eos-core/master-data/master-data/schemas/master-data-schema.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 57 | `eos-core/master-data/master-data/validation/master-data-rules.ts` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |
| 58 | `how HEAD.env  Select-Object -First 20` | 16384 | `33707fe2475f5971e9db766ae6fb7adf0b82039e812da6997ede33c5430575ac` | POWERSHELL_COMMAND_CAPTURE | CORRUPT_PATH | no | no | DELETE_CONFIRMED | yes |
| 59 | `run_brain_cli.py` | 4 | `b42f2099187886def637d6aa840022266e05cb6c987a9394e708e23cd505eb46` | BOM_ONLY_EMPTY_CLI | BOM_ONLY | yes | yes | DELETE_CONFIRMED | yes |
| 60 | `scripts/repair-canonical-products.ps1` | 0 | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ZERO_BYTE_HUSK | ZERO_BYTE | no | yes | DELETE_CONFIRMED | yes |

Parent SHA, show-stat, and name-status: `git-show-stat.txt`, `git-name-status.txt`.

## 6 / J. OMITTED-SUMMARIZED-UNRESOLVED-REGISTER

Nonempty (`count=25`). Therefore this report does not call the census complete.

Includes: AG tree, OneDrive/Skrivebord, project ZIPs on AG, donor/retired/TREE-001 objects, 30 files >8MB not hashed, 127 untracked not fully hashed, env go/ollama/powershell archives not member-indexed, C1 local C5 JSON unread, tokens absent, credential-gate JSON name-only, historical CROSS-TREE process list not re-asserted as live.

## 7 / D. Tree comparison (reachable objects only)

| id | full SHA | files | state | vs HEAD |
|----|----------|-------|-------|---------|
| TREE-001 | 12603d0… | n/a | ABSENT | cannot inspect |
| TREE-P0 | `30637e7821c0c58d16e2ef57e902428a14396be1` | 2340 | GIT_ONLY ancestor | +126 / −63 vs HEAD; unique includes later-deleted husks |
| TREE-GL005 | `3d9f58136d318ba07d743e127ab1e433605ce1ea` | 1327 | GIT_ONLY diverged | named GL-005 code; GL005_PROVEN=false |
| TREE-V9 | `b877a232a486f539691112e9114997acb4a3a21e` | 2257 | GIT_ONLY ancestor | title ≠ assimilation proven |
| TREE-CURSOR | `2d41ef264bdda70b1ba0f0588585ee740aea3ff2` | 2061 | GIT_ONLY diverged | unique `RAIOS-COGNITIVE-LEARNING-FABRIC-REFERENCE-V2` — do not merge as second fabric |
| TREE-CLEANUP | `d17335a8a1428acdd0b98849550e4c930c1d9e97` | 2252 | GIT_ONLY ancestor | +25 files in fabric HEAD |
| TREE-C5-DONOR | f7354c24… | n/a | ABSENT | AG attest 31 C5 paths |
| TREE-RETIRED | fd2775e3 | n/a | ABSENT | |
| TREE-FABRIC / C2-CLOUD | `ff366772edaa823e154fc53b76f52dd6fdf5ceb5` | 2277 | ON_DISK | HEAD; dirty untracked 127 |
| origin/main | `da67f44963fafde67df52cb62ab32f75fe725df0` | 616 | GIT_ONLY | backups/images; `/tmp/c5-clone-main` matches this HEAD |

`/tmp/c5-clone-v9` deleted earlier. `/tmp/c5-clone-main` ARCHIVE_READONLY, 616 tracked, not a live keeper.

## 8. Census gaps from the first order

Surfaces still uncovered **from this VM**: OneDrive Skrivebord pic/Ny mappe, cloud placeholders, dated Codex folders, project ZIPs/nested archives, Norwegian desktop, AG domain/product/honey/export trees, git-only donor/retired/12603d0. Proven hashes on this clone were not re-walked except HEAD/d17335a/ff36677 and the 60-file parent blobs.

## 9. Constraints honored

No merge, restore, or new delete. No WAL write. No secret bind. No GL-005/Assimilation/E2E claim. No actor rebind.

## Q. Verdict flags

* `D17335A_CI_PASS=true`
* `FF36677_CI_PASS=true`
* `C2_CLOUD_GUARDS_JOINED=true`
* `C2_JOIN_PROVEN=false`
* `COMMAND_FABRIC_E2E_PROVEN=false`
* `CROSS_HOST_ROUND_TRIP_PROVEN=false`
* `C5_PUBLIC_CHANNEL_PROVEN=false`
* `C5_PUBLIC_CHANNEL_PROVEN_AG_ATTESTED=true`
* `C5_PUBLIC_CHANNEL_PROVEN_C2_CLOUD=false`
* `C5_FOUNDER_CHANNEL_PROVEN=false`
* `C5_MAIN_CORTEX_PROVEN=false`
* `WAL_WRITTEN=false`
* `GL005_PROVEN=false`
* `PHASE1_COMPLETE=false`
* `READY_FOR_PHASE2=false`
* `CI_PASS_NE_ASSIMILATION=true`
* `ASSIMILATION_PROVEN=false`

### Evidence paths

* `.ai-os/reports/phase1-final/`
* `.ai-os/reports/UNREPAIRABLE-GC.json`
* `.ai-os/reports/command-fabric/DIAGNOSIS.json`
* `.ai-os/receipts/command-fabric/`
* `.ai-os/state/command-fabric/FLAGS.json`
* CI URLs in `A-EXECUTIVE-TRUTH-SUMMARY.json`

### Tests

`/tmp/pytest-nl/bin/python -m pytest tests/command_fabric tests/neuro_lingua/test_unrepairable_gc.py` → 8 passed.

### Smallest safe next

C1 issues a scoped gitignored MCP grant and documents a bridge (public HTTPS on the **same** 8787 process, or the existing nonce+founder-relay path). Do not rebind actors. Do not merge or restore.
