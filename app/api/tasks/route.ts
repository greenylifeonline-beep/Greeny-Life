import { authorizeRequest, writeRolePolicy } from "@/lib/authz";
import { Prisma } from "@prisma/client";
import crypto from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { createTaskContract, type TaskInput, type TaskStatus, validateTaskInput } from "@/lib/intelligence/task-orchestration";
import { prisma } from "@/lib/prisma";

interface TaskRow { id: string; taskType: string; ownerCompany: string; subjectId: string; requestedBy: string; executor: string; status: string; priority: string; evidenceIds: unknown; dependsOn: unknown; payload: unknown; outputContract: string; idempotencyKey: string; correlationId: string; createdAt: Date; updatedAt: Date; }
const text = (value: unknown) => typeof value === "string" ? value.trim() : "";
const taskTypes = new Set(["PRODUCT_CONTEXT", "INVENTORY_REVIEW", "SUPPLIER_REVIEW", "SHIPMENT_REVIEW", "EXPORT_EVIDENCE_REVIEW", "OUTCOME_CAPTURE"]);
const companies = new Set(["GREENY_LIFE_EGYPT", "GREENS_NATURE_UAE", "GREEN_LINES_NORWAY_EU", "MASTERMIND"]);

export async function GET(request: NextRequest) {
  try {
    const status = new URL(request.url).searchParams.get("status")?.trim().toUpperCase();
    const rows = await prisma.$queryRaw<TaskRow[]>`
      SELECT * FROM "OrchestrationTask"
      WHERE (${status ?? null}::text IS NULL OR "status" = ${status ?? null})
      ORDER BY "createdAt" DESC LIMIT 100
    `;
    return NextResponse.json({ success: true, count: rows.length, data: rows });
  } catch (error) { return NextResponse.json({ success: false, error: "Unable to read tasks", details: (error as Error).message }, { status: 500 }); }
}

export async function POST(request: NextRequest) {
  const authorization = await authorizeRequest(request, writeRolePolicy.task, "/api/tasks", "POST" );
  if (authorization.response) return authorization.response;
  const actorEmail = authorization.session!.email;
  try {
    const body = await request.json() as Record<string, unknown>;
    const taskType = text(body.taskType).toUpperCase();
    const ownerCompany = text(body.ownerCompany).toUpperCase();
    if (!taskTypes.has(taskType) || !companies.has(ownerCompany)) return NextResponse.json({ success: false, error: "Unknown taskType or ownerCompany." }, { status: 400 });
    const input: TaskInput = { taskType: taskType as TaskInput["taskType"], ownerCompany: ownerCompany as TaskInput["ownerCompany"], subjectId: text(body.subjectId), requestedBy: actorEmail, evidenceIds: Array.isArray(body.evidenceIds) ? body.evidenceIds.filter((item): item is string => typeof item === "string").map((item) => item.trim()) : [], dependsOn: Array.isArray(body.dependsOn) ? body.dependsOn.filter((item): item is string => typeof item === "string").map((item) => item.trim()) : [], priority: text(body.priority).toUpperCase() as TaskInput["priority"], payload: body.payload && typeof body.payload === "object" && !Array.isArray(body.payload) ? body.payload as Record<string, unknown> : {} };
    const errors = validateTaskInput(input);
    if (errors.length) return NextResponse.json({ success: false, errors }, { status: 400 });
    const task = createTaskContract(input);
    const [existing] = await prisma.$queryRaw<Pick<TaskRow, "id">[]>`SELECT "id" FROM "OrchestrationTask" WHERE "idempotencyKey" = ${task.idempotencyKey}`;
    if (existing) return NextResponse.json({ success: false, error: "Identical task already exists; duplicate creation is blocked.", taskId: existing.id }, { status: 409 });
    if (task.dependsOn.length) {
      const dependencies = await prisma.$queryRaw<Array<Pick<TaskRow, "id">>>`SELECT "id" FROM "OrchestrationTask" WHERE "id" IN (${Prisma.join(task.dependsOn)})`;
      if (dependencies.length !== task.dependsOn.length) return NextResponse.json({ success: false, error: "Every dependency task ID must exist." }, { status: 400 });
    }
    const id = crypto.randomUUID(); const correlationId = crypto.randomUUID();
    await prisma.$executeRaw`
      INSERT INTO "OrchestrationTask" ("id", "taskType", "ownerCompany", "subjectId", "requestedBy", "executor", "status", "priority", "evidenceIds", "dependsOn", "payload", "outputContract", "idempotencyKey", "correlationId", "createdAt", "updatedAt")
      VALUES (${id}, ${task.taskType}, ${task.ownerCompany}, ${task.subjectId}, ${task.requestedBy}, ${task.executor}, ${task.status}, ${task.priority}, ${JSON.stringify(task.evidenceIds)}::jsonb, ${JSON.stringify(task.dependsOn)}::jsonb, ${JSON.stringify(task.payload)}::jsonb, ${task.outputContract}, ${task.idempotencyKey}, ${correlationId}, NOW(), NOW())
    `;
    const [record] = await prisma.$queryRaw<TaskRow[]>`SELECT * FROM "OrchestrationTask" WHERE "id" = ${id}`;
    return NextResponse.json({ success: true, data: record, contract: { authority: task.authority, executionRule: task.executionRule } }, { status: 201 });
  } catch (error) { return NextResponse.json({ success: false, error: "Unable to create task", details: (error as Error).message }, { status: 400 }); }
}