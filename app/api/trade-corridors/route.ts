import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { assessCorridor, companies, tradeGovernance, type CompanyId } from "@/lib/intelligence/trade-corridors";

const isCompany = (value: unknown): value is CompanyId => typeof value === "string" && value in companies;
const validTypes = new Set(["IMPORT", "EXPORT", "INTERCOMPANY_TRANSFER"]);

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.salesOrder, "/api/trade-corridors", "READ_TRADE_GOVERNANCE");
  if (authorization.response) return authorization.response;
  return NextResponse.json({ success: true, data: tradeGovernance() });
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.salesOrder, "/api/trade-corridors", "ASSESS_TRADE_CORRIDOR");
  if (authorization.response) return authorization.response;
  const actorEmail = authorization.session!.email;
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const tradeType = typeof body.tradeType === "string" ? body.tradeType.toUpperCase() : "";
    if (!isCompany(body.originCompany) || !isCompany(body.destinationCompany) || !validTypes.has(tradeType)) {
      return NextResponse.json({ success: false, error: "originCompany, destinationCompany and a valid tradeType are required." }, { status: 400 });
    }
    const data = await assessCorridor(body.originCompany, body.destinationCompany, tradeType, actorEmail, typeof body.productId === "string" ? body.productId.trim() : undefined);
    return NextResponse.json({ success: true, data }, { status: 201 });
  } catch (error) { return NextResponse.json({ success: false, error: "Unable to assess trade corridor", details: (error as Error).message }, { status: 400 }); }
}
