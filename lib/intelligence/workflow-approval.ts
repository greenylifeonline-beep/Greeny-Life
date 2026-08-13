import { prisma } from "@/lib/prisma";
import type { OrderWorkflowState } from "@/lib/domain/order-workflow";

export const WORKFLOW_APPROVAL_TTL_MINUTES = 30;

export type WorkflowApprovalSnapshot = {
  id: string;
  orderId: string;
  targetState: string;
  requestedBy: string;
  approvedBy: string | null;
  status: string;
  expiresAt: Date;
  executedAt: Date | null;
};

export function assessWorkflowApproval(
  approval: WorkflowApprovalSnapshot | null,
  input: { orderId: string; targetState: OrderWorkflowState; now?: Date },
) {
  const now = input.now ?? new Date();
  if (!approval) return { eligible: false, reason: "A durable workflow approval was not found." } as const;
  if (approval.orderId !== input.orderId || approval.targetState !== input.targetState) return { eligible: false, reason: "The approval does not match this order and target state." } as const;
  if (approval.status !== "APPROVED") return { eligible: false, reason: "The approval is not in APPROVED state." } as const;
  if (!approval.approvedBy || approval.approvedBy === approval.requestedBy) return { eligible: false, reason: "Approval requires a distinct human approver." } as const;
  if (approval.executedAt) return { eligible: false, reason: "The approval has already been consumed." } as const;
  if (!(approval.expiresAt instanceof Date) || Number.isNaN(approval.expiresAt.getTime()) || approval.expiresAt <= now) return { eligible: false, reason: "The approval is expired or invalid." } as const;
  return { eligible: true, reason: "Durable approval is eligible for one controlled transition." } as const;
}

export async function findExecutableWorkflowApproval(input: { approvalId: string; orderId: string; targetState: OrderWorkflowState }) {
  const approval = await prisma.workflowApproval.findUnique({ where: { id: input.approvalId } });
  return assessWorkflowApproval(approval, input);
}