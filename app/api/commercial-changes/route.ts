import { NextRequest, NextResponse } from "next/server";
import crypto from "crypto";

import { ControlledRuntimeOrchestrator } from "@/canonical/intelligence/runtime/controlled-runtime-orchestrator";
import { prisma } from "@/lib/prisma";

const nonEmptyText = (value: unknown): value is string =>
  typeof value === "string" && value.trim().length > 0;

const riskLevels = new Set(["LOW", "MEDIUM", "HIGH", "CRITICAL"]);
const reviewDomains = new Set(["PRICE", "SUPPLIER", "SHIPMENT"]);

interface CommercialChangeRow {
  id: string;
  domain: string;
  subjectType: string;
  subjectId: string;
  changeType: string;
  status: string;
  riskLevel: string;
  source: string;
  payload: unknown;
  rationale: string | null;
  effectiveFrom: Date | null;
  effectiveTo: Date | null;
  requestedBy: string;
  reviewedBy: string | null;
  reviewedAt: Date | null;
  correlationId: string;
  createdAt: Date;
  updatedAt: Date;
}

function jsonError(error: string, status = 400) {
  return NextResponse.json({ success: false, error }, { status });
}

function requiredRisk(domain: string, submittedRisk: string) {
  if (submittedRisk === "CRITICAL") return "CRITICAL";
  if (reviewDomains.has(domain)) return "HIGH";
  return submittedRisk;
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const domain = searchParams.get("domain")?.trim().toUpperCase();
    const subjectId = searchParams.get("subjectId")?.trim();
    const status = searchParams.get("status")?.trim().toUpperCase();

    const changes = await prisma.$queryRaw<CommercialChangeRow[]>`
      SELECT * FROM "CommercialChange"
      WHERE (${domain}::text IS NULL OR "domain" = ${domain})
        AND (${subjectId}::text IS NULL OR "subjectId" = ${subjectId})
        AND (${status}::text IS NULL OR "status" = ${status})
      ORDER BY "createdAt" DESC
      LIMIT 100
    `;

    return NextResponse.json({ success: true, count: changes.length, data: changes });
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to fetch commercial changes", details: (error as Error).message },
      { status: 500 },
    );
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const { domain, subjectType, subjectId, changeType, source, payload, requestedBy } = body;
    const submittedRisk = typeof body.riskLevel === "string" ? body.riskLevel.trim().toUpperCase() : "MEDIUM";

    if (
      !nonEmptyText(domain) ||
      !nonEmptyText(subjectType) ||
      !nonEmptyText(subjectId) ||
      !nonEmptyText(changeType) ||
      !nonEmptyText(source) ||
      !nonEmptyText(requestedBy)
    ) {
      return jsonError("domain, subjectType, subjectId, changeType, source, and requestedBy are required.");
    }
    if (!riskLevels.has(submittedRisk)) return jsonError("riskLevel must be LOW, MEDIUM, HIGH, or CRITICAL.");
    if (payload === null || Array.isArray(payload) || typeof payload !== "object") {
      return jsonError("payload must be a JSON object.");
    }

    const normalizedDomain = domain.trim().toUpperCase();
    const riskLevel = requiredRisk(normalizedDomain, submittedRisk);
    const governance = await new ControlledRuntimeOrchestrator().execute({
      operation: `commercial-change:${normalizedDomain}:${changeType.trim().toUpperCase()}`,
      actor: requestedBy.trim(),
      riskLevel: riskLevel as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
      input: payload,
    });

    const status = governance.status === "AUTHORIZED" ? "APPROVED" : governance.status;
    const id = crypto.randomUUID();
    const rationale = nonEmptyText(body.rationale) ? body.rationale.trim() : null;
    const effectiveFrom = nonEmptyText(body.effectiveFrom) ? new Date(body.effectiveFrom) : null;
    const effectiveTo = nonEmptyText(body.effectiveTo) ? new Date(body.effectiveTo) : null;
    if ((effectiveFrom && Number.isNaN(effectiveFrom.valueOf())) || (effectiveTo && Number.isNaN(effectiveTo.valueOf()))) {
      return jsonError("effectiveFrom and effectiveTo must be valid ISO dates.");
    }
    const reviewedBy = status === "APPROVED" ? "GL-DOS" : null;
    const reviewedAt = status === "APPROVED" ? new Date() : null;
    await prisma.$executeRaw`
      INSERT INTO "CommercialChange" (
        "id", "domain", "subjectType", "subjectId", "changeType", "status", "riskLevel", "source",
        "payload", "rationale", "effectiveFrom", "effectiveTo", "requestedBy", "reviewedBy", "reviewedAt",
        "correlationId", "createdAt", "updatedAt"
      ) VALUES (
        ${id}, ${normalizedDomain}, ${subjectType.trim().toUpperCase()}, ${subjectId.trim()},
        ${changeType.trim().toUpperCase()}, ${status}, ${riskLevel}, ${source.trim()},
        ${JSON.stringify(payload)}::jsonb, ${rationale}, ${effectiveFrom}, ${effectiveTo}, ${requestedBy.trim()},
        ${reviewedBy}, ${reviewedAt}, ${governance.correlationId}, NOW(), NOW()
      )
    `;
    const [change] = await prisma.$queryRaw<CommercialChangeRow[]>`
      SELECT * FROM "CommercialChange" WHERE "id" = ${id}
    `;

    return NextResponse.json(
      {
        success: true,
        governance: { status: governance.status, reason: governance.governanceReason },
        data: change,
      },
      { status: governance.status === "DENIED" ? 403 : 201 },
    );
  } catch (error) {
    return NextResponse.json(
      { success: false, error: "Failed to record commercial change", details: (error as Error).message },
      { status: 400 },
    );
  }
}
