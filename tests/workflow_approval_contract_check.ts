import assert from "node:assert/strict";
import { assessWorkflowApproval } from "../lib/intelligence/workflow-approval";
import { OrderWorkflowState } from "../lib/domain/order-workflow";

const now = new Date("2026-08-13T12:00:00.000Z");
const valid = { id: "approval-1", orderId: "order-1", targetState: OrderWorkflowState.PENDING_SUPPLIER, requestedBy: "requester@greeny-life.local", approvedBy: "admin@greeny-life.local", status: "APPROVED", expiresAt: new Date("2026-08-13T12:30:00.000Z"), executedAt: null };
const input = { orderId: "order-1", targetState: OrderWorkflowState.PENDING_SUPPLIER, now };

assert.equal(assessWorkflowApproval(valid, input).eligible, true);
assert.equal(assessWorkflowApproval(null, input).eligible, false);
assert.equal(assessWorkflowApproval({ ...valid, status: "PENDING_APPROVAL" }, input).eligible, false);
assert.equal(assessWorkflowApproval({ ...valid, approvedBy: valid.requestedBy }, input).eligible, false);
assert.equal(assessWorkflowApproval({ ...valid, expiresAt: new Date("2026-08-13T11:59:59.000Z") }, input).eligible, false);
assert.equal(assessWorkflowApproval({ ...valid, executedAt: now }, input).eligible, false);
assert.equal(assessWorkflowApproval({ ...valid, targetState: OrderWorkflowState.CONFIRMED }, input).eligible, false);
console.log("workflow_approval_contract_check: PASS");