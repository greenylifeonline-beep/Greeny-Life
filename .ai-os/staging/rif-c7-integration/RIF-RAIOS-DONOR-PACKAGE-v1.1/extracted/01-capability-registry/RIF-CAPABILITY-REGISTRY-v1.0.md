# RIF Capability Registry v1.0

## Purpose
Central registry for RIF-evaluable capabilities within a bounded evaluation context.

## Historical Design (v1.0)
- capability_id: unique identifier
- capability_type: functional | non-functional | composite
- required_evidence_types: list of evidence schema references
- risk_profile: pre-computed risk classification
- dependencies: other capability_ids required
- canonical_fingerprint: SHA256 of normalized capability descriptor (RETIRED in v1.1)

## v1.0 Limitations
- Assumed local canonicalization authority
- No adapter interfaces for external registries
- Free-form producer identity ("C7")
- No schema versioning on capability descriptors

## v1.1 Adaptation Notes
- canonical_fingerprint → SANDBOX_REFERENCE_FINGERPRINT
- Externalized to CanonicalFingerprintProvider adapter
- Producer identity split into declared/verified/component/version
- Schema versioning added per D-C requirements
