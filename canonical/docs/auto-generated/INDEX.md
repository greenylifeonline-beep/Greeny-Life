# 📚 Greeny-Life EOS - Auto-Generated Documentation

Generated on: 2026-08-04 21:55:53

## Project Structure

```
├── __tests__
│   └── workflowEngine.test.ts
├── AI-CORE-FILES.txt
├── alerts
│   └── alerts_20260804.log
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
│   │   │   └── style.css
│   │   ├── images
│   │   │   ├── categories
│   │   │   │   ... (more)
│   │   │   └── products
│   │   │       ... (more)
│   │   └── logos
│   │       └── logo.jpg
│   ├── globals.css
│   ├── js
│   │   └── script.js
│   ├── layout.tsx
│   ├── page.tsx
│   └── views
│       ├── about.html
│       ├── contact.html
│       ├── home.html
│       ├── packaging.html
│       ├── product.html
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
│   │   ├── final-product-master-v7.json
│   │   ├── gels-normalized-registry-v1.json
│   │   ├── gels-v1.json
│   │   ├── guardrails.jsonl
│   │   ├── index.ts
│   │   ├── links.jsonl
│   │   ├── README.md
│   │   ├── references.jsonl
│   │   └── taxonomy.json
│   └── old_folders
│       ├── GREENY-LIFE-EOS
│       │   └── governance
│       │       ... (more)
│       ├── GREENY-LIFE-EOS-FINAL
│       │   ├── 03_PRODUCTS
│       │   │   ... (more)
│       │   └── 10_GOVERNANCE
│       │       ... (more)
│       ├── GREENY-LIFE-EOS-PRODUCTION
│       │   ├── activation
│       │   │   ... (more)
│       │   ├── ai
│       │   │   ... (more)
│       │   ├── ai-decision-engine-report-v1.json
│       │   ├── ai-intelligence-engine-report-v1.json
│       │   ├── analytics
│       │   │   ... (more)
│       │   ├── api-engine-report-v1.json
│       │   ├── apps
│       │   │   ... (more)
│       │   ├── auth-runtime-engine-report-v1.json
│       │   ├── business-flow-map-v1.json
│       │   ├── core
│       │   │   ... (more)
│       │   ├── crm
│       │   │   ... (more)
│       │   ├── database
│       │   │   ... (more)
│       │   ├── enterprise-automation-report-v1.json
│       │   ├── enterprise-control-center-v1
│       │   │   ... (more)
│       │   ├── enterprise-integration-report-v1.json
│       │   ├── erp
│       │   │   ... (more)
│       │   ├── frontend
│       │   │   ... (more)
│       │   ├── global-export-os-report-v1.json
│       │   ├── global-market-intelligence-report-v1.json
│       │   ├── global-partner-network-report-v1.json
│       │   ├── infrastructure
│       │   │   ... (more)
│       │   ├── intelligence
│       │   │   ... (more)
│       │   ├── master-data
│       │   │   ... (more)
│       │   ├── operations
│       │   │   ... (more)
│       │   ├── platform
│       │   │   ... (more)
│       │   ├── production-manifest-v1.json
│       │   ├── production-readiness-report-v1.json
│       │   ├── real-operation-report-v1.json
│       │   ├── runtime-governance-report-v1.json
│       │   ├── security
│       │   │   ... (more)
│       │   └── services
│       │       ... (more)
│       └── unified-intelligence
│           ├── active-foundation
│           │   ... (more)
│           ├── adapters
│           │   ... (more)
│           ├── archive
│           │   ... (more)
│           ├── contracts
│           │   ... (more)
│           ├── governance
│           │   ... (more)
│           ├── intelligence
│           │   ... (more)
│           ├── knowledge
│           │   ... (more)
│           ├── master-data
│           │   ... (more)
│           ├── memory
│           │   ... (more)
│           ├── reports
│           │   ... (more)
│           ├── runtime
│           │   ... (more)
│           └── scripts
│               ... (more)
├── backup
├── brain.py
├── cleanup_report.json
├── components
│   ├── layout
│   │   ├── Footer.tsx
│   │   ├── Header.tsx
│   │   └── Navigation.tsx
│   ├── sections
│   │   ├── Collections.tsx
│   │   ├── Contact.tsx
│   │   └── Hero.tsx
│   └── ui
│       ├── Loader.tsx
│       ├── Modal.tsx
│       └── Toast.tsx
├── data
│   ├── 01_global.json
│   ├── 02_collections.json
│   ├── 03_packaging_system.json
│   ├── 04_packaging_profiles.json
│   ├── 05_master_products.json
│   ├── 06_markets.json
│   ├── 07_documents.json
│   ├── 08_media.json
│   ├── 09_design_system.json
│   ├── ai-image-generation-v1
│   │   ├── ai-image-generation-prompts-v1.json
│   │   └── ai-image-generation-report-v1.json
│   ├── ai-packaging-mockup-v1
│   │   ├── export-shelf-scenes-v1.json
│   │   ├── front-label-mockups-v1.json
│   │   ├── packaging-mockup-profiles-v1.json
│   │   └── packaging-validation-report-v1.json
│   ├── ai-product-branding-v1
│   │   ├── ai-branding-engine-report-v1.json
│   │   ├── ai-branding-master-v1.json
│   │   ├── product-image-prompts-v1.json
│   │   └── product-label-profiles-v1.json
│   ├── category-assets-registry-v1.json
│   ├── customer-specification-registry-v1.json
│   ├── customers.json
│   ├── documentation-remediation-v1.json
│   ├── enterprise-domain-registry-lock-v1.json
│   ├── enterprise-final-production-status-certificate-v1.json
│   ├── enterprise-master-data-freeze-v1.json
│   ├── enterprise-operational-command-center-v1.json
│   ├── enterprise-production-governance-v1.json
│   ├── enterprise-runtime-activation-registry-v1.json
│   ├── export-business-kpi-registry-v1.json
│   ├── export-catalog-master-v1.json
│   ├── export-compliance-gap-analysis-v1.json
│   ├── export-compliance-remediation-report-v1.json
│   ├── export-crm-control-report-v1.json
│   ├── export-customer-account-ledger-v1.json
│   ├── export-customer-delivery-report-v1.json
│   ├── export-customer-feedback-engine-v1.json
│   ├── export-customer-interaction-history-v1.json
│   ├── export-customer-master-registry-v1.json
│   ├── export-customer-order-registry-v1.json
│   ├── export-delivery-tracking-ledger-v1.json
│   ├── export-domain-health-check-v1.json
│   ├── export-domain-integration-gate-v1.json
│   ├── export-executive-intelligence-report-v1.json
│   ├── export-finance-settlement-report-v1.json
│   ├── export-go-live-gate-report-v1.json
│   ├── export-invoice-registry-v1.json
│   ├── export-logistics-control-tower-registry-v1.json
│   ├── export-logistics-control-tower-report-v1.json
│   ├── export-logistics-event-stream-v1.json
│   ├── export-logistics-kpi-monitor-v1.json
│   ├── export-margin-analysis-v1.json
│   ├── export-market-performance-report-v1.json
│   ├── export-market-ready-product-cards-v1.json
│   ├── export-master-data-final-integrity-report-v1.json
│   ├── export-operations-control-gate-v1.json
│   ├── export-operations-domain-activation-registry-v1.json
│   ├── export-operations-execution-readiness-registry-v1.json
│   ├── export-operations-execution-readiness-report-v1.json
│   ├── export-operations-handover-control-v1.json
│   ├── export-operations-process-map-v1.json
│   ├── export-operations-runtime-status-report-v1.json
│   ├── export-operations-workflow-runtime-map-v1.json
│   ├── export-order-fulfillment-engine-v1.json
│   ├── export-performance-dashboard-v1.json
│   ├── export-product-performance-analytics-v1.json
│   ├── export-product-release-manifest-v1.json
│   ├── export-readiness-remediation-plan-v1.json
│   ├── export-readiness-report-v1.json
│   ├── export-receivable-ledger-v1.json
│   ├── export-release-certificate-registry-v1.json
│   ├── export-release-package-registry-v1.json
│   ├── export-runtime-event-ledger-v1.json
│   ├── export-shipment-exception-engine-v1.json
│   ├── export-shipment-execution-map-v1.json
│   ├── export-shipment-lifecycle-registry-v1.json
│   ├── export-shipment-lifecycle-report-v1.json
│   ├── export-shipment-state-machine-v1.json
│   ├── final-product-portfolio-v1
│   │   └── archive-products.json
│   ├── gels-compliance-remediation-v1.json
│   ├── gels-governance-gate-report-v1.json
│   ├── gels-intelligent-match-report-v1.json
│   ├── global-export-visual-system-v1
│   │   ├── export-brand-book-v1.json
│   │   ├── final-product-visual-catalog-v1.json
│   │   ├── final-visual-system-report-v1.json
│   │   ├── GELS-compliance-check-v1.json
│   │   └── portfolio-presentation-v1.json
│   ├── legacy_brand.json
│   ├── legacy_categories.json
│   ├── legacy_certificates.json
│   ├── legacy_countries.json
│   ├── legacy_incoterms.json
│   ├── legacy_markets.json
│   ├── legacy_packaging.json
│   ├── legacy_products.json
│   ├── legacy_units.json
│   ├── live-normalized-v1
│   │   └── normalized-business-registry.json
│   ├── master-data-cleaning-report-v1.json
│   ├── master-data-key-alignment-report-v1.json
│   ├── master_products.json
│   ├── migrated_categories.json
│   ├── migrated_products.json
│   ├── opportunities.json
│   ├── packaging-gels-registry-v1.json
│   ├── packaging-reconciliation-report-v1.json
│   ├── packaging-registry-remediation-v1.json
│   ├── packaging_policies.json
│   ├── product-assets-registry-v1.json
│   ├── product-cleaning-v1
│   │   ├── final-product-portfolio.json
│   │   ├── product-master-profile.json
│   │   └── product-portfolio-cleaning-report-v1.json
│   ├── product-cleaning-v2
│   │   ├── cleaning-report.json
│   │   └── removed-products.json
│   ├── product-cleaning-v4
│   │   ├── cleaning-report.json
│   │   └── review-products.json
│   ├── product-cleaning-v6
│   │   ├── archive-products-v6.json
│   │   ├── cleaning-report-v6.json
│   │   └── final-product-portfolio-v6.json
│   ├── product-id-reconciliation-report-v1.json
│   ├── product-master-activation-registry-v1.json
│   ├── product-master-reconciliation-report-v1.json
│   ├── product-master-v7
│   │   ├── final-product-master-v7.json
│   │   ├── GELS-product-links-v1.json
│   │   └── product-branding-profile-v1.json
│   ├── product-master-validation-report-v1.json
│   ├── product_master_extended.json
│   ├── reconciliation-v1
│   │   └── master-registry-v1.json
│   ├── supplier-master-remediation-v1.json
│   ├── supplier-settlement-mapping-v1.json
│   └── suppliers.json
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
│   │   ├── administration.md
│   │   ├── analytics.md
│   │   ├── compliance.md
│   │   ├── crm.md
│   │   ├── finance.md
│   │   ├── gl_dos.md
│   │   ├── INDEX.md
│   │   ├── logistics.md
│   │   ├── master_data.md
│   │   └── operations.md
│   ├── calibration
│   │   └── improvement_claim_ledger.jsonl
│   ├── certificates_data.json
│   ├── GOVERN_STOP.md
│   ├── improvements
│   │   └── 0000-template.md
│   ├── legacy_brand.md
│   ├── migrated_brand.md
│   ├── packaging
│   │   ├── packaging_master.md
│   │   └── PACKING_CODES.md
│   ├── products
│   │   ├── PRODUCT_CODE.md
│   │   ├── PRODUCT_DATABASE.md
│   │   ├── PRODUCT_LIBRARY.md
│   │   ├── PRODUCT_MASTER.md
│   │   └── PRODUCT_TEMPLATE.md
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
│           └── catalog.json
├── evolution_report.json
├── final_audit.json
├── governance
│   ├── eos-asset-preservation-report-v1.json
│   ├── eos-assets-registry-v1.json
│   ├── eos-canonical-validation-report-v1.json
│   ├── eos-critical-product-assets-v1.json
│   ├── eos-deep-asset-discovery-v1.json
│   ├── eos-knowledge-registry-v1.json
│   ├── eos-real-product-master-v2.json
│   ├── keep-assets-files-v1.json
│   ├── keep-core-files-v1.json
│   ├── keep-knowledge-files-v1.json
│   └── review-required-files-v1.json
├── GREENY-LIFE-EOS-KNOWLEDGE-BASE-V1
│   ├── Architecture
│   │   └── architecture-extraction.csv
│   ├── Business-Flows
│   │   └── business-assets.csv
│   ├── Decisions
│   │   └── project-decisions.csv
│   ├── Master-Data
│   │   └── master-data-extraction.csv
│   └── source-index.csv
├── guardrails
│   ├── guardrails.jsonl
│   ├── links.jsonl
│   ├── references.jsonl
│   └── taxonomy.json
├── infrastructure
│   └── database
├── intelligence
│   ├── active-foundation
│   │   └── phase-32-closure-report.json
│   ├── adapters
│   │   ├── gl-dos-governance-gate.ts
│   │   ├── intelligence-adapter.ts
│   │   ├── master-data-adapter.ts
│   │   └── traceable-report-adapter.ts
│   ├── api-application-connection-analysis.json
│   ├── application-command-contract-discovery.json
│   ├── application-file-reality-check.json
│   ├── architecture.manifest.json
│   ├── asset-domain-classification.json
│   ├── cleanup_report.json
│   ├── command-signature-extraction.json
│   ├── comprehensive_report.json
│   ├── comprehensive_report.md
│   ├── contracts
│   │   ├── authority-registry.json
│   │   └── execution-contract.json
│   ├── daily_reports
│   ├── domain-integration-map-validation.json
│   ├── eos-api-event-discovery.json
│   ├── eos-api-runtime-trace.json
│   ├── eos-application-activation-readiness.json
│   ├── eos-audit-compliance-model-v1.json
│   ├── eos-business-contract-discovery.json
│   ├── eos-business-flow-execution-proof.json
│   ├── eos-core-consolidation-result.json
│   ├── eos-core-validation.json
│   ├── eos-database-architecture-alignment.json
│   ├── eos-database-boundary-validation-v1.json
│   ├── eos-deep-business-logic-discovery.json
│   ├── eos-deployment-architecture-v1.json
│   ├── eos-domain-activation-blueprint-v1.json
│   ├── eos-domain-api-ownership.json
│   ├── eos-domain-boundary-validation.json
│   ├── eos-domain-capability-matrix.json
│   ├── eos-domain-connection-matrix.json
│   ├── eos-domain-contracts-v1.json
│   ├── eos-domain-gap-closure-roadmap-v1.json
│   ├── eos-domain-maturity-gap-analysis-v1.json
│   ├── eos-domain-reality-report.json
│   ├── eos-domain-runtime-ownership-map.json
│   ├── eos-enterprise-architecture-final.json
│   ├── eos-enterprise-operating-model-v1.json
│   ├── eos-enterprise-readiness-validation-v1.json
│   ├── eos-event-architecture-map-v1.json
│   ├── eos-execution-truth-map.json
│   ├── eos-final-enterprise-blueprint-package-v1.json
│   ├── eos-gels-architecture-alignment.json
│   ├── eos-gldos-architecture-alignment.json
│   ├── eos-implementation-execution-engine-v1.json
│   ├── eos-implementation-roadmap-v1.json
│   ├── eos-intelligence-kpi-model-v1.json
│   ├── eos-intelligent-domain-ownership-graph.json
│   ├── eos-master-data-final-alignment.json
│   ├── eos-master-data-governance-model-v1.json
│   ├── eos-mvp-api-implementation-specification-v1.json
│   ├── eos-mvp-build-specification-v1.json
│   ├── eos-mvp-database-initialization-plan-v1.json
│   ├── eos-mvp-event-bus-implementation-v1.json
│   ├── eos-mvp-workflow-engine-implementation-v1.json
│   ├── eos-prisma-domain-ownership.json
│   ├── eos-production-operating-model-v1.json
│   ├── eos-rbac-access-control-model-v1.json
│   ├── eos-real-business-flow-reconstruction.json
│   ├── eos-real-execution-path-map.json
│   ├── eos-real-logic-ownership-map.json
│   ├── eos-roadmap-readiness.json
│   ├── eos-runtime-alignment-map.json
│   ├── eos-service-boundary-map-v1.json
│   ├── eos-workflow-state-machine-map-v1.json
│   ├── executive-ai-decision-engine-v1
│   │   ├── executive-ai-decision-report-v1.json
│   │   ├── executive-decision-matrix-v1.json
│   │   ├── executive-kpi-intelligence-v1.json
│   │   ├── management-action-center-v1.json
│   │   └── risk-monitoring-engine-v1.json
│   ├── existing-api-pattern-extraction.json
│   ├── existing-asset-discovery.json
│   ├── existing-business-flow-validation.json
│   ├── existing-domain-ownership.json
│   ├── final-cleanup-result.json
│   ├── final-structure-audit.json
│   ├── final-structure-check.json
│   ├── folder-classification.json
│   ├── foundation-closure-report-final.json
│   ├── generated_labels
│   ├── generated_specs
│   ├── global-export-intelligence-v1
│   │   ├── export-opportunity-ranking-v1.json
│   │   ├── global-export-intelligence-report-v1.json
│   │   └── product-country-market-matrix-v1.json
│   ├── greenylife-eos-final-map.json
│   ├── intelligence
│   │   ├── analytics
│   │   │   └── index.ts
│   │   ├── comprehensive_report.json
│   │   ├── comprehensive_report.md
│   │   ├── core
│   │   │   ├── confidence.ts
│   │   │   ├── engine-registry.ts
│   │   │   └── report-writer.ts
│   │   ├── decision-support
│   │   │   └── index.ts
│   │   ├── duplicate-engine.ts
│   │   ├── engines
│   │   │   ├── audit-engine.ts
│   │   │   ├── cleanup-engine.ts
│   │   │   ├── data-integrity-engine.ts
│   │   │   └── duplicate-engine-v2.ts
│   │   ├── gl-dos.ts
│   │   ├── health
│   │   │   └── health-reporter.ts
│   │   ├── index.ts
│   │   ├── intelligence-test.ts
│   │   ├── knowledge-base.json
│   │   ├── knowledge_base
│   │   │   ├── project_metadata.json
│   │   │   └── tools_manifest.json
│   │   ├── memory
│   │   │   └── project-memory.ts
│   │   ├── metrics
│   │   │   └── index.ts
│   │   ├── product-audit.ts
│   │   ├── project-memory.json
│   │   ├── project-scan.ts
│   │   ├── recommendations
│   │   │   └── index.ts
│   │   ├── reporting
│   │   │   └── index.ts
│   │   ├── rules
│   │   │   ├── duplicate-rules.ts
│   │   │   └── project.rules.json
│   │   ├── scanners
│   │   │   ├── duplicate-scanner.ts
│   │   │   ├── json-scanner.ts
│   │   │   └── system-scanner.ts
│   │   ├── schemas
│   │   │   └── product-schema-map.ts
│   │   └── test
│   │       ├── test-audit.ts
│   │       ├── test-cleanup.ts
│   │       ├── test-duplicate-v2.ts
│   │       ├── test-health.ts
│   │       ├── test-integrity.ts
│   │       └── test-registry.ts
│   ├── knowledge_base
│   │   ├── project_metadata.json
│   │   └── tools_manifest.json
│   ├── project-cleanup-result.json
│   ├── query-layer-reality-check.json
│   ├── README.md
│   ├── review-asset-content-analysis.json
│   ├── review-folder-analysis.json
│   ├── runtime
│   │   └── controlled-runtime-orchestrator.ts
│   ├── scripts
│   │   └── phase-2-capability-discovery.ps1
│   ├── supply-chain-intelligence-v1
│   │   ├── batch-traceability-intelligence-v1.json
│   │   ├── inventory-control-intelligence-v1.json
│   │   ├── shipment-readiness-score-v1.json
│   │   ├── supplier-product-mapping-v1.json
│   │   └── supply-chain-intelligence-report-v1.json
│   ├── typescript-asset-inventory.json
│   └── workflow-engine-alignment-validation.json
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
│   │   ├── canonical-source-candidates.csv
│   │   ├── CANONICAL-SOURCE-POLICY.txt
│   │   ├── project-manifest.csv
│   │   └── reconciliation
│   │       ├── execution-truth-reconciliation.csv
│   │       ├── gels-reconciliation.csv
│   │       ├── product-reconciliation.csv
│   │       ├── RECONCILIATION-SUMMARY.json
│   │       └── supplier-current.json
│   ├── KEEP-PACKAGE
│   │   ├── Activation
│   │   │   ├── export-operations-runtime-activation-registry-v1.json
│   │   │   └── export-production-release-certificate-v1.json
│   │   ├── GELS
│   │   │   └── gels-normalized-registry-v1.json
│   │   └── Product
│   │       └── canonical-product-master-v1.json
│   ├── Legacy-Reference
│   │   └── data-legacy
│   │       ├── categories.json
│   │       ├── category-extensions.json
│   │       ├── certificates.json
│   │       ├── countries.json
│   │       ├── incoterms.json
│   │       ├── legal-entities.json
│   │       ├── markets.json
│   │       ├── packaging.json
│   │       ├── product-variants.json
│   │       ├── product.schema.json
│   │       ├── products.json
│   │       └── units.json
│   ├── Master-Data
│   │   ├── activation-gap-analysis.csv
│   │   ├── KEEP-master-data.txt
│   │   ├── master-data-files.csv
│   │   └── master-data-priority-list.txt
│   └── MASTER-SOURCE
│       └── MASTER-TRUTH-v1.json
├── lib
│   ├── data
│   │   ├── collections.ts
│   │   ├── documents.ts
│   │   ├── global.ts
│   │   ├── markets.ts
│   │   ├── media.ts
│   │   ├── packaging-profiles.ts
│   │   ├── packaging.ts
│   │   └── products.ts
│   └── workflowEngine.ts
├── logs
│   └── brain-20260804.log
├── migration-engine
│   ├── queue
│   └── staging
│       └── master-data
├── prisma
│   ├── migrations
│   │   ├── 20260724234453_enterprise_eos_v1
│   │   │   └── migration.sql
│   │   └── migration_lock.toml
│   └── schema.prisma
├── public
├── requirements.txt
├── scripts
│   ├── audit-project.js
│   ├── backup-data.js
│   ├── execute_seed.py
│   ├── extract_product_master.py
│   ├── generate_sql_seed.py
│   ├── inspect_master_products.py
│   ├── integrity-check.js
│   ├── legacy_audit.py
│   ├── migrate-data.js
│   ├── migrate-schema.js
│   ├── repair-canonical-products.ps1
│   ├── seed_master_products.ts
│   ├── system_analyzer.py
│   └── validate-schema.js
├── services
│   └── api.ts
├── shared
│   ├── constants
│   ├── errors
│   ├── schemas
│   ├── types
│   ├── utilities
│   │   └── index.ts
│   ├── utils.js
│   └── validators
│       └── index.ts
├── src
│   ├── administration
│   ├── analytics
│   ├── compliance
│   ├── crm
│   │   └── customer-intelligence-engine-v1
│   │       ├── b2b-leads-engine-v1.json
│   │       ├── crm-intelligence-report-v1.json
│   │       ├── crm-sales-pipeline-v1.json
│   │       ├── customer-master-v1.json
│   │       └── customer-segmentation-v1.json
│   ├── finance
│   ├── gl_dos
│   ├── logistics
│   ├── master_data
│   └── operations
├── system_manifest.json
└── tests
    └── performance
        ├── __init__.py
        ├── results.json
        └── smoke_test.js

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

