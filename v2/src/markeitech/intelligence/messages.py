from __future__ import annotations

import json
from dataclasses import asdict, dataclass

EVIDENCE_HEALTH_SIGNAL = "markeitech.evidence.health"
EVIDENCE_HEALTH_SCHEMA_VERSION = 1
EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL = "markeitech.evidence.health.snapshot.request"
EVIDENCE_HEALTH_SNAPSHOT_SIGNAL = "markeitech.evidence.health.snapshot"
EVIDENCE_HEALTH_SNAPSHOT_SCHEMA_VERSION = 1
EVIDENCE_RECENCY_PROFILE_SIGNAL = "markeitech.evidence.recency_profile"
EVIDENCE_RECENCY_PROFILE_SCHEMA_VERSION = 1

EVIDENCE_STATES = {
    "NOT_EVALUATED",
    "DORMANT",
    "HEALTHY",
    "DEGRADED",
    "STALE",
    "UNAVAILABLE",
    "UNSUPPORTED",
}
EVIDENCE_FIDELITIES = {"REPORTED", "DERIVED", "INFERRED", "PARTIAL", "UNAVAILABLE"}


@dataclass(frozen=True, slots=True)
class EvidenceHealthEvent:
    event_id: str
    instrument_id: str
    calendar_id: str
    feed_kind: str
    selector: str
    state: str
    previous_state: str | None
    reason: str
    fidelity: str
    subscription_state: str
    event_ts_ns: int | None
    receive_ts_ns: int | None
    evaluated_ts_ns: int
    age_ms: int | None
    session_phase: str | None
    session_trade_date: str | None
    session_alignment: str
    source: str
    policy_version: str
    revision: int
    schema_version: int = EVIDENCE_HEALTH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(self.schema_version, EVIDENCE_HEALTH_SCHEMA_VERSION, "evidence health")
        for field in (
            "event_id",
            "instrument_id",
            "calendar_id",
            "feed_kind",
            "selector",
            "reason",
            "subscription_state",
            "session_alignment",
            "source",
            "policy_version",
        ):
            _text(getattr(self, field), field)
        if self.state not in EVIDENCE_STATES:
            raise ValueError(f"unsupported evidence state: {self.state!r}")
        if self.previous_state is not None and self.previous_state not in EVIDENCE_STATES:
            raise ValueError(f"unsupported previous evidence state: {self.previous_state!r}")
        if self.fidelity not in EVIDENCE_FIDELITIES:
            raise ValueError(f"unsupported evidence fidelity: {self.fidelity!r}")
        if self.session_phase is not None:
            _phase(self.session_phase, "session_phase")
        _positive(self.revision, "revision")
        _optional_ns(self.event_ts_ns, "event_ts_ns")
        _optional_ns(self.receive_ts_ns, "receive_ts_ns")
        _optional_ns(self.evaluated_ts_ns, "evaluated_ts_ns", optional=False)
        if self.age_ms is not None and self.age_ms < 0:
            raise ValueError("age_ms must be non-negative")

    def to_signal_value(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_signal_value(cls, value: str) -> EvidenceHealthEvent:
        return cls(**_payload(value, set(cls.__dataclass_fields__)))


@dataclass(frozen=True, slots=True)
class EvidenceHealthSnapshotRequest:
    requester: str
    instrument_ids: tuple[str, ...]
    feed_kind: str
    selector: str
    schema_version: int = EVIDENCE_HEALTH_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(
            self.schema_version,
            EVIDENCE_HEALTH_SNAPSHOT_SCHEMA_VERSION,
            "evidence health snapshot request",
        )
        for field in ("requester", "feed_kind", "selector"):
            _text(getattr(self, field), field)
        if not isinstance(self.instrument_ids, (list, tuple)) or not self.instrument_ids:
            raise ValueError("instrument_ids must contain at least one instrument")
        normalized = tuple(
            sorted({_normalized_text(value, "instrument_id") for value in self.instrument_ids})
        )
        if len(normalized) != len(self.instrument_ids):
            raise ValueError("instrument_ids must not contain duplicates")
        object.__setattr__(self, "instrument_ids", normalized)

    def to_signal_value(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_signal_value(cls, value: str) -> EvidenceHealthSnapshotRequest:
        return cls(**_payload(value, set(cls.__dataclass_fields__)))


@dataclass(frozen=True, slots=True)
class EvidenceHealthSnapshot:
    requester: str
    source: str
    events: tuple[EvidenceHealthEvent, ...]
    snapshot_ts_ns: int
    schema_version: int = EVIDENCE_HEALTH_SNAPSHOT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(
            self.schema_version,
            EVIDENCE_HEALTH_SNAPSHOT_SCHEMA_VERSION,
            "evidence health snapshot",
        )
        _text(self.requester, "requester")
        _text(self.source, "source")
        _optional_ns(self.snapshot_ts_ns, "snapshot_ts_ns", optional=False)
        if not isinstance(self.events, (list, tuple)):
            raise ValueError("events must be a sequence")
        events = tuple(
            event if isinstance(event, EvidenceHealthEvent) else EvidenceHealthEvent(**event)
            for event in self.events
        )
        keys = [(event.instrument_id, event.feed_kind, event.selector) for event in events]
        if len(keys) != len(set(keys)):
            raise ValueError("events must not contain duplicate streams")
        object.__setattr__(
            self,
            "events",
            tuple(
                sorted(
                    events, key=lambda event: (event.instrument_id, event.feed_kind, event.selector)
                )
            ),
        )

    def to_signal_value(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_signal_value(cls, value: str) -> EvidenceHealthSnapshot:
        return cls(**_payload(value, set(cls.__dataclass_fields__)))


@dataclass(frozen=True, slots=True)
class EvidenceRecencyProfileEvent:
    event_id: str
    instrument_id: str
    feed_kind: str
    selector: str
    provider_id: str
    session_phase: str
    policy_version: str
    sample_count: int
    mean_interval_ms: float
    variance_ms2: float
    last_observed_ns: int
    fresh_for_ms: int
    stale_after_ms: int
    unavailable_after_ms: int
    source: str
    schema_version: int = EVIDENCE_RECENCY_PROFILE_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _schema(
            self.schema_version,
            EVIDENCE_RECENCY_PROFILE_SCHEMA_VERSION,
            "evidence recency profile",
        )
        for field in (
            "event_id",
            "instrument_id",
            "feed_kind",
            "selector",
            "provider_id",
            "session_phase",
            "policy_version",
            "source",
        ):
            _text(getattr(self, field), field)
        _positive(self.sample_count, "sample_count")
        _optional_ns(self.last_observed_ns, "last_observed_ns", optional=False)
        if self.mean_interval_ms < 0 or self.variance_ms2 < 0:
            raise ValueError("recency profile statistics must be non-negative")
        if not 0 < self.fresh_for_ms < self.stale_after_ms < self.unavailable_after_ms:
            raise ValueError("recency profile thresholds must be positive and increasing")

    def to_signal_value(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_signal_value(cls, value: str) -> EvidenceRecencyProfileEvent:
        return cls(**_payload(value, set(cls.__dataclass_fields__)))


def _payload(value: str, expected: set[str]) -> dict[str, object]:
    try:
        payload = json.loads(value)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("signal value must be valid JSON") from exc
    if not isinstance(payload, dict) or set(payload) != expected:
        raise ValueError("signal payload fields do not match the contract")
    return payload


def _text(value: object, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _normalized_text(value: object, label: str) -> str:
    _text(value, label)
    return str(value).strip()


def _schema(actual: int, expected: int, label: str) -> None:
    if actual != expected:
        raise ValueError(f"unsupported {label} schema: {actual}")


def _phase(value: object, label: str) -> None:
    _text(value, label)
    if value != str(value).upper():
        raise ValueError(f"{label} must be uppercase")


def _positive(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")


def _optional_ns(value: object, label: str, *, optional: bool = True) -> None:
    if value is None and optional:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
