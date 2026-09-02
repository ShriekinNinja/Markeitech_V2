from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal
from uuid import UUID

from nautilus_trader.model import DataType

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
    raw_int,
    raw_list,
    raw_string,
    raw_string_list,
    text_tuple,
    topic_token,
    uuid_from_wire,
    uuid_value,
)
from markeitech.intelligence.metric_messages import (
    MetricFidelity,
    MetricHealth,
    MetricReasonCode,
)

COMPLETED_BAR_V1_TYPE_NAME = "markeitech.completed_bar.canonical.v1"
"""Inactive Slice 1 wire identity for canonical completed bars."""

_METRIC_REASON_ORDER = {reason: index for index, reason in enumerate(MetricReasonCode)}

_COMPLETED_BAR_SERIES_IDENTITY_KEYS = frozenset(
    {
        "instrument_id",
        "venue",
        "canonical_bar_specification",
        "interval_ns",
        "aggregation_policy",
        "timestamp_policy",
        "completion_policy",
        "revision_policy",
        "calendar_id",
        "calendar_definition_version",
        "calendar_definition_digest",
        "calendar_definition_effective_from_ns",
        "analytical_profile_id",
        "analytical_profile_version",
        "configuration_epoch",
        "configuration_digest",
        "canonical_producer_id",
        "output_schema_version",
        "series_id",
    },
)

_COMPLETED_BAR_INPUT_IDENTITY_KEYS = frozenset(
    {
        "provider_id",
        "adapter_id",
        "source_stream_id",
        "source_selector",
        "source_schema_id",
    },
)

_COMPLETED_BAR_LINEAGE_KEYS = frozenset(
    {
        "source_class",
        "input_identity",
        "provider_observation_ref",
        "evidence_refs",
        "source_observed_ts_ns",
        "source_received_ts_ns",
        "normalized_ts_ns",
        "transformation_chain",
        "source_correction_metadata",
    },
)

_COMPLETED_BAR_KEYS = frozenset(
    {
        "series_id",
        "series_identity",
        "interval_start_ns",
        "interval_end_ns",
        "run_epoch",
        "publication_sequence",
        "completion_state",
        "expected_constituent_count",
        "received_constituent_count",
        "missing_subintervals",
        "completion_reasons",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "volume_state",
        "trade_date",
        "exchange_state",
        "product_phases",
        "state_evidence_refs",
        "projection_evidence_refs",
        "published_ts_ns",
        "lineage",
        "health",
        "fidelity",
        "evidence_refs",
    },
)


class BarCompletionState(StrEnum):
    """Evidence completeness of one closed canonical bar interval."""

    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"


class VolumeState(StrEnum):
    """Truth state of the optional canonical bar volume value."""

    OBSERVED = "OBSERVED"
    MISSING = "MISSING"
    UNSUPPORTED = "UNSUPPORTED"
    PARTIAL = "PARTIAL"


