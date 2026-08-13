import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest } from "@/lib/authz";
import { prisma } from "@/lib/prisma";
import {
  assessOfficialExportEvidence,
  type OfficialEvidenceRecord,
} from "@/lib/intelligence/official-evidence-gate";

function text(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

function mapRecord(row: {
  evidenceKey: string; product: string; destination: string; authority: string;
  verificationStatus: string; claimStatus: string; validTo: Date | null; gates: unknown; sourceUrl: string | null;
}): OfficialEvidenceRecord {
  return {
    id: row.evidenceKey,
    scope: { product: row.product, destination: row.destination },
    authority: ["official", "secondary", "internal", "unknown"].includes(row.authority) ? row.authority as OfficialEvidenceRecord["authority"] : "unknown",
    verificationStatus: ["verified_current", "unverified", "expired", "unknown"].includes(row.verificationStatus) ? row.verificationStatus as OfficialEvidenceRecord["verificationStatus"] : "unknown",
    claimStatus: ["supported", "prohibited", "unknown"].includes(row.claimStatus) ? row.claimStatus as OfficialEvidenceRecord["claimStatus"] : "unknown",
    validTo: row.validTo?.toISOString().slice(0, 10),
    gates: Array.isArray(row.gates) ? row.gates.filter((gate): gate is OfficialEvidenceRecord["gates"][number] =>
      ["country_eligibility", "establishment_listing", "official_certificate", "border_process", "importer_registration"].includes(String(gate)),
    ) : [],
    sourceUrl: row.sourceUrl ?? undefined,
  };
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(
    request, ["ADMIN", "EXPORT"], "/api/decisions/official-evidence-review", "OFFICIAL_EVIDENCE_REVIEW",
  );
  if (authorization.response) return authorization.response;
  if (!authorization.session) return NextResponse.json({ success: false, error: "Authenticated session is required." }, { status: 401 });
  try {
    const body = await request.json() as Record<string, unknown>;
    const product = text(body.product);
    const destination = text(body.destination);
    if (!product || !destination) return NextResponse.json({ success: false, error: "product and destination are required." }, { status: 400 });
    const stored = await prisma.officialEvidenceRegistry.findMany({ where: { product, destination }, orderBy: { updatedAt: "desc" } });
    const assessment = assessOfficialExportEvidence(stored.map(mapRecord), product, destination);
    return NextResponse.json({
      success: true,
      data: {
        product, destination, assessment,
        source: "OfficialEvidenceRegistry",
        evidenceRecordCount: stored.length,
        automaticExecution: false,
        nextAction: assessment.state === "SUPPORTED_BY_OFFICIAL_SOURCE"
          ? "Submit the package to an authorized human reviewer; commercial, quality, and operational gates remain separate."
          : "Do not execute. Resolve the evidence gaps or prohibition before resubmission.",
        reviewedBy: authorization.session.email,
      },
    });
  } catch {
    return NextResponse.json({ success: false, error: "Invalid evidence review request." }, { status: 400 });
  }
}