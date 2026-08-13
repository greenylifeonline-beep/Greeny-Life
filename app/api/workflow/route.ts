import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { NextRequest, NextResponse } from "next/server";
import { EOSWorkflowEngine, OrderWorkflowState } from "../../../canonical/lib/workflowEngine";
import { reviewWorkflowTransition } from "@/lib/intelligence/workflow-governance";
import { findExecutableWorkflowApproval } from "@/lib/intelligence/workflow-approval";

// POST: تغيير حالة الطلب وسير العمل
export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.workflow, "/api/workflow", "POST" );
  if (authorization.response) return authorization.response;
  const actorEmail = authorization.session!.email;
  try {
    const body = await request.json();
    const { orderId, targetState, approvalId } = body;

    if (!orderId || !targetState || !approvalId) {
      return NextResponse.json(
        { success: false, error: "Missing required fields: orderId, targetState, approvalId" },
        { status: 400 }
      );
    }

    // التحقق من صحة الحالة المرسلة
    if (!Object.values(OrderWorkflowState).includes(targetState)) {
      return NextResponse.json(
        { success: false, error: "Invalid target workflow state" },
        { status: 400 }
      );
    }

    const governance = await reviewWorkflowTransition({
      orderId: String(orderId).trim(),
      targetState: targetState as OrderWorkflowState,
      actor: actorEmail,
    });
    if (governance.status === "DENIED") {
      return NextResponse.json({ success: false, status: "DENIED", automaticExecution: false, governance: { correlationId: governance.correlationId, reason: governance.governanceReason } }, { status: 403 });
    }
    const approval = await findExecutableWorkflowApproval({ approvalId: String(approvalId).trim(), orderId: String(orderId).trim(), targetState: targetState as OrderWorkflowState });
    if (!approval.eligible) {
      return NextResponse.json({
        success: false, status: "REVIEW_REQUIRED", automaticExecution: false,
        governance: { correlationId: governance.correlationId, reason: governance.governanceReason },
        approval: { eligible: false, reason: approval.reason }, executionRule: governance.executionRule,
      }, { status: 202 });
    }
    const result = await EOSWorkflowEngine.transitionOrderState(String(orderId).trim(), targetState as OrderWorkflowState, actorEmail, String(approvalId).trim());

    return NextResponse.json({ success: true, data: result });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Workflow transition failed", details: (error as Error).message },
      { status: 500 }
    );
  }
}

// GET: حساب التكاليف اللوجستية والجمركية لعنصر أو شحنة
export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const required = ["qty", "price", "tariff", "shipping"] as const;
  if (required.some((key) => searchParams.get(key) === null)) {
    return NextResponse.json({ success: false, error: "qty, price, tariff, and shipping are required. No assumed tariff or shipping quote is used." }, { status: 400 });
  }
  const qty = parseFloat(searchParams.get("qty")!);
  const price = parseFloat(searchParams.get("price")!);
  const tariff = parseFloat(searchParams.get("tariff")!);
  const shipping = parseFloat(searchParams.get("shipping")!);

  try {
    const calculation = EOSWorkflowEngine.calculateLogisticsCost(qty, price, tariff, shipping);
    return NextResponse.json({
      success: true,
      status: "CALCULATION_ONLY",
      automaticExecution: false,
      parameters: { qty, price, tariff, shipping },
      calculation,
      evidenceRule: "All inputs are caller-supplied and unverified. This is not a customs, tax, shipping, or commercial quote.",
    });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: (error as Error).message },
      { status: 400 },
    );
  }
}
