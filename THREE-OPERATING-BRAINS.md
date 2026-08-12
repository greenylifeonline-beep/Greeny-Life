# MasterMind and the Three Operating Brains

## Authority and operating separation

**MasterMind AI is the primary decision intelligence and command authority.** It coordinates all specialist agents and the three local operating brains, compares alternatives, separates data context, and issues a proposed controlled command only after the user's explicit approval.

| Brain | Company | Semi-independent daily scope | Must escalate to MasterMind |
| --- | --- | --- | --- |
| Greeny-Life Egypt Brain | Greeny-Life Egypt | Production, packaging, supplier/warehouse work, import/export preparation in Egypt | New opportunity, imports of fish/equipment/technical assets, new market/product, error, cross-company work, material commercial change |
| Greens Nature UAE Brain | Greens Nature UAE | UAE/GCC import, distribution, local customer/inventory work, re-export opportunity detection | New opportunity, error, cross-company work, material commercial change, new market/product |
| Green Lines Norway/EU Brain | Green Lines Norway/EU | European sourcing, local import/export/re-export preparation, distribution and compliance preparation | New opportunity, error, cross-company work, material commercial change, new market/product |

## Decision and approval cycle

`Local Brain finds an opportunity or exception → MasterMind separates context and asks specialist Agents → MasterMind sends editable approval notification → User approves/rejects/edits → controlled operational action may be authorized → result is measured for a reviewed learning proposal.`

An approval notification includes recommendation, alternatives, blockers, proposed actions, and editable commercial assumptions. It is always `PENDING_USER_APPROVAL`; it never performs shipping, payment, customs, legal-title transfer, deletion, or self-modification.

`GET /api/mastermind/operating-model` exposes the operating model. `POST /api/mastermind/decision-package` returns the decision package and approval notification.
