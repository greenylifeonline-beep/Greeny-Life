# Greeny-Life Controlled Commercial Intake

Purpose: collect real commercial facts for the existing 15-product catalogue without changing the operational system.

Rules
1. Do not alter product_id, product_code, HS code, origin, or current supplier identifiers in the template.
2. A market price requires currency, basis, effective date, source URL or source reference, and named owner approval.
3. A supplier is not verified until source URL/reference, verification date, and accountable owner are complete.
4. Freight is reference-only until route, mode, currency, effective date, and source are complete.
5. Empty commercial values mean UNKNOWN, never zero and never approved.
6. This CSV is an intake draft. It cannot be imported into canonical data or PostgreSQL until a separate validation/review gate passes.

Required before approval per commercial row
- Market
- Currency and unit_price
- Price basis and effective-from date
- Price source URL or immutable reference
- Supplier source/reference and verification date
- Route, shipping mode, freight currency/cost/effective date if freight is supplied
- Evidence status and owner approval