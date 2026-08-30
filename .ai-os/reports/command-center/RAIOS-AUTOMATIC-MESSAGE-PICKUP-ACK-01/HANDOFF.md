# Automatic Message Pickup and Delivery ACK

Task: RAIOS-AUTOMATIC-MESSAGE-PICKUP-ACK-01

Implemented in the existing Command Center and Command Fabric only. The worker scans the canonical inbox, validates envelopes, creates per-seat deliveries, writes idempotent DELIVERY_ACK receipts, retries transient failures with bounded exponential backoff, moves exhausted invalid messages to dead-letter, publishes runtime heartbeat, and registers itself as RAIOS_SYSTEM-owned without a permanent lock.

Canary MSG-1788068043151742-6781c6cc produced two delivery acknowledgements: C2 and C6, attempt 1. DELIVERY_ACK proves queue delivery only; it never impersonates an actor response.

Validation: compile PASS; worker tests 3/3 PASS; staged canonical deployment PASS; post-deploy health HTTP 200. Legacy TestClient suite remains blocked by missing httpx2 and no package was installed.
