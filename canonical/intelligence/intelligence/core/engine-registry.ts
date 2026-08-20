export type EngineStatus = "ACTIVE" | "DISABLED" | "DEPRECATED";

export interface EngineDefinition {
  name: string;
  capability: string;
  version: string;
  status: EngineStatus;
  location: string;
}

/** Live keepers only. Historical duplicate-engine/cleanup-engine paths are not capabilities. */
export const ENGINE_REGISTRY: EngineDefinition[] = [
  {
    name: "audit-engine",
    capability: "canonical_product_audit",
    version: "1.0",
    status: "ACTIVE",
    location: "canonical/intelligence/intelligence/engines/audit-engine.ts",
  },
  {
    name: "data-integrity-engine",
    capability: "canonical_data_integrity",
    version: "1.0",
    status: "ACTIVE",
    location: "canonical/intelligence/intelligence/engines/data-integrity-engine.ts",
  },
  {
    name: "EOSWorkflowEngine",
    capability: "order_workflow_transition",
    version: "1.0",
    status: "ACTIVE",
    location: "canonical/lib/workflowEngine.ts",
  },
  {
    name: "ControlledRuntimeOrchestrator",
    capability: "governance_gated_runtime",
    version: "1.0",
    status: "ACTIVE",
    location: "canonical/intelligence/runtime/controlled-runtime-orchestrator.ts",
  },
  {
    name: "task-orchestration",
    capability: "task_orchestration_review_only",
    version: "1.0",
    status: "ACTIVE",
    location: "lib/intelligence/task-orchestration.ts",
  },
];

export function getActiveEngines() {
  return ENGINE_REGISTRY.filter((engine) => engine.status === "ACTIVE");
}

export function findEngine(name: string) {
  return ENGINE_REGISTRY.find((engine) => engine.name === name);
}
