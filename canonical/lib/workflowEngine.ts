import { PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/prisma";
import { assertOrderTransition, calculateLandedCost, OrderWorkflowState } from "@/lib/domain/order-workflow";

type WorkflowTransaction = Pick<PrismaClient, "salesOrder" | "auditLog">;

export { OrderWorkflowState } from "@/lib/domain/order-workflow";

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
    assertOrderTransition(order.status, targetState);

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
    return calculateLandedCost(itemsQuantity, basePrice, customsTariffRate, shippingFee);
  }
}
