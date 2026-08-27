# RIF-RAIOS Integration Map v1.1

## System Context

```
┌─────────────────────────────────────────────────────────────┐
│                        RAIOS ECOSYSTEM                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │     UCP     │  │   RKG/RAG   │  │  Evidence-Trust-    │  │
│  │  (Global    │  │  (Model     │  │  Lattice            │  │
│  │  Authority) │  │  Ecology)   │  │  (Canonical Store)  │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                    │             │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌──────────┴──────────┐  │
│  │   NATS      │  │    MCP      │  │    Policy Authority │  │
│  │ (Transport) │  │  (Tools)    │  │    (Rules Engine)   │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                    │             │
│  ┌──────┴────────────────┴────────────────────┴──────────┐  │
│  │              RIF DONOR PACKAGE (C7)                   │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │  │
│  │  │  State  │ │ Evidence│ │  Risk   │ │  Governor   │  │  │
│  │  │ Machine │ │  View   │ │ Donor   │ │  (Pure)     │  │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └──────┬──────┘  │  │
│  │       └───────────┴───────────┴─────────────┘         │  │
│  │                        │                              │  │
│  │              ┌─────────┴─────────┐                    │  │
│  │              │  Adapter Layer    │                    │  │
│  │              │ (12 Interfaces)   │                    │  │
│  │              └─────────┬─────────┘                    │  │
│  └────────────────────────┼─────────────────────────────┘  │
│                           │                                │
│              ┌────────────┼────────────┐                 │
│              ▼            ▼            ▼                 │
│         ┌─────────┐  ┌─────────┐  ┌─────────┐            │
│         │  A2A    │  │  M001   │  │  Tests  │            │
│         │ Bridge  │  │ Harness │  │ (56)    │            │
│         └─────────┘  └─────────┘  └─────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Adapter Bindings

| RIF Component | Adapter | RAIOS System |
|---------------|---------|--------------|
| Canonicalization | CanonicalFingerprintProvider | RAIOS Canonicalizer |
| Evidence | EvidenceStoreAdapter | Evidence-Trust-Lattice |
| Trust | TrustLatticeAdapter | Evidence-Trust-Lattice |
| WAL | WALAdapter | Existing WAL Adapter |
| Control | ControlPlaneAdapter | UCP |
| Semantic | SemanticResolverAdapter | NeuroLingua |
| Policy | PolicyAdapter | Policy Authority |
| Observability | ObservabilitySinkAdapter | Existing Infrastructure |
| Models | ModelEcologyAdapter | RKG |
| Factory | ModelFactoryAdapter | Model Factory |
| Tools | MCPToolAdapter | MCP |
| Transport | TransportAdapter | NATS |

## Data Flow

1. A2A request → A2A Bridge → Evaluation Context
2. Evaluation Context → State Machine
3. State Machine → Evidence View (via EvidenceStoreAdapter)
4. Evidence View → Trust Assessment (via TrustLatticeAdapter)
5. State Machine → Risk Donor → PolicyAdapter
6. Governor → Decision → ControlPlaneAdapter + WALAdapter
7. Observability → ObservabilitySinkAdapter
8. M001 → ModelEcologyAdapter (discovery only)

## Ownership Boundaries

| Asset | Owner | C7 Access |
|-------|-------|-----------|
| Global task state | UCP | Read via ControlPlaneAdapter |
| Canonical state | RAIOS Canonicalizer | Read via CanonicalFingerprintProvider |
| Evidence | Evidence-Trust-Lattice | Read/Write via EvidenceStoreAdapter |
| Policy | Policy Authority | Write (assessments) via PolicyAdapter |
| Models | RKG | Read via ModelEcologyAdapter |
| Transport | NATS | Write via TransportAdapter |
| WAL | Existing WAL | Append via WALAdapter |

## Integration Points

### Point 1: Evaluation Registration
- C7 → ControlPlaneAdapter.register_evaluation()
- UCP assigns TASK_ID
- C7 uses TASK_ID for all subsequent operations

### Point 2: Evidence Ingestion
- External → EvidenceStoreAdapter.store()
- C7 reads via EvidenceStoreAdapter.retrieve()
- C7 never stores evidence locally

### Point 3: Risk Assessment
- C7 Risk Donor produces assessment
- PolicyAdapter.evaluate_policy() receives it
- Policy Authority makes binding decision

### Point 4: Governor Decision
- Governor produces pure decision
- WALAdapter.append() for persistence
- ObservabilitySinkAdapter.emit_event() for monitoring
- ControlPlaneAdapter.update_status() for global state

### Point 5: Canonical Promotion
- C7 produces CANONICAL_CANDIDATE advisory
- RAIOS authority decides promotion
- C7 never promotes directly
