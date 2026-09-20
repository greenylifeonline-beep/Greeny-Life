# Handoff — D-058 MCP Streamable HTTP session channel

- Agent: C2@AG
- Task: RAIOS-CANONICAL-CONVERGENCE-001
- Status: Universal MCP now has a live Streamable HTTP session channel. Program IN_PROGRESS. Not DONE.
- Work authority: C1 — MCP must have a channel as specified; MCP and Command Center remain highest priority; C5 is RAIOS.
- C6 was not impersonated. No second gateway. No ninth tool. No C2/C6 grants invented.

## Defect (OBSERVED)

Live `:8788` answered `/health` and POST `/mcp`, but `GET /mcp` returned 405 `GET_SSE_NOT_REQUIRED_STATELESS_V1` with `mcp-session-id=stateless`. That is not a client channel. This Cursor chat still does not list RAIOS MCP tools until the client reloads.

## Upgrade (existing server only)

- `scripts/ai-os/raios_mcp/server.py`: real session ids; GET `/mcp` JSON channel status; GET `/mcp` SSE `: connected` + ping; POST notifications 202; protocol negotiate `2024-11-05`/`2025-03-26`/`2025-06-18`
- Command Center `mcp_bind` requires `get_sse=true` for `live`
- `.cursor/mcp.json` already pointed at `http://127.0.0.1:8788/mcp`

## Live proof (OBSERVED)

- Existing `raios_mcp_local_ensure.ps1 -Reload`: PID 43452 → 33112, same `:8788`, 8 tools
- `/health` `channel=streamable-http-session` `get_sse=true` `stateless=false`
- GET `/mcp` JSON 200, session id not `stateless`
- GET `/mcp` SSE 200 `text/event-stream` first line `: connected`
- initialize `protocolVersion=2025-06-18`; notifications 202
- Command Center in-place restart listen 24044 → 51976, same TX `TX-CC-C6-SELF-REAUTH-20260919T0226`
- `/api/mcp` `live=true` `get_sse=true` `client_channel=streamable-http-session`
- Tests: 30 passed (`tests/mcp/test_mcp_health.py` + `tests/command_center/test_app.py`)

## Remaining

C6 self check-in still required before P0. This Cursor chat listing RAIOS tools remains UNPROVEN until the client reloads MCP. LOCKS/SEAT-MAP/CHATGPT-NORMAL not mutated.
