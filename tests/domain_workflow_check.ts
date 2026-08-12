import assert from "node:assert/strict";

import {
  assertOrderTransition,
  calculateLandedCost,
  OrderWorkflowState,
} from "../lib/domain/order-workflow";

assert.doesNotThrow(() => assertOrderTransition(OrderWorkflowState.CREATED, OrderWorkflowState.PENDING_SUPPLIER));
assert.throws(
  () => assertOrderTransition(OrderWorkflowState.CREATED, OrderWorkflowState.DELIVERED),
  /not permitted/,
);
assert.throws(
  () => assertOrderTransition("UNKNOWN", OrderWorkflowState.CREATED),
  /unknown workflow state/,
);
assert.deepEqual(calculateLandedCost(10, 12, 5, 20), {
  subtotalUSD: 120,
  customsDutyUSD: 6,
  shippingFeeUSD: 20,
  totalCostUSD: 146,
});
assert.throws(() => calculateLandedCost(0, 12, 5, 20), /positive whole number/);
assert.throws(() => calculateLandedCost(1, 12, 101, 20), /between 0 and 100/);

console.log("Domain workflow rules: PASS");
