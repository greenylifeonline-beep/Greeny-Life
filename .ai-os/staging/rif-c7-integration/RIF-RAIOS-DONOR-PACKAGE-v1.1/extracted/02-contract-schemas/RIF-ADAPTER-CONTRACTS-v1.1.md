# RIF Adapter Contracts v1.1

## Design Principle
These are interfaces/contracts, NOT new backends. No implementation assumes ownership of WAL, NATS, MCP, UCP, RKG, canonical state, evidence database, or policy authority.

## 1. CanonicalFingerprintProvider

```
interface CanonicalFingerprintProvider {
  canonicalize(object: Any) -> CanonicalForm
  fingerprint(object: Any) -> Fingerprint
  schema_version() -> String
  algorithm_id() -> String
  verify(object: Any, fingerprint: Fingerprint) -> Boolean
}
```

- Provided by RAIOS during integration
- C7 tests inject deterministic fake for sandbox isolation
- No C7 implementation claims canonical authority

## 2. EvidenceStoreAdapter

```
interface EvidenceStoreAdapter {
  store(evidence: Evidence) -> EvidenceReference
  retrieve(reference: EvidenceReference) -> Evidence
  query(criteria: EvidenceQuery) -> EvidenceCollection
  lineage(evidence_id: String) -> LineageChain
  exists(evidence_id: String) -> Boolean
}
```

- Wraps existing RAIOS evidence store
- C7 ClaimGraph is logical view over this adapter
- No second evidence store created

## 3. TrustLatticeAdapter

```
interface TrustLatticeAdapter {
  evaluate_trust(source_id: String, evidence_type: String) -> TrustAssessment
  get_lattice_state() -> LatticeSnapshot
  register_source(source: SourceDescriptor) -> Boolean
  revoke_source(source_id: String) -> Boolean
}
```

- Integrates with existing RAIOS trust lattice
- Provides source trust assessments for evidence evaluation

## 4. WALAdapter

```
interface WALAdapter {
  append(entry: WALEntry) -> WALReference
  read_since(position: WALPosition) -> WALEntryCollection
  checkpoint() -> WALPosition
  recover(from_position: WALPosition) -> StateSnapshot
}
```

- Wraps existing WAL adapter (reuse per TREE-001)
- C7 governor decisions logged through this adapter
- No direct WAL writes from C7

## 5. ControlPlaneAdapter

```
interface ControlPlaneAdapter {
  register_evaluation(evaluation: EvaluationContext) -> TaskReference
  update_status(task_id: String, status: EvaluationStatus) -> Boolean
  request_authority(decision: AuthorityRequest) -> AuthorityResponse
  get_global_state() -> GlobalStateSnapshot
}
```

- Wraps UCP (reuse per TREE-001)
- C7 evaluation state machine reports to UCP
- C7 does NOT own global task authority

## 6. SemanticResolverAdapter

```
interface SemanticResolverAdapter {
  resolve(concept: String, context: ResolutionContext) -> SemanticBinding
  validate_contract(contract: SemanticContract) -> ValidationResult
  get_concept_set_hash() -> Hash
}
```

- Wraps NeuroLingua (reuse per TREE-001)
- Resolves semantic contracts to evaluation contexts

## 7. PolicyAdapter

```
interface PolicyAdapter {
  evaluate_policy(risk_assessment: RiskAssessment) -> PolicyDecision
  get_active_policies(scope: PolicyScope) -> PolicyCollection
  register_policy_event(event: PolicyEvent) -> Boolean
}
```

- Wraps existing RAIOS policy authority
- C7 risk assessment feeds into this adapter
- C7 is NOT policy authority

## 8. ObservabilitySinkAdapter

```
interface ObservabilitySinkAdapter {
  emit_event(event: ObservabilityEvent) -> Boolean
  emit_span(span: ObservabilitySpan) -> Boolean
  emit_metric(metric: Metric) -> Boolean
}
```

- Wraps existing RAIOS observability infrastructure
- C7 ObservabilityLogger is client to this adapter
- No second provenance store created

## 9. ModelEcologyAdapter

```
interface ModelEcologyAdapter {
  list_available_models(criteria: ModelCriteria) -> ModelCollection
  get_model_metadata(model_id: String) -> ModelMetadata
  validate_model_role(model_id: String, role: ModelRole) -> ValidationResult
}
```

- Wraps RKG/Model Ecology (reuse per TREE-001)
- M001 uses this adapter for model discovery
- No direct model ownership

## 10. ModelFactoryAdapter

```
interface ModelFactoryAdapter {
  request_model_instance(request: ModelInstanceRequest) -> ModelInstanceReference
  release_model_instance(reference: ModelInstanceReference) -> Boolean
  get_factory_status() -> FactoryStatus
}
```

- Wraps Model Factory (reuse per TREE-001)
- M001 spec references this adapter
- No model download/deployment/training in C7

## 11. MCPToolAdapter

```
interface MCPToolAdapter {
  discover_tools() -> ToolCollection
  invoke_tool(tool_id: String, parameters: Map) -> ToolResult
  validate_tool_schema(tool_id: String) -> SchemaValidation
}
```

- Wraps MCP (reuse per TREE-001)
- Tool invocation goes through this adapter

## 12. TransportAdapter

```
interface TransportAdapter {
  send(message: TransportMessage) -> DeliveryReceipt
  receive(filter: TransportFilter) -> TransportMessageCollection
  subscribe(topic: String, handler: MessageHandler) -> Subscription
}
```

- Wraps NATS (reuse per TREE-001)
- No direct NATS publish from C7
