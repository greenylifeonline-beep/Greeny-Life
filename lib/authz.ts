import crypto from "node:crypto";
import { NextRequest, NextResponse } from "next/server";
import { type AppRole, requireRole } from "@/lib/auth";
import { prisma } from "@/lib/prisma";

export const writeRolePolicy = {
  productMaster: ["ADMIN"] as AppRole[],
  supplierMaster: ["ADMIN"] as AppRole[],
  salesOrder: ["ADMIN", "SALES", "EXPORT"] as AppRole[],
  workflow: ["ADMIN", "WAREHOUSE", "EXPORT"] as AppRole[],
  commercialChange: ["ADMIN"] as AppRole[],
  traceability: ["ADMIN", "WAREHOUSE", "EXPORT"] as AppRole[],
  task: ["ADMIN", "WAREHOUSE", "EXPORT"] as AppRole[],
  outcome: ["ADMIN", "SALES", "EXPORT", "WAREHOUSE", "FINANCE"] as AppRole[],
  training: ["ADMIN"] as AppRole[],
  evaluation: ["ADMIN"] as AppRole[],
} as const;

async function audit(route: string, action: string, actorEmail: string | null, role: string | null, outcome: "ALLOWED" | "DENIED", reason: string) {
  try {
    await prisma.$executeRaw`
      INSERT INTO "SecurityAuditEvent" ("id", "route", "action", "actorEmail", "role", "outcome", "reason", "createdAt")
      VALUES (${crypto.randomUUID()}, ${route}, ${action}, ${actorEmail}, ${role}, ${outcome}, ${reason}, NOW())
    `;
  } catch {
    // Auditing must never make an authorization failure appear authorized.
  }
}

export async function authorizeRequest(request: NextRequest, allowed: readonly AppRole[], route: string, action: string) {
  const authorization = requireRole(request, allowed);
  if (authorization.response) {
    await audit(route, action, authorization.session?.email ?? null, authorization.session?.role ?? null, "DENIED", "Authentication missing or role insufficient.");
    return { session: authorization.session, response: authorization.response };
  }
  await audit(route, action, authorization.session!.email, authorization.session!.role, "ALLOWED", "Role policy satisfied.");
  return { session: authorization.session!, response: null as NextResponse | null };
}