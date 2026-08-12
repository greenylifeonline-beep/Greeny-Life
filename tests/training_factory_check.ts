import assert from "node:assert/strict";
import { buildTrainingCase, validateTrainingCaseInput } from "../lib/intelligence/training-factory";

const outcome = { id: "OUT-001", decisionId: "DEC-001", contextId: "CTX-001", metric: "production_yield", expectedValue: 94, actualValue: 87, variance: -7, variancePercent: -7.45, unit: "percent", evidenceIds: ["BATCH-001", "QC-001"] };
const input = { outcome, expectedDecision: "Release after verified QC", actualDecision: "Yield missed target", rootCause: "Root cause pending review", actor: "verification" };
assert.deepEqual(validateTrainingCaseInput(input), []);
const training = buildTrainingCase(input);
assert.equal(training.status, "REVIEW_REQUIRED");
assert.equal(training.learningSignal, "MATERIAL_VARIANCE");
assert.ok(training.trainingRule.includes("cannot train"));
assert.ok(training.promotionRule.includes("human reviewer"));
assert.ok(validateTrainingCaseInput({ ...input, expectedDecision: "" }).some((error) => error.includes("expectedDecision")));
console.log("Training factory: PASS");