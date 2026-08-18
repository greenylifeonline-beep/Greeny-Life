from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .identity import SCHEMA_VERSION, utc_now


class ObjectState(str, Enum):
    AVAILABLE = "AVAILABLE"
    QUARANTINED = "QUARANTINED"
    MISSING = "MISSING"
    ORPHAN = "ORPHAN"
    RETAINED = "RETAINED"


class RetentionPolicy(str, Enum):
    RETAIN = "RETAIN"
    REVIEW = "REVIEW"
    GOVERNED_CANDIDATE = "GOVERNED_CANDIDATE"


class StorageStatus(str, Enum):
    STORED = "STORED"
    MISSING = "MISSING"
    QUARANTINED = "QUARANTINED"


class ValidationStatus(str, Enum):
    UNVALIDATED = "UNVALIDATED"
    VALID = "VALID"
    INVALID = "INVALID"


class TrustStatus(str, Enum):
    UNTRUSTED = "UNTRUSTED"
    TRUSTED = "TRUSTED"
    CONTRADICTED = "CONTRADICTED"


class CanonicalStatus(str, Enum):
    NOT_CANONICAL = "NOT_CANONICAL"
    CANDIDATE = "CANDIDATE"
    CANONICAL = "CANONICAL"


class TaskState(str, Enum):
    CREATED = "CREATED"
    ADMITTED = "ADMITTED"
    LEASED = "LEASED"
    RUNNING = "RUNNING"
    VERIFYING = "VERIFYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    BLOCKED = "BLOCKED"


class LeaseMode(str, Enum):
    WRITE = "WRITE"
    READ_VERIFY = "READ_VERIFY"


class LeaseState(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    RELEASED = "RELEASED"
    FENCED = "FENCED"


class EventType(str, Enum):
    TASK_CREATED = "TASK_CREATED"
    TASK_STATE_CHANGED = "TASK_STATE_CHANGED"
    RESULT_INGESTED = "RESULT_INGESTED"
    HANDOFF_INGESTED = "HANDOFF_INGESTED"
    ARTIFACT_INGESTED = "ARTIFACT_INGESTED"
    LEASE_ISSUED = "LEASE_ISSUED"
    LEASE_RENEWED = "LEASE_RENEWED"
    LEASE_RELEASED = "LEASE_RELEASED"
    LEASE_FENCED = "LEASE_FENCED"
    CAPSULE_CREATED = "CAPSULE_CREATED"
    OBJECT_QUARANTINED = "OBJECT_QUARANTINED"
    OBJECT_RECONCILED = "OBJECT_RECONCILED"


@dataclass(frozen=True)
class Provenance:
    producer_id: str
    producer_type: str
    source_type: str
    generation_method: str
    observed_at: str
    received_at: str
    task_id: str | None = None
    trust_state: TrustStatus = TrustStatus.UNTRUSTED
    verification_state: str = "UNVERIFIED"
    schema_version: str = SCHEMA_VERSION


@dataclass(frozen=True)
class Authority:
    storage_status: StorageStatus
    validation_status: ValidationStatus
    trust_status: TrustStatus
    canonical_status: CanonicalStatus


@dataclass(frozen=True)
class ContextCapsule:
    capsule_id: str
    refs: tuple[str, ...]
    task_id: str
    purpose: str
    schema_version: str = SCHEMA_VERSION
    created_at: str = field(default_factory=utc_now)
