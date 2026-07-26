# 📚 Greeny-Life EOS - Auto-Generated Documentation

Generated on: 2026-07-26 12:49:43

## Project Structure

```
├── (.env
├── __tests__
│   └── workflowEngine.test.ts
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
│   │   ├── fonts
│   │   ├── icons
│   │   ├── images
│   │   │   ├── categories
│   │   │   │   ... (more)
│   │   │   ├── certifications
│   │   │   │   ... (more)
│   │   │   ├── countries
│   │   │   │   ... (more)
│   │   │   ├── gallery
│   │   │   │   ... (more)
│   │   │   ├── hero
│   │   │   │   ... (more)
│   │   │   └── products
│   │   │       ... (more)
│   │   ├── logos
│   │   │   └── logo.jpg
│   │   ├── products
│   │   └── videos
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
├── app_tree.txt
├── backup
│   ├── 2026-07-17_18-51-09
│   │   ├── 01_global.json
│   │   ├── 02_collections.json
│   │   ├── 03_packaging_system.json
│   │   ├── 04_packaging_profiles.json
│   │   ├── 05_master_products.json
│   │   ├── 06_markets.json
│   │   ├── 07_documents.json
│   │   ├── 08_media.json
│   │   └── legacy
│   │       ├── brand.json
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
│   ├── 2026-07-18_13-18-28
│   │   ├── 01_global.json
│   │   ├── 02_collections.json
│   │   ├── 03_packaging_system.json
│   │   ├── 04_packaging_profiles.json
│   │   ├── 05_master_products.json
│   │   ├── 06_markets.json
│   │   ├── 07_documents.json
│   │   ├── 08_media.json
│   │   └── legacy
│   │       ├── brand.json
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
│   ├── 2026-07-18_13-21-54
│   │   ├── 01_global.json
│   │   ├── 02_collections.json
│   │   ├── 03_packaging_system.json
│   │   ├── 04_packaging_profiles.json
│   │   ├── 05_master_products.json
│   │   ├── 06_markets.json
│   │   ├── 07_documents.json
│   │   ├── 08_media.json
│   │   └── legacy
│   │       ├── brand.json
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
│   ├── 2026-07-18_13-49-51
│   │   ├── 01_global.json
│   │   ├── 02_collections.json
│   │   ├── 03_packaging_system.json
│   │   ├── 04_packaging_profiles.json
│   │   ├── 05_master_products.json
│   │   ├── 06_markets.json
│   │   ├── 07_documents.json
│   │   ├── 08_media.json
│   │   └── legacy
│   │       ├── brand.json
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
│   ├── deprecated_schemas
│   │   ├── entity.schema.json
│   │   └── products.schema.json
│   └── intelligence-old
├── BOUND.md
├── brain.py
├── cards
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
├── config
├── config.yaml
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
│   ├── customers.json
│   ├── legacy
│   │   ├── categories.json
│   │   ├── category-extensions.json
│   │   ├── certificates.json
│   │   ├── countries.json
│   │   ├── incoterms.json
│   │   ├── legal-entities.json
│   │   ├── markets.json
│   │   ├── packaging.json
│   │   ├── product-variants.json
│   │   ├── product.schema.json
│   │   ├── products.json
│   │   └── units.json
│   ├── legacy_brand.json
│   ├── legacy_categories.json
│   ├── legacy_certificates.json
│   ├── legacy_countries.json
│   ├── legacy_incoterms.json
│   ├── legacy_markets.json
│   ├── legacy_packaging.json
│   ├── legacy_products.json
│   ├── legacy_units.json
│   ├── migrated_categories.json
│   ├── migrated_products.json
│   ├── migration
│   │   ├── migration-history.json
│   │   └── migration-progress.json
│   ├── opportunities.json
│   ├── packaging_policies.json
│   ├── product_master_extended.json
│   └── suppliers.json
├── DOC_INDEX.txt
├── DOC_METADATA.csv
├── docs
│   ├── architecture
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
├── EOS-Connect-Brain.ps1
├── eos-health-report.json
├── EOS-HealthCheck.ps1
├── EOS-Setup-Environment.ps1
├── eos_architecture
│   ├── 01.Master_Data
│   │   ├── honey_reference.json
│   │   └── schema_v1.json
│   ├── 02.Gl-DOS
│   ├── 03.Operations
│   ├── 04.CRM
│   ├── 05.Logistics
│   ├── 06.Compliance
│   ├── 07.Finance
│   ├── 08.Analytics
│   └── 09.Administration
├── folders_tree.txt
├── forms
├── full_report.json
├── guardrails
│   ├── guardrails.jsonl
│   ├── links.jsonl
│   ├── references.jsonl
│   └── taxonomy.json
├── health.json
├── health_report.json
├── index.html
├── initial_inspection.json
├── intelligence
│   ├── backups
│   ├── comprehensive_report.json
│   ├── comprehensive_report.md
│   ├── core
│   │   ├── confidence.ts
│   │   ├── engine-registry.ts
│   │   └── report-writer.ts
│   ├── duplicate-engine.ts
│   ├── engines
│   │   ├── audit-engine.ts
│   │   ├── cleanup-engine.ts
│   │   ├── data-integrity-engine.ts
│   │   └── duplicate-engine-v2.ts
│   ├── gl-dos.ts
│   ├── health
│   │   └── health-reporter.ts
│   ├── index.ts
│   ├── intelligence-test.ts
│   ├── knowledge-base.json
│   ├── knowledge_base
│   │   ├── project_metadata.json
│   │   └── tools_manifest.json
│   ├── memory
│   │   └── project-memory.ts
│   ├── product-audit.ts
│   ├── project-memory.json
│   ├── project-scan.ts
│   ├── reports
│   │   ├── cleanup-plan.json
│   │   ├── duplicate-report.json
│   │   └── migration-decision.json
│   ├── rules
│   │   ├── duplicate-rules.ts
│   │   └── project.rules.json
│   ├── scanners
│   │   ├── duplicate-scanner.ts
│   │   ├── json-scanner.ts
│   │   └── system-scanner.ts
│   ├── schemas
│   │   └── product-schema-map.ts
│   └── test
│       ├── test-audit.ts
│       ├── test-cleanup.ts
│       ├── test-duplicate-v2.ts
│       ├── test-health.ts
│       ├── test-integrity.ts
│       └── test-registry.ts
├── legacy_audit_reports
│   ├── active_master_products.json
│   ├── legacy_system_inventory.json
│   ├── product_master_targets.json
│   └── seed_products.sql
├── lib
│   ├── data
│   │   ├── collections.ts
│   │   ├── documents.ts
│   │   ├── global.ts
│   │   ├── markets.ts
│   │   ├── media.ts
│   │   ├── packaging-profiles.ts
│   │   ├── packaging.ts
│   │   ├── products.ts
│   │   └── validators
│   ├── helpers
│   └── workflowEngine.ts
├── logo.png
├── logs
│   ├── brain-20260725.log
│   ├── brain-deep-run-20260725-123455.log
│   ├── brain-interactive-20260725-123742.log
│   ├── brain-master-20260725-123959.log
│   ├── brain-master-20260725-124338.log
│   ├── brain-master-20260725-124717.log
│   ├── brain-master-20260725-125108.log
│   ├── brain-run-20260724-212914.log
│   ├── brain-run-20260724-213838.log
│   ├── brain-run-20260724-213959.log
│   ├── brain-run-20260724-214046.log
│   └── brain-run-20260725-122942.log
├── middleware.ts
├── next-env.d.ts
├── package-lock.json
├── package.json
├── packaging
├── prisma
│   ├── migrations
│   │   ├── 20260724234453_enterprise_eos_v1
│   │   │   └── migration.sql
│   │   └── migration_lock.toml
│   └── schema.prisma
├── prisma.config.js
├── products_data
│   └── catalog.json
├── project-summary.txt
├── project-tree.txt
├── Project_Audit.txt
├── PROJECT_FILES.txt
├── project_tree.txt
├── public
│   ├── backgrounds
│   ├── brand
│   ├── certifications
│   ├── flags
│   ├── icons
│   ├── mokups
│   ├── packaging
│   └── products
├── Real_Project_Files.txt
├── reports
│   ├── cleanup-actions.json
│   ├── cleanup-plan.json
│   ├── cleanup-report.json
│   ├── db_health_report.json
│   ├── doc-metadata.csv
│   ├── duplicate-analysis.txt
│   ├── duplicate-report.json
│   ├── full-file-inventory.txt
│   ├── intelligence-scan.json
│   ├── intelligence-schema-report.json
│   ├── legacy-analysis.json
│   ├── legacy-archive.json
│   ├── legacy-assets.json
│   ├── legacy-components.json
│   ├── legacy-migration-plan.json
│   ├── legacy-progress.json
│   ├── legacy-refactor.json
│   ├── legacy-remove.json
│   ├── legacy-summary.json
│   ├── migration-conflicts.json
│   ├── migration-decision.json
│   ├── migration-history.json
│   ├── migration-progress.json
│   ├── migration-registry.json
│   ├── migration-report.json
│   ├── product-audit.json
│   ├── project-audit.json
│   ├── project-decisions.before-execution.json
│   ├── project-decisions.json
│   ├── project-roadmap.json
│   ├── report-catalog-results.json
│   ├── report-catalog.json
│   ├── system-health.json
│   └── technical-debt.txt
├── requirements.txt
├── schema
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
│   ├── migration
│   │   ├── config.js
│   │   ├── legacy-engine.js
│   │   ├── legacy-engine.js.backup
│   │   ├── migration-decision-engine.js
│   │   ├── migration-executor.backup.js
│   │   ├── migration-executor.js
│   │   ├── migration-executor.js.backup
│   │   ├── registry-builder.js
│   │   └── utils.js
│   ├── seed_master_products.ts
│   ├── system_analyzer.py
│   └── validate-schema.js
├── services
│   └── api.ts
├── src
│   ├── administration
│   │   └── __init__.py
│   ├── analytics
│   │   └── __init__.py
│   ├── compliance
│   │   └── __init__.py
│   ├── crm
│   │   └── __init__.py
│   ├── finance
│   │   └── __init__.py
│   ├── gl_dos
│   │   └── __init__.py
│   ├── logistics
│   │   └── __init__.py
│   ├── master_data
│   │   └── __init__.py
│   └── operations
│       └── __init__.py
├── sync_git.ps1
├── TECHNICAL_DEBT.txt
├── test_db_entities.py
├── tests
│   └── performance
│       ├── __init__.py
│       ├── results.json
│       └── smoke_test.js
├── tsconfig.json
├── tsconfig.tsbuildinfo
└── ui

```

## Source Modules

### administration (1 files)

### analytics (1 files)

### compliance (1 files)

### crm (1 files)

### finance (1 files)

### gl_dos (1 files)

### logistics (1 files)

### master_data (1 files)

### operations (1 files)

