import { NextResponse } from "next/server";
import { assetAssimilationRegistry } from "@/lib/intelligence/portfolio-and-assets";

export async function GET() {
  try {
    return NextResponse.json({ success: true, data: assetAssimilationRegistry() });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to read asset registry", details: (error as Error).message }, { status: 500 });
  }
}
