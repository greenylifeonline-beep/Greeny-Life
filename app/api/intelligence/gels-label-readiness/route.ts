import { NextRequest, NextResponse } from "next/server";
import { evaluateGelsLabel, type BatchLabelEvidence, type GelsMarket } from "@/lib/intelligence/gels-label-readiness";

const markets = new Set<GelsMarket>(["EGYPT", "GCC", "EU", "USA", "ASIA"]);
const text = (value: unknown) => typeof value === "string" ? value.trim() : "";

export async function GET(request: NextRequest) {
  const params = new URL(request.url).searchParams;
  const productId = params.get("productId")?.trim();
  const market = params.get("market")?.trim().toUpperCase() as GelsMarket;
  if (!productId || !markets.has(market)) return NextResponse.json({ success: false, error: "productId and market (EGYPT, GCC, EU, USA, ASIA) are required." }, { status: 400 });
  return NextResponse.json({ success: true, data: evaluateGelsLabel({ productId, market }) });
}

export async function POST(request: NextRequest) {
  const body = await request.json() as Record<string, unknown>;
  const productId = text(body.productId); const market = text(body.market).toUpperCase() as GelsMarket;
  if (!productId || !markets.has(market)) return NextResponse.json({ success: false, error: "productId and valid market are required." }, { status: 400 });
  const batch: BatchLabelEvidence = body.batch && typeof body.batch === "object" && !Array.isArray(body.batch) ? body.batch as BatchLabelEvidence : {};
  return NextResponse.json({ success: true, data: evaluateGelsLabel({ productId, market, batch }) });
}