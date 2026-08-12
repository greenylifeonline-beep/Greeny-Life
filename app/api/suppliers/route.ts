import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;

export async function GET() {
  try {
    const suppliers = await prisma.supplier.findMany({ include: { entity: true, products: true }, orderBy: { createdAt: "desc" } });
    return NextResponse.json({ success: true, count: suppliers.length, data: suppliers });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to fetch suppliers", details: (error as Error).message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.supplierMaster, "/api/suppliers", "POST" );
  if (authorization.response) return authorization.response;
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const { entityId, supplierId, nameAr, nameEn, contactPerson, email, phone, country } = body;
    if (!text(entityId) || !text(supplierId) || !text(nameAr) || !text(nameEn)) {
      return NextResponse.json({ success: false, error: "entityId ÙˆsupplierId ÙˆnameAr ÙˆnameEn Ø­Ù‚ÙˆÙ„ Ù…Ø·Ù„ÙˆØ¨Ø©." }, { status: 400 });
    }
    const supplier = await prisma.supplier.create({
      data: {
        entityId: entityId.trim(), supplierId: supplierId.trim(), nameAr: nameAr.trim(), nameEn: nameEn.trim(),
        ...(text(contactPerson) ? { contactPerson: contactPerson.trim() } : {}), ...(text(email) ? { email: email.trim() } : {}), ...(text(phone) ? { phone: phone.trim() } : {}),
        country: text(country) ? country.trim() : "Egypt",
      },
      include: { entity: true },
    });
    return NextResponse.json({ success: true, data: supplier }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to create supplier", details: (error as Error).message }, { status: 400 });
  }
}

