# GREENY-LIFE Final Runtime Baseline

## Single final runtime

The only runtime target is this directory:

`C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair`

The active application is limited to:

- `app/` - Next.js UI and API routes
- `lib/prisma.ts` - shared Prisma client
- `prisma/schema.prisma` - active database schema
- `prisma.config.js` - Prisma CLI configuration
- `.env` - local-only database connection (never commit)
- `package.json` / `package-lock.json` - Node runtime dependencies

## Verified baseline

- PostgreSQL 18 is running locally on `127.0.0.1:5432`.
- Development database: `greeny_life_dev`.
- Schema validation: passed.
- Database schema synchronization: passed.
- Prisma client generation: completed before this baseline.
- TypeScript check: passed.
- Production build: passed.
- Live routes: `/`, `/api/products`, `/api/suppliers`, `/api/sales-orders` returned HTTP 200.
- Commercial changes use a source, validity period, risk level, governance decision, and correlation ID. A price, supplier, or shipment change requires review; a critical request is denied.

## Authority boundaries

- `canonical/` is source material and governance/reference data. It is not a second running application.
- `archive/`, `backup/`, E3 output folders, knowledge bases, and reports are historical/reference assets. They are excluded from the active TypeScript application surface.
- Do not run legacy migration, cleanup, duplicate-removal, or seed scripts without a reviewed execution plan.

## Current operational data state

The development database is intentionally empty. The historical product seed is not compatible with the active Prisma schema because the source lacks required supplier, price, and weight fields. No synthetic commercial data has been inserted.

## Standard verification

From this directory:

```powershell
npm.cmd run type-check
npm.cmd run build
npm.cmd run dev
```

Then verify:

```text
http://localhost:3000/
http://localhost:3000/api/products
```
