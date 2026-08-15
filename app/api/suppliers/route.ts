import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { nullableText, supplierMasterAuthorityContract, supplierStatuses, supplierVerificationStatuses, validateSupplierTransition } from "@/lib/supplier-master-policy";
const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.supplierMaster, "/api/suppliers", "READ_SUPPLIER_MASTER");
  if (authorization.response) return authorization.response;
  try {
    const suppliers = await prisma.supplier.findMany({ include: { entity: true, products: true }, orderBy: { createdAt: "desc" } });
    return NextResponse.json({ success: true, count: suppliers.length, data: suppliers, authority: supplierMasterAuthorityContract });
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
      return NextResponse.json({ success: false, error: "entityId Ã™Ë†supplierId Ã™Ë†nameAr Ã™Ë†nameEn Ã˜Â­Ã™â€šÃ™Ë†Ã™â€ž Ã™â€¦Ã˜Â·Ã™â€žÃ™Ë†Ã˜Â¨Ã˜Â©." }, { status: 400 });
    }
    const supplier = await prisma.supplier.create({
      data: {
        entityId: entityId.trim(), supplierId: supplierId.trim(), nameAr: nameAr.trim(), nameEn: nameEn.trim(),
        ...(text(contactPerson) ? { contactPerson: contactPerson.trim() } : {}), ...(text(email) ? { email: email.trim() } : {}), ...(text(phone) ? { phone: phone.trim() } : {}),
        country: text(country) ? country.trim() : "Egypt",
        status: "PENDING_VERIFICATION", verificationStatus: "UNVERIFIED",
      },
      include: { entity: true },
    });
    return NextResponse.json({ success: true, data: supplier }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Failed to create supplier", details: (error as Error).message }, { status: 400 });
  }
}


export async function PATCH(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.supplierMaster, "/api/suppliers", "PATCH");
  if (authorization.response) return authorization.response;
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const has = (key: string) => Object.prototype.hasOwnProperty.call(body, key);
    const id = nullableText(body.id, has("id"), "id");
    const supplierId = nullableText(body.supplierId, has("supplierId"), "supplierId");
    if (!id && !supplierId) return NextResponse.json({ success: false, error: "id or supplierId is required." }, { status: 400 });
    const existing = await prisma.supplier.findFirst({ where: id ? { id } : { supplierId: supplierId! } });
    if (!existing) return NextResponse.json({ success: false, error: "Supplier not found." }, { status: 404 });
    const getText = (key: string) => nullableText(body[key], has(key), key);
    const status = getText("status"); const verificationStatus = getText("verificationStatus");
    if (status !== undefined && (status === null || !supplierStatuses.includes(status as typeof supplierStatuses[number]))) throw new Error("status is invalid.");
    if (verificationStatus !== undefined && (verificationStatus === null || !supplierVerificationStatuses.includes(verificationStatus as typeof supplierVerificationStatuses[number]))) throw new Error("verificationStatus is invalid.");
    const edit = { status: status as typeof supplierStatuses[number] | undefined, verificationStatus: verificationStatus as typeof supplierVerificationStatuses[number] | undefined, sourceUrl: getText("sourceUrl"), sourceReference: getText("sourceReference"), deactivationReason: getText("deactivationReason") };
    const result = validateSupplierTransition(existing, edit);
    const data: Record<string, unknown> = {};
    for (const field of ["nameAr", "nameEn", "contactPerson", "email", "phone", "country", "sourceUrl", "sourceReference", "deactivationReason"] as const) {
      const value = getText(field); if (value !== undefined) data[field] = value;
    }
    if (data.nameAr === null || data.nameEn === null || data.country === null) return NextResponse.json({ success: false, error: "nameAr, nameEn and country cannot be empty." }, { status: 400 });
    data.status = result.status; data.verificationStatus = result.verificationStatus; data.sourceUrl = result.sourceUrl; data.sourceReference = result.sourceReference;
    if (result.status === "INACTIVE") data.deactivatedAt = new Date();
    if (result.status !== "INACTIVE" && existing.status === "INACTIVE") { data.deactivatedAt = null; data.deactivationReason = null; }
    const supplier = await prisma.supplier.update({ where: { id: existing.id }, data: data as never, include: { entity: true } });
    return NextResponse.json({ success: true, data: supplier });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Supplier update rejected.", details: (error as Error).message }, { status: 400 });
  }
}

export async function DELETE(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.supplierMaster, "/api/suppliers", "DELETE_DEACTIVATE");
  if (authorization.response) return authorization.response;
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const id = text(body.id) ? body.id.trim() : "";
    const reason = text(body.reason) ? body.reason.trim() : "";
    if (!id || !reason) return NextResponse.json({ success: false, error: "id and deactivation reason are required." }, { status: 400 });
    const existing = await prisma.supplier.findUnique({ where: { id }, include: { products: { select: { id: true } } } });
    if (!existing) return NextResponse.json({ success: false, error: "Supplier not found." }, { status: 404 });
    const supplier = await prisma.supplier.update({ where: { id }, data: { status: "INACTIVE", deactivatedAt: new Date(), deactivationReason: reason }, include: { entity: true } });
    return NextResponse.json({ success: true, data: supplier, message: existing.products.length ? "Supplier deactivated; linked products preserved." : "Supplier deactivated." });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Supplier deactivation rejected.", details: (error as Error).message }, { status: 400 });
  }
}