import shipmentsSource from "@/canonical/logistics/shipments.json";
import trackingSource from "@/canonical/logistics/tracking.json";
import { assessFreshness } from "@/lib/intelligence/operational-data-freshness";

type Shipment = { shipment_id: string; product_id: string; status: string; tracking_code: string; destination_country: string; market: string; last_updated: string };
type TrackingUpdate = { tracking_code: string; status: string; location: string; timestamp: string };

const shipments = (shipmentsSource as { shipments: Shipment[] }).shipments;
const updates = (trackingSource as { updates: TrackingUpdate[] }).updates;

export function shipmentTrackingReview(productId?: string) {
  const selected = productId ? shipments.filter((shipment) => shipment.product_id === productId) : shipments;
  const records = selected.map((shipment) => {
    const history = updates.filter((update) => update.tracking_code === shipment.tracking_code)
      .sort((left, right) => new Date(right.timestamp).valueOf() - new Date(left.timestamp).valueOf());
    const latest = history[0] ?? null;
    const shipmentFreshness = assessFreshness(shipment.last_updated);
    const trackingFreshness = latest ? assessFreshness(latest.timestamp) : null;
    const mismatch = latest && latest.status !== shipment.status;
    return {
      shipmentId: shipment.shipment_id,
      trackingCode: shipment.tracking_code,
      declaredStatus: shipment.status,
      latestTrackingUpdate: latest,
      statusMismatch: mismatch,
      freshness: { shipment: shipmentFreshness, tracking: trackingFreshness },
      destination: { country: shipment.destination_country, market: shipment.market },
    };
  });
  const mismatches = records.filter((record) => record.statusMismatch);
  const stale = records.filter((record) => record.freshness.shipment.state === "STALE_REFERENCE" || record.freshness.tracking?.state === "STALE_REFERENCE");
  return {
    status: records.length === 0 ? "NOT_READY" as const : "REVIEW_REQUIRED" as const,
    records,
    summary: { shipments: records.length, statusMismatches: mismatches.length, staleRecords: stale.length },
    blockers: [
      ...(mismatches.length ? [`${mismatches.length} shipment record(s) disagree with their latest historical tracking update.`] : []),
      ...(stale.length ? [`${stale.length} shipment record(s) have stale reference timestamps; query the carrier and documents before relying on their status.`] : []),
      "No carrier API, signed transport document, customs message, or proof-of-delivery is connected to this review.",
    ],
    sourceBoundaries: ["canonical/logistics/shipments.json", "canonical/logistics/tracking.json"],
    executionRule: "Tracking records are historical reference only. This review does not release, reroute, clear customs, invoice, or confirm delivery.",
  };
}
