import { describe, it, expect, vi, beforeEach } from "vitest";
import { EOSWorkflowEngine, OrderWorkflowState } from "../lib/workflowEngine";

const findUniqueMock = vi.fn();
const updateMock = vi.fn();
const auditCreateMock = vi.fn();
const transactionMock = vi.fn(async (callback) => {
  return await callback({
    salesOrder: { update: updateMock },
    auditLog: { create: auditCreateMock }
  });
});

vi.mock("@prisma/client", () => {
  return {
    PrismaClient: class {
      salesOrder = {
        findUnique: (...args: any[]) => findUniqueMock(...args),
        update: (...args: any[]) => updateMock(...args)
      };
      auditLog = {
        create: (...args: any[]) => auditCreateMock(...args)
      };
      $transaction = (...args: any[]) => transactionMock(...args);
    }
  };
});

describe("EOSWorkflowEngine Unit & Integration Tests", () => {
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should calculate logistics and customs cost correctly", () => {
    const result = EOSWorkflowEngine.calculateLogisticsCost(10, 100, 5, 50);

    expect(result.subtotalUSD).toBe(1000);
    expect(result.customsDutyUSD).toBe(50);
    expect(result.shippingFeeUSD).toBe(50);
    expect(result.totalCostUSD).toBe(1100);
  });

  it("should transition order state successfully", async () => {
    findUniqueMock.mockResolvedValueOnce({
      id: "order-123",
      status: "CREATED",
      items: [{ productId: "p-1", quantity: 10, unitPriceUSD: 50 }]
    });
    updateMock.mockResolvedValueOnce({
      id: "order-123",
      status: "IN_PRODUCTION",
      updatedAt: new Date()
    });

    const updatedOrder = await EOSWorkflowEngine.transitionOrderState(
      "order-123", 
      OrderWorkflowState.IN_PRODUCTION, 
      "user-admin-1"
    );

    expect(updatedOrder).toBeDefined();
    expect(updatedOrder.id).toBe("order-123");
  });

  it("should throw error if order does not exist during transition", async () => {
    // إرجاع null خصيصاً لهذا الاختبار لضمان رمي الخطأ
    findUniqueMock.mockResolvedValueOnce(null);

    await expect(
      EOSWorkflowEngine.transitionOrderState("non-existent", OrderWorkflowState.DELIVERED, "user-1")
    ).rejects.toThrow("Order with ID non-existent not found.");
  });

});
