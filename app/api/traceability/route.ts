import crypto from "crypto";

import { NextRequest, NextResponse } from "next/server";

import { ControlledRuntimeOrchestrator } from "@/canonical/intelligence/runtime/controlled-runtime-orchestrator";
import { initialOwnership, type TraceRecordInput, validateTraceRecord } from "@/lib/domain/trade-traceability";
import { findLegacyBatch, legacyBatchRegistry } from "@/lib/intelligence/legacy-batch-traceability";
import { prisma } from "@/lib/prisma";

interface TraceRow {
  id: string;
  traceCode: string;
  recordType: string;
  parentTraceCode: string | null;
  sourceParty: string;
  holderCompany: string;
  destinationParty: string | null;
  materialName: string;
  batchCode: string;
  quantity: number;
  unit: string;
  originCountry: string;
  processingCountry: string | null;
  status: string;
  ownershipHistory: unknown;
  evidence: unknown;
  correlationId: string;
  createdAt: Date;
  updatedAt: Date;
}

const stringValue = (value: unknown) => typeof value === "string" ? value.trim() : "";
const numberValue = (value: unknown) => typeof value === "number" ? value : Number(value);

export async function GET(request: NextRequest) {
  try {
    const params = new URL(request.url).searchParams;
    if (params.get("legacy") === "true") {
      return NextResponse.json({ success: true, data: legacyBatchRegistry() });
    }
    const traceCode = params.get("traceCode")?.trim();
    if (!traceCode) return NextResponse.json({ success: false, error: "traceCode is required; use legacy=true for the consolidated historical batch registry." }, { status: 400 });
    const [record] = await prisma.$queryRaw<TraceRow[]>`
      SELECT * FROM "TradeTraceRecord" WHERE "traceCode" = ${traceCode}
    `;
    if (!record) {
      const legacy = findLegacyBatch(traceCode);
      if (legacy) return NextResponse.json({ success: true, data: { record: legacy, descendants: [], sourceStatus: "HISTORICAL_REFERENCE_NOT_CURRENT_EVIDENCE" } });
      return NextResponse.json({ success: false, error: "Trace record not found." }, { status: 404 });
    }
    const descendants = await prisma.$queryRaw<TraceRow[]>`
      SELECT * FROM "TradeTraceRecord" WHERE "parentTraceCode" = ${traceCode} ORDER BY "createdAt" ASC
    `;
    return NextResponse.json({ success: true, data: { record, descendants } });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to read trace record", details: (error as Error).message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = (await request.json()) as Record<string, unknown>;
    const input: TraceRecordInput = {
      recordType: stringValue(body.recordType) as TraceRecordInput["recordType"],
      traceCode: stringValue(body.traceCode),
      parentTraceCode: stringValue(body.parentTraceCode) || undefined,
      sourceParty: stringValue(body.sourceParty),
      holderCompany: stringValue(body.holderCompany),
      destinationParty: stringValue(body.destinationParty) || undefined,
      materialName: stringValue(body.materialName),
      batchCode: stringValue(body.batchCode),
      quantity: numberValue(body.quantity),
      unit: stringValue(body.unit),
      originCountry: stringValue(body.originCountry),
      processingCountry: stringValue(body.processingCountry) || undefined,
      actor: stringValue(body.actor),
      evidence: body.evidence && typeof body.evidence === "object" && !Array.isArray(body.evidence) ? body.evidence as Record<string, unknown> : undefined,
    };
    const errors = validateTraceRecord(input);
    if (errors.length) return NextResponse.json({ success: false, errors }, { status: 400 });

    if (input.parentTraceCode) {
      const [parent] = await prisma.$queryRaw<Pick<TraceRow, "traceCode" | "holderCompany">[]>`
        SELECT "traceCode", "holderCompany" FROM "TradeTraceRecord" WHERE "traceCode" = ${input.parentTraceCode}
      `;
      if (!parent) return NextResponse.json({ success: false, error: "parentTraceCode does not exist." }, { status: 400 });
      if (parent.holderCompany !== input.holderCompany) return NextResponse.json({ success: false, error: "Only the current holding company may transform or plan re-export of a traced batch." }, { status: 403 });
    }

    const governance = await new ControlledRuntimeOrchestrator().execute({
      operation: `traceability:${input.recordType}`,
      actor: input.actor,
      riskLevel: "HIGH",
      input,
    });
    const id = crypto.randomUUID();
    await prisma.$executeRaw`
      INSERT INTO "TradeTraceRecord" (
        "id", "traceCode", "recordType", "parentTraceCode", "sourceParty", "holderCompany", "destinationParty",
        "materialName", "batchCode", "quantity", "unit", "originCountry", "processingCountry", "status",
        "ownershipHistory", "evidence", "correlationId", "createdAt", "updatedAt"
      ) VALUES (
        ${id}, ${input.traceCode}, ${input.recordType}, ${input.parentTraceCode ?? null}, ${input.sourceParty},
        ${input.holderCompany}, ${input.destinationParty ?? null}, ${input.materialName}, ${input.batchCode}, ${input.quantity},
        ${input.unit}, ${input.originCountry}, ${input.processingCountry ?? null}, ${"REVIEW_REQUIRED"},
        ${JSON.stringify(initialOwnership(input))}::jsonb, ${input.evidence ? JSON.stringify(input.evidence) : null}::jsonb,
        ${governance.correlationId}, NOW(), NOW()
      )
    `;
    const [record] = await prisma.$queryRaw<TraceRow[]>`SELECT * FROM "TradeTraceRecord" WHERE "id" = ${id}`;
    return NextResponse.json({
      success: true,
      governance: { status: governance.status, reason: governance.governanceReason },
      safety: "Trace recorded as REVIEW_REQUIRED. No shipment, customs filing, payment, or legal title transfer was executed.",
      data: record,
    }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to record traceability event", details: (error as Error).message }, { status: 400 });
  }
}
