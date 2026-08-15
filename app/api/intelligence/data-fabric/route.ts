import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { dataFabricCatalog, distributeFabricContext, type FabricConsumer, type FabricDomain } from "@/lib/intelligence/data-intelligence-fabric";

const consumers = new Set<FabricConsumer>(["GREENY_LIFE_EGYPT_BRAIN", "GREENS_NATURE_UAE_BRAIN", "GREEN_LINES_NORWAY_EU_BRAIN", "MASTERMIND_AI", "TRAINING_FACTORY"]);
const domains = new Set<FabricDomain>(["PRODUCT", "SUPPLIER", "INVENTORY", "SHIPMENT"]);

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.supplierMaster, "/api/intelligence/data-fabric", "READ_DATA_FABRIC");
  if (authorization.response) return authorization.response;
  const params = new URL(request.url).searchParams;
  const consumer = params.get("consumer")?.trim().toUpperCase() as FabricConsumer | undefined;
  if (!consumer) return NextResponse.json({ success: true, data: dataFabricCatalog() });
  if (!consumers.has(consumer)) return NextResponse.json({ success: false, error: "Unknown consumer." }, { status: 400 });
  const requested = params.getAll("domain").map((value) => value.trim().toUpperCase());
  if (requested.some((domain) => !domains.has(domain as FabricDomain))) return NextResponse.json({ success: false, error: "Unknown domain." }, { status: 400 });
  return NextResponse.json({ success: true, data: distributeFabricContext({ consumer, productId: params.get("productId")?.trim() || undefined, domains: requested as FabricDomain[] }) });
}