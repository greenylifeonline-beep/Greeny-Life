import { NextResponse } from "next/server";
import { productionReadinessReport } from "@/lib/intelligence/production-readiness";

export async function GET() {
  return NextResponse.json({ success: true, data: productionReadinessReport() });
}