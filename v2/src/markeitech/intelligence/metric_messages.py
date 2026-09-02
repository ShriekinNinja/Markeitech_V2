from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from markeitech.intelligence._contract_validation import (
    bounded_ascii,
    canonical_bytes,
    canonical_digest,
    decimal_from_wire,
    decimal_to_wire,
    decimal_value,
    digest,
    evidence_references,
    exact_dict,
    positive_int,
    positive_int64,
    raw_bool,
    raw_int,
    raw_optional_int,
    raw_optional_string,
    raw_string,
    raw_string_list,
    topic_token,
    uuid_from_wire,
    uuid_value,
)

METRIC_VALUE_V2_TYPE_NAME = "markeitech.metric.value.v2"
"""Inactive Slice 1 wire identity for canonical v2 metric values."""

type MetricScalarValueV2 = str | int | Decimal | bool


class MetricValueKind(StrEnum):
    """Scalar representation carried by a canonical metric value."""

    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    TEXT = "text"


class MetricHealth(StrEnum):
    """Availability and freshness of one canonical metric result."""

    READY = "READY"
    WARMING = "WARMING"
    DEGRADED = "DEGRADED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class MetricFidelity(StrEnum):
    """Relationship between a metric value and its source observations."""

    REPORTED = "REPORTED"
    DERIVED = "DERIVED"
    INFERRED = "INFERRED"
    PARTIAL = "PARTIAL"
    UNAVAILABLE = "UNAVAILABLE"


class MetricReasonCode(StrEnum):
    """Bounded canonical reasons for non-ready metric evidence."""

    PARTIAL_COMPLETED_BAR = "PARTIAL_COMPLETED_BAR"
    MISSING_SUBINTERVALS = "MISSING_SUBINTERVALS"
    VOLUME_MISSING = "VOLUME_MISSING"
    VOLUME_UNSUPPORTED = "VOLUME_UNSUPPORTED"
    VOLUME_PARTIAL = "VOLUME_PARTIAL"
    INPUT_PARTIAL = "INPUT_PARTIAL"
    HISTORICAL_PARTIAL = "HISTORICAL_PARTIAL"
    GAP = "GAP"
    WARMUP_INCOMPLETE = "WARMUP_INCOMPLETE"
    EVIDENCE_UNAVAILABLE = "EVIDENCE_UNAVAILABLE"
    EVIDENCE_UNSUPPORTED = "EVIDENCE_UNSUPPORTED"
    VALUE_STALE = "VALUE_STALE"
    IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    ORDERING_INVALID = "ORDERING_INVALID"
    REVISION_INVALID = "REVISION_INVALID"
    CALCULATION_FAILED = "CALCULATION_FAILED"


_REASON_ORDER = {reason: index for index, reason in enumerate(MetricReasonCode)}

_METRIC_SUBJECT_KEYS = frozenset(
    {
        "metric_id",
        "metric_version",
        "parameter_version",
        "parameter_effective_from_ns",
        "parameter_epoch",
        "configuration_epoch",
        "configuration_digest",
        "instrument_id",
        "output_schema_version",
        "canonical_producer_id",
        "input_series_id",
        "calendar_id",
        "calendar_definition_version",
        "calendar_definition_digest",
        "calendar_definition_effective_from_ns",
        "analytical_profile_id",
        "analytical_profile_version",
        "session_id",
        "trade_date",
        "analytical_window_id",
        "analytical_window_version",
        "rolling_family_id",
        "rolling_candidate_id",
        "input_timeframe",
        "horizon",
        "baseline_policy_id",
    },
)

_METRIC_VALUE_KEYS = frozenset(
    {
        "subject",
        "kind",
        "value",
        "unit_id",
        "effective_ts_ns",
        "observed_ts_ns",
        "received_ts_ns",
        "calculated_ts_ns",
        "published_ts_ns",
        "health",
        "fidelity",
        "reasons",
        "evidence_refs",
        "run_epoch",
        "revision",
        "previous_revision",
    },
)


