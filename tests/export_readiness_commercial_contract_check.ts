import assert from "node:assert/strict";
import { assessCommercialReadiness } from "../lib/intelligence/export-decision";

const now = new Date("2026-08-13T12:00:00.000Z");
const current = { status: "APPROVED", effectiveFrom: new Date("2026-08-01T00:00:00.000Z"), effectiveTo: new Date("2026-08-31T23:59:59.000Z"), payload: { destination: "Norway" } };

const complete = assessCommercialReadiness([
  { ...current, domain: "PRICE" },
  { ...current, domain: "SHIPMENT" },
  { ...current, domain: "OFFER" },
], "Norway", now);
assert.equal(complete.supported, true);
assert.deepEqual(complete.missingDomains, []);

const missingShipment = assessCommercialReadiness([
  { ...current, domain: "PRICE" },
  { ...current, domain: "OFFER" },
], "Norway", now);
assert.equal(missingShipment.supported, false);
assert.deepEqual(missingShipment.missingDomains, ["SHIPMENT"]);

const expired = assessCommercialReadiness([
  { ...current, domain: "PRICE", effectiveTo: new Date("2026-08-12T23:59:59.000Z") },
  { ...current, domain: "SHIPMENT" },
  { ...current, domain: "OFFER" },
], "Norway", now);
assert.equal(expired.supported, false);
assert.ok(expired.missingDomains.includes("PRICE"));

const wrongDestination = assessCommercialReadiness([
  { ...current, domain: "PRICE", payload: { destination: "UAE" } },
  { ...current, domain: "SHIPMENT", payload: { destination: "UAE" } },
  { ...current, domain: "OFFER", payload: { destination: "UAE" } },
], "Norway", now);
assert.equal(wrongDestination.supported, false);
assert.deepEqual(wrongDestination.missingDomains, ["PRICE", "SHIPMENT", "OFFER"]);

const conflictingPrice = assessCommercialReadiness([
  { ...current, domain: "PRICE", payload: { destination: "Norway", amount: 10 } },
  { ...current, domain: "PRICE", payload: { destination: "Norway", amount: 12 } },
  { ...current, domain: "SHIPMENT" },
  { ...current, domain: "OFFER" },
], "Norway", now);
assert.equal(conflictingPrice.supported, false, "Concurrent approved commercial records must not silently select a winner.");
assert.deepEqual(conflictingPrice.conflictingDomains, ["PRICE"]);
assert.ok(conflictingPrice.reasons.some((reason) => reason.includes("human must resolve")));
console.log("export_readiness_commercial_contract_check: PASS");
