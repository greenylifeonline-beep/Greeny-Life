import fs from "node:fs";
import path from "node:path";

export interface LegacyBatchTrace {
  batchCode: string;
  productId: string | null;
  productName: string;
  originCountry: string | null;
  traceability: string;
  qualityCheck: string;
  source: "OPERATIONS_EXPORT_FLOW_V1" | "ERP_INTEGRATION_V1";
}

const root = process.cwd();
const operationsFile = path.join(root, "archive", "old_folders", "GREENY-LIFE-EOS-PRODUCTION", "operations", "export-operating-flow-v1", "batch-traceability-v1.json");
const erpFile = path.join(root, "archive", "old_folders", "GREENY-LIFE-EOS-PRODUCTION", "erp", "erp-integration-layer-v1", "batch-traceability-v1.json");

type LegacyRow = { BatchID?: unknown; ProductID?: unknown; ProductName?: unknown; Product?: unknown; Origin?: unknown; Traceability?: unknown; QualityCheck?: unknown };

function read(file: string, source: LegacyBatchTrace["source"]): LegacyBatchTrace[] {
  if (!fs.existsSync(file)) return [];
  const rows = JSON.parse(fs.readFileSync(file, "utf8")) as LegacyRow[];
  return rows.map((row) => ({
    batchCode: String(row.BatchID ?? "").trim(),
    productId: typeof row.ProductID === "string" ? row.ProductID.trim() : null,
    productName: String(row.ProductName ?? row.Product ?? "").trim(),
    originCountry: typeof row.Origin === "string" ? row.Origin.trim() : null,
    traceability: String(row.Traceability ?? "UNKNOWN").trim(),
    qualityCheck: String(row.QualityCheck ?? "UNKNOWN").trim(),
    source,
  })).filter((row) => row.batchCode && row.productName);
}

/**
 * The operations register is authoritative where the two historical snapshots
 * overlap because it contains product IDs. ERP fills only absent metadata.
 * This is read-only: historical statements are not silently converted into
 * current verified operational records.
 */
export function legacyBatchRegistry() {
  const operations = read(operationsFile, "OPERATIONS_EXPORT_FLOW_V1");
  const erp = read(erpFile, "ERP_INTEGRATION_V1");
  const erpByBatch = new Map(erp.map((row) => [row.batchCode, row]));
  const batchCodes = new Set([...operations.map((row) => row.batchCode), ...erp.map((row) => row.batchCode)]);
  const records: LegacyBatchTrace[] = [];
  const inconsistencies: Array<{ batchCode: string; field: string; operations: string | null; erp: string | null }> = [];

  for (const batchCode of [...batchCodes].sort()) {
    const operational = operations.find((row) => row.batchCode === batchCode);
    const legacyErp = erpByBatch.get(batchCode);
    if (operational) {
      records.push({ ...operational, originCountry: operational.originCountry ?? legacyErp?.originCountry ?? null });
      for (const field of ["productName", "traceability", "qualityCheck"] as const) {
        if (legacyErp && operational[field] !== legacyErp[field]) {
          inconsistencies.push({ batchCode, field, operations: operational[field], erp: legacyErp[field] });
        }
      }
    } else if (legacyErp) {
      records.push(legacyErp);
    }
  }

  return {
    status: "HISTORICAL_REFERENCE_NOT_CURRENT_EVIDENCE",
    authority: "OPERATIONS_EXPORT_FLOW_V1 with ERP_INTEGRATION_V1 enrichment",
    records,
    inconsistencies,
    sourceFiles: [
      path.relative(root, operationsFile),
      path.relative(root, erpFile),
    ],
    rule: "A legacy ENABLED/PASSED label is historical data only. Current quality, certificates, custody, shipment, and legal status require current verified evidence.",
  };
}

export function findLegacyBatch(batchCode: string) {
  return legacyBatchRegistry().records.find((record) => record.batchCode === batchCode) ?? null;
}