@dataclass(frozen=True, slots=True)
class MetricSubjectIdentity:
    """Identify the complete subject of one versioned metric stream.

    Optional fields are absent only when that dimension is not applicable to
    the metric. Calendar, analytical-profile, window, and rolling dimensions
    are validated as complete groups so consumers never reconstruct meaning
    from an opaque metric or actor identifier.
    """

    metric_id: str
    metric_version: int
    parameter_version: int
    parameter_effective_from_ns: int
    parameter_epoch: UUID
    configuration_epoch: UUID
    configuration_digest: str
    instrument_id: str
    output_schema_version: int
    canonical_producer_id: str
    input_series_id: str | None = None
    calendar_id: str | None = None
    calendar_definition_version: int | None = None
    calendar_definition_digest: str | None = None
    calendar_definition_effective_from_ns: int | None = None
    analytical_profile_id: str | None = None
    analytical_profile_version: int | None = None
    session_id: str | None = None
    trade_date: date | None = None
    analytical_window_id: str | None = None
    analytical_window_version: int | None = None
    rolling_family_id: str | None = None
    rolling_candidate_id: str | None = None
    input_timeframe: str | None = None
    horizon: str | None = None
    baseline_policy_id: str | None = None

    def __post_init__(self) -> None:
        for field in ("metric_id", "instrument_id", "canonical_producer_id"):
            object.__setattr__(self, field, bounded_ascii(getattr(self, field), field))
        positive_int(self.metric_version, "metric_version")
        positive_int(self.parameter_version, "parameter_version")
        positive_int64(self.parameter_effective_from_ns, "parameter_effective_from_ns")
        uuid_value(self.parameter_epoch, "parameter_epoch")
        uuid_value(self.configuration_epoch, "configuration_epoch")
        object.__setattr__(
            self,
            "configuration_digest",
            digest(self.configuration_digest, "configuration_digest"),
        )
        positive_int(self.output_schema_version, "output_schema_version")
        if self.output_schema_version != 2:
            raise ValueError("MetricValue v2 subjects require output_schema_version = 2")
        if self.input_series_id is not None:
            object.__setattr__(self, "input_series_id", topic_token(self.input_series_id))
        self._validate_calendar_group()
        self._validate_pair("analytical_profile_id", "analytical_profile_version")
        self._validate_pair("analytical_window_id", "analytical_window_version")
        if (self.session_id is None) != (self.trade_date is None):
            raise ValueError("session_id and trade_date must be provided together")
        if self.session_id is not None:
            object.__setattr__(self, "session_id", bounded_ascii(self.session_id, "session_id"))
            if type(self.trade_date) is not date:
                raise ValueError("trade_date must be a date")
            if self.calendar_id is None:
                raise ValueError("session subject dimensions require calendar identity")
        rolling = (
            self.rolling_family_id,
            self.rolling_candidate_id,
            self.input_timeframe,
            self.horizon,
            self.baseline_policy_id,
        )
        if any(item is not None for item in rolling) and any(item is None for item in rolling):
            raise ValueError("rolling subject dimensions must be provided together")
        for field in (
            "rolling_family_id",
            "rolling_candidate_id",
            "input_timeframe",
            "horizon",
            "baseline_policy_id",
        ):
            value = getattr(self, field)
            if value is not None:
                object.__setattr__(self, field, bounded_ascii(value, field))
        if self.analytical_window_id is not None and any(
            item is None
            for item in (
                self.input_series_id,
                self.calendar_id,
                self.analytical_profile_id,
            )
        ):
            raise ValueError(
                "analytical-window subjects require input-series, calendar, and profile identity",
            )
        if self.rolling_family_id is not None and any(
            item is None
            for item in (
                self.input_series_id,
                self.calendar_id,
                self.analytical_profile_id,
            )
        ):
            raise ValueError(
                "rolling subjects require input-series, calendar, and profile identity",
            )

    def _validate_calendar_group(self) -> None:
        values = (
            self.calendar_id,
            self.calendar_definition_version,
            self.calendar_definition_digest,
            self.calendar_definition_effective_from_ns,
        )
        if any(item is not None for item in values) and any(item is None for item in values):
            raise ValueError("calendar subject dimensions must be provided together")
        if self.calendar_id is not None:
            object.__setattr__(self, "calendar_id", bounded_ascii(self.calendar_id, "calendar_id"))
            positive_int(self.calendar_definition_version, "calendar_definition_version")
            object.__setattr__(
                self,
                "calendar_definition_digest",
                digest(self.calendar_definition_digest, "calendar_definition_digest"),
            )
            positive_int64(
                self.calendar_definition_effective_from_ns,
                "calendar_definition_effective_from_ns",
            )

    def _validate_pair(self, text_field: str, version_field: str) -> None:
        text_value = getattr(self, text_field)
        version_value = getattr(self, version_field)
        if (text_value is None) != (version_value is None):
            raise ValueError(f"{text_field} and {version_field} must be provided together")
        if text_value is not None:
            object.__setattr__(self, text_field, bounded_ascii(text_value, text_field))
            positive_int(version_value, version_field)

    @property
    def identity_digest(self) -> str:
        """Return the deterministic SHA-256 digest of the complete identity."""

        return canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical serialization-ready identity mapping."""

        return {
            field: _encode_identity_value(getattr(self, field))
            for field in self.__dataclass_fields__
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> MetricSubjectIdentity:
        """Reconstruct and validate an identity from its canonical mapping."""

        fields = exact_dict(value, _METRIC_SUBJECT_KEYS, "MetricSubjectIdentity")
        raw_trade_date = raw_optional_string(fields["trade_date"], "trade_date")
        trade_date_value: date | None = None
        if raw_trade_date is not None:
            try:
                trade_date_value = date.fromisoformat(raw_trade_date)
            except ValueError as exc:
                raise ValueError("trade_date must be a canonical ISO date") from exc
            if trade_date_value.isoformat() != raw_trade_date:
                raise ValueError("trade_date must be a canonical ISO date")
        return cls(
            metric_id=raw_string(fields["metric_id"], "metric_id"),
            metric_version=raw_int(fields["metric_version"], "metric_version"),
            parameter_version=raw_int(fields["parameter_version"], "parameter_version"),
            parameter_effective_from_ns=raw_int(
                fields["parameter_effective_from_ns"],
                "parameter_effective_from_ns",
            ),
            parameter_epoch=uuid_from_wire(fields["parameter_epoch"], "parameter_epoch"),
            configuration_epoch=uuid_from_wire(
                fields["configuration_epoch"],
                "configuration_epoch",
            ),
            configuration_digest=raw_string(
                fields["configuration_digest"],
                "configuration_digest",
            ),
            instrument_id=raw_string(fields["instrument_id"], "instrument_id"),
            output_schema_version=raw_int(
                fields["output_schema_version"],
                "output_schema_version",
            ),
            canonical_producer_id=raw_string(
                fields["canonical_producer_id"],
                "canonical_producer_id",
            ),
            input_series_id=raw_optional_string(fields["input_series_id"], "input_series_id"),
            calendar_id=raw_optional_string(fields["calendar_id"], "calendar_id"),
            calendar_definition_version=raw_optional_int(
                fields["calendar_definition_version"],
                "calendar_definition_version",
            ),
            calendar_definition_digest=raw_optional_string(
                fields["calendar_definition_digest"],
                "calendar_definition_digest",
            ),
            calendar_definition_effective_from_ns=raw_optional_int(
                fields["calendar_definition_effective_from_ns"],
                "calendar_definition_effective_from_ns",
            ),
            analytical_profile_id=raw_optional_string(
                fields["analytical_profile_id"],
                "analytical_profile_id",
            ),
            analytical_profile_version=raw_optional_int(
                fields["analytical_profile_version"],
                "analytical_profile_version",
            ),
            session_id=raw_optional_string(fields["session_id"], "session_id"),
            trade_date=trade_date_value,
            analytical_window_id=raw_optional_string(
                fields["analytical_window_id"],
                "analytical_window_id",
            ),
            analytical_window_version=raw_optional_int(
                fields["analytical_window_version"],
                "analytical_window_version",
            ),
            rolling_family_id=raw_optional_string(
                fields["rolling_family_id"],
                "rolling_family_id",
            ),
            rolling_candidate_id=raw_optional_string(
                fields["rolling_candidate_id"],
                "rolling_candidate_id",
            ),
            input_timeframe=raw_optional_string(fields["input_timeframe"], "input_timeframe"),
            horizon=raw_optional_string(fields["horizon"], "horizon"),
            baseline_policy_id=raw_optional_string(
                fields["baseline_policy_id"],
                "baseline_policy_id",
            ),
        )


@dataclass(frozen=True, slots=True)
class MetricValue:
    """Carry one immutable canonical v2 metric value.

    Effective time is the market boundary described by the value and maps to
    Nautilus ``ts_event``. Published time maps to ``ts_init``. Processing times
    are positive UTC Unix nanoseconds and must satisfy observed, received,
    calculated, then published order. Canonical numeric values never use
    ``float`` and unavailable evidence never substitutes numeric zero.
    """

    subject: MetricSubjectIdentity
    kind: MetricValueKind
    value: MetricScalarValueV2 | None
    unit_id: str
    effective_ts_ns: int
    observed_ts_ns: int
    received_ts_ns: int
    calculated_ts_ns: int
    published_ts_ns: int
    health: MetricHealth
    fidelity: MetricFidelity
    reasons: tuple[MetricReasonCode, ...]
    evidence_refs: tuple[str, ...]
    run_epoch: UUID
    revision: int
    previous_revision: int | None

    def __post_init__(self) -> None:
        if not isinstance(self.subject, MetricSubjectIdentity):
            raise ValueError("subject must be a MetricSubjectIdentity")
        if not isinstance(self.kind, MetricValueKind):
            raise ValueError("kind must be a MetricValueKind")
        object.__setattr__(self, "unit_id", bounded_ascii(self.unit_id, "unit_id"))
        for field in (
            "effective_ts_ns",
            "observed_ts_ns",
            "received_ts_ns",
            "calculated_ts_ns",
            "published_ts_ns",
        ):
            positive_int64(getattr(self, field), field)
        if not (
            self.observed_ts_ns
            <= self.received_ts_ns
            <= self.calculated_ts_ns
            <= self.published_ts_ns
        ):
            raise ValueError(
                "metric timestamps must satisfy observed <= received <= calculated <= published",
            )
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be a MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be a MetricFidelity")
        self._validate_reasons()
        object.__setattr__(self, "evidence_refs", evidence_references(self.evidence_refs))
        uuid_value(self.run_epoch, "run_epoch")
        positive_int64(self.revision, "revision")
        if self.revision == 1:
            if self.previous_revision is not None:
                raise ValueError("previous_revision must be None for revision 1")
        elif self.previous_revision != self.revision - 1:
            raise ValueError("previous_revision must name the immediately preceding revision")
        self._validate_health_and_value()

    def _validate_reasons(self) -> None:
        if not isinstance(self.reasons, tuple) or any(
            not isinstance(reason, MetricReasonCode) for reason in self.reasons
        ):
            raise ValueError("reasons must be a tuple of MetricReasonCode values")
        if len(self.reasons) > 16:
            raise ValueError("reasons must contain at most 16 entries")
        if len(self.reasons) != len(set(self.reasons)):
            raise ValueError("reasons must be unique")
        if tuple(sorted(self.reasons, key=_REASON_ORDER.__getitem__)) != self.reasons:
            raise ValueError("reasons must use canonical MetricReasonCode order")
        if self.health is MetricHealth.READY and self.reasons:
            raise ValueError("READY metrics require an empty reason tuple")
        if self.health is not MetricHealth.READY and not self.reasons:
            raise ValueError("non-ready metrics require at least one typed reason")

    def _validate_health_and_value(self) -> None:
        value_required = {
            MetricHealth.READY,
            MetricHealth.DEGRADED,
            MetricHealth.STALE,
        }
        if self.health in value_required and self.value is None:
            raise ValueError(f"{self.health.value} metrics require a value")
        if self.health not in value_required and self.value is not None:
            raise ValueError(f"{self.health.value} metrics require a null value")
        if self.health is MetricHealth.STALE and MetricReasonCode.VALUE_STALE not in self.reasons:
            raise ValueError("STALE metrics require VALUE_STALE")
        if self.value is None:
            return
        valid = {
            MetricValueKind.NUMBER: isinstance(self.value, Decimal),
            MetricValueKind.INTEGER: isinstance(self.value, int)
            and not isinstance(self.value, bool),
            MetricValueKind.BOOLEAN: isinstance(self.value, bool),
            MetricValueKind.TEXT: isinstance(self.value, str),
        }[self.kind]
        if not valid:
            raise ValueError(f"value must match MetricValueKind.{self.kind.name}")
        if isinstance(self.value, Decimal):
            decimal_value(self.value, "value")
        if isinstance(self.value, str):
            if not self.value or len(self.value) > 512:
                raise ValueError("TEXT metric values must contain 1 through 512 Unicode characters")

    @property
    def key(self) -> tuple[str, int]:
        """Return the compatible metric-definition key."""

        return (self.subject.metric_id, self.subject.metric_version)

    @property
    def metric_id(self) -> str:
        return self.subject.metric_id

    @property
    def metric_version(self) -> int:
        return self.subject.metric_version

    @property
    def parameter_version(self) -> int:
        return self.subject.parameter_version

    @property
    def instrument_id(self) -> str:
        return self.subject.instrument_id

    @property
    def session_id(self) -> str | None:
        return self.subject.session_id

    @property
    def unit(self) -> str:
        """Return the compatibility alias for the definition-owned unit ID."""

        return self.unit_id

    @property
    def missing_reasons(self) -> tuple[str, ...]:
        """Return typed reasons as compatibility string tokens."""

        return tuple(reason.value for reason in self.reasons)

    @property
    def source(self) -> str:
        """Return the canonical producer identity for compatibility readers."""

        return self.subject.canonical_producer_id

    @property
    def ts_event(self) -> int:
        """Return effective market time for future typed CustomData publication."""

        return self.effective_ts_ns

    @property
    def ts_init(self) -> int:
        """Return publication time for future typed CustomData publication."""

        return self.published_ts_ns

    @property
    def identity_digest(self) -> str:
        """Return the deterministic digest of subject, epoch, and revision identity."""

        return canonical_digest(
            {
                "subject": self.subject.to_dict(),
                "run_epoch": str(self.run_epoch),
                "revision": self.revision,
            },
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical serialization-ready value mapping."""

        return {
            "subject": self.subject.to_dict(),
            "kind": self.kind.value,
            "value": None
            if self.value is None
            else decimal_to_wire(self.value, "value")
            if isinstance(self.value, Decimal)
            else self.value,
            "unit_id": self.unit_id,
            "effective_ts_ns": self.effective_ts_ns,
            "observed_ts_ns": self.observed_ts_ns,
            "received_ts_ns": self.received_ts_ns,
            "calculated_ts_ns": self.calculated_ts_ns,
            "published_ts_ns": self.published_ts_ns,
            "health": self.health.value,
            "fidelity": self.fidelity.value,
            "reasons": [reason.value for reason in self.reasons],
            "evidence_refs": list(self.evidence_refs),
            "run_epoch": str(self.run_epoch),
            "revision": self.revision,
            "previous_revision": self.previous_revision,
        }

    def to_bytes(self) -> bytes:
        """Serialize the value deterministically without float conversion."""

        return canonical_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> MetricValue:
        """Reconstruct and validate a metric value from its canonical mapping."""

        fields = exact_dict(value, _METRIC_VALUE_KEYS, "MetricValue")
        kind = MetricValueKind(raw_string(fields["kind"], "kind"))
        raw_value = fields["value"]
        if raw_value is not None:
            if kind is MetricValueKind.NUMBER:
                raw_value = decimal_from_wire(raw_value, "value")
            elif kind is MetricValueKind.INTEGER:
                raw_value = raw_int(raw_value, "value")
            elif kind is MetricValueKind.BOOLEAN:
                raw_value = raw_bool(raw_value, "value")
            else:
                raw_value = raw_string(raw_value, "value")
        return cls(
            subject=MetricSubjectIdentity.from_dict(fields["subject"]),
            kind=kind,
            value=raw_value,
            unit_id=raw_string(fields["unit_id"], "unit_id"),
            effective_ts_ns=raw_int(fields["effective_ts_ns"], "effective_ts_ns"),
            observed_ts_ns=raw_int(fields["observed_ts_ns"], "observed_ts_ns"),
            received_ts_ns=raw_int(fields["received_ts_ns"], "received_ts_ns"),
            calculated_ts_ns=raw_int(fields["calculated_ts_ns"], "calculated_ts_ns"),
            published_ts_ns=raw_int(fields["published_ts_ns"], "published_ts_ns"),
            health=MetricHealth(raw_string(fields["health"], "health")),
            fidelity=MetricFidelity(raw_string(fields["fidelity"], "fidelity")),
            reasons=tuple(
                MetricReasonCode(reason) for reason in raw_string_list(fields["reasons"], "reasons")
            ),
            evidence_refs=raw_string_list(fields["evidence_refs"], "evidence_refs"),
            run_epoch=uuid_from_wire(fields["run_epoch"], "run_epoch"),
            revision=raw_int(fields["revision"], "revision"),
            previous_revision=raw_optional_int(
                fields["previous_revision"],
                "previous_revision",
            ),
        )


def _encode_identity_value(value: object) -> object:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value
