import { authorizeRequest } from "@/lib/authz";
import { NextRequest, NextResponse } from "next/server";
import { prisma } from "@/lib/prisma";
import { supplierMasterAuthorityContract } from "@/lib/supplier-master-policy";

const roles = ["ADMIN", "EXPORT", "SALES", "FINANCE", "WAREHOUSE", "VIEWER"] as const;

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, roles, "/api/data-control", "READ_COMMERCIAL_DATA_CONTROL");
  if (authorization.response) return authorization.response;
  try {
    const [products, suppliers, customers, changes] = await Promise.all([
      prisma.product.findMany({ select: { id: true, productId: true, nameAr: true, nameEn: true, category: true, createdAt: true, updatedAt: true, supplier: { select: { id: true, supplierId: true, nameEn: true, country: true } } }, orderBy: { updatedAt: "desc" }, take: 200 }),
      prisma.supplier.findMany({ select: { id: true, supplierId: true, nameAr: true, nameEn: true, country: true, email: true, phone: true, status: true, verificationStatus: true, sourceUrl: true, sourceReference: true, verificationExpiresAt: true, deactivatedAt: true, deactivationReason: true, createdAt: true, updatedAt: true }, orderBy: { updatedAt: "desc" }, take: 200 }),
      prisma.customer.findMany({ select: { id: true, customerCode: true, name: true, country: true, email: true, createdAt: true }, orderBy: { createdAt: "desc" }, take: 200 }),
      prisma.commercialChange.findMany({ select: { id: true, domain: true, subjectType: true, subjectId: true, changeType: true, status: true, riskLevel: true, source: true, payload: true, effectiveFrom: true, effectiveTo: true, requestedBy: true, createdAt: true }, orderBy: { createdAt: "desc" }, take: 200 }),
    ]);
    return NextResponse.json({
      success: true,
      data: { products, suppliers, customers, commercialChanges: changes },
      policy: {
        operatingRule: "Current records may be temporary. Changes are proposed with source, owner and validity; they are not applied silently.",
        deletionRule: "Related master data is deactivated or archived through a controlled change; history is not hard-deleted.",
        authorityRule: "Only an authenticated role may read this workspace. Only ADMIN may propose commercial master-data changes.",
      },
      authority: { supplierMaster: supplierMasterAuthorityContract },
    });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to load commercial data control", details: (error as Error).message }, { status: 500 });
  }
}
