import { NextRequest, NextResponse } from "next/server";

import { greenyLifeEgyptOperationalView } from "@/lib/intelligence/greeny-life-egypt-brain";

export async function GET(request: NextRequest) {
  const productId = new URL(request.url).searchParams.get("productId")?.trim() || undefined;
  return NextResponse.json({ success: true, data: greenyLifeEgyptOperationalView(productId) });
}
