import assert from "node:assert/strict";
import { assessReadOnlyDecisionSafety, MASTERMIND_DECISION_POLICY } from "../lib/intelligence/mastermind-agents";

assert.equal(assessReadOnlyDecisionSafety({ confidence: 85, policy: MASTERMIND_DECISION_POLICY }).status, "REQUIRES_HUMAN_REVIEW");
assert.equal(assessReadOnlyDecisionSafety({ confidence: null, policy: MASTERMIND_DECISION_POLICY }).status, "NOT_READY");
assert.equal(assessReadOnlyDecisionSafety({ confidence: 69, policy: MASTERMIND_DECISION_POLICY }).status, "NOT_READY");
assert.equal(assessReadOnlyDecisionSafety({ confidence: 85 }).status, "NOT_READY");
assert.equal(assessReadOnlyDecisionSafety({ confidence: 85, policy: { ...MASTERMIND_DECISION_POLICY, automaticExecution: true } }).status, "NOT_READY");
console.log("Decision confidence/policy fail-closed: PASS");