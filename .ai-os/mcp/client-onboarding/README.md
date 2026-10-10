# RAIOS Universal Client Onboarding

Canonical client-visible name:

`raios`

All clients connect to the SAME RAIOS Universal MCP.

## Invariants

- one MCP
- one gateway
- one command plane
- no raw shell
- no C1 impersonation
- separate principal per external client
- separate credential generation per client
- transport is not authority
- RAIOS_SYSTEM owns locks

## Clients

- ChatGPT → CHATGPT_NATIVE_DELEGATE
- Claude → CLAUDE_NATIVE_DELEGATE
- Kimi → KIMI_NATIVE_DELEGATE
- DeepSeek → DEEPSEEK_NATIVE_DELEGATE
- Generic MCP client → GENERIC_AGENT_DELEGATE

## Local endpoint

http://127.0.0.1:8788/mcp

## Remote endpoint

Remote clients use the existing HTTPS transport referenced by
RAIOS_EXTERNAL_MCP_URL.

No remote client creates another RAIOS gateway.

## User experience

After the client has been configured once under the server name `raios`,
the same name is used in future conversations.

ChatGPT's app:// connector URI is ChatGPT-specific and is not a portable
URI standard for other model vendors.
