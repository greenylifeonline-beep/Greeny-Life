export enum OrderWorkflowState {
  CREATED = "CREATED",
  PENDING_SUPPLIER = "PENDING_SUPPLIER",
  IN_PRODUCTION = "IN_PRODUCTION",
  SHIPPED_FROM_SUPPLIER = "SHIPPED_FROM_SUPPLIER",
  CUSTOMS_CLEARANCE = "CUSTOMS_CLEARANCE",
  IN_WAREHOUSE = "IN_WAREHOUSE",
  DELIVERED = "DELIVERED",
  CANCELLED = "CANCELLED",
}

const allowedTransitions: Record<OrderWorkflowState, readonly OrderWorkflowState[]> = {
  [OrderWorkflowState.CREATED]: [OrderWorkflowState.PENDING_SUPPLIER, OrderWorkflowState.CANCELLED],
  [OrderWorkflowState.PENDING_SUPPLIER]: [OrderWorkflowState.IN_PRODUCTION, OrderWorkflowState.CANCELLED],
  [OrderWorkflowState.IN_PRODUCTION]: [OrderWorkflowState.SHIPPED_FROM_SUPPLIER, OrderWorkflowState.CANCELLED],
  [OrderWorkflowState.SHIPPED_FROM_SUPPLIER]: [OrderWorkflowState.CUSTOMS_CLEARANCE, OrderWorkflowState.CANCELLED],
  [OrderWorkflowState.CUSTOMS_CLEARANCE]: [OrderWorkflowState.IN_WAREHOUSE, OrderWorkflowState.CANCELLED],
  [OrderWorkflowState.IN_WAREHOUSE]: [OrderWorkflowState.DELIVERED, OrderWorkflowState.CANCELLED],
  [OrderWorkflowState.DELIVERED]: [],
  [OrderWorkflowState.CANCELLED]: [],
};

export function assertOrderTransition(current: string, target: OrderWorkflowState) {
  if (!Object.values(OrderWorkflowState).includes(current as OrderWorkflowState)) {
    throw new Error(`Order has an unknown workflow state: ${current}. Manual review is required.`);
  }
  if (!allowedTransitions[current as OrderWorkflowState].includes(target)) {
    throw new Error(`Transition from ${current} to ${target} is not permitted.`);
  }
}

export function calculateLandedCost(
  itemsQuantity: number,
  basePrice: number,
  customsTariffRate: number,
  shippingFee: number,
) {
  if (!Number.isInteger(itemsQuantity) || itemsQuantity <= 0) {
    throw new Error("itemsQuantity must be a positive whole number.");
  }
  if (!Number.isFinite(basePrice) || basePrice < 0) {
    throw new Error("basePrice must be a non-negative finite number.");
  }
  if (!Number.isFinite(customsTariffRate) || customsTariffRate < 0 || customsTariffRate > 100) {
    throw new Error("customsTariffRate must be between 0 and 100.");
  }
  if (!Number.isFinite(shippingFee) || shippingFee < 0) {
    throw new Error("shippingFee must be a non-negative finite number.");
  }

  const subtotalUSD = itemsQuantity * basePrice;
  const customsDutyUSD = subtotalUSD * (customsTariffRate / 100);
  return {
    subtotalUSD,
    customsDutyUSD,
    shippingFeeUSD: shippingFee,
    totalCostUSD: subtotalUSD + customsDutyUSD + shippingFee,
  };
}

export const workflowTransitions = allowedTransitions;
