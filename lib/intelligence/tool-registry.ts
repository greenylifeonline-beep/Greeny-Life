import fs from "node:fs";
import path from "node:path";

export type ToolDisposition = "READ_ONLY_READY" | "ADAPTER_REQUIRED" | "BLOCKED_DIRECT_EXECUTION";

interface LegacyCapability {
  name: string;
  type: "EXECUTION" | "BUILD" | "ANALYSIS" | "GENERATION" | "INTEGRATION" | "VALIDATION";
  source_line: number;
  confidence: string;
  legacy_origin: string;
}

const blocked = new Set([
  "run_consolidation", "run_deep_clean", "run_unified_cleanup", "run_continuous_evolution_cycle",
  "execute_full_pipeline", "run_scheduler_mode", "run_periodic_monitoring", "run_daily_audit",
]);
const adapterRequired = new Set([
  "build_supplier_master", "build_certificate_master", "build_els", "build_customer_domain",
  "build_analytics_layer", "build_logistics_system", "build_finance_system", "build_inventory_system",
  "build_crm_system", "build_packaging_visual_engine", "generate_dynamic_packaging",
  "generate_gels_labels_with_visuals", "integrate_business_assets", "run_asset_classifier",
  "run_canonical_validation", "run_master_data_audit", "run_deep_packaging_audit",
  "run_integrity_analysis", "run_arch_guard", "run_govern_kit", "run_ouro_loop",
  "run_sonarqube_scan", "run_security_scan", "run_performance_test", "run_documentation_agent",
]);

function readCapabilities(): LegacyCapability[] {
  const file = path.join(process.cwd(), "greenlines_brain", "dna", "extracted_knowledge.json");
  const source = JSON.parse(fs.readFileSync(file, "utf8")) as { capabilities?: LegacyCapability[] };
  return source.capabilities ?? [];
}

function disposition(capability: LegacyCapability): ToolDisposition {
  if (blocked.has(capability.name)) return "BLOCKED_DIRECT_EXECUTION";
  if (capability.type === "ANALYSIS" || capability.type === "VALIDATION") return "READ_ONLY_READY";
  if (adapterRequired.has(capability.name)) return "ADAPTER_REQUIRED";
  return "ADAPTER_REQUIRED";
}

function purpose(name: string) {
  const names: Record<string, string> = {
    analyze_visual_brand: "Analyze legacy brand and visual-identity references.",
    analyze_packaging_policies: "Analyze packaging rules and policy references.",
    analyze_ui_structure: "Analyze application structure without changing it.",
    analyze_inventory: "Analyze inventory sources without creating movements.",
    analyze_duplication_reason: "Analyze the cause and evidence of duplicate assets.",
    validate_global_specs: "Validate HS-code, EAN, and certificate reference fields.",
  };
  return names[name] ?? "Historical capability retained for reviewed integration.";
}

export function toolRegistry() {
  const tools = readCapabilities().map((capability) => ({
    id: `LEGACY-${capability.name.toUpperCase()}`,
    name: capability.name,
    category: capability.type,
    disposition: disposition(capability),
    purpose: purpose(capability.name),
    source: capability.legacy_origin,
    confidence: capability.confidence,
    authority: "MasterMind AI routes tools; local brains may request them; no tool can execute commercial actions.",
    inputs: "Explicit reviewed context only",
    outputs: "Auditable finding, recommendation, or adapter proposal",
    executionRule: disposition(capability) === "READ_ONLY_READY"
      ? "Read-only analysis; result remains subject to MasterMind and user approval."
      : disposition(capability) === "ADAPTER_REQUIRED"
        ? "Cannot run until a tested adapter binds it to current canonical data."
        : "Direct execution is prohibited; retained only as historical capability evidence.",
  }));
  const counts = Object.fromEntries(([
    "READ_ONLY_READY", "ADAPTER_REQUIRED", "BLOCKED_DIRECT_EXECUTION",
  ] as const).map((status) => [status, tools.filter((tool) => tool.disposition === status).length]));
  return {
    system: "MasterMind AI Tool Registry",
    source: "greenlines_brain/dna/extracted_knowledge.json",
    total: tools.length,
    counts,
    rules: [
      "MasterMind AI routes and combines tools; it does not let tools override approval requirements.",
      "Local operating brains may request a tool only inside their company context.",
      "All tools are read-only until an explicit tested adapter and user-approved operational workflow exists.",
    ],
    tools,
  };
}
