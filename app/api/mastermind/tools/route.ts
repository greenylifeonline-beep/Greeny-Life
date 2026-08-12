import { NextResponse } from "next/server";

import { toolRegistry } from "@/lib/intelligence/tool-registry";

export async function GET() {
  return NextResponse.json({ success: true, data: toolRegistry() });
}
