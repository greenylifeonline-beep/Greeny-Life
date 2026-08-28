import sys
import json
import logging
import argparse
import traceback
from pathlib import Path
from brain import GreenyLifeBrain

def main():
    parser = argparse.ArgumentParser(
        description="Greeny-Life EOS Brain - CLI (Standalone)",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--repo", required=True, help="Path to the project repository root.")
    parser.add_argument("--config", help="Path to the YAML configuration file.")

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--full-audit", action="store_true", help="Run the full pipeline once.")
    mode_group.add_argument("--build-suppliers", action="store_true", help="Build the supplier master data.")
    mode_group.add_argument("--daily", action="store_true", help="Run the daily audit.")
    mode_group.add_argument("--monitor", action="store_true", help="Run continuous monitoring.")
    mode_group.add_argument("--schedule", action="store_true", help="Run autonomous scheduler.")
    mode_group.add_argument("--cleanup", action="store_true", help="Run unified cleanup.")
    mode_group.add_argument("--evolve", action="store_true", help="Run self-evolution cycle.")
    mode_group.add_argument("--classify", action="store_true", help="Run EOS Asset Intelligence Classification.")
    mode_group.add_argument("--consolidate", action="store_true", help="Execute consolidation plan.")
    mode_group.add_argument("--validate", action="store_true", help="Run Canonical Validation.")
    mode_group.add_argument("--build-certificates", action="store_true", help="Build Certificate Master Data.")
    mode_group.add_argument("--build-els", action="store_true", help="Build Enterprise Label Management System.")
    mode_group.add_argument("--build-customers", action="store_true", help="Build Customer Domain.")
    mode_group.add_argument("--build-analytics", action="store_true", help="Build Analytics Layer.")
    mode_group.add_argument("--build-logistics", action="store_true", help="Build Logistics System.")
    mode_group.add_argument("--deep-clean", action="store_true", help="Deep clean of the file system.")
    mode_group.add_argument("--master-data-audit", action="store_true", help="Audit all product data sources.")
    mode_group.add_argument("--build-finance", action="store_true", help="Build Finance System.")
    mode_group.add_argument("--build-inventory", action="store_true", help="Build Inventory System.")
    mode_group.add_argument("--build-crm", action="store_true", help="Build CRM System.")
    mode_group.add_argument("--build-packaging-visual", action="store_true", help="Build packaging profiles.")
    mode_group.add_argument("--generate-labels-visual", action="store_true", help="Generate GELS labels.")
    mode_group.add_argument("--deep-packaging-audit", action="store_true", help="Deep audit packaging files.")
    mode_group.add_argument("--integrate-business-assets", action="store_true", help="Extract markets and specs.")

    parser.add_argument("--no-fix", action="store_true", help="Skip auto-remediation.")
    parser.add_argument("--no-pr", action="store_true", help="Skip GitHub PR creation.")
    parser.add_argument("--output", help="Save results to a JSON file.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging.")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    try:
        brain = GreenyLifeBrain(args.repo, args.config)

        if args.full_audit:
            results = brain.execute_full_pipeline(auto_fix=not args.no_fix, create_pr=not args.no_pr)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Results saved to: {args.output}")
            print(f"🏁 Status: {results['overall_status']}")

        elif args.classify:
            results = brain.run_asset_classifier()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Classification results saved to: {args.output}")
            print(f"🧠 Classification Status: COMPLETED")
            print(f"📋 Summary: {results['summary']}")

        elif args.build_suppliers:
            results = brain.build_supplier_master()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Supplier master results saved to: {args.output}")
            print(f"🏗️ Suppliers Created: {results['suppliers_created']}")

        elif args.build_certificates:
            results = brain.build_certificate_master()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Certificate master results saved to: {args.output}")
            print(f"📜 Certificates Created: {results['certificates_created']}")

        elif args.build_els:
            results = brain.build_els()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ ELMS results saved to: {args.output}")
            print(f"🏷️ Labels Created: {results['labels_created']}")

        elif args.build_customers:
            results = brain.build_customer_domain()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Customer domain results saved to: {args.output}")
            print(f"👥 Customers Created: {results['customers_created']}")

        elif args.build_analytics:
            results = brain.build_analytics_layer()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Analytics results saved to: {args.output}")
            print(f"📊 Analytics Status: {results['status']}")

        elif args.build_logistics:
            results = brain.build_logistics_system()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Logistics results saved to: {args.output}")
            print(f"🚛 Logistics Status: {results['status']}")

        elif args.build_finance:
            results = brain.build_finance_system()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Finance results saved to: {args.output}")
            print(f"💰 Finance Status: {results['status']}")

        elif args.build_inventory:
            results = brain.build_inventory_system()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Inventory results saved to: {args.output}")
            print(f"📦 Inventory Status: {results['status']}")

        elif args.build_crm:
            results = brain.build_crm_system()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ CRM results saved to: {args.output}")
            print(f"👤 CRM Status: {results['status']}")

        elif args.daily:
            results = brain.run_daily_audit()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Daily audit saved to: {args.output}")
            print(f"🏁 Daily Audit Status: {results['overall_status']}")

        elif args.monitor:
            brain.run_periodic_monitoring(30)

        elif args.schedule:
            brain.run_scheduler_mode()

        elif args.cleanup:
            results = brain.run_unified_cleanup()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Cleanup results saved to: {args.output}")
            print(f"🏁 Cleanup Status: {results['status']}")

        elif args.evolve:
            results = brain.run_continuous_evolution_cycle()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Evolution results saved to: {args.output}")
            print(f"🧬 Evolution Status: {results['status']}")

        elif args.deep_clean:
            results = brain.run_deep_clean()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Deep clean results saved to: {args.output}")
            print(f"🧹 Critical Kept: {results['critical_kept']}")

        elif args.master_data_audit:
            results = brain.run_master_data_audit()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Audit results saved to: {args.output}")
            print(f"📊 Product Sources Found: {len(results['sources'])}")

        elif args.build_packaging_visual:
            results = brain.build_packaging_visual_engine()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Packaging visual results saved to: {args.output}")
            print(f"🎨 Products Processed: {results['products_processed']}")

        elif args.generate_labels_visual:
            results = brain.generate_gels_labels_with_visuals()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Labels results saved to: {args.output}")
            print(f"📜 Labels Created: {results['labels_created']}")

        elif args.deep_packaging_audit:
            results = brain.run_deep_packaging_audit()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Deep packaging audit results saved to: {args.output}")
            print(f"🔍 Total Packaging Files Found: {len(results['files_found'])}")

        elif args.integrate_business_assets:
            results = brain.integrate_business_assets()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Business assets results saved to: {args.output}")
            print(f"🌍 Markets Files Found: {results['markets_found']}")

        elif args.validate:
            results = brain.run_canonical_validation()
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Validation results saved to: {args.output}")
            print(f"🔍 Validation Status: {results['validation_status']}")

        elif args.consolidate:
            print("⚠️ This will move/archive files based on classification_report_v3.json.")
            confirm = input("Do you want to proceed? (yes/no): ")
            if confirm.lower() == "yes":
                dry_run = input("Run in dry-run mode? (yes/no, recommended yes): ")
                if dry_run.lower() != "no":
                    results = brain.run_consolidation(dry_run=True)
                    print("✅ DRY RUN COMPLETED.")
                else:
                    results = brain.run_consolidation(dry_run=False)
            else:
                print("❌ Consolidation cancelled.")
                sys.exit(0)
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                print(f"✅ Consolidation results saved to: {args.output}")
            print(f"📋 Summary: {results['summary']}")

        else:
            parser.print_help()

    except KeyboardInterrupt:
        print("\n⏹️ Execution interrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
