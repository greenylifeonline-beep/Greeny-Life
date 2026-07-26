import { NextRequest, NextResponse } from "next/server";
import { EOSWorkflowEngine, OrderWorkflowState } from "@/lib/workflowEngine";

// POST: تغيير حالة الطلب وسير العمل
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { orderId, targetState, userId } = body;

    if (!orderId || !targetState || !userId) {
      return NextResponse.json(
        { success: false, error: "Missing required fields: orderId, targetState, userId" },
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

    const result = await EOSWorkflowEngine.transitionOrderState(
      orderId, 
      targetState as OrderWorkflowState, 
      userId
    );

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
  const qty = parseFloat(searchParams.get("qty") || "0");
  const price = parseFloat(searchParams.get("price") || "0");
  const tariff = parseFloat(searchParams.get("tariff") || "5"); // نسبة الجمرك الافتراضية
  const shipping = parseFloat(searchParams.get("shipping") || "50"); // رسوم الشحن الثابتة

  const calculation = EOSWorkflowEngine.calculateLogisticsCost(qty, price, tariff, shipping);

  return NextResponse.json({
    success: true,
    parameters: { qty, price, tariff, shipping },
    calculation
  });
}
