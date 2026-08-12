import { NextResponse } from "next/server";

import { commercialContextSummary } from "@/lib/intelligence/commercial-context-fabric";

export async function GET() {
  return NextResponse.json({ success: true, data: commercialContextSummary() });
}
