import crypto from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest } from "@/lib/authz";
import { prisma } from "@/lib/prisma";
import { isOfficialEvidenceSourceUrl } from "@/lib/intelligence/official-evidence-gate";

const value = (input: unknown) => typeof input === "string" ? input.trim() : "";
const allowedGates = new Set(["country_eligibility", "establishment_listing", "official_certificate", "border_process", "importer_registration"]);

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, ["ADMIN", "EXPORT"], "/api/evidence/official", "READ_OFFICIAL_EVIDENCE");
  if (authorization.response) return authorization.response;
  const params = new URL(request.url).searchParams;
  const product = params.get("product")?.trim();
  const destination = params.get("destination")?.trim();
  const rows = await prisma.officialEvidenceRegistry.findMany({
    where: { ...(product ? { product } : {}), ...(destination ? { destination } : {}) },
    orderBy: { updatedAt: "desc" }, take: 200,
  });
  return NextResponse.json({ success: true, count: rows.length, data: rows });
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, ["ADMIN", "EXPORT"], "/api/evidence/official", "SUBMIT_OFFICIAL_EVIDENCE");
  if (authorization.response) return authorization.response;
  const session = authorization.session!;
  try {
    const body = await request.json() as Record<string, unknown>;
    const product=value(body.product), destination=value(body.destination), sourceTitle=value(body.sourceTitle), sourceUrl=value(body.sourceUrl);
    const requestedGates=Array.isArray(body.gates) ? body.gates.filter((gate): gate is string => typeof gate === "string" && allowedGates.has(gate)) : [];
    if(!product || !destination || !sourceTitle || !sourceUrl || !requestedGates.length) return NextResponse.json({success:false,error:"product, destination, sourceTitle, sourceUrl, and at least one valid gate are required."},{status:400});
    if(!isOfficialEvidenceSourceUrl(sourceUrl)) return NextResponse.json({success:false,error:"sourceUrl must be a valid HTTP(S) URL."},{status:400});
    const record=await prisma.officialEvidenceRegistry.create({data:{
      evidenceKey:"EV-"+crypto.randomUUID().slice(0,8).toUpperCase(), product, destination, sourceTitle, sourceUrl,
      sourceExcerpt:value(body.sourceExcerpt) || null, gates:requestedGates, authority:"unknown", verificationStatus:"unverified",
      claimStatus:"unknown", submittedBy:session.email
    }});
    return NextResponse.json({success:true,data:record,safety:"Submitted evidence is unverified and cannot authorize execution."},{status:201});
  } catch { return NextResponse.json({success:false,error:"Invalid evidence submission."},{status:400}); }
}

export async function PATCH(request: NextRequest) {
  const authorization = await authorizeRequest(request, ["ADMIN"], "/api/evidence/official", "VERIFY_OFFICIAL_EVIDENCE");
  if (authorization.response) return authorization.response;
  const session = authorization.session!;
  try {
    const body=await request.json() as Record<string,unknown>;
    const id=value(body.id), authority=value(body.authority), verificationStatus=value(body.verificationStatus), claimStatus=value(body.claimStatus);
    if(!id || !["official","secondary","internal","unknown"].includes(authority) || !["verified_current","unverified","expired","unknown"].includes(verificationStatus) || !["supported","prohibited","unknown"].includes(claimStatus)) return NextResponse.json({success:false,error:"id and valid authority, verificationStatus, and claimStatus are required."},{status:400});
    const validTo=value(body.validTo);
    const record=await prisma.officialEvidenceRegistry.update({where:{id},data:{
      authority, verificationStatus, claimStatus, validTo:validTo ? new Date(validTo) : null,
      reviewNotes:value(body.reviewNotes) || null, reviewedBy:session.email, reviewedAt:new Date()
    }});
    return NextResponse.json({success:true,data:record,safety:"Verification records evidence review only; it never executes a trade operation."});
  } catch { return NextResponse.json({success:false,error:"Evidence record was not found or verification input was invalid."},{status:400}); }
}