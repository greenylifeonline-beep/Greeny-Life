import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import crypto from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { ControlledRuntimeOrchestrator } from "@/canonical/intelligence/runtime/controlled-runtime-orchestrator";
import { buildTrainingCase } from "@/lib/intelligence/training-factory";
import { prisma } from "@/lib/prisma";

interface OutcomeRow { id: string; decisionId: string; contextId: string; metric: string; expectedValue: number; actualValue: number; variance: number; variancePercent: number | null; unit: string; evidenceIds: unknown; }
interface TrainingRow { id: string; outcomeId: string; decisionId: string; contextId: string; metric: string; expectedDecision: string; actualDecision: string; rootCause: string | null; learningSignal: string; evidenceIds: unknown; status: string; recordedBy: string; correlationId: string; createdAt: Date; }
const text = (value: unknown) => typeof value === "string" ? value.trim() : "";

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.training, "/api/learning/training-cases", "READ_TRAINING_CASES");
  if (authorization.response) return authorization.response;
  try {
    const outcomeId = new URL(request.url).searchParams.get("outcomeId")?.trim();
    const rows = await prisma.$queryRaw<TrainingRow[]>`
      SELECT * FROM "TrainingCase"
      WHERE (${outcomeId ?? null}::text IS NULL OR "outcomeId" = ${outcomeId ?? null})
      ORDER BY "createdAt" DESC LIMIT 100
    `;
    return NextResponse.json({ success: true, count: rows.length, data: rows });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to read training cases", details: (error as Error).message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.training, "/api/learning/training-cases", "POST" );
  if (authorization.response) return authorization.response;
  const actorEmail = authorization.session!.email;
  try {
    const body = await request.json() as Record<string, unknown>;
    const outcomeId = text(body.outcomeId);
    if (!outcomeId) return NextResponse.json({ success: false, errors: ["outcomeId is required."] }, { status: 400 });
    const [outcome] = await prisma.$queryRaw<OutcomeRow[]>`SELECT * FROM "DecisionOutcome" WHERE "id" = ${outcomeId}`;
    if (!outcome) return NextResponse.json({ success: false, error: "Outcome record was not found." }, { status: 404 });
    const [existing] = await prisma.$queryRaw<Pick<TrainingRow, "id">[]>`SELECT "id" FROM "TrainingCase" WHERE "outcomeId" = ${outcomeId}`;
    if (existing) return NextResponse.json({ success: false, error: "A training case already exists for this outcome; it cannot be duplicated.", trainingCaseId: existing.id }, { status: 409 });
    const training = buildTrainingCase({ outcome, expectedDecision: text(body.expectedDecision), actualDecision: text(body.actualDecision), rootCause: text(body.rootCause) || undefined, actor: actorEmail });
    const governance = await new ControlledRuntimeOrchestrator().execute({ operation: "learning:create-training-case", actor: actorEmail, riskLevel: "MEDIUM", input: training });
    const id = crypto.randomUUID();
    await prisma.$executeRaw`
      INSERT INTO "TrainingCase" (
        "id", "outcomeId", "decisionId", "contextId", "metric", "expectedDecision", "actualDecision", "rootCause",
        "learningSignal", "evidenceIds", "status", "recordedBy", "correlationId", "createdAt"
      ) VALUES (
        ${id}, ${training.outcomeId}, ${training.decisionId}, ${training.contextId}, ${training.metric}, ${training.expectedDecision}, ${training.actualDecision}, ${training.rootCause},
        ${training.learningSignal}, ${JSON.stringify(training.evidenceIds)}::jsonb, ${training.status}, ${actorEmail}, ${governance.correlationId}, NOW()
      )
    `;
    const [record] = await prisma.$queryRaw<TrainingRow[]>`SELECT * FROM "TrainingCase" WHERE "id" = ${id}`;
    return NextResponse.json({ success: true, governance: { status: governance.status, reason: governance.governanceReason }, data: record, safety: training.trainingRule, promotionRule: training.promotionRule }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to create training case", details: (error as Error).message }, { status: 400 });
  }
}