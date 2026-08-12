import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { NextRequest, NextResponse } from "next/server";
import { EOSWorkflowEngine, OrderWorkflowState } from "../../../canonical/lib/workflowEngine";
import { reviewWorkflowTransition } from "@/lib/intelligence/workflow-governance";

// POST: تغيير حالة الطلب وسير العمل
export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.workflow, "/api/workflow", "POST" );
  if (authorization.response) return authorization.response;
  const actorEmail = authorization.session!.email;
  try {
    const body = await request.json();
    const { orderId, targetState } = body;

    if (!orderId || !targetState) {
      return NextResponse.json(
        { success: false, error: "Missing required fields: orderId, targetState" },
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
    if (governance.status !== "AUTHORIZED") {
      return NextResponse.json({
        success: false,
        status: governance.status,
        automaticExecution: false,
        governance: { correlationId: governance.correlationId, reason: governance.governanceReason },
        executionRule: governance.executionRule,
      }, { status: 202 });
    }
    const result = await EOSWorkflowEngine.transitionOrderState(orderId, targetState as OrderWorkflowState, actorEmail);

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
