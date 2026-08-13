import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import crypto from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { ControlledRuntimeOrchestrator } from "@/canonical/intelligence/runtime/controlled-runtime-orchestrator";
import { learningProposal, type OutcomeInput, validateOutcomeInput } from "@/lib/intelligence/controlled-learning";
import { prisma } from "@/lib/prisma";

interface OutcomeRow {
  id: string; decisionId: string; contextId: string; metric: string;
  expectedValue: number; actualValue: number; variance: number; variancePercent: number | null;
  unit: string; status: string; evidenceIds: unknown; notes: string | null; observedAt: Date;
  recordedBy: string; correlationId: string; createdAt: Date;
}
const text = (value: unknown) => typeof value === "string" ? value.trim() : "";
const numeric = (value: unknown) => typeof value === "number" ? value : Number(value);

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.outcome, "/api/learning/outcomes", "READ_DECISION_OUTCOMES");
  if (authorization.response) return authorization.response;
  try {
    const decisionId = new URL(request.url).searchParams.get("decisionId")?.trim();
    const rows = await prisma.$queryRaw<OutcomeRow[]>`
      SELECT * FROM "DecisionOutcome"
      WHERE (${decisionId ?? null}::text IS NULL OR "decisionId" = ${decisionId ?? null})
      ORDER BY "createdAt" DESC LIMIT 100
    `;
    return NextResponse.json({ success: true, count: rows.length, data: rows });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to read decision outcomes", details: (error as Error).message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.outcome, "/api/learning/outcomes", "POST" );
  if (authorization.response) return authorization.response;
  const actorEmail = authorization.session!.email;
  try {
    const body = await request.json() as Record<string, unknown>;
    const input: OutcomeInput = {
      decisionId: text(body.decisionId), contextId: text(body.contextId), metric: text(body.metric),
      expectedValue: numeric(body.expectedValue), actualValue: numeric(body.actualValue), unit: text(body.unit),
      observedAt: text(body.observedAt), actor: actorEmail,
      evidenceIds: Array.isArray(body.evidenceIds) ? body.evidenceIds.filter((item): item is string => typeof item === "string").map((item) => item.trim()) : [],
      notes: text(body.notes) || undefined,
    };
    const errors = validateOutcomeInput(input);
    if (errors.length) return NextResponse.json({ success: false, errors }, { status: 400 });
    const governance = await new ControlledRuntimeOrchestrator().execute({ operation: "learning:record-outcome", actor: actorEmail, riskLevel: "MEDIUM", input });
    const proposal = learningProposal(input);
    const id = crypto.randomUUID();
    await prisma.$executeRaw`
      INSERT INTO "DecisionOutcome" (
        "id", "decisionId", "contextId", "metric", "expectedValue", "actualValue", "variance", "variancePercent",
        "unit", "status", "evidenceIds", "notes", "observedAt", "recordedBy", "correlationId", "createdAt"
      ) VALUES (
        ${id}, ${input.decisionId}, ${input.contextId}, ${input.metric}, ${input.expectedValue}, ${input.actualValue}, ${proposal.variance}, ${proposal.variancePercent},
        ${input.unit}, ${proposal.status}, ${JSON.stringify(input.evidenceIds)}::jsonb, ${input.notes ?? null}, ${new Date(input.observedAt)}, ${input.actor}, ${governance.correlationId}, NOW()
      )
    `;
    const [record] = await prisma.$queryRaw<OutcomeRow[]>`SELECT * FROM "DecisionOutcome" WHERE "id" = ${id}`;
    return NextResponse.json({ success: true, governance: { status: governance.status, reason: governance.governanceReason }, data: record, learning: proposal, safety: "Outcome recorded for review only. No model, policy, master data, workflow, supplier, price, shipment, payment, or customs action was changed." }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to record decision outcome", details: (error as Error).message }, { status: 400 });
  }
}