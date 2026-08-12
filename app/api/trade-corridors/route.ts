import { NextRequest, NextResponse } from "next/server";
import { assessCorridor, companies, tradeGovernance, type CompanyId } from "@/lib/intelligence/trade-corridors";

const isCompany = (value: unknown): value is CompanyId => typeof value === "string" && value in companies;
const validTypes = new Set(["IMPORT", "EXPORT", "INTERCOMPANY_TRANSFER"]);

export async function GET() { return NextResponse.json({ success: true, data: tradeGovernance() }); }

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const tradeType = typeof body.tradeType === "string" ? body.tradeType.toUpperCase() : "";
    if (!isCompany(body.originCompany) || !isCompany(body.destinationCompany) || typeof body.actor !== "string" || !body.actor.trim() || !validTypes.has(tradeType)) {
      return NextResponse.json({ success: false, error: "originCompany, destinationCompany, actor and a valid tradeType are required." }, { status: 400 });
    }
    const data = await assessCorridor(body.originCompany, body.destinationCompany, tradeType, body.actor.trim(), typeof body.productId === "string" ? body.productId.trim() : undefined);
    return NextResponse.json({ success: true, data }, { status: 201 });
  } catch (error) { return NextResponse.json({ success: false, error: "Unable to assess trade corridor", details: (error as Error).message }, { status: 400 }); }
}
