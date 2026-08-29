import assert from "node:assert/strict";
import { pathToFileURL } from "node:url";
import path from "node:path";

const repo = path.resolve(import.meta.dirname, "..", "..");
const mod = await import(pathToFileURL(path.join(repo, "lib", "intelligence", "training-factory.ts")).href);
const { buildTrainingCase, validateTrainingCaseInput } = mod;

const outcome = {
  id: "OUT-001",
  decisionId: "DEC-001",
  contextId: "CTX-001",
  metric: "production_yield",
  expectedValue: 94,
  actualValue: 87,
  variance: -7,
  variancePercent: -7.45,
  unit: "percent",
  evidenceIds: ["BATCH-001", "QC-001"],
};
const input = {
  outcome,
  expectedDecision: "Release after verified QC",
  actualDecision: "Yield missed target",
  rootCause: "Root cause pending review",
  actor: "verification",
};

assert.deepEqual(validateTrainingCaseInput(input), []);
const training = buildTrainingCase(input);
assert.equal(training.status, "REVIEW_REQUIRED");
assert.equal(training.learningSignal, "MATERIAL_VARIANCE");
assert.match(training.trainingRule, /cannot train/i);
assert.match(training.promotionRule, /human reviewer/i);
assert.ok(validateTrainingCaseInput({ ...input, expectedDecision: "" }).some((x) => x.includes("expectedDecision")));

console.log(JSON.stringify({
  factory: "TRAINING_FACTORY",
  status: "PASS",
  runner: "NODE_NATIVE_TYPESCRIPT",
  external_dependency: false,
  auto_train: false,
  auto_promote: false,
}));
