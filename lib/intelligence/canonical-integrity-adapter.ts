import { runAuditEngine } from "@/canonical/intelligence/intelligence/engines/audit-engine";
import { runIntegrityEngine } from "@/canonical/intelligence/intelligence/engines/data-integrity-engine";

export function canonicalIntegrityReview() {
  const audit = runAuditEngine();
  const integrity = runIntegrityEngine();
  const errors = audit.summary.errors + integrity.summary.errors;
  const warnings = audit.summary.warnings + integrity.summary.warnings;
  return {
    status: errors > 0 ? "NOT_READY" as const : warnings > 0 ? "REVIEW_REQUIRED" as const : "SUPPORTED" as const,
    source: "canonical/data/master_products.json",
    checkedAt: new Date().toISOString(),
    engines: {
      audit: { version: audit.version, summary: audit.summary },
      integrity: { version: integrity.version, summary: integrity.summary },
    },
    blockers: errors > 0 ? ["Canonical product master has validation errors and cannot be used as a reliable decision context."] : [],
    warnings: warnings > 0 ? ["Canonical product master has warnings requiring data-owner review."] : [],
    executionRule: "This is a read-only data-quality review. It does not validate live stock, supplier authorization, certificates, prices, customs, or commercial eligibility; it never edits canonical data.",
  };
}
