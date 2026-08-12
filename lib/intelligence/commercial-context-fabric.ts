import customersSource from "@/canonical/data/customer-domain/customers.json";
import demandSource from "@/canonical/data/customer-domain/customer-product-demand-map.json";
import opportunitiesSource from "@/canonical/data/customer-domain/opportunities.json";

import type { CompanyId } from "@/lib/intelligence/trade-corridors";

type CanonicalCustomer = {
  customer_id: string;
  company_name: string;
  market: string;
  country: string;
  city: string;
  segment: string;
  type: string;
  status: string;
  channels: string[];
  preferred_products: string[];
};

type DemandEntry = { customer_id: string; market: string; products: string[]; total_orders: number; total_value: number };
type Opportunity = { opportunity_id: string; customer_id: string; product_id: string; stage: string; value: number; probability: number; expected_close: string; status: string };

const customers = (customersSource as { customers: CanonicalCustomer[] }).customers;
const demand = (demandSource as { demand: Record<string, DemandEntry> }).demand;
const opportunities = (opportunitiesSource as { opportunities: Opportunity[] }).opportunities;

const companyForMarket: Record<string, CompanyId> = {
  gcc: "GREENS_NATURE_UAE",
  eu: "GREEN_LINES_NORWAY_EU",
};

function samePlace(left: string, right: string) {
  return left.trim().toLocaleUpperCase() === right.trim().toLocaleUpperCase();
}

export function customerContext(input: { customerId?: string; productId: string; destination: string; destinationCompany: CompanyId }) {
  if (!input.customerId) {
    return {
      status: "REVIEW_REQUIRED" as const,
      summary: "No canonical customer is attached. The commercial decision remains customer-unconfirmed.",
      evidence: ["canonical/data/customer-domain/customers.json"],
      blockers: ["Attach a canonical customer ID before an offer, order, shipment, invoice, or payment can be approved."],
      data: null,
    };
  }

  const customer = customers.find((item) => item.customer_id.toUpperCase() === input.customerId!.trim().toUpperCase());
  if (!customer) {
    return {
      status: "NOT_READY" as const,
      summary: "Customer is not present in the canonical customer master.",
      evidence: ["canonical/data/customer-domain/customers.json"],
      blockers: ["Create or validate the customer in canonical master data; do not use a free-text customer as an approval basis."],
      data: null,
    };
  }

  const blockers: string[] = [];
  if (customer.status.toLowerCase() !== "active") blockers.push("Customer is not active in canonical master data.");
  if (!samePlace(customer.country, input.destination)) blockers.push(`Customer country (${customer.country}) does not match the requested destination (${input.destination}).`);
  if (!customer.preferred_products.includes(input.productId)) blockers.push(`Product ${input.productId} is not in this customer's canonical preference profile.`);
  const responsibleCompany = companyForMarket[customer.market.toLowerCase()];
  if (responsibleCompany && responsibleCompany !== input.destinationCompany) blockers.push(`${customer.market.toUpperCase()} customer context is normally managed by ${responsibleCompany}; the selected destination company requires MasterMind review.`);
  if (!responsibleCompany) blockers.push(`No default operating-company assignment exists for the ${customer.market} market; MasterMind must assign ownership.`);

  const customerDemand = demand[customer.customer_id] ?? null;
  const relevantOpportunities = opportunities.filter((item) => item.customer_id === customer.customer_id && item.product_id === input.productId && item.status.toLowerCase() === "open");
  return {
    status: blockers.length ? "REVIEW_REQUIRED" as const : "SUPPORTED" as const,
    summary: blockers.length ? "Customer context was found, but it needs MasterMind review before a commercial commitment." : "Canonical customer, product preference, destination, and operating-company context align.",
    evidence: ["canonical/data/customer-domain/customers.json", "canonical/data/customer-domain/customer-product-demand-map.json", "canonical/data/customer-domain/opportunities.json"],
    blockers,
    data: {
      customer: { id: customer.customer_id, name: customer.company_name, market: customer.market, country: customer.country, city: customer.city, segment: customer.segment, channels: customer.channels },
      demand: customerDemand,
      openOpportunities: relevantOpportunities.map(({ opportunity_id, stage, value, probability, expected_close }) => ({ opportunityId: opportunity_id, stage, value, probability, expectedClose: expected_close })),
      recommendedOperatingCompany: responsibleCompany ?? null,
      sourceStatus: "CANONICAL_INTERNAL_DATA_NOT_EXTERNAL_COMMERCIAL_OR_REGULATORY_EVIDENCE",
    },
  };
}

export function commercialContextSummary() {
  return {
    source: "canonical customer-domain masters",
    customerCount: customers.length,
    demandProfiles: Object.keys(demand).length,
    opportunityCount: opportunities.length,
    companyOwnershipRule: companyForMarket,
    executionRule: "Customer records describe internal context only. They do not authorize offers, contracts, shipment, payment, customs, or title transfer.",
  };
}
