import { NextResponse } from "next/server";
import { egyptianExportPortfolio } from "@/lib/intelligence/portfolio-and-assets";

export async function GET() {
  try {
    return NextResponse.json({ success: true, data: egyptianExportPortfolio() });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to load Egyptian export portfolio", details: (error as Error).message }, { status: 500 });
  }
}
