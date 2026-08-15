# Legacy brain.py extraction map

Lines: 6637

## Conclusion
brain.py is a mixed legacy toolbox. It is not an approved runtime brain and must not be integrated directly.

## Global risk surfaces
- Delete call sites: 3
- Process launch call sites: 3
- Network call sites: 2
- Cleanup flags: 3

| Line | Definition | Capability | Risk | Recommendation |
|---:|---|---|---|---|
| 67 | class ScanResult | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 75 | def to_dict | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 78 | def add_finding | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 82 | def mark_failed | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 87 | def is_success | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 91 | class RemediationResult | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 98 | def to_dict | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 101 | def mark_success | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 107 | def mark_failure | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 112 | class FileInsight | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 127 | def to_dict | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 130 | def summarize | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 141 | class GreenyLifeBrain | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 157 | def __init__ | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 178 | def _should_ignore | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 186 | def _load_config | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 237 | def _deep_update | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 244 | def _setup_logging | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 264 | def _check_prerequisites | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 288 | def _which | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 291 | def run_asset_classifier | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 578 | def _ensure_directories | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 588 | def _ensure_manifest_exists | REPORTING_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 593 | def _run_command | UNCLASSIFIED | PROCESS | QUARANTINE_DO_NOT_REUSE_DIRECTLY |
| 631 | def classify_assets | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 895 | def run_consolidation | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 1031 | def run_canonical_validation | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 1220 | def build_supplier_master | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 1428 | def build_certificate_master | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 1694 | def build_els | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 1961 | def build_customer_domain | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 2367 | def build_analytics_layer | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 2594 | def build_logistics_system | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 2853 | def _get_net_weights | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 2866 | def _get_nutrition_facts | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 2879 | def _get_certifications_for_product | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 2888 | def _get_side_panel | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 2930 | def run_deep_clean | MAINTENANCE_RISK |  | REVIEW_REQUIRED |
| 3077 | def _extract_domain | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 3091 | def run_master_data_audit | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 3223 | def build_finance_system | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 3338 | def build_inventory_system | REPORTING_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 3431 | def build_crm_system | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 3541 | def enrich_product_details | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 3612 | def self_clean_reports_and_logs | REPORTING_CANDIDATE | DELETE | QUARANTINE_DO_NOT_REUSE_DIRECTLY |
| 3647 | def validate_global_specs | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 3677 | def generate_dynamic_packaging | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 3728 | def build_packaging_visual_engine | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 3889 | def generate_gels_labels_with_visuals | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 3989 | def run_deep_packaging_audit | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 4198 | def integrate_business_assets | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 4456 | def _get_manifest_path | REPORTING_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 4459 | def initialize_system_manifest | REPORTING_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 4538 | def run_integrity_analysis | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 4628 | def propose_system_evolution | UNCLASSIFIED | DELETE | QUARANTINE_DO_NOT_REUSE_DIRECTLY |
| 4697 | def run_continuous_evolution_cycle | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 4742 | def run_arch_guard | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 4794 | def run_govern_kit | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 4825 | def run_ouro_loop | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 4868 | def run_sonarqube_scan | ANALYSIS_CANDIDATE | NETWORK | QUARANTINE_DO_NOT_REUSE_DIRECTLY |
| 4929 | def run_security_scan | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 4980 | def run_performance_test | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 5075 | def run_documentation_agent | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 5142 | def _generate_tree_structure | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 5160 | def _extract_classes_from_file | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5169 | def discover_and_merge_intelligence | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 5199 | def scan_project_metadata | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5274 | def deep_scan_files | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5302 | def _deep_scan_single_file | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5411 | def _extract_business_value | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5425 | def analyze_visual_brand | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5486 | def analyze_packaging_policies | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5517 | def analyze_ui_structure | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5563 | def analyze_inventory | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5618 | def analyze_duplication_reason | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5649 | def create_remediation_pr | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 5703 | def _generate_comprehensive_report | REPORTING_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5796 | def run_unified_cleanup | MAINTENANCE_RISK |  | REVIEW_REQUIRED |
| 5918 | def _send_alert | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 5946 | def auto_correct_issues | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 5967 | def run_daily_audit | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 5995 | def check_system_health | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 6017 | def continuous_log_analyzer | ANALYSIS_CANDIDATE |  | EXTRACT_ONLY_AFTER_INDEPENDENT_TEST |
| 6043 | def run_periodic_monitoring | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 6062 | def run_scheduler_mode | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 6092 | def execute_full_pipeline | UNCLASSIFIED |  | REVIEW_REQUIRED |
| 6223 | def cli | UNCLASSIFIED |  | REVIEW_REQUIRED |

No code was executed, changed, moved, or deleted.
