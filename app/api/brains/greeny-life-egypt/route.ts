import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest, writeRolePolicy } from "@/lib/authz";

import { greenyLifeEgyptOperationalView } from "@/lib/intelligence/greeny-life-egypt-brain";

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.salesOrder, "/api/brains/greeny-life-egypt", "READ_EGYPT_OPERATIONAL_VIEW");
  if (authorization.response) return authorization.response;
  const productId = new URL(request.url).searchParams.get("productId")?.trim() || undefined;
  return NextResponse.json({ success: true, data: greenyLifeEgyptOperationalView(productId) });
}
