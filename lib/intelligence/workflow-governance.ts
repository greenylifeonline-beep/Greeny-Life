import { ControlledRuntimeOrchestrator } from "@/canonical/intelligence/runtime/controlled-runtime-orchestrator";
import type { OrderWorkflowState } from "@/lib/domain/order-workflow";

export async function reviewWorkflowTransition(input: { orderId: string; targetState: OrderWorkflowState; actor: string }) {
  const governance = await new ControlledRuntimeOrchestrator().execute({
    operation: `workflow-transition:${input.targetState}`,
    actor: input.actor,
    riskLevel: "HIGH",
    input: { orderId: input.orderId, targetState: input.targetState },
  });
  return {
    ...governance,
    automaticExecution: false,
    executionRule: "An order-state transition is a controlled operational write. It requires an explicit, durable user approval record before the workflow engine may mutate the order.",
  };
}
