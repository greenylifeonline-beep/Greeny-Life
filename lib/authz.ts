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

export type AuthorizationAuditWriter = (event: {
  route: string;
  action: string;
  actorEmail: string | null;
  role: string | null;
  outcome: "ALLOWED" | "DENIED";
  reason: string;
}) => Promise<boolean>;

const persistAuthorizationAudit: AuthorizationAuditWriter = async (event) => {
  try {
    await prisma.$executeRaw`
      INSERT INTO "SecurityAuditEvent" ("id", "route", "action", "actorEmail", "role", "outcome", "reason", "createdAt")
      VALUES (${crypto.randomUUID()}, ${event.route}, ${event.action}, ${event.actorEmail}, ${event.role}, ${event.outcome}, ${event.reason}, NOW())
    `;
    return true;
  } catch {
    return false;
  }
};

export async function authorizeRequest(
  request: NextRequest,
  allowed: readonly AppRole[],
  route: string,
  action: string,
  options: { auditWriter?: AuthorizationAuditWriter } = {},
) {
  const auditWriter = options.auditWriter ?? persistAuthorizationAudit;
  const authorization = requireRole(request, allowed);
  if (authorization.response) {
    await auditWriter({
      route, action, actorEmail: authorization.session?.email ?? null, role: authorization.session?.role ?? null,
      outcome: "DENIED", reason: "Authentication missing or role insufficient.",
    });
    return { session: authorization.session, response: authorization.response };
  }
  const audited = await auditWriter({
    route, action, actorEmail: authorization.session!.email, role: authorization.session!.role,
    outcome: "ALLOWED", reason: "Role policy satisfied.",
  });
  if (!audited) {
    return {
      session: authorization.session,
      response: NextResponse.json(
        { success: false, error: "Authorization audit persistence failed; write operations are blocked." },
        { status: 503 },
      ),
    };
  }
  return { session: authorization.session!, response: null as NextResponse | null };
}