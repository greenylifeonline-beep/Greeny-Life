export type FreshnessState = "LIVE_CONFIRMED" | "RECENT_REFERENCE" | "STALE_REFERENCE" | "INVALID_TIMESTAMP";

const recentHours = 24;

export function assessFreshness(timestamp: string, now = new Date()) {
  const observedAt = new Date(timestamp);
  if (Number.isNaN(observedAt.valueOf())) {
    return { state: "INVALID_TIMESTAMP" as const, observedAt: timestamp, ageHours: null, usableForAutomaticExecution: false };
  }
  const ageHours = Math.max(0, (now.valueOf() - observedAt.valueOf()) / 3_600_000);
  return {
    state: ageHours <= recentHours ? "RECENT_REFERENCE" as FreshnessState : "STALE_REFERENCE" as FreshnessState,
    observedAt: observedAt.toISOString(),
    ageHours: Number(ageHours.toFixed(2)),
    usableForAutomaticExecution: false,
  };
}

export function operationalDataStatus(input: { stockUpdatedAt: string[]; supplierGeneratedAt?: string; shipmentUpdatedAt: string[] }) {
  const stock = input.stockUpdatedAt.map((timestamp) => assessFreshness(timestamp));
  const shipments = input.shipmentUpdatedAt.map((timestamp) => assessFreshness(timestamp));
  const supplier = input.supplierGeneratedAt ? assessFreshness(input.supplierGeneratedAt) : null;
  const states = [...stock, ...shipments, ...(supplier ? [supplier] : [])];
  const stale = states.filter((item) => item.state === "STALE_REFERENCE" || item.state === "INVALID_TIMESTAMP");
  return {
    status: stale.length ? "REVIEW_REQUIRED" as const : "REFERENCE_ONLY" as const,
    freshnessPolicy: { recentHours, liveDefinition: "LIVE_CONFIRMED requires a connected, authenticated operational source with an independently verified retrieval time." },
    sources: { stock, supplier, shipments },
    blockers: stale.length ? [`${stale.length} operational record(s) are stale or have invalid timestamps; confirm current values before production, purchase, allocation, shipment, or export decisions.`] : [],
    executionRule: "Reference records are never live confirmation and never authorize automatic operational execution.",
  };
}
