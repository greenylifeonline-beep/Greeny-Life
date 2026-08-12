import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;
const numeric = (value: unknown): number | null => {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim() !== "" && Number.isFinite(Number(value))) return Number(value);
  return null;
};
const invalid = (error: string) => NextResponse.json({ success: false, error }, { status: 400 });

// Product and SKU are distinct canonical models. A SKU is created only with complete SKU data.
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    if (searchParams.get("categoryId")) return invalid("categoryId Ù„ÙŠØ³ Ø­Ù‚Ù„Ø§Ù‹ Ù‚Ø§Ù†ÙˆÙ†ÙŠØ§Ù‹Ø› Ø§Ø³ØªØ®Ø¯Ù… category.");
    const category = searchParams.get("category");
    const products = await prisma.product.findMany({
      where: category ? { category } : {},
      include: { supplier: true, skus: { include: { packaging: true } } },
      orderBy: { createdAt: "desc" },
    });
    return NextResponse.json({ success: true, count: products.length, data: products });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to fetch products", details: (error as Error).message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.productMaster, "/api/products", "POST" );
  if (authorization.response) return authorization.response;
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const unsupported = ["categoryId", "packagingProfileId", "hsCode"].filter((key) => body[key] !== undefined);
    if (unsupported.length) return invalid(`Ø­Ù‚ÙˆÙ„ Ù‚Ø¯ÙŠÙ…Ø© Ø¨Ù„Ø§ Ù…Ù‚Ø§Ø¨Ù„ Ù‚Ø§Ù†ÙˆÙ†ÙŠ: ${unsupported.join(", ")}.`);

    const { productId, nameAr, nameEn, category, supplierId, barcode, marketRules } = body;
    const skuCode = body.skuCode ?? body.sku;
    if (![productId, nameAr, nameEn, category, supplierId].every(text)) return invalid("productId ÙˆnameAr ÙˆnameEn Ùˆcategory ÙˆsupplierId Ø­Ù‚ÙˆÙ„ Ù…Ø·Ù„ÙˆØ¨Ø©.");
    if (marketRules !== undefined && (marketRules === null || Array.isArray(marketRules) || typeof marketRules !== "object")) {
      return invalid("marketRules ÙŠØ¬Ø¨ Ø£Ù† ÙŠÙƒÙˆÙ† ÙƒØ§Ø¦Ù†Ø§Ù‹ JSON.");
    }
    const canonicalMarketRules = marketRules === undefined ? undefined : JSON.parse(JSON.stringify(marketRules));
    if (skuCode !== undefined && !text(skuCode)) return invalid("skuCode (Ø£Ùˆ sku) ÙŠØ¬Ø¨ Ø£Ù† ÙŠÙƒÙˆÙ† Ù†ØµØ§Ù‹ ØºÙŠØ± ÙØ§Ø±Øº.");

    if (!text(productId) || !text(nameAr) || !text(nameEn) || !text(category) || !text(supplierId)) {
      return invalid("Invalid product payload.");
    }

    const hasSku = text(skuCode);
    const unitPriceUSD = numeric(body.unitPriceUSD);
    const weightKg = numeric(body.weightKg);
    if (hasSku && (unitPriceUSD === null || unitPriceUSD < 0 || weightKg === null || weightKg <= 0)) {
      return invalid("Ø¥Ù†Ø´Ø§Ø¡ SKU ÙŠØªØ·Ù„Ø¨ unitPriceUSD ØºÙŠØ± Ø³Ø§Ù„Ø¨ ÙˆweightKg Ù…ÙˆØ¬Ø¨Ø§Ù‹.");
    }

    const product = await prisma.product.create({
      data: {
        productId: productId.trim(), nameAr: nameAr.trim(), nameEn: nameEn.trim(),
        category: category.trim(), supplierId: supplierId.trim(),
        ...(canonicalMarketRules === undefined ? {} : { marketRules: canonicalMarketRules }),
        ...(hasSku ? { skus: { create: { skuCode: skuCode.trim(), ...(text(barcode) ? { barcode: barcode.trim() } : {}), unitPriceUSD: unitPriceUSD!, weightKg: weightKg! } } } : {}),
      },
      include: { supplier: true, skus: { include: { packaging: true } } },
    });
    return NextResponse.json({ success: true, data: product }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to create product", details: (error as Error).message }, { status: 400 });
  }
}

