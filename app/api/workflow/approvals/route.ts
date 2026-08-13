import crypto from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { prisma } from "@/lib/prisma";
import { OrderWorkflowState } from "@/lib/domain/order-workflow";
import { WORKFLOW_APPROVAL_TTL_MINUTES } from "@/lib/intelligence/workflow-approval";

function text(value: unknown) { return typeof value === "string" ? value.trim() : ""; }

// POST creates a review request only. It never changes an order state.
export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.workflow, "/api/workflow/approvals", "REQUEST_WORKFLOW_APPROVAL");
  if (authorization.response) return authorization.response;
  try {
    const body = await request.json();
    const orderId = text(body.orderId);
    const targetState = text(body.targetState);
    if (!orderId || !Object.values(OrderWorkflowState).includes(targetState as OrderWorkflowState)) {
      return NextResponse.json({ success: false, error: "A valid orderId and targetState are required." }, { status: 400 });
    }
    const now = new Date();
    const expiresAt = new Date(now.getTime() + WORKFLOW_APPROVAL_TTL_MINUTES * 60_000);
    const approval = await prisma.workflowApproval.create({
      data: {
        id: crypto.randomUUID(), orderId, targetState, requestedBy: authorization.session!.email,
        status: "PENDING_APPROVAL", expiresAt, correlationId: crypto.randomUUID(), createdAt: now, updatedAt: now,
      },
    });
    return NextResponse.json({
      success: true, data: approval,
      executionRule: "This is a request only. A distinct ADMIN must approve it before any workflow transition can be attempted.",
      automaticExecution: false,
    }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to create workflow approval request", details: (error as Error).message }, { status: 400 });
  }
}

// PATCH records a distinct ADMIN approval. It never changes an order state.
export async function PATCH(request: NextRequest) {
  const authorization = await authorizeRequest(request, ["ADMIN"], "/api/workflow/approvals", "APPROVE_WORKFLOW_TRANSITION");
  if (authorization.response) return authorization.response;
  try {
    const body = await request.json();
    const approvalId = text(body.approvalId);
    if (!approvalId) return NextResponse.json({ success: false, error: "approvalId is required." }, { status: 400 });
    const approval = await prisma.workflowApproval.findUnique({ where: { id: approvalId } });
    if (!approval) return NextResponse.json({ success: false, error: "Workflow approval request was not found." }, { status: 404 });
    if (approval.requestedBy === authorization.session!.email) return NextResponse.json({ success: false, error: "A requester cannot approve their own workflow transition." }, { status: 403 });
    if (approval.status !== "PENDING_APPROVAL" || approval.expiresAt <= new Date()) return NextResponse.json({ success: false, error: "Only an unexpired pending request may be approved." }, { status: 409 });
    const updated = await prisma.workflowApproval.update({
      where: { id: approval.id }, data: { status: "APPROVED", approvedBy: authorization.session!.email, approvedAt: new Date() },
    });
    return NextResponse.json({ success: true, data: updated, automaticExecution: false, executionRule: "Approval is one-time and must still pass the guarded workflow transition." });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to approve workflow transition", details: (error as Error).message }, { status: 400 });
  }
}