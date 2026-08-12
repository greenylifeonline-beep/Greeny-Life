export const commercialCompanies = new Set([
  "GREENY_LIFE_EGYPT",
  "GREENS_NATURE_UAE",
  "GREEN_LINES_NORWAY_EU",
]);

export const traceRecordTypes = new Set([
  "RECEIVE_RAW_MATERIAL",
  "TRANSFORM_OR_PACKAGE",
  "PLAN_REEXPORT",
]);

export type TraceRecordType = "RECEIVE_RAW_MATERIAL" | "TRANSFORM_OR_PACKAGE" | "PLAN_REEXPORT";

export interface TraceRecordInput {
  recordType: TraceRecordType;
  traceCode: string;
  parentTraceCode?: string;
  sourceParty: string;
  holderCompany: string;
  destinationParty?: string;
  materialName: string;
  batchCode: string;
  quantity: number;
  unit: string;
  originCountry: string;
  processingCountry?: string;
  actor: string;
  evidence?: Record<string, unknown>;
}

const text = (value: unknown): value is string => typeof value === "string" && value.trim().length > 0;

export function validateTraceRecord(input: TraceRecordInput): string[] {
  const errors: string[] = [];
  if (!traceRecordTypes.has(input.recordType)) errors.push("recordType is not supported.");
  if (!text(input.traceCode)) errors.push("traceCode is required.");
  if (!text(input.sourceParty)) errors.push("sourceParty is required.");
  if (!commercialCompanies.has(input.holderCompany)) errors.push("holderCompany must be one of the three commercial companies.");
  if (!text(input.materialName)) errors.push("materialName is required.");
  if (!text(input.batchCode)) errors.push("batchCode is required.");
  if (!Number.isFinite(input.quantity) || input.quantity <= 0) errors.push("quantity must be positive.");
  if (!text(input.unit)) errors.push("unit is required.");
  if (!text(input.originCountry)) errors.push("originCountry is required.");
  if (!text(input.actor)) errors.push("actor is required.");
  if (input.recordType === "RECEIVE_RAW_MATERIAL" && input.parentTraceCode) errors.push("Received raw material cannot have a parent trace code.");
  if (input.recordType !== "RECEIVE_RAW_MATERIAL" && !text(input.parentTraceCode)) errors.push("Transformation and re-export require a parentTraceCode.");
  if (input.recordType === "PLAN_REEXPORT" && !text(input.destinationParty)) errors.push("Re-export planning requires destinationParty.");
  if (input.destinationParty === "MASTERMIND") errors.push("MasterMind AI cannot be a commercial destination.");
  return errors;
}

export function initialOwnership(input: TraceRecordInput) {
  return [{
    event: input.recordType === "RECEIVE_RAW_MATERIAL" ? "RECEIPT_RECORDED" : "PROCESSING_OR_REEXPORT_RECORDED",
    sourceParty: input.sourceParty.trim(),
    holderCompany: input.holderCompany,
    destinationParty: input.destinationParty?.trim() ?? null,
    actor: input.actor.trim(),
    recordedAt: new Date().toISOString(),
    legalTitleTransferred: false,
    note: "Operational trace only; legal title, customs filing, shipment, and payment require separate approved evidence.",
  }];
}
