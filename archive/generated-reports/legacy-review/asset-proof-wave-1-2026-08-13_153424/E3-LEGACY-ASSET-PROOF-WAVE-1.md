# E3 Legacy Asset Proof â€” Wave 1

Generated: 2026-08-13T13:34:25.5610757Z

| Asset | Status | Evidence | Finding |
|---|---|---|---|
| KnowledgeGraph | PARTIAL | entity/relation/path/serialization behavior executed successfully in memory | find_node_by_name returns duplicate entity references when `name` is also indexed again during attribute iteration. |
| ImplementationEvidenceLayer | FAIL | TypeError: non-default argument 'raw' follows default argument | Import fails before conversion: dataclass field ordering has a default field before required raw/normalized/source_snippet fields. |
| JSONKnowledgeRepository | PASS | temporary JSON load/entity/rule/relationship/evidence retrieval executed; no legacy data was written |  |
| BrainContractDataStructures | PASS | Evidence and Decision contracts instantiate and preserve typed data |  |

## Boundary

- PASS is bounded runtime proof only, not System-of-Record or production approval.
- No legacy source, data, database, network, or external service was changed.
