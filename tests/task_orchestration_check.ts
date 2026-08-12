import assert from "node:assert/strict";
import { createTaskContract, validateTaskTransition } from "../lib/intelligence/task-orchestration";

const task = createTaskContract({ taskType: "INVENTORY_REVIEW", ownerCompany: "GREENY_LIFE_EGYPT", subjectId: "H001", requestedBy: "verification", evidenceIds: ["canonical/inventory/stock-levels.json"] });
assert.equal(task.status, "REVIEW_REQUIRED");
assert.equal(task.executor, "LEGACY-ANALYZE_INVENTORY");
assert.ok(task.executionRule.includes("cannot create an order"));
assert.equal(createTaskContract({ taskType: "INVENTORY_REVIEW", ownerCompany: "GREENY_LIFE_EGYPT", subjectId: "H001", requestedBy: "verification", evidenceIds: ["canonical/inventory/stock-levels.json"] }).idempotencyKey, task.idempotencyKey);
assert.equal(validateTaskTransition({ current: "REVIEW_REQUIRED", target: "COMPLETED", dependenciesComplete: false, hasValidatedOutput: true }).allowed, false);
assert.equal(validateTaskTransition({ current: "REVIEW_REQUIRED", target: "VALIDATING", dependenciesComplete: true, hasValidatedOutput: false }).allowed, true);
console.log("Task orchestration core: PASS");