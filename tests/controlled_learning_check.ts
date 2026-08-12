import assert from "node:assert/strict";
import { learningProposal, validateOutcomeInput } from "../lib/intelligence/controlled-learning";

const input = { decisionId: "DEC-001", contextId: "CTX-001", metric: "production_yield", expectedValue: 94, actualValue: 87, unit: "percent", observedAt: "2026-08-12T12:00:00.000Z", actor: "verification", evidenceIds: ["BATCH-001", "QC-001"] };
assert.deepEqual(validateOutcomeInput(input), []);
const proposal = learningProposal(input);
assert.equal(proposal.status, "REVIEW_REQUIRED");
assert.equal(proposal.material, true);
assert.equal(proposal.variance, -7);
assert.equal(proposal.variancePercent, -7.45);
assert.ok(proposal.prohibited.includes("automatic model update"));
assert.ok(validateOutcomeInput({ ...input, evidenceIds: [] }).some((error) => error.includes("evidence")));
console.log("Controlled learning: PASS");