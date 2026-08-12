import { NextRequest, NextResponse } from "next/server";

import { buildMasterMindDecisionPackage, type MasterMindRequest } from "@/lib/intelligence/mastermind-agents";
import { companies } from "@/lib/intelligence/trade-corridors";

const isCompany = (value: unknown): value is MasterMindRequest["originCompany"] => typeof value === "string" && value in companies;

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    if (typeof body.productId !== "string" || typeof body.destination !== "string" || typeof body.actor !== "string" || !isCompany(body.originCompany) || !isCompany(body.destinationCompany)) {
      return NextResponse.json({ success: false, error: "productId, destination, actor, originCompany and destinationCompany are required." }, { status: 400 });
    }
    const data = await buildMasterMindDecisionPackage({
      productId: body.productId.trim(),
      destination: body.destination.trim(),
      actor: body.actor.trim(),
      originCompany: body.originCompany,
      destinationCompany: body.destinationCompany,
      traceCode: typeof body.traceCode === "string" ? body.traceCode.trim() : undefined,
      eventType: typeof body.eventType === "string" ? body.eventType.trim() : undefined,
      customerId: typeof body.customerId === "string" ? body.customerId.trim() : undefined,
    });
    return NextResponse.json({ success: true, data }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to build MasterMind decision package", details: (error as Error).message }, { status: 400 });
  }
}
