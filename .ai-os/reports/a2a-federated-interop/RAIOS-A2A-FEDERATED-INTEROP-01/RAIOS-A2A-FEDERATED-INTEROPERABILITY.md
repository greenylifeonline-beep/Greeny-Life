# RAIOS Federated Agent Interoperability (A2A)

TASK_ID: RAIOS-A2A-FEDERATED-INTEROP-01  
MODE: FOUNDATION_ONLY  
A2A_PRODUCTION_ACTIVATED: false

## What each layer solves

**A2A solves: CAN_WE_TALK**

A2A v1.x is the external/federated agent interoperability edge. Official SDK `a2a-sdk==1.1.2` provides AgentCard, protocol bindings, well-known discovery path, and JSON-RPC method types. RAIOS does not fork the protocol.

**Governed Semantic Context solves: DO_WE_MEAN_THE_SAME_THING**

Transport compatibility is not semantic agreement. RAIOS owns `urn:raios:a2a:semantic-context:v1`. Fingerprints are UTF-8, sorted-key JSON, SHA-256, with volatile timestamps excluded. Match / mismatch / unknown are fail-closed. The extension is optional at protocol interoperability level and mandatory for governed RAIOS capability execution.

**RIF / Trust / Policy solves: SHOULD_I_TRUST_YOU**

`SIGNATURE_VALID`, `ISSUER_IDENTIFIED`, `ISSUER_TRUSTED`, and `SCOPE_AUTHORIZED` are separate. A valid signature is not `TRUSTED_ORGANIZATION`. Production trusted issuers are empty. Self-signed test identities are not production trust.

**Unified Control Plane solves: ARE_YOU_ALLOWED_TO_DO_IT**

There is no `A2A_REQUEST -> EXECUTE` path. Required path:

A2A Request → Identity → Authentication → Semantic normalization → Capability resolution → Policy → Risk classification → RAIOS Intent → Plan → Authority Gate when required → Unified Control Plane → Execution → Verification → Receipt → A2A Task Result / Artifact.

A2A has no independent mutation authority. HIGH/CRITICAL mutation and DELETE / FORCE_PUSH / CANONICAL_REPLACEMENT / IRREVERSIBLE_MIGRATION / SECRET_ROTATION require existing authority gates.

**Evidence Fabric solves: CAN_WE_PROVE_WHAT_HAPPENED**

Accepted A2A tasks emit receipts mapping A2A task/context identifiers onto COMMAND_ID / CORRELATION_ID without replacing existing IDs. PRE/POST hashes are `NOT_APPLICABLE` when conceptually impossible. Existing command-fabric receipt directory is reused; no second WAL.

## Architecture

```
External / Foreign Agents
          |
          | A2A
          v
RAIOS A2A EDGE GATEWAY
          |
          v
RAIOS GOVERNED CONTEXT LAYER
          |
          v
RAIOS UNIFIED CONTROL PLANE
          |
          +------ NATS internal transport
          |
          +------ existing HTTP fallback
          |
          v
RAIOS brains / C5 / runtime
          |
          v
MCP
          |
          v
Tools / Files / DB / Git / Kaggle / ERP / external systems
```

A2A = external/federated agent interoperability edge  
RAIOS Governed Semantic Context = shared meaning / semantic contracts  
Unified Control Plane = execution authority  
NATS = internal transport  
MCP = tools/data access  
Evidence Fabric = receipts/provenance

## Non-goals

- NO_SECOND_COMMAND_FABRIC
- NO_SECOND_WAL
- NO_SECOND_EVENT_BUS
- NO_MCP_REPLACEMENT
- NO_NATS_REPLACEMENT
- NO_PROTOCOL_FORK
- NO_AP2_NOW

AP2 remains an extension hook only: A2A → future extension → AP2.  
AP2_IMPLEMENTED=false. AP2_ACTIVATED=false.

## Identity law

Operational seats are not public A2A agents:

- C1
- C2-KAGGLE-CONTROL
- C2-ESTATE-RECON
- C6-AG-REMOTE-RECON

Only stable service identities backed by real current capability may be cards. This foundation publishes **RAIOS Foundation Agent** with public skill `raios.foundation.noop_intent` only. Candidate class agents are not auto-created.

## Transport truth preserved

- HTTP_PRIMARY=true
- NATS_PRIMARY=false
- NATS_REPLACED=false
- HTTP_FALLBACK_PRESERVED=true

## Production activation

A2A_MODE remains FOUNDATION_ONLY until all production gates are independently true, including C1_PRODUCTION_ACTIVATION_APPROVED. This task does not activate production, public listeners, firewalls, tunnels, or external mutation.
