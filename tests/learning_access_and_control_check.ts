import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const outcomes = readFileSync("app/api/learning/outcomes/route.ts", "utf8");
const training = readFileSync("app/api/learning/training-cases/route.ts", "utf8");
const evaluations = readFileSync("app/api/learning/evaluations/route.ts", "utf8");
const controlled = readFileSync("lib/intelligence/controlled-learning.ts", "utf8");
const factory = readFileSync("lib/intelligence/training-factory.ts", "utf8");
const governance = readFileSync("lib/intelligence/evaluation-governance.ts", "utf8");

assert.ok(outcomes.includes('"READ_DECISION_OUTCOMES"'));
assert.ok(training.includes('"READ_TRAINING_CASES"'));
assert.ok(evaluations.includes('"READ_EVALUATION_RUNS"'));
assert.ok(!training.includes('const actor = text(body.actor);'));
assert.ok(training.includes('actor: actorEmail, riskLevel: "MEDIUM"'));
assert.ok(controlled.includes('automatic model update'));
assert.ok(factory.includes('cannot train, promote, deploy, or modify'));
assert.ok(governance.includes('No evaluation can promote, deploy, replace, or modify'));
console.log("learning_access_and_control_check: PASS");