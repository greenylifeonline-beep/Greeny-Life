# RAIOS execution and configuration implementation plan

Goal: upgrade the existing channel in place with an official MCP client, bounded provider calls, and one configuration contract.
Spec: DESIGN.md and TOOLING.md in this directory.
Execution: inline, following the user's explicit instruction to execute immediately. No further authorization for reversible source changes is needed.

Constraints: preserve eight cognitive tools and the existing execute_scoped_task interface; retain authentication and mutation restrictions; no parallel gateway or task ledger; no destructive operation on the host; do not claim Windows deployment from Linux tests.

Review focus: startup hangs, stalled stdin, hung tool replies, stale environment HEAD, inconsistent readiness tools, unauthorized execution, provider errors containing secrets, partial HTTP bodies.

1. Replace the owned provider's hand-written JSON-RPC client with pinned official mcp SDK. Keep its public call/status/close interfaces. Bound admission and total initialization/discovery/call time. Start an isolated stdio connection per admitted call, avoiding a shared poisoned session. Discover tool schemas and validate arguments. Test with actual subprocess fixtures before implementing.
2. Derive readiness expectations from POLICY.json rather than copying a numeric census. Both local and tunnel launchers use the same helper; health exposes the actual registered schemas. Correct the policy's stale branch without rewriting actors. Validate valid extensions and reject missing execution, duplicates, count mismatches and invalid service properties.
3. Make HEAD follow actual Git metadata, including worktrees; remove stale environment precedence. Bound HTTP body reads and immediately reject oversized requests without draining an attacker-controlled body. Test a stalled socket alongside health.
4. Run all MCP tests with PowerShell, the project's default suite, and dependency checks. Record limitations. Review the whole diff and resolve material findings before publishing.
5. Publish a reviewable source change and handoff. Keep local deployment unverified until the full host source can be reconciled and Windows runtime exercised.

Mutation execution remains gated: the existing lease acquisition is a read-then-write operation without proven cross-process atomicity. Do not enable arbitrary write_tools or shell execution while that invariant is unproven. A locally executed read capability is real execution, but does not prove mutation readiness.
