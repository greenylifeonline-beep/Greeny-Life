import assert from "node:assert/strict";
import { assessTaskInterestConflict, createTaskContract, detectTaskConflicts, validateTaskTransition } from "../lib/intelligence/task-orchestration";

const task = createTaskContract({ taskType: "INVENTORY_REVIEW", ownerCompany: "GREENY_LIFE_EGYPT", subjectId: "H001", requestedBy: "verification", evidenceIds: ["canonical/inventory/stock-levels.json"] });
assert.equal(task.status, "REVIEW_REQUIRED");
assert.equal(task.executor, "LEGACY-ANALYZE_INVENTORY");
assert.ok(task.executionRule.includes("cannot create an order"));
assert.equal(createTaskContract({ taskType: "INVENTORY_REVIEW", ownerCompany: "GREENY_LIFE_EGYPT", subjectId: "H001", requestedBy: "verification", evidenceIds: ["canonical/inventory/stock-levels.json"] }).idempotencyKey, task.idempotencyKey);
const maintenance = createTaskContract({ taskType: "SYSTEM_MAINTENANCE_REVIEW", ownerCompany: "MASTERMIND", subjectId: "current:commercial-data", requestedBy: "verification", evidenceIds: ["E4-SMART-CLEANER-CONTROL-PLANE"], payload: { scope: "DATA", intent: "CLASSIFY" } });
assert.equal(maintenance.executor, "E5_CONTINUOUS_ASSURANCE_CONTROL_PLANE");
assert.equal(maintenance.status, "REVIEW_REQUIRED");
assert.ok(maintenance.executionRule.includes("cannot create an order"));
assert.equal(validateTaskTransition({ current: "REVIEW_REQUIRED", target: "COMPLETED", dependenciesComplete: false, hasValidatedOutput: true }).allowed, false);
assert.equal(validateTaskTransition({ current: "REVIEW_REQUIRED", target: "VALIDATING", dependenciesComplete: true, hasValidatedOutput: false }).allowed, true);
const taskConflicts = detectTaskConflicts([
  { id: "A", taskType: "SYSTEM_MAINTENANCE_REVIEW", ownerCompany: "MASTERMIND", subjectId: "component:x", requestedBy: "a@greeny.life", idempotencyKey: "same", status: "REVIEW_REQUIRED", dependsOn: [] },
  { id: "B", taskType: "SYSTEM_MAINTENANCE_REVIEW", ownerCompany: "MASTERMIND", subjectId: "component:x", requestedBy: "b@greeny.life", idempotencyKey: "same", status: "REVIEW_REQUIRED", dependsOn: ["B"] },
]);
assert.ok(taskConflicts.some((item) => item.kind === "DUPLICATE_TASK"));
assert.ok(taskConflicts.some((item) => item.kind === "SELF_DEPENDENCY"));
assert.equal(assessTaskInterestConflict({ requestedBy: "owner@greeny.life", proposedApprover: "OWNER@greeny.life" }).status, "BLOCKED_SELF_APPROVAL");
assert.equal(assessTaskInterestConflict({ requestedBy: "owner@greeny.life", proposedApprover: "approver@greeny.life" }).status, "DISTINCT_APPROVER_REQUIRED");
console.log("Task orchestration core: PASS");
