import { NextRequest, NextResponse } from "next/server";
import { buildExportDecision } from "@/lib/intelligence/export-decision";

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const productId = searchParams.get("productId")?.trim();
  const destination = searchParams.get("destination")?.trim();
  if (!productId || !destination) {
    return NextResponse.json({ success: false, error: "productId and destination are required." }, { status: 400 });
  }
  try {
    return NextResponse.json({ success: true, data: buildExportDecision(productId, destination) });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to build decision package", details: (error as Error).message }, { status: 500 });
  }
}