@dataclass(frozen=True, slots=True)
class CompletedBarInputIdentity:
    """Identify one exact upstream path contributing to a canonical bar.

    Canonical series identity is intentionally independent of the provider path
    which supplied an observation. Historical one-minute and live five-second
    inputs therefore converge into one output series while each lineage entry
    preserves its exact provider, adapter, stream, raw selector, and source
    schema identity.

    Attributes:
        provider_id: Bounded provider identity, such as ``IB``.
        adapter_id: Bounded adapter implementation identity.
        source_stream_id: Exact upstream stream or request-lane identity.
        source_selector: Exact raw input selector or native bar type.
        source_schema_id: Exact schema identity of the upstream observation.

    Raises:
        ValueError: If an identity is empty, non-ASCII, or exceeds its bound.
    """

    provider_id: str
    adapter_id: str
    source_stream_id: str
    source_selector: str
    source_schema_id: str

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            object.__setattr__(self, field, bounded_ascii(getattr(self, field), field))

    def to_dict(self) -> dict[str, str]:
        """Return the canonical serialization-ready input identity mapping."""

        return {field: getattr(self, field) for field in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CompletedBarInputIdentity:
        """Reconstruct and validate an input identity from canonical data."""

        fields = exact_dict(value, _COMPLETED_BAR_INPUT_IDENTITY_KEYS, cls.__name__)
        return cls(
            provider_id=raw_string(fields["provider_id"], "provider_id"),
            adapter_id=raw_string(fields["adapter_id"], "adapter_id"),
            source_stream_id=raw_string(fields["source_stream_id"], "source_stream_id"),
            source_selector=raw_string(fields["source_selector"], "source_selector"),
            source_schema_id=raw_string(fields["source_schema_id"], "source_schema_id"),
        )


@dataclass(frozen=True, slots=True)
class CompletedBarSeriesIdentity:
    """Identify one canonical completed-bar series completely.

    The short ``series_id`` is a bounded routing token, not a substitute for
    this identity. The deterministic digest binds canonical output semantics,
    calendar/profile configuration, and producer schema without actor-local
    interpretation. Upstream provider paths belong to
    :class:`CompletedBarInputIdentity` values in lineage and never split this
    canonical output identity.
    """

    instrument_id: str
    venue: str
    canonical_bar_specification: str
    interval_ns: int
    aggregation_policy: str
    timestamp_policy: str
    completion_policy: str
    revision_policy: str
    calendar_id: str
    calendar_definition_version: int
    calendar_definition_digest: str
    calendar_definition_effective_from_ns: int
    analytical_profile_id: str
    analytical_profile_version: int
    configuration_epoch: UUID
    configuration_digest: str
    canonical_producer_id: str
    output_schema_version: int
    series_id: str

    def __post_init__(self) -> None:
        for field in (
            "instrument_id",
            "venue",
            "canonical_bar_specification",
            "aggregation_policy",
            "timestamp_policy",
            "completion_policy",
            "revision_policy",
            "calendar_id",
            "analytical_profile_id",
            "canonical_producer_id",
        ):
            object.__setattr__(self, field, bounded_ascii(getattr(self, field), field))
        positive_int64(self.interval_ns, "interval_ns")
        if self.timestamp_policy != "interval_end":
            raise ValueError("canonical completed bars require timestamp_policy = interval_end")
        if self.revision_policy != "reject":
            raise ValueError("CompletedBarV1 requires revision_policy = reject")
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
        positive_int(self.analytical_profile_version, "analytical_profile_version")
        uuid_value(self.configuration_epoch, "configuration_epoch")
        object.__setattr__(
            self,
            "configuration_digest",
            digest(self.configuration_digest, "configuration_digest"),
        )
        positive_int(self.output_schema_version, "output_schema_version")
        if self.output_schema_version != 1:
            raise ValueError("CompletedBarV1 identities require output_schema_version = 1")
        object.__setattr__(self, "series_id", topic_token(self.series_id))

    @property
    def identity_digest(self) -> str:
        """Return the deterministic SHA-256 digest of the complete identity."""

        return canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical serialization-ready identity mapping."""

        return {
            field: str(getattr(self, field))
            if isinstance(getattr(self, field), UUID)
            else getattr(self, field)
            for field in self.__dataclass_fields__
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CompletedBarSeriesIdentity:
        """Reconstruct and validate a series identity from canonical data."""

        fields = exact_dict(
            value,
            _COMPLETED_BAR_SERIES_IDENTITY_KEYS,
            "CompletedBarSeriesIdentity",
        )
        return cls(
            instrument_id=raw_string(fields["instrument_id"], "instrument_id"),
            venue=raw_string(fields["venue"], "venue"),
            canonical_bar_specification=raw_string(
                fields["canonical_bar_specification"],
                "canonical_bar_specification",
            ),
            interval_ns=raw_int(fields["interval_ns"], "interval_ns"),
            aggregation_policy=raw_string(fields["aggregation_policy"], "aggregation_policy"),
            timestamp_policy=raw_string(fields["timestamp_policy"], "timestamp_policy"),
            completion_policy=raw_string(fields["completion_policy"], "completion_policy"),
            revision_policy=raw_string(fields["revision_policy"], "revision_policy"),
            calendar_id=raw_string(fields["calendar_id"], "calendar_id"),
            calendar_definition_version=raw_int(
                fields["calendar_definition_version"],
                "calendar_definition_version",
            ),
            calendar_definition_digest=raw_string(
                fields["calendar_definition_digest"],
                "calendar_definition_digest",
            ),
            calendar_definition_effective_from_ns=raw_int(
                fields["calendar_definition_effective_from_ns"],
                "calendar_definition_effective_from_ns",
            ),
            analytical_profile_id=raw_string(
                fields["analytical_profile_id"],
                "analytical_profile_id",
            ),
            analytical_profile_version=raw_int(
                fields["analytical_profile_version"],
                "analytical_profile_version",
            ),
            configuration_epoch=uuid_from_wire(
                fields["configuration_epoch"],
                "configuration_epoch",
            ),
            configuration_digest=raw_string(
                fields["configuration_digest"],
                "configuration_digest",
            ),
            canonical_producer_id=raw_string(
                fields["canonical_producer_id"],
                "canonical_producer_id",
            ),
            output_schema_version=raw_int(
                fields["output_schema_version"],
                "output_schema_version",
            ),
            series_id=raw_string(fields["series_id"], "series_id"),
        )


@dataclass(frozen=True, slots=True)
class CompletedBarLineageEntry:
    """Preserve one historical or live source path into a canonical bar.

    ``input_identity`` preserves the exact upstream path without changing the
    canonical output series identity. Source, receive, and normalization times
    are positive UTC Unix nanoseconds. Correction metadata is an immutable
    ordered key/value tuple; it records provider facts but never authorizes a
    canonical revision.
    """

    source_class: Literal["HISTORICAL", "LIVE"]
    input_identity: CompletedBarInputIdentity
    provider_observation_ref: str
    evidence_refs: tuple[str, ...]
    source_observed_ts_ns: int
    source_received_ts_ns: int
    normalized_ts_ns: int
    transformation_chain: tuple[str, ...]
    source_correction_metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if self.source_class not in {"HISTORICAL", "LIVE"}:
            raise ValueError("source_class must be HISTORICAL or LIVE")
        if not isinstance(self.input_identity, CompletedBarInputIdentity):
            raise ValueError("input_identity must be a CompletedBarInputIdentity")
        if not isinstance(self.provider_observation_ref, str) or not self.provider_observation_ref:
            raise ValueError("provider_observation_ref must be a non-empty string")
        if len(self.provider_observation_ref) > 256:
            raise ValueError("provider_observation_ref must be at most 256 characters")
        object.__setattr__(self, "evidence_refs", evidence_references(self.evidence_refs))
        for field in (
            "source_observed_ts_ns",
            "source_received_ts_ns",
            "normalized_ts_ns",
        ):
            positive_int64(getattr(self, field), field)
        if not (self.source_observed_ts_ns <= self.source_received_ts_ns <= self.normalized_ts_ns):
            raise ValueError("lineage timestamps must satisfy observed <= received <= normalized")
        object.__setattr__(
            self,
            "transformation_chain",
            text_tuple(
                self.transformation_chain,
                "transformation_chain",
                maximum_items=16,
            ),
        )
        if not isinstance(self.source_correction_metadata, tuple):
            raise ValueError("source_correction_metadata must be a tuple")
        normalized_metadata: list[tuple[str, str]] = []
        for item in self.source_correction_metadata:
            if not isinstance(item, tuple) or len(item) != 2:
                raise ValueError("source correction metadata entries must be key/value tuples")
            normalized_metadata.append(
                (
                    bounded_ascii(item[0], "correction key"),
                    bounded_ascii(item[1], "correction value"),
                ),
            )
        if normalized_metadata != sorted(normalized_metadata):
            raise ValueError("source correction metadata must use deterministic key order")
        if len({key for key, _ in normalized_metadata}) != len(normalized_metadata):
            raise ValueError("source correction metadata keys must be unique")
        object.__setattr__(self, "source_correction_metadata", tuple(normalized_metadata))

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical serialization-ready lineage mapping."""

        return {
            "source_class": self.source_class,
            "input_identity": self.input_identity.to_dict(),
            "provider_observation_ref": self.provider_observation_ref,
            "evidence_refs": list(self.evidence_refs),
            "source_observed_ts_ns": self.source_observed_ts_ns,
            "source_received_ts_ns": self.source_received_ts_ns,
            "normalized_ts_ns": self.normalized_ts_ns,
            "transformation_chain": list(self.transformation_chain),
            "source_correction_metadata": [list(item) for item in self.source_correction_metadata],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CompletedBarLineageEntry:
        """Reconstruct and validate one lineage entry from canonical data."""

        fields = exact_dict(value, _COMPLETED_BAR_LINEAGE_KEYS, "CompletedBarLineageEntry")
        metadata: list[tuple[str, str]] = []
        for item in raw_list(fields["source_correction_metadata"], "source_correction_metadata"):
            values = raw_list(item, "source correction metadata entry")
            if len(values) != 2:
                raise ValueError("source correction metadata entries require exactly two values")
            metadata.append(
                (
                    raw_string(values[0], "source correction metadata key"),
                    raw_string(values[1], "source correction metadata value"),
                ),
            )
        return cls(
            source_class=raw_string(fields["source_class"], "source_class"),  # type: ignore[arg-type]
            input_identity=CompletedBarInputIdentity.from_dict(fields["input_identity"]),
            provider_observation_ref=raw_string(
                fields["provider_observation_ref"],
                "provider_observation_ref",
            ),
            evidence_refs=raw_string_list(fields["evidence_refs"], "evidence_refs"),
            source_observed_ts_ns=raw_int(
                fields["source_observed_ts_ns"],
                "source_observed_ts_ns",
            ),
            source_received_ts_ns=raw_int(
                fields["source_received_ts_ns"],
                "source_received_ts_ns",
            ),
            normalized_ts_ns=raw_int(fields["normalized_ts_ns"], "normalized_ts_ns"),
            transformation_chain=raw_string_list(
                fields["transformation_chain"],
                "transformation_chain",
            ),
            source_correction_metadata=tuple(metadata),
        )


@dataclass(frozen=True, slots=True)
class CompletedBarV1:
    """Carry one immutable closed canonical bar with complete identity.

    Event time is always the exclusive interval end. A ``PARTIAL`` bar is a
    final closed-interval observation built from one or more truthful
    constituents; it is never upgraded in place. Missing or unsupported volume
    uses ``None`` plus ``VolumeState`` rather than numeric zero or a sentinel.
    """

    series_id: str
    series_identity: CompletedBarSeriesIdentity
    interval_start_ns: int
    interval_end_ns: int
    run_epoch: UUID
    publication_sequence: int
    completion_state: BarCompletionState
    expected_constituent_count: int
    received_constituent_count: int
    missing_subintervals: tuple[tuple[int, int], ...]
    completion_reasons: tuple[MetricReasonCode, ...]
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    volume_state: VolumeState
    trade_date: date
    exchange_state: str
    product_phases: tuple[str, ...]
    state_evidence_refs: tuple[str, ...]
    projection_evidence_refs: tuple[str, ...]
    published_ts_ns: int
    lineage: tuple[CompletedBarLineageEntry, ...]
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "series_id", topic_token(self.series_id))
        if not isinstance(self.series_identity, CompletedBarSeriesIdentity):
            raise ValueError("series_identity must be a CompletedBarSeriesIdentity")
        if self.series_id != self.series_identity.series_id:
            raise ValueError("route series_id must match complete series identity")
        positive_int64(self.interval_start_ns, "interval_start_ns")
        positive_int64(self.interval_end_ns, "interval_end_ns")
        if self.interval_end_ns - self.interval_start_ns != self.series_identity.interval_ns:
            raise ValueError("bar interval must match the series interval")
        uuid_value(self.run_epoch, "run_epoch")
        positive_int64(self.publication_sequence, "publication_sequence")
        if not isinstance(self.completion_state, BarCompletionState):
            raise ValueError("completion_state must be a BarCompletionState")
        positive_int(self.expected_constituent_count, "expected_constituent_count")
        positive_int(self.received_constituent_count, "received_constituent_count")
        if self.received_constituent_count > self.expected_constituent_count:
            raise ValueError("received constituent count cannot exceed expected count")
        self._validate_missing_intervals()
        self._validate_completion_reasons()
        for field in ("open", "high", "low", "close"):
            decimal_value(getattr(self, field), field)
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("bar prices must satisfy low <= open/close <= high")
        if self.high < self.low:
            raise ValueError("high must not be below low")
        self._validate_volume()
        if type(self.trade_date) is not date:
            raise ValueError("trade_date must be a date")
        object.__setattr__(
            self, "exchange_state", bounded_ascii(self.exchange_state, "exchange_state")
        )
        object.__setattr__(
            self,
            "product_phases",
            text_tuple(self.product_phases, "product_phases", maximum_items=16),
        )
        object.__setattr__(
            self, "state_evidence_refs", evidence_references(self.state_evidence_refs)
        )
        object.__setattr__(
            self,
            "projection_evidence_refs",
            evidence_references(self.projection_evidence_refs),
        )
        positive_int64(self.published_ts_ns, "published_ts_ns")
        if not isinstance(self.lineage, tuple) or any(
            not isinstance(item, CompletedBarLineageEntry) for item in self.lineage
        ):
            raise ValueError("lineage must be a tuple of CompletedBarLineageEntry values")
        if not self.lineage or len(self.lineage) > 64:
            raise ValueError("lineage must contain 1 through 64 entries")
        if len(self.lineage) != len(set(self.lineage)):
            raise ValueError("lineage entries must be unique")
        if not isinstance(self.health, MetricHealth):
            raise ValueError("health must be a MetricHealth")
        if not isinstance(self.fidelity, MetricFidelity):
            raise ValueError("fidelity must be a MetricFidelity")
        if self.completion_state is BarCompletionState.PARTIAL and (
            self.health is not MetricHealth.DEGRADED or self.fidelity is not MetricFidelity.PARTIAL
        ):
            raise ValueError("PARTIAL bars require DEGRADED health and PARTIAL fidelity")
        object.__setattr__(self, "evidence_refs", evidence_references(self.evidence_refs))
        all_references = evidence_references(
            (
                *self.state_evidence_refs,
                *self.projection_evidence_refs,
                *self.evidence_refs,
                *(item.provider_observation_ref for item in self.lineage),
                *(ref for item in self.lineage for ref in item.evidence_refs),
            ),
        )
        if len(all_references) > 256:
            raise ValueError("completed bar evidence exceeds the payload reference bound")
        if self.published_ts_ns < max(item.normalized_ts_ns for item in self.lineage):
            raise ValueError("published_ts_ns cannot precede lineage normalization")

    def _validate_missing_intervals(self) -> None:
        if not isinstance(self.missing_subintervals, tuple):
            raise ValueError("missing_subintervals must be a tuple")
        if len(self.missing_subintervals) > self.expected_constituent_count:
            raise ValueError("missing intervals cannot exceed the constituent count")
        if len(self.missing_subintervals) != len(set(self.missing_subintervals)):
            raise ValueError("missing subintervals must be unique, ordered, and non-overlapping")
        if self.series_identity.interval_ns % self.expected_constituent_count:
            raise ValueError("bar interval must divide into exact constituent slots")
        constituent_interval_ns = (
            self.series_identity.interval_ns // self.expected_constituent_count
        )
        previous_end = self.interval_start_ns
        for start_ns, end_ns in self.missing_subintervals:
            positive_int64(start_ns, "missing subinterval start")
            positive_int64(end_ns, "missing subinterval end")
            if (
                start_ns < self.interval_start_ns
                or end_ns > self.interval_end_ns
                or end_ns <= start_ns
            ):
                raise ValueError("missing subintervals must be valid intervals inside the bar")
            if start_ns < previous_end:
                raise ValueError("missing subintervals must be ordered and non-overlapping")
            if (
                end_ns - start_ns != constituent_interval_ns
                or (start_ns - self.interval_start_ns) % constituent_interval_ns
            ):
                raise ValueError("missing subintervals must be exact constituent slots")
            previous_end = end_ns
        expected_missing = self.expected_constituent_count - self.received_constituent_count
        if len(self.missing_subintervals) != expected_missing:
            raise ValueError("missing subinterval count must reconcile constituent accounting")

    def _validate_completion_reasons(self) -> None:
        if not isinstance(self.completion_reasons, tuple) or any(
            not isinstance(reason, MetricReasonCode) for reason in self.completion_reasons
        ):
            raise ValueError("completion_reasons must contain MetricReasonCode values")
        if len(self.completion_reasons) > 16 or len(self.completion_reasons) != len(
            set(self.completion_reasons),
        ):
            raise ValueError("completion_reasons must contain at most 16 unique values")
        if (
            tuple(sorted(self.completion_reasons, key=_METRIC_REASON_ORDER.__getitem__))
            != self.completion_reasons
        ):
            raise ValueError("completion_reasons must use canonical MetricReasonCode order")
        if self.completion_state is BarCompletionState.COMPLETE:
            if self.received_constituent_count != self.expected_constituent_count:
                raise ValueError("COMPLETE bars require every expected constituent")
            if self.missing_subintervals or self.completion_reasons:
                raise ValueError("COMPLETE bars cannot report missing intervals or reasons")
        else:
            if self.received_constituent_count >= self.expected_constituent_count:
                raise ValueError("PARTIAL bars require fewer than all expected constituents")
            required = {
                MetricReasonCode.PARTIAL_COMPLETED_BAR,
                MetricReasonCode.MISSING_SUBINTERVALS,
            }
            if not required.issubset(self.completion_reasons):
                raise ValueError("PARTIAL bars require typed partial and missing-interval reasons")

    def _validate_volume(self) -> None:
        if not isinstance(self.volume_state, VolumeState):
            raise ValueError("volume_state must be a VolumeState")
        if self.volume_state in {VolumeState.OBSERVED, VolumeState.PARTIAL}:
            if self.volume is None:
                raise ValueError("observed or partial volume state requires a value")
            decimal_value(self.volume, "volume")
            if self.volume < 0:
                raise ValueError("volume must not be negative")
        elif self.volume is not None:
            raise ValueError("missing or unsupported volume state requires a null value")

    @property
    def key(self) -> tuple[str, int, int]:
        """Return canonical market observation identity for conflict checks."""

        return (self.series_id, self.interval_start_ns, self.interval_end_ns)

    @property
    def ts_event(self) -> int:
        """Return the accepted interval-end event timestamp."""

        return self.interval_end_ns

    @property
    def ts_init(self) -> int:
        """Return the canonical publication timestamp."""

        return self.published_ts_ns

    @property
    def equivalence_key(self) -> tuple[object, ...]:
        """Return canonical content excluding delivery and additional lineage."""

        return (
            self.series_identity,
            self.interval_start_ns,
            self.interval_end_ns,
            self.completion_state,
            self.expected_constituent_count,
            self.received_constituent_count,
            self.missing_subintervals,
            self.completion_reasons,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.volume_state,
            self.trade_date,
            self.exchange_state,
            self.product_phases,
            self.health,
            self.fidelity,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the canonical serialization-ready completed-bar mapping."""

        return {
            "series_id": self.series_id,
            "series_identity": self.series_identity.to_dict(),
            "interval_start_ns": self.interval_start_ns,
            "interval_end_ns": self.interval_end_ns,
            "run_epoch": str(self.run_epoch),
            "publication_sequence": self.publication_sequence,
            "completion_state": self.completion_state.value,
            "expected_constituent_count": self.expected_constituent_count,
            "received_constituent_count": self.received_constituent_count,
            "missing_subintervals": [list(item) for item in self.missing_subintervals],
            "completion_reasons": [reason.value for reason in self.completion_reasons],
            "open": decimal_to_wire(self.open, "open"),
            "high": decimal_to_wire(self.high, "high"),
            "low": decimal_to_wire(self.low, "low"),
            "close": decimal_to_wire(self.close, "close"),
            "volume": None if self.volume is None else decimal_to_wire(self.volume, "volume"),
            "volume_state": self.volume_state.value,
            "trade_date": self.trade_date.isoformat(),
            "exchange_state": self.exchange_state,
            "product_phases": list(self.product_phases),
            "state_evidence_refs": list(self.state_evidence_refs),
            "projection_evidence_refs": list(self.projection_evidence_refs),
            "published_ts_ns": self.published_ts_ns,
            "lineage": [item.to_dict() for item in self.lineage],
            "health": self.health.value,
            "fidelity": self.fidelity.value,
            "evidence_refs": list(self.evidence_refs),
        }

    def to_bytes(self) -> bytes:
        """Serialize the completed bar deterministically without float conversion."""

        return canonical_bytes(self.to_dict())

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> CompletedBarV1:
        """Reconstruct and validate a completed bar from canonical data."""

        fields = exact_dict(value, _COMPLETED_BAR_KEYS, "CompletedBarV1")
        raw_trade_date = raw_string(fields["trade_date"], "trade_date")
        try:
            trade_date_value = date.fromisoformat(raw_trade_date)
        except ValueError as exc:
            raise ValueError("trade_date must be a canonical ISO date") from exc
        if trade_date_value.isoformat() != raw_trade_date:
            raise ValueError("trade_date must be a canonical ISO date")
        return cls(
            series_id=raw_string(fields["series_id"], "series_id"),
            series_identity=CompletedBarSeriesIdentity.from_dict(fields["series_identity"]),
            interval_start_ns=raw_int(fields["interval_start_ns"], "interval_start_ns"),
            interval_end_ns=raw_int(fields["interval_end_ns"], "interval_end_ns"),
            run_epoch=uuid_from_wire(fields["run_epoch"], "run_epoch"),
            publication_sequence=raw_int(
                fields["publication_sequence"],
                "publication_sequence",
            ),
            completion_state=BarCompletionState(
                raw_string(fields["completion_state"], "completion_state"),
            ),
            expected_constituent_count=raw_int(
                fields["expected_constituent_count"],
                "expected_constituent_count",
            ),
            received_constituent_count=raw_int(
                fields["received_constituent_count"],
                "received_constituent_count",
            ),
            missing_subintervals=_intervals_from_wire(
                fields["missing_subintervals"],
                "missing_subintervals",
            ),
            completion_reasons=tuple(
                MetricReasonCode(reason)
                for reason in raw_string_list(
                    fields["completion_reasons"],
                    "completion_reasons",
                )
            ),
            open=decimal_from_wire(fields["open"], "open"),
            high=decimal_from_wire(fields["high"], "high"),
            low=decimal_from_wire(fields["low"], "low"),
            close=decimal_from_wire(fields["close"], "close"),
            volume=(
                None if fields["volume"] is None else decimal_from_wire(fields["volume"], "volume")
            ),
            volume_state=VolumeState(raw_string(fields["volume_state"], "volume_state")),
            trade_date=trade_date_value,
            exchange_state=raw_string(fields["exchange_state"], "exchange_state"),
            product_phases=raw_string_list(fields["product_phases"], "product_phases"),
            state_evidence_refs=raw_string_list(
                fields["state_evidence_refs"],
                "state_evidence_refs",
            ),
            projection_evidence_refs=raw_string_list(
                fields["projection_evidence_refs"],
                "projection_evidence_refs",
            ),
            published_ts_ns=raw_int(fields["published_ts_ns"], "published_ts_ns"),
            lineage=tuple(
                CompletedBarLineageEntry.from_dict(item)
                for item in raw_list(fields["lineage"], "lineage")
            ),
            health=MetricHealth(raw_string(fields["health"], "health")),
            fidelity=MetricFidelity(raw_string(fields["fidelity"], "fidelity")),
            evidence_refs=raw_string_list(fields["evidence_refs"], "evidence_refs"),
        )


def _canonical_completed_bar_data_type(series_id: str) -> DataType:
    """Construct the pinned Nautilus metadata-qualified route for a series."""

    return DataType(COMPLETED_BAR_V1_TYPE_NAME, metadata={"series_id": topic_token(series_id)})


def _validate_completed_bar_route(data_type: DataType, payload: CompletedBarV1) -> None:
    """Fail closed when route type, metadata, and payload identity disagree."""

    if not isinstance(data_type, DataType):
        raise ValueError("data_type must be a Nautilus DataType")
    if not isinstance(payload, CompletedBarV1):
        raise ValueError("payload must be a CompletedBarV1")
    if data_type.type_name != COMPLETED_BAR_V1_TYPE_NAME:
        raise ValueError("completed-bar route type name is incompatible")
    if data_type.identifier is not None:
        raise ValueError("completed-bar route identifier must be None")
    metadata = data_type.metadata
    if metadata != {"series_id": payload.series_id}:
        raise ValueError("completed-bar route metadata must match payload series identity")
    if payload.series_identity.series_id != payload.series_id:
        raise ValueError("completed-bar payload series identity is inconsistent")


def _intervals_from_wire(value: object, label: str) -> tuple[tuple[int, int], ...]:
    result: list[tuple[int, int]] = []
    for item in raw_list(value, label):
        fields = raw_list(item, f"{label} entry")
        if len(fields) != 2:
            raise ValueError(f"{label} entries require exactly two integers")
        result.append(
            (
                raw_int(fields[0], f"{label} start"),
                raw_int(fields[1], f"{label} end"),
            ),
        )
    return tuple(result)
