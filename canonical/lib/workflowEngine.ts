import { PrismaClient } from "@prisma/client";
import { prisma } from "@/lib/prisma";
import { assertOrderTransition, calculateLandedCost, OrderWorkflowState } from "@/lib/domain/order-workflow";

type WorkflowTransaction = Pick<PrismaClient, "salesOrder" | "auditLog" | "workflowApproval">;

export { OrderWorkflowState } from "@/lib/domain/order-workflow";

export class EOSWorkflowEngine {
  public static async transitionOrderState(
    orderId: string,
    targetState: OrderWorkflowState,
    userId: string,
    approvalId: string,
  ) {
    return prisma.$transaction(async (tx: WorkflowTransaction) => {
      const order = await tx.salesOrder.findUnique({ where: { id: orderId } });
      if (!order) throw new Error(`Order with ID ${orderId} not found.`);
      assertOrderTransition(order.status, targetState);

      const approval = await tx.workflowApproval.findUnique({ where: { id: approvalId } });
      if (!approval || approval.requestedBy === approval.approvedBy) {
        throw new Error("A distinct human approval is required before any state transition.");
      }
      const consumed = await tx.workflowApproval.updateMany({
        where: {
          id: approvalId, orderId, targetState, status: "APPROVED", executedAt: null,
          approvedBy: { not: null }, expiresAt: { gt: new Date() },
        },
        data: { status: "EXECUTING" },
      });
      if (consumed.count !== 1) throw new Error("A matching unexpired workflow approval is required before any state transition.");

      const currentOrder = await tx.salesOrder.update({ where: { id: orderId }, data: { status: targetState } });
      await tx.auditLog.create({
        data: { orderId, action: `WORKFLOW_STATE_CHANGE_${targetState}`, actor: userId, details: { previousState: order.status, newState: targetState, approvalId } },
      });
      await tx.workflowApproval.update({ where: { id: approvalId }, data: { status: "EXECUTED", executedAt: new Date() } });
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
