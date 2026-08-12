import assert from "node:assert/strict";

import { reviewWorkflowTransition } from "../lib/intelligence/workflow-governance";
import { OrderWorkflowState } from "../lib/domain/order-workflow";

async function main() {
  const review = await reviewWorkflowTransition({ orderId: "test-order", targetState: OrderWorkflowState.PENDING_SUPPLIER, actor: "test-reviewer" });
  assert.equal(review.status, "REVIEW_REQUIRED");
  assert.equal(review.automaticExecution, false);
  assert.ok(review.executionRule.includes("durable user approval"));
  console.log("Workflow governance: PASS");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });
