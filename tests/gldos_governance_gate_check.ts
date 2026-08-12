import assert from "node:assert/strict";

import { GLDOSGovernanceGate } from "../canonical/intelligence/adapters/gl-dos-governance-gate";

const gate = new GLDOSGovernanceGate();

const evaluate = (riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL") =>
  gate.evaluate({
    operation: "test-operation",
    actor: "test-reviewer",
    correlationId: `test-${riskLevel}`,
    riskLevel,
  });

assert.equal(evaluate("LOW").decision, "REVIEW_REQUIRED");
assert.equal(evaluate("MEDIUM").decision, "REVIEW_REQUIRED");
assert.equal(evaluate("HIGH").decision, "REVIEW_REQUIRED");
assert.equal(evaluate("CRITICAL").decision, "DENIED");

console.log("GL-DOS governance gate: PASS");