import { NextRequest, NextResponse } from "next/server";
import { PrismaClient } from "@prisma/client";

const prisma = new PrismaClient();

// GET: جلب أوامر البيع
export async function GET() {
  try {
    const orders = await prisma.salesOrder.findMany({
      include: {
        customer: true,
        market: true,
        items: {
          include: { product: true },
        },
      },
      orderBy: { createdAt: "desc" },
    });

    return NextResponse.json({ success: true, count: orders.length, data: orders });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to fetch sales orders", details: (error as Error).message },
      { status: 500 }
    );
  }
}

// POST: إنشاء أمر بيع جديد
export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { orderId, customerId, marketId, items } = body;

    let totalAmountUSD = 0;
    const orderItemsData = items.map((item: { productId: string; quantity: number; unitPriceUSD: number }) => {
      totalAmountUSD += item.quantity * item.unitPriceUSD;
      return {
        productId: item.productId,
        quantity: item.quantity,
        unitPriceUSD: item.unitPriceUSD,
      };
    });

    const newOrder = await prisma.$transaction(async (tx) => {
      return await tx.salesOrder.create({
        data: {
          orderId,
          customerId,
          marketId,
          totalAmountUSD,
          items: {
            create: orderItemsData,
          },
        },
        include: { items: true },
      });
    });

    return NextResponse.json({ success: true, data: newOrder }, { status: 201 });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to create sales order", details: (error as Error).message },
      { status: 400 }
    );
  }
}
