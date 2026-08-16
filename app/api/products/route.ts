import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { finiteNumber as numeric, hasText as text, invalidRequest as invalid } from "@/lib/http-input";


// Product and SKU are distinct canonical models. A SKU is created only with complete SKU data.
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    if (searchParams.get("categoryId")) return invalid("categoryId ليس حقلاً قانونياً؛ استخدم category.");
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
    if (unsupported.length) return invalid(`حقول قديمة بلا مقابل قانوني: ${unsupported.join(", ")}.`);

    const { productId, nameAr, nameEn, category, supplierId, barcode, marketRules } = body;
    const skuCode = body.skuCode ?? body.sku;
    if (![productId, nameAr, nameEn, category, supplierId].every(text)) return invalid("productId وnameAr وnameEn وcategory وsupplierId حقول مطلوبة.");
    if (marketRules !== undefined && (marketRules === null || Array.isArray(marketRules) || typeof marketRules !== "object")) {
      return invalid("marketRules يجب أن يكون كائناً JSON.");
    }
    const canonicalMarketRules = marketRules === undefined ? undefined : JSON.parse(JSON.stringify(marketRules));
    if (skuCode !== undefined && !text(skuCode)) return invalid("skuCode (أو sku) يجب أن يكون نصاً غير فارغ.");

    if (!text(productId) || !text(nameAr) || !text(nameEn) || !text(category) || !text(supplierId)) {
      return invalid("Invalid product payload.");
    }

    const hasSku = text(skuCode);
    const unitPriceUSD = numeric(body.unitPriceUSD);
    const weightKg = numeric(body.weightKg);
    if (hasSku && (unitPriceUSD === null || unitPriceUSD < 0 || weightKg === null || weightKg <= 0)) {
      return invalid("إنشاء SKU يتطلب unitPriceUSD غير سالب وweightKg موجباً.");
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

