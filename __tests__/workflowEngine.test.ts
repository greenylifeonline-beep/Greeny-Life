import { describe, it, expect, vi, beforeEach } from "vitest";
import { EOSWorkflowEngine, OrderWorkflowState } from "@/lib/workflowEngine";

// محاكاة لـ Prisma Client لتجنب الاعتماد على قاعدة بيانات حية أثناء اختبارات الوحدة
vi.mock("@prisma/client", () => {
  return {
    PrismaClient: class {
      salesOrder = {
        findUnique: vi.fn().mockResolvedValue({
          id: "order-123",
          status: "CREATED",
          items: [{ productId: "p-1", quantity: 10, unitPriceUSD: 50 }]
        }),
        update: vi.fn().mockResolvedValue({
          id: "order-123",
          status: "IN_PRODUCTION",
          updatedAt: new Date()
        })
      };
      auditLog = {
        create: vi.fn().mockResolvedValue({ id: "log-1" })
      };
      $transaction = vi.fn(async (callback) => {
        return await callback({
          salesOrder: {
            update: vi.fn().mockResolvedValue({
              id: "order-123",
              status: "IN_PRODUCTION",
              updatedAt: new Date()
            })
          },
          auditLog: {
            create: vi.fn().mockResolvedValue({ id: "log-1" })
          }
        });
      });
    }
  };
});

describe("EOSWorkflowEngine Unit & Integration Tests", () => {
  
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("should calculate logistics and customs cost correctly", () => {
    // الكمية: 10، السعر: 100 دولار، نسبة الجمرك: 5%، الشحن: 50 دولار
    const result = EOSWorkflowEngine.calculateLogisticsCost(10, 100, 5, 50);

    expect(result.subtotalUSD).toBe(1000);         // 10 * 100
    expect(result.customsDutyUSD).toBe(50);        // 5% من 1000
    expect(result.shippingFeeUSD).toBe(50);      // 50 ثابت
    expect(result.totalCostUSD).toBe(1100);        // 1000 + 50 + 50
  });

  it("should transition order state successfully", async () => {
    const orderId = "order-123";
    const targetState = OrderWorkflowState.IN_PRODUCTION;
    const userId = "user-admin-1";

    const updatedOrder = await EOSWorkflowEngine.transitionOrderState(
      orderId, 
      targetState, 
      userId
    );

    expect(updatedOrder).toBeDefined();
    expect(updatedOrder.id).toBe(orderId);
  });

  it("should throw error if order does not exist during transition", async () => {
    // تعديل مؤقت للـ mock لإرجاع null
    const { PrismaClient } = await import("@prisma/client");
    const prismaMock = new (PrismaClient as any)();
    prismaMock.salesOrder.findUnique.mockResolvedValueOnce(null);

    await expect(
      EOSWorkflowEngine.transitionOrderState("non-existent", OrderWorkflowState.DELIVERED, "user-1")
    ).rejects.toThrow("Order with ID non-existent not found.");
  });

});
