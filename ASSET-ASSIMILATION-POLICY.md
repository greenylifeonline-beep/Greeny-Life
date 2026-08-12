# Asset Assimilation Policy

The E3 repository manifest contains 50,007 historical assets. They are not a single codebase and must not be merged indiscriminately. Dependency trees (`node_modules`, `.venv`, `.next`, and caches) are explicitly excluded from business-source assimilation.

1. **Active runtime** is the verified Next.js, Prisma, and governed intelligence surface only.
2. **Reusable source** enters through a tested module or adapter, never by copying folders wholesale.
3. **Reference data** supplies product, market, or business context but is not automatically current commercial or legal truth.
4. **Historical evidence** is preserved and searchable but never executed directly.
5. **Generated reports** are read on demand; the system does not create recurring duplicate reports.
6. **Dependencies and build artifacts** are regenerated from their definitions and are never business assets.

The 15 Egyptian products in `canonical/data/master_products.json` belong to Greeny-Life Egypt. They can be assessed for routes to Greens Nature (UAE/GCC) and Green Lines (Norway/EU), but every actual export remains evidence-gated and human-authorized.
