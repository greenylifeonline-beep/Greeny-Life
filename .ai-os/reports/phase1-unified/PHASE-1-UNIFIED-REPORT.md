# Phase-1 unified report (C2-OBS Cloud)

Source reports in `.ai-os/reports/phase1-final/` are kept. C6/AG TREE-001 work was not executed here.

## A. Executive truth

C1 named TREE-001 on device AG as the canonical runtime/repair tree. This executor is HOST=`cursor` ROOT=`/workspace` TREE=`C2-CLOUD` SHA=`15bcaf1fa13af43bc6352b47862bd1cac13e74fa` (report successor; this commit will move HEAD). The two contexts are not mixed.

Cloud Adapter `raios.cross-host-packet.v1` sits on existing MCP `send_packet`/`ack_packet` (still 8 tools). Isolated tests cover direct, broadcast, founder fail-closed, replay, invalid schema/signature, expired, missing token, lease conflict, duplicate ACK, missing return path. That is **not** AG↔Cloud transport. `EXPORTED_NOT_TRANSPORTED` is not a connection.

C5 PUBLIC `POST /api/chat` hello on this VM: HTTP 200, `raios.c5-screen-turn.v1`, lane=PUBLIC, `wal_written=false`, WAL mtime unchanged at 2026-08-20T23:49:44Z, `paid_api=false`, `gl005_proven=false`. Response has **no** `correlation_id` / `message_id`, so `USER_TO_C5_PUBLIC_PROVEN=false`.

C5-FOUNDER remains fail-closed. Cloud `:8876` C1-lane HTTP 200 is not the AG founder channel.

## Flags

* `CANONICAL_BUILD_TREE_PROVEN=false`
* `D17335A_CI_PASS=true`
* `FF36677_CI_PASS=true`
* `REPORT_SUCCESSOR_CI_PASS=true`
* `C2_CLOUD_GUARDS_JOINED=true`
* `C2_JOIN_PROVEN=false`
* `COMMAND_FABRIC_E2E_PROVEN=false`
* `CROSS_HOST_ROUND_TRIP_PROVEN=false`
* `USER_TO_C5_PUBLIC_PROVEN=false`
* `USER_TO_C5_PUBLIC_LOCAL_CLOUD_HTTP=true`
* `USER_TO_C5_FOUNDER_PROVEN=false`
* `USER_TO_ALL_PROVEN=false`
* `C5_MAIN_CORTEX_PROVEN=false`
* `WAL_WRITTEN=false`
* `GL005_PROVEN=false`
* `PHASE1_COMPLETE=false`
* `READY_FOR_PHASE2=false`
* `CI_PASS_NE_ASSIMILATION=true`
* `EXPORTED_NOT_TRANSPORTED=true`

## Evidence

* Adapter: `scripts/ai-os/raios_mcp/cross_host_adapter.py`
* Schema: `.ai-os/mcp/CROSS-HOST-PACKET.schema.json`
* Routes: `.ai-os/mcp/ROUTE-REGISTRY.json`
* Tests: 11 passed `tests/command_fabric`
* Prior 60-file register reused: `.ai-os/reports/phase1-final/I-DELETED-60-FILES-REGISTER.json`
* Issuer: C1/owner; store `.ai-os/mcp/tokens.local.json` gitignored; no values in this report

## Smallest safe next

C1 issues a scoped gitignored MCP grant and automatic transport onto the same `8787` process. C6 continues on TREE-001. Do not rebind, merge, restore, write WAL, or run the cross-host challenge until those exist.
