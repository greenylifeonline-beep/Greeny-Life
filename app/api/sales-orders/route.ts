import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { finiteNumber as numeric, hasText as text, invalidRequest as invalid } from "@/lib/http-input";


export async function GET() {
  try {
    const orders = await prisma.salesOrder.findMany({
      include: { entity: true, customer: true, items: { include: { sku: { include: { product: true } } } } },
      orderBy: { createdAt: "desc" },
    });
    return NextResponse.json({ success: true, count: orders.length, data: orders });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to fetch sales orders", details: (error as Error).message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.salesOrder, "/api/sales-orders", "POST" );
  if (authorization.response) return authorization.response;
  try {
    const body = (await request.json()) as Record<string, unknown>;
    if (body.marketId !== undefined) return invalid("marketId Ù„Ø§ ÙŠÙ…Ù„Ùƒ Ù…Ù‚Ø§Ø¨Ù„Ø§Ù‹ ÙÙŠ Ø§Ù„Ù†Ù…ÙˆØ°Ø¬ Ø§Ù„Ù‚Ø§Ù†ÙˆÙ†ÙŠ Ø§Ù„Ø­Ø§Ù„ÙŠØ› Ù„Ø§ ÙŠÙ…ÙƒÙ† Ø­ÙØ¸Ù‡ Ø¨ØµÙ…Øª.");
    const orderCode = body.orderCode ?? body.orderId;
    const { entityId, customerId } = body;
    if (![orderCode, entityId, customerId].every(text)) return invalid("orderCode (Ø£Ùˆ orderId) ÙˆentityId ÙˆcustomerId Ø­Ù‚ÙˆÙ„ Ù…Ø·Ù„ÙˆØ¨Ø©.");
    if (!Array.isArray(body.items) || body.items.length === 0) return invalid("items ÙŠØ¬Ø¨ Ø£Ù† ØªÙƒÙˆÙ† Ù‚Ø§Ø¦Ù…Ø© ØºÙŠØ± ÙØ§Ø±ØºØ© Ù…Ù† Ø¹Ù†Ø§ØµØ± SKU.");

    if (!text(orderCode) || !text(entityId) || !text(customerId)) {
      return invalid("Invalid sales order payload.");
    }

    let totalAmount = 0;
    const lines: Array<{ skuId: string; quantity: number; unitPriceUSD: number; totalPriceUSD: number }> = [];
    for (const item of body.items as Array<Record<string, unknown>>) {
      if (!text(item.skuId)) return invalid("ÙƒÙ„ Ø¹Ù†ØµØ± ÙŠØ­ØªØ§Ø¬ skuIdØ› productId ÙˆØ­Ø¯Ù‡ Ù„Ø§ ÙŠØ­Ø¯Ø¯ SKU Ø¨Ø£Ù…Ø§Ù†.");
      const quantity = numeric(item.quantity);
      const unitPriceUSD = numeric(item.unitPriceUSD);
      if (quantity === null || !Number.isInteger(quantity) || quantity <= 0 || unitPriceUSD === null || unitPriceUSD < 0) return invalid("ÙƒÙ„ Ø¹Ù†ØµØ± ÙŠØ­ØªØ§Ø¬ quantity ØµØ­ÙŠØ­Ø§Ù‹ Ù…ÙˆØ¬Ø¨Ø§Ù‹ ÙˆunitPriceUSD ØºÙŠØ± Ø³Ø§Ù„Ø¨.");
      const totalPriceUSD = quantity * unitPriceUSD;
      totalAmount += totalPriceUSD;
      lines.push({ skuId: item.skuId.trim(), quantity, unitPriceUSD, totalPriceUSD });
    }
    const order = await prisma.salesOrder.create({
      data: {
        entityId: entityId.trim(), orderCode: orderCode.trim(), customerId: customerId.trim(),
        currency: text(body.currency) ? body.currency.trim() : "USD", totalAmount,
        ...(text(body.notes) ? { notes: body.notes.trim() } : {}), items: { create: lines },
      },
      include: { entity: true, customer: true, items: { include: { sku: { include: { product: true } } } } },
    });
    return NextResponse.json({ success: true, data: order }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to create sales order", details: (error as Error).message }, { status: 400 });
  }
}

