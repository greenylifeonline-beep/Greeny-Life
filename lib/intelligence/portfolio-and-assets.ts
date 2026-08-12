import fs from "fs";
import path from "path";

export type CompanyId = "GREENY_LIFE_EGYPT" | "GREENS_NATURE_UAE" | "GREEN_LINES_NORWAY_EU" | "MASTERMIND";

interface EgyptianProduct {
  id: string;
  product_code: string;
  category: string;
  name: { en?: string; ar?: string };
  markets: Record<string, boolean>;
  global_specs?: { country_of_origin?: string; hs_code?: string; required_certificates?: string[] };
}

function readJson<T>(relativePath: string): T {
  const content = fs.readFileSync(path.join(process.cwd(), relativePath), "utf8").replace(/^\uFEFF/, "");
  return JSON.parse(content) as T;
}

export function egyptianExportPortfolio() {
  const master = readJson<{ products: EgyptianProduct[] }>("canonical/data/master_products.json");
  return {
    source: "canonical/data/master_products.json",
    status: "REFERENCE_PORTFOLIO_NOT_AUTOMATICALLY_EXPORTABLE",
    owner: "GREENY_LIFE_EGYPT" as CompanyId,
    count: master.products.length,
    products: master.products.map((product) => ({
      id: product.id,
      code: product.product_code,
      name: product.name?.en ?? product.id,
      category: product.category,
      origin: product.global_specs?.country_of_origin ?? "Egypt",
      hsCode: product.global_specs?.hs_code ?? null,
      targetMarkets: Object.entries(product.markets ?? {}).filter(([, allowed]) => allowed).map(([market]) => market.toUpperCase()),
      requiredCertificates: product.global_specs?.required_certificates ?? [],
      routes: [
        { destinationOwner: "GREEN_LINES_NORWAY_EU" as CompanyId, markets: ["NORWAY", "EU"], status: "REQUIRES_OFFICIAL_EVIDENCE_AND_APPROVAL" },
        { destinationOwner: "GREENS_NATURE_UAE" as CompanyId, markets: ["UAE", "GCC"], status: "REQUIRES_OFFICIAL_EVIDENCE_AND_APPROVAL" },
      ],
    })),
  };
}

type AssetClass = "ACTIVE_RUNTIME" | "REUSABLE_SOURCE" | "REFERENCE_DATA" | "HISTORICAL_EVIDENCE" | "GENERATED_REPORT" | "DEPENDENCY_OR_BUILD";

function classifyAsset(assetPath: string): AssetClass {
  const normalized = assetPath.replace(/\\/g, "/").toLowerCase();
  if (normalized.startsWith("node_modules/") || normalized.startsWith(".next/") || normalized.startsWith(".npm-cache/") || normalized.startsWith(".venv/") || normalized.startsWith("venv/")) return "DEPENDENCY_OR_BUILD";
  if (normalized === ".env" || normalized.startsWith(".env.")) return "HISTORICAL_EVIDENCE";
  if (normalized.startsWith("app/") || normalized.startsWith("lib/") || normalized === "prisma/schema.prisma") return "ACTIVE_RUNTIME";
  if (normalized.startsWith("canonical/data/") || normalized.startsWith("canonical/business/") || normalized.startsWith("canonical/governance/")) return "REFERENCE_DATA";
  if (normalized.includes("report") || normalized.includes("audit") || normalized.includes("recon-output")) return "GENERATED_REPORT";
  if (normalized.startsWith("archive/") || normalized.startsWith("backup/") || normalized.includes("legacy")) return "HISTORICAL_EVIDENCE";
  return "REUSABLE_SOURCE";
}

export function assetAssimilationRegistry() {
  const manifest = readJson<Array<{ Path: string; Size: number; LastWriteTime: string }>>("E3-REPOSITORY-MANIFEST.json");
  const groups = new Map<AssetClass, { count: number; size: number; samples: string[] }>();
  for (const asset of manifest) {
    const classification = classifyAsset(asset.Path);
    const group = groups.get(classification) ?? { count: 0, size: 0, samples: [] };
    group.count += 1;
    group.size += asset.Size ?? 0;
    if (group.samples.length < 12) group.samples.push(asset.Path);
    groups.set(classification, group);
  }
  return {
    manifest: "E3-REPOSITORY-MANIFEST.json",
    totalAssets: manifest.length,
    policy: {
      activeRuntime: "May be imported into the final runtime only after build and execution proof.",
      reusableSource: "Review, normalize, test, then integrate through an explicit adapter or module.",
      referenceData: "Use as evidence/context; never treat as current legal or commercial truth without verification.",
      historicalEvidence: "Preserve and consult; do not run directly.",
      generatedReport: "Read on demand; do not accumulate new duplicate reports.",
      dependencyOrBuild: "Rebuild from package definitions; never merge into business source.",
    },
    classes: Object.fromEntries([...groups.entries()].map(([name, group]) => [name, { ...group, sizeMB: Number((group.size / 1024 / 1024).toFixed(2)) }])),
  };
}
