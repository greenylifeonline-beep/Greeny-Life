import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest } from "@/lib/authz";
import { prisma } from "@/lib/prisma";
import { assessOfficialExportEvidence } from "@/lib/intelligence/official-evidence-gate";
import { mapPersistedOfficialEvidence } from "@/lib/intelligence/persisted-official-evidence";

function text(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
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
    const assessment = assessOfficialExportEvidence(stored.map(mapPersistedOfficialEvidence), product, destination);
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