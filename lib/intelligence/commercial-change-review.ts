import { prisma } from "@/lib/prisma";

type CommercialChangeRow = {
  id: string;
  domain: string;
  subjectType: string;
  subjectId: string;
  changeType: string;
  status: string;
  riskLevel: string;
  source: string;
  rationale: string | null;
  effectiveFrom: Date | null;
  effectiveTo: Date | null;
  requestedBy: string;
  correlationId: string;
  createdAt: Date;
};

const governedDomains = new Set(["PRICE", "SUPPLIER", "SHIPMENT", "OFFER"]);
const pendingStatuses = new Set(["PROPOSED", "REVIEW_REQUIRED", "PENDING_USER_APPROVAL"]);

export async function commercialChangeReview(productId: string) {
  const rows = await prisma.$queryRaw<CommercialChangeRow[]>`
    SELECT "id", "domain", "subjectType", "subjectId", "changeType", "status", "riskLevel", "source",
           "rationale", "effectiveFrom", "effectiveTo", "requestedBy", "correlationId", "createdAt"
    FROM "CommercialChange"
    WHERE "subjectId" = ${productId}
    ORDER BY "createdAt" DESC
    LIMIT 50
  `;

  const relevant = rows.filter((row) => governedDomains.has(row.domain));
  const pending = relevant.filter((row) => pendingStatuses.has(row.status));
  const critical = pending.filter((row) => row.riskLevel === "CRITICAL");
  const blockers = pending.map((row) => `${row.domain} ${row.changeType} (${row.status}, ${row.riskLevel}) requires explicit user approval: ${row.id}.`);

  return {
    status: critical.length ? "NOT_READY" as const : "REVIEW_REQUIRED" as const,
    summary: pending.length
      ? `${pending.length} pending commercial change(s) are attached to this product; none is effective in the decision package.`
      : "No pending price, supplier, shipment, or offer changes are attached to this product.",
    evidence: pending.length ? pending.map((row) => `CommercialChange ${row.id} / ${row.correlationId}`) : ["CommercialChange ledger queried; no pending governed changes found."],
    blockers,
    data: {
      subjectId: productId,
      pendingCount: pending.length,
      criticalPendingCount: critical.length,
      changes: pending.map((row) => ({
        id: row.id,
        domain: row.domain,
        changeType: row.changeType,
        status: row.status,
        riskLevel: row.riskLevel,
        source: row.source,
        rationale: row.rationale,
        effectiveFrom: row.effectiveFrom,
        effectiveTo: row.effectiveTo,
        requestedBy: row.requestedBy,
        correlationId: row.correlationId,
        createdAt: row.createdAt,
      })),
      executionRule: "A ledger entry is a proposal, not an applied change. MasterMind must show it to the user before any controlled operational execution.",
    },
  };
}
