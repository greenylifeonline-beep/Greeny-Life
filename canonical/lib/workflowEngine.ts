import { PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/prisma";

type WorkflowTransaction = Pick<PrismaClient, "salesOrder" | "auditLog">;

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

export class EOSWorkflowEngine {
  public static async transitionOrderState(
    orderId: string,
    targetState: OrderWorkflowState,
    userId: string
  ) {
    const order = await prisma.salesOrder.findUnique({
      where: { id: orderId },
      include: { items: true },
    });

    if (!order) throw new Error(`Order with ID ${orderId} not found.`);

    return prisma.$transaction(async (tx: WorkflowTransaction) => {
      const currentOrder = await tx.salesOrder.update({
        where: { id: orderId },
        data: { status: targetState },
      });
      await tx.auditLog.create({
        data: {
          orderId,
          action: `WORKFLOW_STATE_CHANGE_${targetState}`,
          actor: userId,
          details: { previousState: order.status, newState: targetState },
        },
      });
      return currentOrder;
    });
  }

  public static calculateLogisticsCost(
    itemsQuantity: number,
    basePrice: number,
    customsTariffRate: number,
    shippingFee: number
  ) {
    const subtotal = itemsQuantity * basePrice;
    const customsDuty = subtotal * (customsTariffRate / 100);
    return {
      subtotalUSD: subtotal,
      customsDutyUSD: customsDuty,
      shippingFeeUSD: shippingFee,
      totalCostUSD: subtotal + customsDuty + shippingFee,
    };
  }
}
