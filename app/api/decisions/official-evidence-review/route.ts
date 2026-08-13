import { NextRequest, NextResponse } from "next/server";
import { authorizeRequest } from "@/lib/authz";
import {
  assessOfficialExportEvidence,
  type OfficialEvidenceRecord,
} from "@/lib/intelligence/official-evidence-gate";

function text(value: unknown) {
  return typeof value === "string" ? value.trim() : "";
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(
    request,
    ["ADMIN", "EXPORT"],
    "/api/decisions/official-evidence-review",
    "OFFICIAL_EVIDENCE_REVIEW",
  );
  if (authorization.response) return authorization.response;
  if (!authorization.session) {
    return NextResponse.json({ success: false, error: "Authenticated session is required." }, { status: 401 });
  }

  try {
    const body = await request.json() as Record<string, unknown>;
    const product = text(body.product);
    const destination = text(body.destination);
    const evidence = Array.isArray(body.evidence) ? body.evidence as OfficialEvidenceRecord[] : null;
    if (!product || !destination || !evidence) {
      return NextResponse.json({ success: false, error: "product, destination, and evidence[] are required." }, { status: 400 });
    }
    const assessment = assessOfficialExportEvidence(evidence, product, destination);
    return NextResponse.json({
      success: true,
      data: {
        product,
        destination,
        assessment,
        automaticExecution: false,
        nextAction: assessment.state === "SUPPORTED_BY_OFFICIAL_SOURCE"
          ? "Submit the package to an authorized human reviewer; commercial, quality, and operational gates remain separate."
          : "Do not execute. Resolve the evidence gaps or prohibition before resubmission.",
        reviewedBy: authorization.session.email,
      },
    });
  } catch {
    return NextResponse.json({ success: false, error: "Invalid JSON request." }, { status: 400 });
  }
}