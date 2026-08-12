import assert from "node:assert/strict";
import { evaluateCandidate, minimumBenchmarkCases, validateEvaluationInput } from "../lib/intelligence/evaluation-governance";

const cases = Array.from({ length: minimumBenchmarkCases }, (_, index) => `CASE-${index + 1}`);
const input = { candidateVersion: "candidate-v2", baselineVersion: "baseline-v1", trainingCaseIds: cases, metricScores: { decision_accuracy: 81, evidence_grounding: 98 }, actor: "verification" };
assert.deepEqual(validateEvaluationInput(input), []);
const evaluation = evaluateCandidate(input);
assert.equal(evaluation.score, 89.5);
assert.equal(evaluation.status, "REVIEW_REQUIRED");
assert.equal(evaluation.benchmarkReady, true);
assert.ok(evaluation.prohibited.includes("automatic promotion"));
const insufficient = evaluateCandidate({ ...input, trainingCaseIds: ["CASE-1"] });
assert.equal(insufficient.status, "INSUFFICIENT_BENCHMARK_CASES");
assert.ok(validateEvaluationInput({ ...input, metricScores: { bad: 101 } }).some((error) => error.includes("0 to 100")));
console.log("Evaluation governance: PASS");