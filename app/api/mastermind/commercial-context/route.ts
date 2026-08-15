import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest, writeRolePolicy } from "@/lib/authz";

import { commercialContextSummary } from "@/lib/intelligence/commercial-context-fabric";

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.salesOrder, "/api/mastermind/commercial-context", "READ_COMMERCIAL_CONTEXT");
  if (authorization.response) return authorization.response;
  return NextResponse.json({ success: true, data: commercialContextSummary() });
}
