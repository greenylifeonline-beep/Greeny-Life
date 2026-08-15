# 📚 Greeny-Life EOS - Auto-Generated Documentation

Generated on: 2026-08-05 15:53:33

## Project Structure

```
├── __tests__
├── alerts
│   ├── alerts_20260804.log
│   └── alerts_20260805.log
├── analytics_report.json
├── app
│   ├── api
│   │   ├── products
│   │   │   └── route.ts
│   │   ├── sales-orders
│   │   │   └── route.ts
│   │   ├── suppliers
│   │   │   └── route.ts
│   │   └── workflow
│   │       └── route.ts
│   ├── assets
│   │   ├── css
│   │   ├── images
│   │   │   ├── categories
│   │   │   │   ... (more)
│   │   │   └── products
│   │   │       ... (more)
│   │   └── logos
│   ├── js
│   │   └── script.js
│   ├── layout.tsx
│   ├── page.tsx
│   └── views
│       └── products.html
├── application
│   ├── customer
│   │   ├── commands
│   │   │   └── customer-command.ts
│   │   ├── queries
│   │   │   └── customer-query.ts
│   │   └── workflows
│   │       └── customer-workflow.ts
│   ├── inventory
│   │   ├── commands
│   │   │   └── inventory-command.ts
│   │   ├── queries
│   │   │   └── inventory-query.ts
│   │   └── workflows
│   │       └── inventory-workflow.ts
│   ├── logistics
│   │   ├── commands
│   │   │   └── logistics-command.ts
│   │   ├── queries
│   │   │   └── logistics-query.ts
│   │   └── workflows
│   │       └── logistics-workflow.ts
│   ├── product
│   │   ├── commands
│   │   │   └── product-command.ts
│   │   ├── queries
│   │   │   └── product-query.ts
│   │   └── workflows
│   │       └── product-workflow.ts
│   ├── quality
│   │   ├── commands
│   │   │   └── quality-command.ts
│   │   ├── queries
│   │   │   └── quality-query.ts
│   │   └── workflows
│   │       └── quality-workflow.ts
│   └── supplier
│       ├── commands
│       │   └── supplier-command.ts
│       ├── queries
│       │   └── supplier-query.ts
│       └── workflows
│           └── supplier-workflow.ts
├── archive
│   ├── duplicates
│   │   ├── __init__.py
│   │   ├── canonical-product-master-v1.json
│   │   ├── cleanup_report.json
│   │   ├── export-operations-runtime-activation-registry-v1.json
│   │   ├── export-production-release-certificate-v1.json
│   │   ├── gels-normalized-registry-v1.json
│   │   ├── guardrails.jsonl
│   │   ├── index.ts
│   │   ├── links.jsonl
│   │   ├── README.md
│   │   ├── references.jsonl
│   │   └── taxonomy.json
│   ├── historical
│   │   ├── __tests__
│   │   │   └── workflowEngine.test.ts
│   │   ├── app
│   │   │   └── views
│   │   │       ... (more)
│   │   ├── docs
│   │   │   └── architecture
│   │   │       ... (more)
│   │   ├── governance
│   │   │   ├── eos-critical-product-assets-v1.json
│   │   │   └── eos-real-product-master-v2.json
│   │   ├── GREENY-LIFE-EOS-KNOWLEDGE-BASE-V1
│   │   │   ├── Architecture
│   │   │   │   ... (more)
│   │   │   └── Master-Data
│   │   │       ... (more)
│   │   ├── intelligence
│   │   │   ├── api-application-connection-analysis.json
│   │   │   ├── eos-api-event-discovery.json
│   │   │   ├── eos-api-runtime-trace.json
│   │   │   ├── eos-application-activation-readiness.json
│   │   │   ├── eos-business-flow-execution-proof.json
│   │   │   ├── eos-deep-business-logic-discovery.json
│   │   │   ├── eos-enterprise-operating-model-v1.json
│   │   │   ├── eos-real-business-flow-reconstruction.json
│   │   │   ├── eos-real-logic-ownership-map.json
│   │   │   ├── eos-runtime-alignment-map.json
│   │   │   ├── eos-service-boundary-map-v1.json
│   │   │   ├── existing-api-pattern-extraction.json
│   │   │   ├── existing-domain-ownership.json
│   │   │   ├── final-structure-audit.json
│   │   │   ├── final-structure-check.json
│   │   │   ├── intelligence
│   │   │   │   ... (more)
│   │   │   ├── review-folder-analysis.json
│   │   │   ├── typescript-asset-inventory.json
│   │   │   └── workflow-engine-alignment-validation.json
│   │   ├── KNOWLEDGE-BASE
│   │   │   ├── INDEX
│   │   │   │   ... (more)
│   │   │   └── Legacy-Reference
│   │   │       ... (more)
│   │   └── scripts
│   │       ├── extract_product_master.py
│   │       ├── integrity-check.js
│   │       ├── migrate-schema.js
│   │       ├── system_analyzer.py
│   │       └── validate-schema.js
│   ├── old-dependencies
│   ├── old_folders
│   │   ├── GREENY-LIFE-EOS
│   │   │   └── governance
│   │   │       ... (more)
│   │   ├── GREENY-LIFE-EOS-FINAL
│   │   │   ├── 03_PRODUCTS
│   │   │   │   ... (more)
│   │   │   └── 10_GOVERNANCE
│   │   │       ... (more)
│   │   ├── GREENY-LIFE-EOS-PRODUCTION
│   │   │   ├── activation
│   │   │   │   ... (more)
│   │   │   ├── ai
│   │   │   │   ... (more)
│   │   │   ├── ai-decision-engine-report-v1.json
│   │   │   ├── ai-intelligence-engine-report-v1.json
│   │   │   ├── analytics
│   │   │   │   ... (more)
│   │   │   ├── api-engine-report-v1.json
│   │   │   ├── apps
│   │   │   │   ... (more)
│   │   │   ├── auth-runtime-engine-report-v1.json
│   │   │   ├── business-flow-map-v1.json
│   │   │   ├── core
│   │   │   │   ... (more)
│   │   │   ├── crm
│   │   │   │   ... (more)
│   │   │   ├── database
│   │   │   │   ... (more)
│   │   │   ├── enterprise-automation-report-v1.json
│   │   │   ├── enterprise-control-center-v1
│   │   │   │   ... (more)
│   │   │   ├── enterprise-integration-report-v1.json
│   │   │   ├── erp
│   │   │   │   ... (more)
│   │   │   ├── frontend
│   │   │   │   ... (more)
│   │   │   ├── global-export-os-report-v1.json
│   │   │   ├── global-market-intelligence-report-v1.json
│   │   │   ├── global-partner-network-report-v1.json
│   │   │   ├── infrastructure
│   │   │   │   ... (more)
│   │   │   ├── intelligence
│   │   │   │   ... (more)
│   │   │   ├── master-data
│   │   │   │   ... (more)
│   │   │   ├── operations
│   │   │   │   ... (more)
│   │   │   ├── platform
│   │   │   │   ... (more)
│   │   │   ├── production-manifest-v1.json
│   │   │   ├── production-readiness-report-v1.json
│   │   │   ├── real-operation-report-v1.json
│   │   │   ├── runtime-governance-report-v1.json
│   │   │   ├── security
│   │   │   │   ... (more)
│   │   │   └── services
│   │   │       ... (more)
│   │   └── unified-intelligence
│   │       ├── active-foundation
│   │       │   ... (more)
│   │       ├── adapters
│   │       │   ... (more)
│   │       ├── archive
│   │       │   ... (more)
│   │       ├── contracts
│   │       │   ... (more)
│   │       ├── governance
│   │       │   ... (more)
│   │       ├── intelligence
│   │       │   ... (more)
│   │       ├── knowledge
│   │       │   ... (more)
│   │       ├── master-data
│   │       │   ... (more)
│   │       ├── memory
│   │       │   ... (more)
│   │       ├── reports
│   │       │   ... (more)
│   │       ├── runtime
│   │       │   ... (more)
│   │       └── scripts
│   │           ... (more)
│   └── old_product_sources
│       ├── archive-products-v6.json
│       ├── archive-products.json
│       ├── enterprise-master-data-freeze-v1.json
│       ├── export-catalog-master-v1.json
│       ├── export-master-data-final-integrity-report-v1.json
│       ├── export-product-release-manifest-v1.json
│       ├── final-product-master-v7.json
│       ├── GELS-product-links-v1.json
│       ├── master-data-cleaning-report-v1.json
│       ├── master-data-key-alignment-report-v1.json
│       ├── master-registry-v1.json
│       ├── product-id-reconciliation-report-v1.json
│       ├── removed-products.json
│       └── review-products.json
├── audit_report.json
├── backup
├── brain.py
├── canonical
│   ├── analytics
│   │   ├── customer-lifetime-value.json
│   │   ├── inventory-summary.json
│   │   ├── revenue-by-market.json
│   │   ├── sales-summary.json
│   │   └── top-products.json
│   ├── app
│   │   ├── api
│   │   │   ├── products
│   │   │   │   ... (more)
│   │   │   ├── sales-orders
│   │   │   │   ... (more)
│   │   │   ├── suppliers
│   │   │   │   ... (more)
│   │   │   └── workflow
│   │   │       ... (more)
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── brain.py
│   ├── classification_report_v2.json
│   ├── cleanup_report.json
│   ├── crm
│   │   ├── crm-automation-v1.json
│   │   ├── customer-analytics-v1.json
│   │   ├── customer-flow-v1.json
│   │   ├── customers.json
│   │   ├── interactions.json
│   │   ├── opportunities.json
│   │   └── opportunity-model.json
│   ├── data
│   │   ├── certificates.json
│   │   ├── customer-domain
│   │   │   ├── customer-contacts.json
│   │   │   ├── customer-product-demand-map.json
│   │   │   ├── customer-product-preferences.json
│   │   │   ├── customer-segments.json
│   │   │   ├── customers.json
│   │   │   ├── opportunities.json
│   │   │   └── orders.json
│   │   ├── customer-specification-registry-v1.json
│   │   ├── export-compliance-gap-analysis-v1.json
│   │   ├── export-compliance-remediation-report-v1.json
│   │   ├── export-go-live-gate-report-v1.json
│   │   ├── export-operations-process-map-v1.json
│   │   ├── export-readiness-remediation-plan-v1.json
│   │   ├── export-readiness-report-v1.json
│   │   ├── gels-compliance-remediation-v1.json
│   │   ├── gels-governance-gate-report-v1.json
│   │   ├── gels-intelligent-match-report-v1.json
│   │   ├── global-export-visual-system-v1
│   │   │   └── final-visual-system-report-v1.json
│   │   ├── live-normalized-v1
│   │   │   └── normalized-business-registry.json
│   │   ├── master_products.json
│   │   ├── packaging-gels-registry-v1.json
│   │   ├── product-certificate-links.json
│   │   ├── product-cleaning-v2
│   │   ├── product-cleaning-v4
│   │   ├── product-master-v7
│   │   ├── reconciliation-v1
│   │   ├── supplier-product-links.json
│   │   └── suppliers.json
│   ├── docs
│   │   ├── architecture
│   │   │   ├── eos_architecture
│   │   │   │   ... (more)
│   │   │   └── SYSTEM_ARCHITECTURE.md
│   │   ├── auto-generated
│   │   │   └── INDEX.md
│   │   ├── legacy_brand.md
│   │   ├── migrated_brand.md
│   │   ├── products
│   │   │   └── PRODUCT_MASTER.md
│   │   ├── README.md
│   │   └── standards
│   │       └── 01_BRAND_STANDARD.md
│   ├── final_audit.json
│   ├── finance
│   │   ├── export-flows.json
│   │   ├── finance-flow-v1.json
│   │   ├── finance-master.json
│   │   ├── finance.sql
│   │   ├── invoices.json
│   │   ├── payments.json
│   │   └── workflows.json
│   ├── governance
│   │   ├── eos-assets-registry-v1.json
│   │   ├── eos-deep-asset-discovery-v1.json
│   │   ├── eos-knowledge-registry-v1.json
│   │   ├── keep-assets-files-v1.json
│   │   ├── keep-core-files-v1.json
│   │   └── review-required-files-v1.json
│   ├── intelligence
│   │   ├── adapters
│   │   │   └── gl-dos-governance-gate.ts
│   │   ├── architecture.manifest.json
│   │   ├── asset_classification_report_v2.json
│   │   ├── cleanup_report.json
│   │   ├── comprehensive_report.json
│   │   ├── contracts
│   │   │   └── execution-contract.json
│   │   ├── eos-business-contract-discovery.json
│   │   ├── eos-domain-activation-blueprint-v1.json
│   │   ├── eos-enterprise-architecture-final.json
│   │   ├── eos-execution-truth-map.json
│   │   ├── eos-gels-architecture-alignment.json
│   │   ├── eos-gldos-architecture-alignment.json
│   │   ├── eos-intelligent-domain-ownership-graph.json
│   │   ├── eos-real-execution-path-map.json
│   │   ├── eos-roadmap-readiness.json
│   │   ├── foundation-closure-report-final.json
│   │   ├── intelligence
│   │   │   ├── core
│   │   │   │   ... (more)
│   │   │   ├── engines
│   │   │   │   ... (more)
│   │   │   ├── gl-dos.ts
│   │   │   ├── health
│   │   │   │   ... (more)
│   │   │   ├── intelligence-test.ts
│   │   │   └── schemas
│   │   │       ... (more)
│   │   ├── README.md
│   │   └── runtime
│   │       └── controlled-runtime-orchestrator.ts
│   ├── inventory
│   │   ├── inventory-analytics-v1.json
│   │   ├── inventory-automation-v1.json
│   │   ├── inventory-control-v1.json
│   │   ├── inventory-master-v1.json
│   │   ├── Inventory.js
│   │   ├── inventory.sql
│   │   ├── movements.json
│   │   ├── stock-levels.json
│   │   ├── typescript-asset-inventory.json
│   │   └── warehouses.json
│   ├── KNOWLEDGE-BASE
│   │   ├── AI-INTELLIGENCE-DISCOVERY-REPORT.json
│   │   ├── INDEX
│   │   │   └── reconciliation
│   │   │       ... (more)
│   │   ├── KEEP-PACKAGE
│   │   │   └── GELS
│   │   │       ... (more)
│   │   └── MASTER-SOURCE
│   │       └── MASTER-TRUTH-v1.json
│   ├── labels
│   │   ├── GL-LBL-BEE-004.json
│   │   ├── GL-LBL-BEE-005.json
│   │   ├── GL-LBL-BEE-006.json
│   │   ├── GL-LBL-BEE-007.json
│   │   ├── GL-LBL-HON-001.json
│   │   ├── GL-LBL-HON-002.json
│   │   ├── GL-LBL-HON-003.json
│   │   ├── GL-LBL-HRB-014.json
│   │   ├── GL-LBL-OIL-015.json
│   │   ├── GL-LBL-SPC-008.json
│   │   ├── GL-LBL-SPC-009.json
│   │   ├── GL-LBL-SPC-010.json
│   │   ├── GL-LBL-SPC-011.json
│   │   ├── GL-LBL-SPC-012.json
│   │   ├── GL-LBL-SPC-013.json
│   │   └── labels-index.json
│   ├── legacy-data
│   │   ├── canonical-product-master-v1.json
│   │   ├── eos-real-product-master-v2.json
│   │   ├── gels-normalized-registry-v1.json
│   │   ├── product-asset-link-map-v1.json
│   │   └── typescript-asset-inventory.json
│   ├── lib
│   │   └── workflowEngine.ts
│   ├── logistics
│   │   ├── logistics.sql
│   │   ├── shipments.json
│   │   └── tracking-summary.json
│   ├── media
│   ├── prisma
│   │   └── schema.prisma
│   ├── scripts
│   │   └── seed_master_products.ts
│   └── system_manifest.json
├── certificate_report.json
├── certificate_report_v2.json
├── certificate_report_v3.json
├── certificate_report_v4.json
├── certs_confirm.json
├── classification_report_v2.json
├── cleanup_report.json
├── components
│   ├── layout
│   ├── sections
│   └── ui
├── config.yaml
├── consolidation_report_final.json
├── consolidation_report_full.json
├── crm_report.json
├── customer_report.json
├── data
│   ├── ai-image-generation-v1
│   ├── ai-packaging-mockup-v1
│   ├── ai-product-branding-v1
│   ├── customer-specification-registry-v1.json
│   ├── export-compliance-gap-analysis-v1.json
│   ├── export-compliance-remediation-report-v1.json
│   ├── export-go-live-gate-report-v1.json
│   ├── export-operations-process-map-v1.json
│   ├── export-readiness-remediation-plan-v1.json
│   ├── export-readiness-report-v1.json
│   ├── final-product-portfolio-v1
│   ├── gels-compliance-remediation-v1.json
│   ├── gels-governance-gate-report-v1.json
│   ├── gels-intelligent-match-report-v1.json
│   ├── global-export-visual-system-v1
│   │   └── final-visual-system-report-v1.json
│   ├── live-normalized-v1
│   │   └── normalized-business-registry.json
│   ├── packaging-gels-registry-v1.json
│   ├── product-cleaning-v1
│   ├── product-cleaning-v2
│   ├── product-cleaning-v4
│   ├── product-cleaning-v6
│   ├── product-master-v7
│   └── reconciliation-v1
├── database
│   ├── connections
│   │   └── index.ts
│   ├── indexes
│   │   └── README.md
│   ├── migrations
│   ├── models
│   │   ├── entities.ts
│   │   └── index.ts
│   ├── repositories
│   │   ├── index.ts
│   │   └── repository-contracts.ts
│   ├── schemas
│   │   ├── core
│   │   │   └── enterprise-schema.ts
│   │   ├── domain
│   │   │   └── domain-schema.ts
│   │   └── index.ts
│   ├── seed
│   └── seeds
├── deep_clean_report.json
├── deep_clean_report_v2.json
├── docs
│   ├── architecture
│   │   ├── architecture
│   │   │   └── application-architecture
│   │   │       ... (more)
│   │   ├── eos_architecture
│   │   │   └── 01.Master_Data
│   │   │       ... (more)
│   │   └── SYSTEM_ARCHITECTURE.md
│   ├── auto-generated
│   │   └── INDEX.md
│   ├── calibration
│   │   └── improvement_claim_ledger.jsonl
│   ├── GOVERN_STOP.md
│   ├── improvements
│   │   └── 0000-template.md
│   ├── legacy_brand.md
│   ├── migrated_brand.md
│   ├── packaging
│   ├── products
│   │   └── PRODUCT_MASTER.md
│   ├── README.md
│   └── standards
│       └── 01_BRAND_STANDARD.md
├── domain
│   ├── customer
│   │   ├── entities
│   │   │   └── customer-entity.ts
│   │   ├── rules
│   │   │   └── customer-rules.ts
│   │   └── services
│   │       └── customer-service.ts
│   ├── inventory
│   │   ├── entities
│   │   │   └── inventory-entity.ts
│   │   ├── rules
│   │   │   └── inventory-rules.ts
│   │   └── services
│   │       └── inventory-service.ts
│   ├── logistics
│   │   ├── entities
│   │   │   └── logistics-entity.ts
│   │   ├── rules
│   │   │   └── logistics-rules.ts
│   │   └── services
│   │       └── logistics-service.ts
│   ├── product
│   │   ├── entities
│   │   │   └── product-entity.ts
│   │   ├── rules
│   │   │   └── product-rules.ts
│   │   └── services
│   │       └── product-service.ts
│   ├── quality
│   │   ├── entities
│   │   │   └── quality-entity.ts
│   │   ├── rules
│   │   │   └── quality-rules.ts
│   │   └── services
│   │       └── quality-service.ts
│   └── supplier
│       ├── entities
│       │   └── supplier-entity.ts
│       ├── rules
│       │   └── supplier-rules.ts
│       └── services
│           └── supplier-service.ts
├── els_final.json
├── els_final_confirm.json
├── els_final_v2.json
├── els_report.json
├── els_report_final.json
├── els_report_final_v2.json
├── els_report_final_v4.json
├── els_report_final_v5.json
├── els_report_new.json
├── eos-core
│   ├── architecture
│   │   ├── architecture
│   │   │   └── application-architecture
│   │   │       ... (more)
│   │   └── eos_architecture
│   │       └── 01.Master_Data
│   │           ... (more)
│   ├── documentation
│   │   └── docs
│   │       ├── architecture
│   │       │   ... (more)
│   │       ├── auto-generated
│   │       │   ... (more)
│   │       ├── calibration
│   │       │   ... (more)
│   │       ├── improvements
│   │       │   ... (more)
│   │       ├── packaging
│   │       │   ... (more)
│   │       ├── products
│   │       │   ... (more)
│   │       └── standards
│   │           ... (more)
│   ├── governance
│   │   └── guardrails
│   ├── intelligence
│   │   └── intelligence
│   │       ├── analytics
│   │       │   ... (more)
│   │       ├── core
│   │       │   ... (more)
│   │       ├── decision-support
│   │       │   ... (more)
│   │       ├── engines
│   │       │   ... (more)
│   │       ├── health
│   │       │   ... (more)
│   │       ├── knowledge_base
│   │       │   ... (more)
│   │       ├── memory
│   │       │   ... (more)
│   │       ├── metrics
│   │       │   ... (more)
│   │       ├── recommendations
│   │       │   ... (more)
│   │       ├── reporting
│   │       │   ... (more)
│   │       ├── rules
│   │       │   ... (more)
│   │       ├── scanners
│   │       │   ... (more)
│   │       ├── schemas
│   │       │   ... (more)
│   │       └── test
│   │           ... (more)
│   ├── master-data
│   │   └── master-data
│   │       ├── contracts
│   │       │   ... (more)
│   │       ├── events
│   │       │   ... (more)
│   │       ├── mapping
│   │       │   ... (more)
│   │       ├── schemas
│   │       │   ... (more)
│   │       └── validation
│   │           ... (more)
│   └── products
│       └── products_data
├── FileSummary.csv
├── final_audit.json
├── final_clean_audit.json
├── final_enterprise_audit.json
├── final_integration.json
├── final_integration_audit.json
├── final_pass_audit.json
├── finance_report.json
├── governance
│   ├── Audit-Packaging.ps1
│   ├── eos-assets-registry-v1.json
│   ├── eos-canonical-truth-registry-v1.json
│   ├── eos-deep-asset-discovery-v1.json
│   ├── eos-knowledge-registry-v1.json
│   ├── keep-assets-files-v1.json
│   ├── keep-core-files-v1.json
│   └── review-required-files-v1.json
├── GREENY-LIFE-EOS-KNOWLEDGE-BASE-V1
│   ├── Architecture
│   ├── Business-Flows
│   ├── Decisions
│   └── Master-Data
├── guardrails
│   ├── guardrails.jsonl
│   ├── links.jsonl
│   ├── references.jsonl
│   └── taxonomy.json
├── ImageInventory.csv
├── infrastructure
│   └── database
├── intelligence
│   ├── active-foundation
│   ├── adapters
│   │   └── gl-dos-governance-gate.ts
│   ├── analytics-validation-report.json
│   ├── architecture.manifest.json
│   ├── archive-intelligence-report.json
│   ├── asset_classification_report_v2.json
│   ├── certificate-validation-report.json
│   ├── cleanup_report.json
│   ├── comprehensive_report.json
│   ├── comprehensive_report.md
│   ├── contracts
│   │   └── execution-contract.json
│   ├── crm-validation-report.json
│   ├── customer-validation-report.json
│   ├── daily_reports
│   │   └── daily_audit_20260805.json
│   ├── deep_clean_report.json
│   ├── eos-business-contract-discovery.json
│   ├── eos-domain-activation-blueprint-v1.json
│   ├── eos-domain-api-ownership.json
│   ├── eos-domain-connection-matrix.json
│   ├── eos-domain-runtime-ownership-map.json
│   ├── eos-enterprise-architecture-final.json
│   ├── eos-execution-truth-map.json
│   ├── eos-final-enterprise-blueprint-package-v1.json
│   ├── eos-gels-architecture-alignment.json
│   ├── eos-gldos-architecture-alignment.json
│   ├── eos-intelligent-domain-ownership-graph.json
│   ├── eos-real-execution-path-map.json
│   ├── eos-roadmap-readiness.json
│   ├── executive-ai-decision-engine-v1
│   ├── finance-validation-report.json
│   ├── foundation-closure-report-final.json
│   ├── gels-validation-report.json
│   ├── generated_labels
│   ├── generated_specs
│   ├── global-export-intelligence-v1
│   ├── intelligence
│   │   ├── analytics
│   │   │   └── index.ts
│   │   ├── core
│   │   │   └── report-writer.ts
│   │   ├── decision-support
│   │   │   └── index.ts
│   │   ├── engines
│   │   │   ├── audit-engine.ts
│   │   │   └── data-integrity-engine.ts
│   │   ├── gl-dos.ts
│   │   ├── health
│   │   │   └── health-reporter.ts
│   │   ├── intelligence-test.ts
│   │   ├── knowledge_base
│   │   ├── memory
│   │   ├── metrics
│   │   │   └── index.ts
│   │   ├── recommendations
│   │   │   └── index.ts
│   │   ├── reporting
│   │   │   └── index.ts
│   │   ├── rules
│   │   ├── scanners
│   │   │   └── system-scanner.ts
│   │   ├── schemas
│   │   │   └── product-schema-map.ts
│   │   └── test
│   ├── inventory-validation-report.json
│   ├── knowledge_base
│   │   ├── project_metadata.json
│   │   └── tools_manifest.json
│   ├── logistics-validation-report.json
│   ├── master-data-integrity-report.json
│   ├── README.md
│   ├── runtime
│   │   └── controlled-runtime-orchestrator.ts
│   ├── scripts
│   │   └── phase-2-capability-discovery.ps1
│   ├── supplier-validation-report.json
│   └── supply-chain-intelligence-v1
├── inventory_report.json
├── KNOWLEDGE-BASE
│   ├── AI-INTELLIGENCE-DISCOVERY-REPORT.json
│   ├── Architecture
│   │   └── architecture-files.csv
│   ├── ARCHIVE
│   │   └── Legacy-Reference
│   ├── CANONICAL
│   │   ├── Activation
│   │   ├── Customer
│   │   ├── GELS
│   │   ├── Operations
│   │   ├── Product
│   │   ├── Release
│   │   └── Supplier
│   ├── INDEX
│   │   └── reconciliation
│   │       └── RECONCILIATION-SUMMARY.json
│   ├── KEEP-PACKAGE
│   │   ├── Activation
│   │   ├── GELS
│   │   │   └── gels-normalized-registry-v1.json
│   │   └── Product
│   ├── Legacy-Reference
│   │   └── data-legacy
│   ├── Master-Data
│   └── MASTER-SOURCE
│       └── MASTER-TRUTH-v1.json
├── lib
│   ├── data
│   └── workflowEngine.ts
├── logistics_report.json
├── logs
│   ├── brain-20260804.log
│   └── brain-20260805.log
├── migration-engine
│   ├── queue
│   └── staging
│       └── master-data
├── prisma
│   ├── migrations
│   │   └── 20260724234453_enterprise_eos_v1
│   └── schema.prisma
├── public
├── scripts
│   ├── repair-canonical-products.ps1
│   └── seed_master_products.ts
├── services
├── shared
│   ├── constants
│   ├── errors
│   ├── schemas
│   ├── types
│   ├── utilities
│   │   └── index.ts
│   └── validators
│       └── index.ts
├── src
│   ├── administration
│   ├── analytics
│   ├── compliance
│   ├── crm
│   │   └── customer-intelligence-engine-v1
│   ├── finance
│   ├── gl_dos
│   ├── logistics
│   ├── master_data
│   └── operations
├── supplier_report.json
├── supplier_report_v2.json
├── supplier_report_v3.json
├── supplier_report_v4.json
├── suppliers_confirm.json
├── system_manifest.json
├── tests
│   └── performance
│       ├── __init__.py
│       ├── results.json
│       └── smoke_test.js
└── validation_report.json

```

## Source Modules

### administration (0 files)

### analytics (0 files)

### compliance (0 files)

### crm (0 files)

### finance (0 files)

### gl_dos (0 files)

### logistics (0 files)

### master_data (0 files)

### operations (0 files)

