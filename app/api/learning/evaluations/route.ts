import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { Prisma } from "@prisma/client";
import crypto from "crypto";
import { NextRequest, NextResponse } from "next/server";
import { ControlledRuntimeOrchestrator } from "@/canonical/intelligence/runtime/controlled-runtime-orchestrator";
import { evaluateCandidate, type EvaluationInput, validateEvaluationInput } from "@/lib/intelligence/evaluation-governance";
import { prisma } from "@/lib/prisma";

interface TrainingRow { id: string; status: string; }
interface EvaluationRow { id: string; evaluationKey: string; candidateVersion: string; baselineVersion: string | null; trainingCaseIds: unknown; metricScores: unknown; score: number; status: string; notes: string | null; recordedBy: string; correlationId: string; createdAt: Date; }
const text = (value: unknown) => typeof value === "string" ? value.trim() : "";

function inputFrom(body: Record<string, unknown>): EvaluationInput {
  const rawScores = body.metricScores && typeof body.metricScores === "object" && !Array.isArray(body.metricScores) ? body.metricScores as Record<string, unknown> : {};
  return {
    candidateVersion: text(body.candidateVersion), baselineVersion: text(body.baselineVersion) || undefined,
    trainingCaseIds: Array.isArray(body.trainingCaseIds) ? body.trainingCaseIds.filter((id): id is string => typeof id === "string").map((id) => id.trim()) : [],
    metricScores: Object.fromEntries(Object.entries(rawScores).map(([key, value]) => [key, typeof value === "number" ? value : Number(value)])),
    actor: text(body.actor), notes: text(body.notes) || undefined,
  };
}

export async function GET(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.evaluation, "/api/learning/evaluations", "READ_EVALUATION_RUNS");
  if (authorization.response) return authorization.response;
  try {
    const candidateVersion = new URL(request.url).searchParams.get("candidateVersion")?.trim();
    const rows = await prisma.$queryRaw<EvaluationRow[]>`
      SELECT * FROM "EvaluationRun"
      WHERE (${candidateVersion ?? null}::text IS NULL OR "candidateVersion" = ${candidateVersion ?? null})
      ORDER BY "createdAt" DESC LIMIT 100
    `;
    return NextResponse.json({ success: true, count: rows.length, data: rows });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to read evaluation runs", details: (error as Error).message }, { status: 500 });
  }
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.evaluation, "/api/learning/evaluations", "POST" );
  if (authorization.response) return authorization.response;
  const actorEmail = authorization.session!.email;
  try {
    const body = await request.json() as Record<string, unknown>;
    const input = { ...inputFrom(body), actor: actorEmail };
    const errors = validateEvaluationInput(input);
    if (errors.length) return NextResponse.json({ success: false, errors }, { status: 400 });
    const cases = await prisma.$queryRaw<TrainingRow[]>`SELECT "id", "status" FROM "TrainingCase" WHERE "id" IN (${Prisma.join(input.trainingCaseIds)})`;
    if (cases.length !== input.trainingCaseIds.length) return NextResponse.json({ success: false, error: "Every trainingCaseId must exist." }, { status: 400 });
    if (cases.some((item) => item.status !== "REVIEW_REQUIRED")) return NextResponse.json({ success: false, error: "Every training case must remain REVIEW_REQUIRED; no promoted or altered case may be benchmark input." }, { status: 400 });
    const evaluation = evaluateCandidate(input);
    const evaluationKey = crypto.createHash("sha256").update(JSON.stringify({ candidateVersion: input.candidateVersion, baselineVersion: input.baselineVersion ?? null, trainingCaseIds: [...input.trainingCaseIds].sort(), metricScores: input.metricScores })).digest("hex");
    const [existing] = await prisma.$queryRaw<Pick<EvaluationRow, "id">[]>`SELECT "id" FROM "EvaluationRun" WHERE "evaluationKey" = ${evaluationKey}`;
    if (existing) return NextResponse.json({ success: false, error: "This exact evaluation already exists; duplicate benchmark runs are blocked.", evaluationId: existing.id }, { status: 409 });
    const governance = await new ControlledRuntimeOrchestrator().execute({ operation: "learning:record-benchmark", actor: actorEmail, riskLevel: "HIGH", input });
    if (governance.status === "DENIED") {
      return NextResponse.json({ success: false, error: "Learning governance denied persistence.", governance: { status: governance.status, reason: governance.governanceReason } }, { status: 403 });
    }
    const id = crypto.randomUUID();
    await prisma.$executeRaw`
      INSERT INTO "EvaluationRun" (
        "id", "evaluationKey", "candidateVersion", "baselineVersion", "trainingCaseIds", "metricScores", "score", "status", "notes", "recordedBy", "correlationId", "createdAt"
      ) VALUES (
        ${id}, ${evaluationKey}, ${input.candidateVersion}, ${input.baselineVersion ?? null}, ${JSON.stringify(input.trainingCaseIds)}::jsonb, ${JSON.stringify(input.metricScores)}::jsonb,
        ${evaluation.score}, ${evaluation.status}, ${input.notes ?? null}, ${input.actor}, ${governance.correlationId}, NOW()
      )
    `;
    const [record] = await prisma.$queryRaw<EvaluationRow[]>`SELECT * FROM "EvaluationRun" WHERE "id" = ${id}`;
    return NextResponse.json({ success: true, governance: { status: governance.status, reason: governance.governanceReason }, data: record, evaluation, safety: "This endpoint records a benchmark only. It cannot activate shadow mode, canary mode, approval, promotion, deployment, rollback, or any commercial action." }, { status: 201 });
  } catch (error) {
    return NextResponse.json({ success: false, error: "Unable to record evaluation", details: (error as Error).message }, { status: 400 });
  }
}