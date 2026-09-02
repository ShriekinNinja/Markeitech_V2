from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal
from functools import partial
from types import MappingProxyType
from typing import Any
from uuid import UUID

from nautilus_trader.common import DataActor, DataActorConfig
from nautilus_trader.model import ActorId, BarType, ClientId, CustomData, DataType

from markeitech.acquisition import (
    HISTORICAL_BATCH_TYPE_NAME,
    HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
    FeedKind,
    FeedRequirement,
    HistoricalDependencyDemandEvent,
    NautilusSubscriptionPort,
)
from markeitech.acquisition.historical import HistoricalRequest
from markeitech.acquisition.historical_execution import (
    HistoricalBatch,
    HistoricalExecutionPort,
    _HistoricalExecutionAuthority,
)
from markeitech.intelligence._contract_validation import (
    bounded_ascii,
    digest,
    positive_int,
    positive_int64,
    topic_token,
    uuid_value,
)
from markeitech.intelligence.calendar_delivery import (
    ProjectionRequestPhase,
    ProjectionRequestState,
    ProjectionRetryPolicy,
    begin_projection_retry,
    classify_projection_response,
    ready_projection_state,
    retain_pending_calendars,
    schedule_projection_retry,
    start_projection_cycle,
    stop_projection_state,
    terminal_projection_state,
)
from markeitech.intelligence.calendar_messages import (
    CALENDAR_PROJECTION_REQUEST_TYPE_NAME,
    CALENDAR_PROJECTION_RESPONSE_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME,
    CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME,
    CALENDAR_TRANSITION_V2_TYPE_NAME,
    CalendarCurrentState,
    CalendarDefinitionExpectation,
    CalendarProjectionRequest,
    CalendarProjectionResponse,
    CalendarStateSnapshotResponse,
    CalendarTransitionV2,
)
from markeitech.intelligence.completed_bar_messages import (
    BarCompletionState,
    CompletedBarInputIdentity,
    CompletedBarLineageEntry,
    CompletedBarSeriesIdentity,
    CompletedBarV1,
    VolumeState,
    _canonical_completed_bar_data_type,
    _validate_completed_bar_route,
)
from markeitech.intelligence.historical_bar_validation import (
    _HistoricalBarObservation,
    _HistoricalUsage,
    _HistoricalValidationDisposition,
    _HistoricalValidationRequest,
    _HistoricalValidationResult,
    _validate_historical_batch,
)
from markeitech.intelligence.metric_messages import (
    MetricFidelity,
    MetricHealth,
    MetricReasonCode,
)
from markeitech.intelligence.metric_producer_manifest import (
    CONSUMER_READINESS_TIMEOUT_MS,
    MAXIMUM_BUFFERED_LIVE_COMPLETED_BARS,
    MAXIMUM_HISTORY_LIVE_OVERLAP_BARS,
    MAXIMUM_RETAINED_COMPLETED_BARS,
    MAXIMUM_SERIES_PER_INSTANCE,
    _AcknowledgementDisposition,
    _ActivationDisposition,
    _BarSeriesProducerClaim,
    _StartupConsumerRequirement,
    _StartupReadinessDecision,
    _StartupReadinessValidator,
    _SubscriptionReadinessAcknowledgement,
)
from markeitech.intelligence.session import CalendarProjectionView
from markeitech.intelligence.session_state_delivery import (
    SessionStateDeliveryDisposition,
    SessionStateDeliveryPhase,
    SessionStateDeliveryPolicy,
    SessionStateDeliveryState,
    begin_session_state_retry,
    current_snapshot_request,
    observe_session_snapshot,
    observe_session_transition,
    resynchronize_session_state_cycle,
    schedule_session_state_retry,
    start_session_state_cycle,
    stop_session_state_delivery,
)
from markeitech.system.messages import ANALYTICAL_DEMAND_SIGNAL, AnalyticalDemandEvent

_READINESS_TYPE_NAME = "markeitech.completed_bar.subscription-readiness.v1"
_FOUNDATION_HEALTH_TYPE_NAME = "markeitech.completed_bar.foundation-health.v1"
_FOUNDATION_SHUTDOWN_TYPE_NAME = "markeitech.completed_bar.foundation-shutdown.v1"
_NANOSECONDS_PER_MILLISECOND = 1_000_000
_FIVE_SECONDS_NS = 5_000_000_000
_ONE_MINUTE_NS = 60_000_000_000
_EXPECTED_CONSTITUENTS = 12
_METRIC_REASON_ORDER = {reason: index for index, reason in enumerate(MetricReasonCode)}
_CALENDAR_PROJECTION_RETRY_ALERT = "completed-bar-calendar-projection-retry"
_SESSION_STATE_RETRY_ALERT = "completed-bar-session-state-retry"
_NANOSECONDS_PER_DAY = 86_400_000_000_000


@dataclass(frozen=True, slots=True)
class _CompletedBarFoundationPolicy:
    """Private, versioned resource and close-finality policy for Slice 2."""

    completion_grace_ms: int = 1_000
    maximum_retained_completed_bars: int = MAXIMUM_RETAINED_COMPLETED_BARS
    maximum_history_live_overlap_bars: int = MAXIMUM_HISTORY_LIVE_OVERLAP_BARS
    maximum_buffered_live_completed_bars: int = MAXIMUM_BUFFERED_LIVE_COMPLETED_BARS
    maximum_open_buckets_per_series: int = 2
    maximum_open_buckets_per_instance: int = 32
    policy_version: int = 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.completion_grace_ms, int)
            or isinstance(self.completion_grace_ms, bool)
            or not 1 <= self.completion_grace_ms <= 5_000
        ):
            raise ValueError("completion_grace_ms must be an integer from 1 through 5000")
        exact = {
            "maximum_retained_completed_bars": MAXIMUM_RETAINED_COMPLETED_BARS,
            "maximum_history_live_overlap_bars": MAXIMUM_HISTORY_LIVE_OVERLAP_BARS,
            "maximum_buffered_live_completed_bars": MAXIMUM_BUFFERED_LIVE_COMPLETED_BARS,
        }
        for name, expected in exact.items():
            if getattr(self, name) != expected:
                raise ValueError(f"{name} must remain exactly {expected} in Slice 2")
        positive_int(self.maximum_open_buckets_per_series, "maximum_open_buckets_per_series")
        positive_int(self.maximum_open_buckets_per_instance, "maximum_open_buckets_per_instance")
        if self.maximum_open_buckets_per_instance < self.maximum_open_buckets_per_series:
            raise ValueError("instance bucket bound cannot be below its per-series bound")
        if self.policy_version != 1:
            raise ValueError("foundation policy_version must be 1")

    @property
    def completion_grace_ns(self) -> int:
        return self.completion_grace_ms * _NANOSECONDS_PER_MILLISECOND


@dataclass(frozen=True, slots=True)
class _NativeLiveInputAuthority:
    """Bind lineage identity to the exact native subscription client and adapter lane."""

    provider_id: str = "IB"
    adapter_id: str = "nautilus-ib"
    source_stream_id: str = "watchlist-last-5s"
    source_schema_id: str = "nautilus.bar.v1"

    def __post_init__(self) -> None:
        expected = {
            "provider_id": "IB",
            "adapter_id": "nautilus-ib",
            "source_stream_id": "watchlist-last-5s",
            "source_schema_id": "nautilus.bar.v1",
        }
        for field_name in (
            "provider_id",
            "adapter_id",
            "source_stream_id",
            "source_schema_id",
        ):
            object.__setattr__(
                self,
                field_name,
                bounded_ascii(getattr(self, field_name), field_name),
            )
            if getattr(self, field_name) != expected[field_name]:
                raise ValueError(
                    f"Slice 2 native subscription authority requires {field_name}="
                    f"{expected[field_name]}",
                )
        ClientId.from_str(self.provider_id)

    @property
    def client_id(self) -> ClientId:
        return ClientId.from_str(self.provider_id)

    def input_identity(self, source_selector: str) -> CompletedBarInputIdentity:
        return CompletedBarInputIdentity(
            provider_id=self.provider_id,
            adapter_id=self.adapter_id,
            source_stream_id=self.source_stream_id,
            source_selector=source_selector,
            source_schema_id=self.source_schema_id,
        )


@dataclass(frozen=True, slots=True)
class _HistoricalBootstrapBinding:
    """Bind one planner-produced transport request to its pure validation authority."""

    transport_request: HistoricalRequest
    validation_request: _HistoricalValidationRequest
    execution_authority: _HistoricalExecutionAuthority

    @classmethod
    def from_execution_port(
        cls,
        *,
        transport_request: HistoricalRequest,
        validation_request: _HistoricalValidationRequest,
        execution_port: HistoricalExecutionPort,
    ) -> _HistoricalBootstrapBinding:
        """Bind expected source identity to the actual port before actor construction."""

        return cls(
            transport_request=transport_request,
            validation_request=validation_request,
            execution_authority=_HistoricalExecutionAuthority.from_port(execution_port),
        )

    def __post_init__(self) -> None:
        if not isinstance(self.transport_request, HistoricalRequest):
            raise ValueError("transport_request must be a HistoricalRequest")
        if not isinstance(self.validation_request, _HistoricalValidationRequest):
            raise ValueError("validation_request must be typed")
        if not isinstance(self.execution_authority, _HistoricalExecutionAuthority):
            raise ValueError("historical execution authority must be typed")
        if self.validation_request.usage is not _HistoricalUsage.CANONICAL_SERIES_BOOTSTRAP:
            raise ValueError("foundation accepts only canonical_series_bootstrap history")
        request = self.transport_request
        validation = self.validation_request
        if (
            request.request_id != validation.request_id
            or request.instrument_id != validation.series_identity.instrument_id
            or request.kind is not FeedKind.BARS
            or request.start_ns != validation.requested_start_ns
            or request.end_ns != validation.requested_end_ns
            or request.limit > validation.maximum_raw_observations
        ):
            raise ValueError("historical transport and validation requests must bind exactly")
        expected = validation.expected_input_identity
        actual = self.execution_authority
        if (
            expected.provider_id != actual.provider_id
            or expected.adapter_id != actual.adapter_id
            or expected.source_stream_id != actual.source_stream_id
            or expected.source_schema_id != actual.source_schema_id
        ):
            raise ValueError(
                "historical input identity must bind the actual execution-port authority",
            )

    def matches(self, request: HistoricalRequest) -> bool:
        return (
            isinstance(request, HistoricalRequest)
            and request.request_id == self.transport_request.request_id
            and request.request_key == self.transport_request.request_key
            and request.window == self.transport_request.window
            and request.dependencies == self.transport_request.dependencies
        )


@dataclass(frozen=True, slots=True)
class _CompletedBarFoundationSeriesConfig:
    """Private exact input/output and calendar authority for one canonical series."""

    series_identity: CompletedBarSeriesIdentity
    producer_claim: _BarSeriesProducerClaim
    live_input_identity: CompletedBarInputIdentity
    historical_bootstrap: _HistoricalBootstrapBinding
    live_selector: str
    required_consumers: tuple[_StartupConsumerRequirement, ...]
    calendar_source: str
    calendar_source_epoch: str
    live_authority: _NativeLiveInputAuthority = field(default_factory=_NativeLiveInputAuthority)
    demand_priority: int = 50

    def __post_init__(self) -> None:
        if not isinstance(self.series_identity, CompletedBarSeriesIdentity):
            raise ValueError("series_identity must be typed")
        if not isinstance(self.producer_claim, _BarSeriesProducerClaim):
            raise ValueError("producer_claim must be typed")
        if (
            self.producer_claim.series_identity != self.series_identity
            or self.producer_claim.activation is not _ActivationDisposition.ENABLED
        ):
            raise ValueError("foundation series requires its exact enabled manifest claim")
        if not isinstance(self.live_input_identity, CompletedBarInputIdentity):
            raise ValueError("live_input_identity must be typed")
        if not isinstance(self.live_authority, _NativeLiveInputAuthority):
            raise ValueError("live_authority must be typed")
        if not isinstance(self.historical_bootstrap, _HistoricalBootstrapBinding):
            raise ValueError("historical_bootstrap must be typed")
        object.__setattr__(
            self,
            "live_selector",
            bounded_ascii(self.live_selector, "live_selector"),
        )
        object.__setattr__(
            self,
            "calendar_source",
            bounded_ascii(self.calendar_source, "calendar_source"),
        )
        object.__setattr__(
            self,
            "calendar_source_epoch",
            bounded_ascii(self.calendar_source_epoch, "calendar_source_epoch"),
        )
        try:
            canonical_bar_type = BarType.from_str(
                self.series_identity.canonical_bar_specification,
            )
            live_bar_type = BarType.from_str(self.live_bar_type)
            historical_bar_type = BarType.from_str(
                f"{self.series_identity.instrument_id}-"
                f"{self.historical_bootstrap.transport_request.selector}",
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("foundation BarType configuration is invalid") from exc
        if (
            str(canonical_bar_type) != self.series_identity.canonical_bar_specification
            or str(canonical_bar_type.instrument_id) != self.series_identity.instrument_id
            or canonical_bar_type.spec.get_interval_ns() != self.series_identity.interval_ns
            or self.series_identity.venue
            != self.series_identity.instrument_id.rsplit(".", 1)[-1]
        ):
            raise ValueError("canonical BarType must bind the exact series instrument and interval")
        if self.series_identity.interval_ns != _ONE_MINUTE_NS:
            raise ValueError("Slice 2 enables only one-minute canonical output")
        if self.live_selector != "5-SECOND-LAST-EXTERNAL":
            raise ValueError("Slice 2 enables only five-second live input")
        if (
            str(live_bar_type) != self.live_bar_type
            or str(live_bar_type.instrument_id) != self.series_identity.instrument_id
            or live_bar_type.spec.get_interval_ns() != _FIVE_SECONDS_NS
            or self.live_input_identity != self.live_authority.input_identity(self.live_bar_type)
        ):
            raise ValueError(
                "live input identity must bind the exact native subscription authority and BarType",
            )
        validation = self.historical_bootstrap.validation_request
        if validation.series_identity != self.series_identity:
            raise ValueError("historical bootstrap must target the canonical series")
        if validation.expected_input_identity == self.live_input_identity:
            raise ValueError("historical and live paths require distinct input identities")
        expected_historical_selector = (
            f"{self.series_identity.instrument_id}-"
            f"{self.historical_bootstrap.transport_request.selector}"
        )
        if (
            str(historical_bar_type) != expected_historical_selector
            or str(historical_bar_type.instrument_id) != self.series_identity.instrument_id
            or historical_bar_type.spec.get_interval_ns() != self.series_identity.interval_ns
            or validation.expected_input_identity.source_selector
            != expected_historical_selector
        ):
            raise ValueError("historical input identity must bind the exact request BarType")
        if not any(
            dependency.consumer_id == self.series_identity.canonical_producer_id
            and dependency.capability_id == "metric:completed-bar-foundation"
            and dependency.purpose == _HistoricalUsage.CANONICAL_SERIES_BOOTSTRAP.value
            for dependency in self.historical_bootstrap.transport_request.dependencies
        ):
            raise ValueError("historical bootstrap requires the exact foundation dependency")
        if not isinstance(self.required_consumers, tuple) or not self.required_consumers:
            raise ValueError("required_consumers must be a non-empty tuple")
        keys = tuple(item.key for item in self.required_consumers)
        if keys != tuple(sorted(set(keys))):
            raise ValueError("required_consumers must be unique and sorted")
        if any(
            item.series_id != self.series_identity.series_id
            or item.producer_actor_id != self.series_identity.canonical_producer_id
            for item in self.required_consumers
        ):
            raise ValueError("readiness requirements must match the exact series and producer")
        if (
            not isinstance(self.demand_priority, int)
            or isinstance(self.demand_priority, bool)
            or not 0 <= self.demand_priority <= 100
        ):
            raise ValueError("demand_priority must be from 0 through 100")

    @property
    def series_id(self) -> str:
        return self.series_identity.series_id

    @property
    def live_bar_type(self) -> str:
        return f"{self.series_identity.instrument_id}-{self.live_selector}"


class _CompletedBarFoundationActorConfig(DataActorConfig):
    """Private disabled actor configuration; it is not accepted profile configuration."""

    def __new__(
        cls,
        *,
        series: tuple[_CompletedBarFoundationSeriesConfig, ...],
        startup_epoch: UUID,
        run_epoch: UUID,
        manifest_digest: str,
        policy: _CompletedBarFoundationPolicy | None = None,
        projection_lookback_days: int = 120,
        projection_lookahead_days: int = 14,
        projection_retry: dict[str, int] | None = None,
        current_state_delivery: dict[str, int] | None = None,
        actor_id: str | ActorId = "COMPLETED-BARS-1",
    ) -> _CompletedBarFoundationActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.series = series
        obj.startup_epoch = startup_epoch
        obj.run_epoch = run_epoch
        obj.manifest_digest = manifest_digest
        obj.policy = policy or _CompletedBarFoundationPolicy()
        obj.projection_lookback_days = projection_lookback_days
        obj.projection_lookahead_days = projection_lookahead_days
        obj.projection_retry = dict(
            projection_retry
            or {
                "response_timeout_ms": 5_000,
                "maximum_attempts": 3,
                "retry_backoff_ms": 1_000,
                "maximum_elapsed_ms": 60_000,
            },
        )
        obj.current_state_delivery = dict(
            current_state_delivery
            or {
                "policy_version": 1,
                "response_timeout_ms": 5_000,
                "maximum_attempts": 3,
                "retry_backoff_ms": 1_000,
                "maximum_elapsed_ms": 60_000,
                "maximum_buffered_transitions_per_calendar": 8,
                "maximum_total_buffered_transitions": 32,
                "boundary_delivery_grace_ms": 2_000,
            },
        )
        return obj


@dataclass(frozen=True, slots=True)
class _CalendarContext:
    trade_date: date
    exchange_state: str
    product_phases: tuple[str, ...]
    state_evidence_refs: tuple[str, ...]
    projection_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _LiveConstituent:
    interval_start_ns: int
    interval_end_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    volume_state: VolumeState
    lineage: CompletedBarLineageEntry
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        positive_int64(self.interval_start_ns, "interval_start_ns")
        positive_int64(self.interval_end_ns, "interval_end_ns")
        if self.interval_end_ns - self.interval_start_ns != _FIVE_SECONDS_NS:
            raise ValueError("live constituents must be exact five-second intervals")
        for field_name in ("open", "high", "low", "close"):
            if not isinstance(getattr(self, field_name), Decimal):
                raise ValueError(f"{field_name} must be Decimal")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("constituent prices violate OHLC ordering")
        if not isinstance(self.volume_state, VolumeState):
            raise ValueError("volume_state must be typed")
        if self.volume_state in {VolumeState.OBSERVED, VolumeState.PARTIAL}:
            if not isinstance(self.volume, Decimal) or self.volume < 0:
                raise ValueError("observed constituent volume must be a non-negative Decimal")
        elif self.volume is not None:
            raise ValueError("missing constituent volume must be null")
        if not isinstance(self.lineage, CompletedBarLineageEntry):
            raise ValueError("lineage must be typed")

    @property
    def equivalence_key(self) -> tuple[object, ...]:
        return (
            self.interval_start_ns,
            self.interval_end_ns,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.volume_state,
        )


@dataclass(slots=True)
class _LiveBucket:
    interval_start_ns: int
    interval_end_ns: int
    cutoff_ns: int
    slots: dict[int, _LiveConstituent] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class _CompletedBarCandidate:
    series_identity: CompletedBarSeriesIdentity
    interval_start_ns: int
    interval_end_ns: int
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
    context: _CalendarContext
    lineage: tuple[CompletedBarLineageEntry, ...]
    health: MetricHealth
    fidelity: MetricFidelity
    evidence_refs: tuple[str, ...]

    @property
    def key(self) -> tuple[str, int, int]:
        return (self.series_identity.series_id, self.interval_start_ns, self.interval_end_ns)

    @property
    def equivalence_key(self) -> tuple[object, ...]:
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
            self.context.trade_date,
            self.context.exchange_state,
            self.context.product_phases,
            self.health,
            self.fidelity,
        )

    def merge_lineage(self, other: _CompletedBarCandidate) -> _CompletedBarCandidate:
        if self.equivalence_key != other.equivalence_key:
            raise ValueError("cannot merge unequal completed-bar candidates")
        lineage = tuple(sorted(set((*self.lineage, *other.lineage)), key=_lineage_sort_key))
        context = replace(
            self.context,
            state_evidence_refs=tuple(
                sorted(
                    set(
                        (*self.context.state_evidence_refs, *other.context.state_evidence_refs),
                    ),
                ),
            ),
            projection_evidence_refs=tuple(
                sorted(
                    set(
                        (
                            *self.context.projection_evidence_refs,
                            *other.context.projection_evidence_refs,
                        ),
                    ),
                ),
            ),
        )
        evidence = tuple(sorted(set((*self.evidence_refs, *other.evidence_refs))))
        return replace(self, context=context, lineage=lineage, evidence_refs=evidence)

    def publish(self, *, run_epoch: UUID, sequence: int, published_ts_ns: int) -> CompletedBarV1:
        return CompletedBarV1(
            series_id=self.series_identity.series_id,
            series_identity=self.series_identity,
            interval_start_ns=self.interval_start_ns,
            interval_end_ns=self.interval_end_ns,
            run_epoch=run_epoch,
            publication_sequence=sequence,
            completion_state=self.completion_state,
            expected_constituent_count=self.expected_constituent_count,
            received_constituent_count=self.received_constituent_count,
            missing_subintervals=self.missing_subintervals,
            completion_reasons=self.completion_reasons,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
            volume_state=self.volume_state,
            trade_date=self.context.trade_date,
            exchange_state=self.context.exchange_state,
            product_phases=self.context.product_phases,
            state_evidence_refs=self.context.state_evidence_refs,
            projection_evidence_refs=self.context.projection_evidence_refs,
            published_ts_ns=published_ts_ns,
            lineage=self.lineage,
            health=self.health,
            fidelity=self.fidelity,
            evidence_refs=self.evidence_refs,
        )


class _SeriesAdmission:
    ACCEPTED = "ACCEPTED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    STALE = "STALE"
    LATE = "LATE"
    OVERFLOW = "OVERFLOW"
    TERMINAL = "TERMINAL"


class _FoundationSeriesState:
    """Bounded per-series aggregation, convergence, and immutable admission state."""

    def __init__(
        self,
        config: _CompletedBarFoundationSeriesConfig,
        policy: _CompletedBarFoundationPolicy,
        run_epoch: UUID,
    ) -> None:
        self.config = config
        self.policy = policy
        self.run_epoch = run_epoch
        self.readiness: _StartupReadinessValidator | None = None
        self.projection: CalendarProjectionView | None = None
        self.projection_ref: str | None = None
        self.transition: CalendarTransitionV2 | None = None
        self.current_state: CalendarCurrentState | None = None
        self.buckets: dict[int, _LiveBucket] = {}
        self.retained: deque[CompletedBarV1] = deque(maxlen=policy.maximum_retained_completed_bars)
        self.pending_live: list[_CompletedBarCandidate] = []
        self.overlap_hold: _CompletedBarCandidate | None = None
        self.history_terminal = False
        self.converged = False
        self.terminal = False
        self.demand_started = False
        self.readiness_resolved = False
        self.sequence = 0
        self.counters: Counter[str] = Counter()

    def start_readiness(
        self,
        *,
        startup_epoch: UUID,
        manifest_digest: str,
        started_at_ns: int,
    ) -> None:
        if self.readiness is not None:
            raise RuntimeError("series readiness already started")
        self.readiness = _StartupReadinessValidator(
            requirements=self.config.required_consumers,
            startup_epoch=startup_epoch,
            manifest_digest=manifest_digest,
            started_at_ns=started_at_ns,
        )

    def acknowledge(
        self,
        value: _SubscriptionReadinessAcknowledgement,
        *,
        received_at_ns: int,
    ) -> _AcknowledgementDisposition:
        if self.readiness is None:
            return _AcknowledgementDisposition.REJECTED
        disposition = self.readiness.acknowledge(value, received_at_ns=received_at_ns)
        self.counters[f"readiness_{disposition.value.lower()}"] += 1
        return disposition

    def readiness_decision(self, *, now_ns: int) -> _StartupReadinessDecision:
        if self.readiness is None:
            raise RuntimeError("series readiness has not started")
        return self.readiness.evaluate(now_ns=now_ns)

    def accept_projection(self, response: CalendarProjectionResponse) -> bool:
        if (
            self.terminal
            or response.requester != self.config.series_identity.canonical_producer_id
            or response.source != self.config.calendar_source
            or response.source_epoch != self.config.calendar_source_epoch
            or response.status != "READY"
            or self.config.series_identity.calendar_id
            not in response.requested_calendar_ids
        ):
            self.counters["projection_rejected"] += 1
            return False
        projection = next(
            (
                item
                for item in response.projections
                if item.calendar_id == self.config.series_identity.calendar_id
            ),
            None,
        )
        identity = self.config.series_identity
        if projection is None or (
            projection.definition_version != identity.calendar_definition_version
            or projection.definition_digest != identity.calendar_definition_digest
            or projection.definition_effective_from_ns
            != identity.calendar_definition_effective_from_ns
        ):
            self.counters["projection_rejected"] += 1
            return False
        self.projection = CalendarProjectionView(projection)
        self.projection_ref = f"calendar-projection:{response.request_id}"
        self.counters["projection_accepted"] += 1
        return True

    def accept_transition(self, transition: CalendarTransitionV2) -> bool:
        identity = self.config.series_identity
        if self.terminal or (
            transition.source != self.config.calendar_source
            or transition.source_epoch != self.config.calendar_source_epoch
            or transition.calendar_id != identity.calendar_id
            or transition.definition_version != identity.calendar_definition_version
            or transition.definition_digest != identity.calendar_definition_digest
            or transition.definition_effective_from_ns
            != identity.calendar_definition_effective_from_ns
        ):
            self.counters["transition_rejected"] += 1
            return False
        current = self.transition
        if current is not None and transition.revision <= current.revision:
            if transition == current:
                self.counters["transition_duplicate"] += 1
            else:
                self.counters["transition_rejected"] += 1
            return False
        self.transition = transition
        self.counters["transition_accepted"] += 1
        return True

    def install_current_state(self, current: CalendarCurrentState) -> bool:
        identity = self.config.series_identity
        if self.terminal or (
            current.source != self.config.calendar_source
            or current.source_epoch != self.config.calendar_source_epoch
            or current.calendar_id != identity.calendar_id
        ):
            self.counters["current_state_rejected"] += 1
            return False
        if (
            current.definition_version != identity.calendar_definition_version
            or current.definition_digest != identity.calendar_definition_digest
            or current.definition_effective_from_ns
            != identity.calendar_definition_effective_from_ns
        ):
            self.counters["current_state_rejected"] += 1
            return False
        existing = self.current_state
        if existing is not None and current.revision <= existing.revision:
            if current == existing:
                self.counters["current_state_duplicate"] += 1
            else:
                self.counters["current_state_rejected"] += 1
            return False
        self.current_state = current
        self.counters["current_state_accepted"] += 1
        return True

    def calendar_context(self, interval_end_ns: int) -> _CalendarContext | None:
        if self.projection is None or self.projection_ref is None:
            self.counters["calendar_unavailable"] += 1
            return None
        try:
            snapshot = self.projection.evaluate(interval_end_ns - 1)
        except ValueError:
            self.counters["calendar_unavailable"] += 1
            return None
        if snapshot.trade_date is None:
            self.counters["calendar_unavailable"] += 1
            return None
        state_refs: tuple[str, ...] = ()
        transition = self.transition
        if transition is not None and transition.state_effective_from_ns <= interval_end_ns - 1:
            state_refs = (f"calendar-transition:{transition.event_id}",)
        elif (
            self.current_state is not None
            and self.current_state.state_effective_from_ns <= interval_end_ns - 1
        ):
            state_refs = (
                f"calendar-current-state:{self.current_state.last_transition_event_id}",
            )
        return _CalendarContext(
            trade_date=snapshot.trade_date,
            exchange_state=snapshot.market_state,
            product_phases=snapshot.phase_memberships,
            state_evidence_refs=state_refs,
            projection_evidence_refs=(self.projection_ref,),
        )

    def accept_live(
        self,
        constituent: _LiveConstituent,
        *,
        owner_received_at_ns: int,
    ) -> str:
        if self.terminal:
            self.counters["terminal_rejected"] += 1
            return _SeriesAdmission.TERMINAL
        if (
            constituent.lineage.source_class != "LIVE"
            or constituent.lineage.input_identity != self.config.live_input_identity
        ):
            self.counters["identity_rejected"] += 1
            return _SeriesAdmission.CONFLICT
        if (
            constituent.interval_start_ns % _FIVE_SECONDS_NS
            or constituent.interval_end_ns % _FIVE_SECONDS_NS
        ):
            self.counters["interval_rejected"] += 1
            return _SeriesAdmission.CONFLICT
        bucket_start = constituent.interval_start_ns - (
            constituent.interval_start_ns % self.config.series_identity.interval_ns
        )
        bucket_end = bucket_start + self.config.series_identity.interval_ns
        if not (
            bucket_start <= constituent.interval_start_ns
            and constituent.interval_end_ns <= bucket_end
        ):
            self.counters["interval_rejected"] += 1
            return _SeriesAdmission.CONFLICT
        cutoff_ns = bucket_end + self.policy.completion_grace_ns
        if owner_received_at_ns >= cutoff_ns:
            self.counters["late_constituents"] += 1
            return _SeriesAdmission.LATE
        bucket = self.buckets.get(bucket_end)
        if bucket is None:
            if len(self.buckets) >= self.policy.maximum_open_buckets_per_series:
                self.counters["bucket_overflow"] += 1
                return _SeriesAdmission.OVERFLOW
            bucket = _LiveBucket(bucket_start, bucket_end, cutoff_ns)
            self.buckets[bucket_end] = bucket
        expected_slot = (constituent.interval_start_ns - bucket_start) // _FIVE_SECONDS_NS
        if not 0 <= expected_slot < _EXPECTED_CONSTITUENTS:
            self.counters["interval_rejected"] += 1
            return _SeriesAdmission.CONFLICT
        expected_start_ns = bucket_start + expected_slot * _FIVE_SECONDS_NS
        if (
            constituent.interval_start_ns != expected_start_ns
            or constituent.interval_end_ns != expected_start_ns + _FIVE_SECONDS_NS
        ):
            self.counters["interval_rejected"] += 1
            return _SeriesAdmission.CONFLICT
        existing = bucket.slots.get(expected_slot)
        if existing is not None:
            if existing.equivalence_key == constituent.equivalence_key:
                self.counters["constituent_duplicates"] += 1
                return _SeriesAdmission.DUPLICATE
            self._mark_terminal("constituent_conflicts")
            return _SeriesAdmission.CONFLICT
        bucket.slots[expected_slot] = constituent
        self.counters["constituents_accepted"] += 1
        return _SeriesAdmission.ACCEPTED

    def finalize_live(self, interval_end_ns: int, *, now_ns: int) -> tuple[CompletedBarV1, ...]:
        if self.terminal:
            return ()
        cutoff_ns = interval_end_ns + self.policy.completion_grace_ns
        if now_ns < cutoff_ns:
            raise ValueError("live interval cannot finalize before its strict cutoff")
        bucket = self.buckets.pop(interval_end_ns, None)
        if bucket is None or not bucket.slots:
            self.counters["empty_intervals"] += 1
            return ()
        context = self.calendar_context(interval_end_ns)
        if context is None:
            self.counters["calendar_bar_rejected"] += 1
            return ()
        candidate = _aggregate_live_bucket(
            bucket,
            series_identity=self.config.series_identity,
            context=context,
        )
        counter = (
            "live_complete"
            if candidate.completion_state is BarCompletionState.COMPLETE
            else "live_partial"
        )
        self.counters[counter] += 1
        return self._converge_live(candidate, published_ts_ns=now_ns)

    def accept_historical(
        self,
        result: _HistoricalValidationResult,
        *,
        published_ts_ns: int,
    ) -> tuple[CompletedBarV1, ...]:
        if self.terminal:
            self.counters["terminal_rejected"] += 1
            return ()
        binding = self.config.historical_bootstrap.validation_request
        if (
            self.history_terminal
            or result.request_id != binding.request_id
            or result.request_digest != binding.request_digest
            or result.usage is not _HistoricalUsage.CANONICAL_SERIES_BOOTSTRAP
            or result.series_identity != self.config.series_identity
            or result.expected_input_identity != binding.expected_input_identity
        ):
            self.counters["historical_rejected"] += 1
            return ()
        self.history_terminal = True
        if result.disposition is _HistoricalValidationDisposition.REJECTED:
            self.counters["historical_rejected"] += 1
            self._mark_terminal("historical_terminal_conflicts")
            return ()
        historical: list[_CompletedBarCandidate] = []
        for item in result.observations:
            context = self.calendar_context(item.interval_end_ns)
            if context is None:
                self.counters["historical_calendar_rejected"] += 1
                self._mark_terminal("historical_terminal_conflicts")
                return ()
            historical.append(_candidate_from_historical(item, context=context))
        self.counters["historical_candidates"] += len(historical)
        return self._converge_history(historical, published_ts_ns=published_ts_ns)

    def _converge_history(
        self,
        historical: list[_CompletedBarCandidate],
        *,
        published_ts_ns: int,
    ) -> tuple[CompletedBarV1, ...]:
        if not historical:
            self.converged = True
            return self._publish_candidates(self.pending_live, published_ts_ns=published_ts_ns)
        output: list[CompletedBarV1] = []
        prefix = historical[:-1]
        last = historical[-1]
        pending = sorted(self.pending_live, key=lambda item: item.interval_start_ns)
        overlap_keys = {item.key for item in historical} & {item.key for item in pending}
        if len(overlap_keys) > self.policy.maximum_history_live_overlap_bars:
            self._mark_terminal("overlap_overflow")
            return ()
        if overlap_keys and overlap_keys != {last.key}:
            self._mark_terminal("overlap_conflicts")
            return ()
        output.extend(self._publish_candidates(prefix, published_ts_ns=published_ts_ns))
        self.pending_live.clear()
        if not pending:
            self.overlap_hold = last
            return tuple(output)
        if pending and pending[0].key == last.key:
            if pending[0].equivalence_key != last.equivalence_key:
                self._mark_terminal("overlap_conflicts")
                return tuple(output)
            last = last.merge_lineage(pending.pop(0))
            self.counters["overlap_duplicates"] += 1
        output.extend(self._publish_candidates([last], published_ts_ns=published_ts_ns))
        output.extend(self._publish_candidates(pending, published_ts_ns=published_ts_ns))
        self.converged = not self.terminal
        return tuple(output)

    def _converge_live(
        self,
        candidate: _CompletedBarCandidate,
        *,
        published_ts_ns: int,
    ) -> tuple[CompletedBarV1, ...]:
        if not self.history_terminal:
            if len(self.pending_live) >= self.policy.maximum_buffered_live_completed_bars:
                self._mark_terminal("pending_live_overflow")
                return ()
            existing = next((item for item in self.pending_live if item.key == candidate.key), None)
            if existing is not None:
                if existing.equivalence_key == candidate.equivalence_key:
                    self.counters["duplicates"] += 1
                    return ()
                self._mark_terminal("conflicts")
                return ()
            self.pending_live.append(candidate)
            self.pending_live.sort(key=lambda item: item.interval_start_ns)
            self.counters["pending_live"] = len(self.pending_live)
            return ()
        if self.overlap_hold is not None:
            held = self.overlap_hold
            self.overlap_hold = None
            if candidate.key == held.key:
                if candidate.equivalence_key != held.equivalence_key:
                    self._mark_terminal("overlap_conflicts")
                    return ()
                candidate = held.merge_lineage(candidate)
                self.counters["overlap_duplicates"] += 1
                output = self._publish_candidates([candidate], published_ts_ns=published_ts_ns)
            elif candidate.interval_start_ns == held.interval_end_ns:
                output = self._publish_candidates(
                    [held, candidate],
                    published_ts_ns=published_ts_ns,
                )
            else:
                self._mark_terminal("overlap_conflicts")
                return ()
            self.converged = not self.terminal
            return output
        return self._publish_candidates([candidate], published_ts_ns=published_ts_ns)

    def _publish_candidates(
        self,
        candidates: list[_CompletedBarCandidate],
        *,
        published_ts_ns: int,
    ) -> tuple[CompletedBarV1, ...]:
        """Validate the complete candidate set before committing sequence or retained state."""

        planned_retained: deque[CompletedBarV1] = deque(
            self.retained,
            maxlen=self.policy.maximum_retained_completed_bars,
        )
        planned_sequence = self.sequence
        counter_deltas: Counter[str] = Counter()
        output: list[CompletedBarV1] = []
        for candidate in sorted(candidates, key=lambda item: item.interval_start_ns):
            if self.terminal:
                return ()
            existing = next(
                (item for item in planned_retained if item.key == candidate.key),
                None,
            )
            if existing is not None:
                if existing.equivalence_key == candidate.equivalence_key:
                    counter_deltas["duplicates"] += 1
                    continue
                self._mark_terminal("conflicts")
                return ()
            if (
                planned_retained
                and candidate.interval_end_ns < planned_retained[0].interval_end_ns
            ):
                counter_deltas["stale"] += 1
                continue
            if (
                planned_retained
                and candidate.interval_start_ns != planned_retained[-1].interval_end_ns
            ):
                counter_deltas["publication_gaps"] += 1
            planned_sequence += 1
            bar = candidate.publish(
                run_epoch=self.run_epoch,
                sequence=planned_sequence,
                published_ts_ns=max(
                    published_ts_ns,
                    max(item.normalized_ts_ns for item in candidate.lineage),
                ),
            )
            planned_retained.append(bar)
            counter_deltas["published"] += 1
            output.append(bar)
        self.sequence = planned_sequence
        self.retained = planned_retained
        self.counters.update(counter_deltas)
        return tuple(output)

    def stop(self) -> None:
        self.terminal = True
        self.buckets.clear()
        self.pending_live.clear()
        self.overlap_hold = None

    def _mark_terminal(self, counter: str) -> None:
        self.counters[counter] += 1
        self.terminal = True
        self.buckets.clear()
        self.pending_live.clear()
        self.overlap_hold = None


@dataclass(frozen=True, slots=True)
class _FoundationHealthEvent:
    series_id: str
    state: str
    reason: str
    occurred_at_ns: int
    counters: tuple[tuple[str, int], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "series_id", topic_token(self.series_id))
        object.__setattr__(self, "state", bounded_ascii(self.state, "state"))
        object.__setattr__(self, "reason", bounded_ascii(self.reason, "reason"))
        positive_int64(self.occurred_at_ns, "occurred_at_ns")
        _validate_counter_snapshot(self.counters)

    @property
    def ts_event(self) -> int:
        return self.occurred_at_ns

    @property
    def ts_init(self) -> int:
        return self.occurred_at_ns


@dataclass(frozen=True, slots=True)
class _FoundationShutdownSummary:
    actor_id: str
    run_epoch: UUID
    stopped_at_ns: int
    actor_counters: tuple[tuple[str, int], ...]
    series_counters: tuple[tuple[str, tuple[tuple[str, int], ...]], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "actor_id", bounded_ascii(self.actor_id, "actor_id"))
        uuid_value(self.run_epoch, "run_epoch")
        positive_int64(self.stopped_at_ns, "stopped_at_ns")
        _validate_counter_snapshot(self.actor_counters)
        series_ids = tuple(item[0] for item in self.series_counters)
        if series_ids != tuple(sorted(set(series_ids))):
            raise ValueError("shutdown series counters must be unique and sorted")
        for series_id, counters in self.series_counters:
            topic_token(series_id)
            _validate_counter_snapshot(counters)

    @property
    def ts_event(self) -> int:
        return self.stopped_at_ns

    @property
    def ts_init(self) -> int:
        return self.stopped_at_ns


class _CompletedBarFoundationActor(DataActor):
    """Disabled Slice 2 canonical completed-bar owner with isolated per-series state."""

    def __init__(self, config: _CompletedBarFoundationActorConfig) -> None:
        super().__init__(config)
        if not isinstance(config.series, tuple) or not config.series:
            raise ValueError("foundation requires a non-empty typed series tuple")
        if any(not isinstance(item, _CompletedBarFoundationSeriesConfig) for item in config.series):
            raise ValueError("foundation series must be typed")
        if len(config.series) > MAXIMUM_SERIES_PER_INSTANCE:
            raise ValueError("foundation instance cannot own more than 16 series")
        series_ids = tuple(item.series_id for item in config.series)
        if series_ids != tuple(sorted(set(series_ids))):
            raise ValueError("foundation series must be unique and sorted")
        live_bar_types = tuple(item.live_bar_type for item in config.series)
        if len(live_bar_types) != len(set(live_bar_types)):
            raise ValueError("Slice 2 requires one canonical series per live BarType route")
        if any(
            item.series_identity.canonical_producer_id != str(config.actor_id)
            for item in config.series
        ):
            raise ValueError("foundation actor ID must match every canonical producer identity")
        calendar_sources = {
            (item.calendar_source, item.calendar_source_epoch) for item in config.series
        }
        if len(calendar_sources) != 1:
            raise ValueError("one foundation instance requires one calendar source run")
        live_authorities = {item.live_authority for item in config.series}
        if len(live_authorities) != 1:
            raise ValueError("one foundation instance requires one native live authority")
        uuid_value(config.startup_epoch, "startup_epoch")
        uuid_value(config.run_epoch, "run_epoch")
        self._startup_epoch = config.startup_epoch
        self._run_epoch = config.run_epoch
        self._manifest_digest = digest(config.manifest_digest, "manifest_digest")
        if not isinstance(config.policy, _CompletedBarFoundationPolicy):
            raise ValueError("foundation policy must be typed")
        self._policy = config.policy
        self._states = {
            item.series_id: _FoundationSeriesState(item, self._policy, self._run_epoch)
            for item in config.series
        }
        self._by_live_bar_type = {
            item.live_bar_type: self._states[item.series_id] for item in config.series
        }
        self._by_request_id = {
            item.historical_bootstrap.transport_request.request_id: self._states[item.series_id]
            for item in config.series
        }
        if len(self._by_request_id) != len(config.series):
            raise ValueError("historical bootstrap request IDs must be unique per instance")
        self._routes = {
            series_id: _canonical_completed_bar_data_type(series_id) for series_id in series_ids
        }
        self._live_authority = next(iter(live_authorities))
        self._port = NautilusSubscriptionPort(
            self,
            client_id=self._live_authority.client_id,
        )
        positive_int(config.projection_lookback_days, "projection_lookback_days")
        positive_int(config.projection_lookahead_days, "projection_lookahead_days")
        self._projection_lookback_ns = config.projection_lookback_days * _NANOSECONDS_PER_DAY
        self._projection_lookahead_ns = config.projection_lookahead_days * _NANOSECONDS_PER_DAY
        self._projection_policy = ProjectionRetryPolicy.from_config(config.projection_retry)
        source, source_epoch = next(iter(calendar_sources))
        self._projection_state = ProjectionRequestState.idle(
            requester=str(config.actor_id),
            expected_source=source,
            expected_source_epoch=source_epoch,
        )
        delivery = config.current_state_delivery
        self._session_state_policy = SessionStateDeliveryPolicy(
            policy_version=delivery["policy_version"],
            response_timeout_ns=delivery["response_timeout_ms"] * _NANOSECONDS_PER_MILLISECOND,
            maximum_attempts=delivery["maximum_attempts"],
            retry_backoff_ns=delivery["retry_backoff_ms"] * _NANOSECONDS_PER_MILLISECOND,
            maximum_elapsed_ns=delivery["maximum_elapsed_ms"] * _NANOSECONDS_PER_MILLISECOND,
            maximum_buffered_transitions_per_calendar=delivery[
                "maximum_buffered_transitions_per_calendar"
            ],
            maximum_total_buffered_transitions=delivery[
                "maximum_total_buffered_transitions"
            ],
            boundary_delivery_grace_ns=delivery["boundary_delivery_grace_ms"]
            * _NANOSECONDS_PER_MILLISECOND,
        )
        expectations: dict[str, CalendarDefinitionExpectation] = {}
        for item in config.series:
            identity = item.series_identity
            expectation = CalendarDefinitionExpectation(
                calendar_id=identity.calendar_id,
                definition_version=identity.calendar_definition_version,
                definition_digest=identity.calendar_definition_digest,
                definition_effective_from_ns=identity.calendar_definition_effective_from_ns,
            )
            existing = expectations.get(identity.calendar_id)
            if existing is not None and existing != expectation:
                raise ValueError("calendar definition authority conflicts inside foundation")
            expectations[identity.calendar_id] = expectation
        self._calendar_expectations = tuple(
            expectations[key] for key in sorted(expectations)
        )
        self._calendar_ids = tuple(item.calendar_id for item in self._calendar_expectations)
        self._session_state = SessionStateDeliveryState.idle(
            requester=str(config.actor_id),
            expected_source=source,
            expected_source_epoch=source_epoch,
            delivery_policy_version=self._session_state_policy.policy_version,
        )
        self._calendar_refresh_generation: Counter[str] = Counter()
        self._projection_refresh_generation: dict[str, int] = {}
        self._calendar_counts: Counter[str] = Counter()
        self._readiness_type = DataType(_READINESS_TYPE_NAME)
        self._historical_type = DataType(HISTORICAL_BATCH_TYPE_NAME)
        self._projection_request_type = DataType(CALENDAR_PROJECTION_REQUEST_TYPE_NAME)
        self._projection_type = DataType(CALENDAR_PROJECTION_RESPONSE_TYPE_NAME)
        self._transition_type = DataType(CALENDAR_TRANSITION_V2_TYPE_NAME)
        self._current_state_request_type = DataType(CALENDAR_STATE_SNAPSHOT_REQUEST_TYPE_NAME)
        self._current_state_type = DataType(CALENDAR_STATE_SNAPSHOT_RESPONSE_TYPE_NAME)
        self._health_type = DataType(_FOUNDATION_HEALTH_TYPE_NAME)
        self._shutdown_type = DataType(_FOUNDATION_SHUTDOWN_TYPE_NAME)
        self._active = False
        self._terminal = False
        self._attached: set[str] = set()
        self._timer_names: set[str] = set()

    @property
    def states(self) -> MappingProxyType[str, _FoundationSeriesState]:
        return MappingProxyType(self._states)

    def on_start(self) -> None:
        if self._terminal:
            raise RuntimeError("completed-bar foundation cannot restart after terminal stop")
        self._active = True
        now_ns = self.clock.timestamp_ns()
        for data_type in (
            self._readiness_type,
            self._historical_type,
            self._projection_type,
            self._transition_type,
            self._current_state_type,
        ):
            self.subscribe_data(data_type)
        self._prepare_session_state_cycle(now_ns=now_ns)
        self._publish_session_state_request()
        self._begin_projection_cycle(now_ns=now_ns)
        for series_id, state in self._states.items():
            state.start_readiness(
                startup_epoch=self._startup_epoch,
                manifest_digest=self._manifest_digest,
                started_at_ns=now_ns,
            )
            timer_name = f"completed-bar-readiness:{series_id}"
            self.clock.set_time_alert_ns(
                timer_name,
                now_ns + CONSUMER_READINESS_TIMEOUT_MS * _NANOSECONDS_PER_MILLISECOND,
                callback=partial(self._evaluate_readiness, series_id),
            )
            self._timer_names.add(timer_name)

    def on_data(self, data: Any) -> None:
        if not self._active:
            return
        payload = data.data if isinstance(data, CustomData) else data
        received_at_ns = self.clock.timestamp_ns()
        if isinstance(payload, _SubscriptionReadinessAcknowledgement):
            state = self._states.get(payload.series_id)
            if state is None:
                return
            state.acknowledge(payload, received_at_ns=received_at_ns)
            self._activate_if_ready(state, now_ns=received_at_ns)
            return
        if isinstance(payload, CalendarProjectionResponse):
            self._retain_projections(payload, received_at_ns=received_at_ns)
            return
        if isinstance(payload, CalendarTransitionV2):
            self._observe_session_transition(payload, received_at_ns=received_at_ns)
            return
        if isinstance(payload, CalendarStateSnapshotResponse):
            self._observe_session_snapshot(payload, received_at_ns=received_at_ns)
            return
        if isinstance(payload, HistoricalBatch):
            self._accept_historical_batch(payload, received_at_ns=received_at_ns)

    def on_bar(self, bar: Any) -> None:
        if not self._active:
            return
        state = self._by_live_bar_type.get(str(bar.bar_type))
        if state is None or not state.demand_started or state.terminal:
            return
        received_at_ns = self.clock.timestamp_ns()
        try:
            constituent = _constituent_from_native_bar(
                bar,
                input_identity=state.config.live_input_identity,
                owner_received_at_ns=received_at_ns,
            )
        except (AttributeError, TypeError, ValueError, ArithmeticError):
            state.counters["malformed_live"] += 1
            return
        self._accept_live_constituent(
            state,
            constituent,
            owner_received_at_ns=received_at_ns,
        )

    def _accept_live_constituent(
        self,
        state: _FoundationSeriesState,
        constituent: _LiveConstituent,
        *,
        owner_received_at_ns: int,
    ) -> str:
        """Admit one callback and apply the instance-wide bucket ceiling."""

        before = len(state.buckets)
        disposition = state.accept_live(
            constituent,
            owner_received_at_ns=owner_received_at_ns,
        )
        if disposition == _SeriesAdmission.ACCEPTED and len(state.buckets) > before:
            bucket_end = constituent.interval_start_ns - (
                constituent.interval_start_ns % state.config.series_identity.interval_ns
            ) + state.config.series_identity.interval_ns
            self._schedule_cutoff(state, bucket_end)
        if sum(len(item.buckets) for item in self._states.values()) > (
            self._policy.maximum_open_buckets_per_instance
        ):
            state._mark_terminal("instance_bucket_overflow")
            return _SeriesAdmission.OVERFLOW
        return disposition

    def on_stop(self) -> None:
        if self._terminal:
            return
        self._active = False
        self._terminal = True
        self._projection_state = stop_projection_state(self._projection_state)
        self._session_state = stop_session_state_delivery(self._session_state)
        for timer_name in sorted(self._timer_names):
            if timer_name in self.clock.timer_names():
                self.clock.cancel_timer(timer_name)
        self._timer_names.clear()
        for state in self._states.values():
            if state.demand_started:
                try:
                    self._publish_demands(
                        state,
                        action="RELEASE",
                        now_ns=self.clock.timestamp_ns(),
                    )
                except Exception:  # noqa: BLE001
                    state.counters["demand_release_failures"] += 1
            if state.config.series_id in self._attached:
                try:
                    self._port.unsubscribe(
                        FeedRequirement(
                            state.config.series_identity.instrument_id,
                            FeedKind.BARS,
                            state.config.live_selector,
                        ),
                    )
                except Exception:  # noqa: BLE001
                    state.counters["unsubscribe_failures"] += 1
            state.stop()
        for data_type in (
            self._readiness_type,
            self._historical_type,
            self._projection_type,
            self._transition_type,
            self._current_state_type,
        ):
            self.unsubscribe_data(data_type)
        now_ns = self.clock.timestamp_ns()
        summary = _FoundationShutdownSummary(
            actor_id=str(self.actor_id),
            run_epoch=self._run_epoch,
            stopped_at_ns=now_ns,
            actor_counters=tuple(sorted(self._calendar_counts.items())),
            series_counters=tuple(
                (series_id, tuple(sorted(state.counters.items())))
                for series_id, state in sorted(self._states.items())
            ),
        )
        self.publish_data(self._shutdown_type, CustomData(self._shutdown_type, summary))

    def _begin_projection_cycle(self, *, now_ns: int | None = None) -> None:
        if not self._active:
            return
        requested = tuple(
            calendar_id
            for calendar_id in self._calendar_ids
            if all(
                state.projection is None
                for state in self._states.values()
                if state.config.series_identity.calendar_id == calendar_id
            )
            or self._calendar_refresh_generation[calendar_id] > 0
        )
        if not requested:
            return
        observed_ns = self.clock.timestamp_ns() if now_ns is None else now_ns
        previous = self._projection_state
        started = start_projection_cycle(
            previous,
            calendar_ids=requested,
            start_ns=max(0, observed_ns - self._projection_lookback_ns),
            end_ns=observed_ns + self._projection_lookahead_ns,
            now_ns=observed_ns,
            policy=self._projection_policy,
        )
        if started.generation == previous.generation:
            return
        self._projection_state = started
        self._projection_refresh_generation = {
            calendar_id: self._calendar_refresh_generation[calendar_id]
            for calendar_id in requested
        }
        self._publish_projection_request()

    def _publish_projection_request(self) -> None:
        state = self._projection_state
        if (
            not self._active
            or state.phase is not ProjectionRequestPhase.WAITING
            or state.request_id is None
            or state.start_ns is None
            or state.end_ns is None
        ):
            return
        self._set_projection_alert()
        request = CalendarProjectionRequest(
            request_id=state.request_id,
            requester=state.requester,
            calendar_ids=state.pending_calendar_ids,
            start_ns=state.start_ns,
            end_ns=state.end_ns,
            requested_ts_ns=self.clock.timestamp_ns(),
        )
        self._calendar_counts["projection_requests"] += 1
        self.publish_data(
            self._projection_request_type,
            CustomData(self._projection_request_type, request),
        )

    def _retain_projections(
        self,
        response: CalendarProjectionResponse,
        *,
        received_at_ns: int,
    ) -> None:
        disposition = classify_projection_response(self._projection_state, response)
        if disposition != "ACCEPT":
            self._calendar_counts[
                "projection_conflicts" if disposition == "CONFLICT" else "projection_stale"
            ] += 1
            return
        state = self._projection_state
        expectations = {item.calendar_id: item for item in self._calendar_expectations}
        for projection in response.projections:
            expected = expectations.get(projection.calendar_id)
            if (
                expected is None
                or projection.definition_version != expected.definition_version
                or projection.definition_digest != expected.definition_digest
                or projection.definition_effective_from_ns
                != expected.definition_effective_from_ns
                or state.start_ns is None
                or state.end_ns is None
                or projection.coverage_start_ns > state.start_ns
                or projection.coverage_end_ns < state.end_ns
            ):
                self._projection_state = terminal_projection_state(
                    state,
                    "projection_identity_or_coverage_conflict",
                )
                self._calendar_counts["projection_conflicts"] += 1
                self._calendar_counts["projection_terminal"] += 1
                self._cancel_projection_alert()
                return
        accepted_ids = {item.calendar_id for item in response.projections}
        for series_state in self._states.values():
            if series_state.config.series_identity.calendar_id in accepted_ids:
                if not series_state.accept_projection(response):
                    self._projection_state = terminal_projection_state(
                        state,
                        "projection_series_admission_conflict",
                    )
                    self._calendar_counts["projection_conflicts"] += 1
                    self._calendar_counts["projection_terminal"] += 1
                    self._cancel_projection_alert()
                    return
        self._cancel_projection_alert()
        for calendar_id in accepted_ids:
            refresh_generation = self._projection_refresh_generation.get(calendar_id, 0)
            if (
                refresh_generation > 0
                and self._calendar_refresh_generation[calendar_id] <= refresh_generation
            ):
                del self._calendar_refresh_generation[calendar_id]
        remaining = tuple(
            item for item in state.pending_calendar_ids if item not in accepted_ids
        )
        if not remaining:
            self._projection_state = ready_projection_state(state)
            self._calendar_counts["projection_ready"] += 1
            self._begin_projection_cycle(now_ns=received_at_ns)
            return
        failures = {item.calendar_id: item for item in response.failures}
        retryable = all(
            calendar_id in failures and failures[calendar_id].retryable
            for calendar_id in remaining
        )
        if response.status == "NOT_READY" or retryable:
            self._projection_state = retain_pending_calendars(state, remaining)
            self._projection_state = schedule_projection_retry(
                self._projection_state,
                now_ns=received_at_ns,
                policy=self._projection_policy,
                retry_at_ns=response.retry_at_ns,
            )
            self._finish_projection_transition()
            return
        self._projection_state = terminal_projection_state(
            state,
            "projection_rejected" if response.status == "REJECTED" else "projection_unavailable",
            rejected=response.status == "REJECTED",
        )
        self._calendar_counts["projection_terminal"] += 1

    def _on_projection_alert(self, _event: Any) -> None:
        if not self._active:
            return
        state = self._projection_state
        now_ns = self.clock.timestamp_ns()
        if state.alert_at_ns is None or now_ns < state.alert_at_ns:
            return
        if state.phase is ProjectionRequestPhase.WAITING:
            self._calendar_counts["projection_timeouts"] += 1
            self._projection_state = schedule_projection_retry(
                state,
                now_ns=now_ns,
                policy=self._projection_policy,
                retry_at_ns=None,
            )
            self._finish_projection_transition()
        elif state.phase is ProjectionRequestPhase.BACKOFF:
            self._projection_state = begin_projection_retry(
                state,
                now_ns=now_ns,
                policy=self._projection_policy,
            )
            self._publish_projection_request()

    def _finish_projection_transition(self) -> None:
        if self._projection_state.phase is ProjectionRequestPhase.BACKOFF:
            self._calendar_counts["projection_retries"] += 1
            self._set_projection_alert()
        elif self._projection_state.phase in {
            ProjectionRequestPhase.FAILED,
            ProjectionRequestPhase.REJECTED,
        }:
            self._calendar_counts["projection_terminal"] += 1
            self._cancel_projection_alert()

    def _set_projection_alert(self) -> None:
        self._cancel_projection_alert()
        alert_at_ns = self._projection_state.alert_at_ns
        if alert_at_ns is not None and self._active:
            self.clock.set_time_alert_ns(
                _CALENDAR_PROJECTION_RETRY_ALERT,
                alert_at_ns,
                callback=self._on_projection_alert,
            )
            self._timer_names.add(_CALENDAR_PROJECTION_RETRY_ALERT)

    def _cancel_projection_alert(self) -> None:
        if _CALENDAR_PROJECTION_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_CALENDAR_PROJECTION_RETRY_ALERT)
        self._timer_names.discard(_CALENDAR_PROJECTION_RETRY_ALERT)

    def _prepare_session_state_cycle(self, *, now_ns: int) -> None:
        self._session_state = start_session_state_cycle(
            self._session_state,
            calendar_expectations=self._calendar_expectations,
            now_ns=now_ns,
            policy=self._session_state_policy,
        )

    def _publish_session_state_request(self) -> None:
        if (
            not self._active
            or self._session_state.phase is not SessionStateDeliveryPhase.WAITING
        ):
            return
        self._set_session_state_alert()
        request = current_snapshot_request(self._session_state)
        self._calendar_counts["snapshot_requests"] += 1
        self.publish_data(
            self._current_state_request_type,
            CustomData(self._current_state_request_type, request),
        )

    def _observe_session_transition(
        self,
        transition: CalendarTransitionV2,
        *,
        received_at_ns: int,
    ) -> None:
        update = observe_session_transition(
            self._session_state,
            transition,
            policy=self._session_state_policy,
        )
        self._session_state = update.state
        self._calendar_counts[f"transition_{update.disposition.value.lower()}"] += 1
        self._install_session_watermarks(
            update.installed_calendar_ids,
            refresh_projection=update.disposition is SessionStateDeliveryDisposition.APPLIED,
            now_ns=received_at_ns,
        )
        if update.disposition in {
            SessionStateDeliveryDisposition.GAP,
            SessionStateDeliveryDisposition.OVERFLOW,
        }:
            self._session_state = resynchronize_session_state_cycle(
                self._session_state,
                now_ns=received_at_ns,
                policy=self._session_state_policy,
            )
            self._publish_session_state_request()
        elif self._session_state.phase is SessionStateDeliveryPhase.LIVE:
            self._set_session_state_boundary_alert()
        elif self._session_state.phase is SessionStateDeliveryPhase.CONFLICT:
            self._cancel_session_state_alert()

    def _observe_session_snapshot(
        self,
        response: CalendarStateSnapshotResponse,
        *,
        received_at_ns: int,
    ) -> None:
        update = observe_session_snapshot(
            self._session_state,
            response,
            now_ns=received_at_ns,
        )
        self._session_state = update.state
        self._calendar_counts[f"snapshot_{update.disposition.value.lower()}"] += 1
        self._install_session_watermarks(
            update.installed_calendar_ids,
            refresh_projection=False,
            now_ns=received_at_ns,
        )
        if self._session_state.phase is SessionStateDeliveryPhase.LIVE:
            self._set_session_state_boundary_alert()
        elif self._session_state.phase is SessionStateDeliveryPhase.DEGRADED:
            self._schedule_session_state_retry(
                self._session_state.terminal_code or "snapshot_degraded",
                now_ns=received_at_ns,
            )
        elif self._session_state.phase is SessionStateDeliveryPhase.CONFLICT:
            self._cancel_session_state_alert()

    def _install_session_watermarks(
        self,
        calendar_ids: tuple[str, ...],
        *,
        refresh_projection: bool,
        now_ns: int,
    ) -> None:
        if not calendar_ids:
            return
        watermarks = {item.calendar_id: item for item in self._session_state.watermarks}
        for series_state in self._states.values():
            calendar_id = series_state.config.series_identity.calendar_id
            if calendar_id in calendar_ids:
                series_state.install_current_state(watermarks[calendar_id])
        if refresh_projection:
            self._calendar_refresh_generation.update(calendar_ids)
            self._begin_projection_cycle(now_ns=now_ns)

    def _schedule_session_state_retry(self, code: str, *, now_ns: int) -> None:
        update = schedule_session_state_retry(
            self._session_state,
            now_ns=now_ns,
            policy=self._session_state_policy,
            code=code,
        )
        self._session_state = update.state
        self._calendar_counts[f"snapshot_{update.disposition.value.lower()}"] += 1
        self._set_session_state_alert()

    def _on_session_state_alert(self, _event: Any) -> None:
        if not self._active:
            return
        now_ns = self.clock.timestamp_ns()
        if self._session_state.phase is SessionStateDeliveryPhase.LIVE:
            self._prepare_session_state_cycle(now_ns=now_ns)
            self._publish_session_state_request()
            return
        if self._session_state.phase is SessionStateDeliveryPhase.WAITING:
            self._schedule_session_state_retry("response_timeout", now_ns=now_ns)
            return
        update = begin_session_state_retry(
            self._session_state,
            now_ns=now_ns,
            policy=self._session_state_policy,
        )
        self._session_state = update.state
        self._calendar_counts[f"snapshot_{update.disposition.value.lower()}"] += 1
        if update.disposition is SessionStateDeliveryDisposition.RETRY_STARTED:
            self._publish_session_state_request()

    def _set_session_state_alert(self) -> None:
        self._cancel_session_state_alert()
        alert_at_ns = self._session_state.alert_at_ns
        if alert_at_ns is not None and self._active:
            self.clock.set_time_alert_ns(
                _SESSION_STATE_RETRY_ALERT,
                alert_at_ns,
                callback=self._on_session_state_alert,
            )
            self._timer_names.add(_SESSION_STATE_RETRY_ALERT)

    def _set_session_state_boundary_alert(self) -> None:
        next_boundaries = tuple(
            item.next_transition_ns
            for item in self._session_state.watermarks
            if item.next_transition_ns is not None
        )
        self._cancel_session_state_alert()
        if not next_boundaries or not self._active:
            return
        prior_attempt_expired_ns = (
            self._session_state.accepted_response.deadline_ts_ns + 1
            if self._session_state.accepted_response is not None
            else 0
        )
        self.clock.set_time_alert_ns(
            _SESSION_STATE_RETRY_ALERT,
            max(
                min(next_boundaries) + self._session_state_policy.boundary_delivery_grace_ns,
                prior_attempt_expired_ns,
            ),
            callback=self._on_session_state_alert,
        )
        self._timer_names.add(_SESSION_STATE_RETRY_ALERT)

    def _cancel_session_state_alert(self) -> None:
        if _SESSION_STATE_RETRY_ALERT in self.clock.timer_names():
            self.clock.cancel_timer(_SESSION_STATE_RETRY_ALERT)
        self._timer_names.discard(_SESSION_STATE_RETRY_ALERT)

    def _evaluate_readiness(self, series_id: str, _event: Any) -> None:
        if not self._active:
            return
        state = self._states[series_id]
        self._activate_if_ready(state, now_ns=self.clock.timestamp_ns())

    def _activate_if_ready(self, state: _FoundationSeriesState, *, now_ns: int) -> None:
        if state.demand_started or state.readiness_resolved or state.terminal:
            return
        decision = state.readiness_decision(now_ns=now_ns)
        if not decision.sealed:
            return
        state.readiness_resolved = True
        if state.config.series_id not in decision.demand_series_ids:
            self._publish_health(state, "QUARANTINED", "no acknowledged consumer", now_ns)
            return
        try:
            self._port.subscribe(
                FeedRequirement(
                    state.config.series_identity.instrument_id,
                    FeedKind.BARS,
                    state.config.live_selector,
                ),
            )
        except Exception as exc:  # noqa: BLE001
            state._mark_terminal("subscription_failures")
            self._publish_health(state, "FAILED", type(exc).__name__, now_ns)
            return
        self._attached.add(state.config.series_id)
        state.demand_started = True
        self._publish_demands(state, action="REQUEST", now_ns=now_ns)
        self._schedule_current_cutoff(state, now_ns=now_ns)
        self._publish_health(state, "WARMING", "demand_started", now_ns)

    def _publish_demands(
        self,
        state: _FoundationSeriesState,
        *,
        action: str,
        now_ns: int,
    ) -> None:
        identity = state.config.series_identity
        live = AnalyticalDemandEvent(
            demand_id=f"completed-bar:{state.config.series_id}:live",
            action=action,
            instrument_id=identity.instrument_id,
            capability_id="metric:completed-bar-foundation",
            capability_version=1,
            feed_kind=FeedKind.BARS.value,
            selector=state.config.live_selector,
            owner_id=str(self.actor_id),
            purpose="canonical completed-bar live input",
            priority=state.config.demand_priority,
        )
        self.publish_signal(ANALYTICAL_DEMAND_SIGNAL, live.to_signal_value())
        state.counters[f"live_demand_{action.lower()}"] += 1
        if action != "REQUEST":
            return
        request = state.config.historical_bootstrap.transport_request
        minimum_observations = max(
            dependency.minimum_observations
            for dependency in request.dependencies
            if dependency.consumer_id == str(self.actor_id)
        )
        historical = HistoricalDependencyDemandEvent(
            demand_id=f"completed-bar:{state.config.series_id}:historical",
            consumer_id=str(self.actor_id),
            capability_id="metric:completed-bar-foundation",
            capability_version=1,
            instrument_id=identity.instrument_id,
            selector=request.selector,
            window=request.window.value,
            minimum_observations=minimum_observations,
            maximum_observations=request.limit,
            priority=state.config.demand_priority,
            purpose="canonical_series_bootstrap",
            as_of_ns=now_ns,
            parameters=dict(request.parameters),
        )
        self.publish_signal(
            HISTORICAL_DEPENDENCY_DEMAND_SIGNAL,
            historical.to_signal_value(),
        )
        state.counters["historical_demand_request"] += 1

    def _schedule_current_cutoff(
        self,
        state: _FoundationSeriesState,
        *,
        now_ns: int,
    ) -> None:
        interval_ns = state.config.series_identity.interval_ns
        remainder = now_ns % interval_ns
        interval_end_ns = now_ns if remainder == 0 else now_ns + interval_ns - remainder
        cutoff_ns = interval_end_ns + self._policy.completion_grace_ns
        if cutoff_ns <= now_ns:
            interval_end_ns += interval_ns
        self._schedule_cutoff(state, interval_end_ns)

    def _schedule_cutoff(self, state: _FoundationSeriesState, interval_end_ns: int) -> None:
        if not self._active or state.terminal:
            return
        timer_name = f"completed-bar-cutoff:{state.config.series_id}:{interval_end_ns}"
        if timer_name in self._timer_names:
            return
        self.clock.set_time_alert_ns(
            timer_name,
            interval_end_ns + self._policy.completion_grace_ns,
            callback=partial(self._on_cutoff, state.config.series_id, interval_end_ns, timer_name),
        )
        self._timer_names.add(timer_name)

    def _on_cutoff(
        self,
        series_id: str,
        interval_end_ns: int,
        timer_name: str,
        _event: Any,
    ) -> None:
        self._timer_names.discard(timer_name)
        if not self._active:
            return
        state = self._states[series_id]
        now_ns = self.clock.timestamp_ns()
        empty_before = state.counters["empty_intervals"]
        bars = state.finalize_live(interval_end_ns, now_ns=now_ns)
        self._publish_bars(state, bars)
        if state.terminal:
            self._publish_health(state, "FAILED", "series_terminal", now_ns)
        elif state.counters["empty_intervals"] > empty_before:
            self._publish_health(state, "DEGRADED", "missing_interval", now_ns)
        elif bars:
            status = (
                "READY"
                if bars[-1].completion_state is BarCompletionState.COMPLETE
                else "DEGRADED"
            )
            reason = "complete_interval" if status == "READY" else "partial_interval"
            self._publish_health(state, status, reason, now_ns)
        if self._active and not state.terminal and state.demand_started:
            next_interval_end_ns, skipped = _next_cutoff_interval_end(
                interval_end_ns=interval_end_ns,
                interval_ns=state.config.series_identity.interval_ns,
                grace_ns=self._policy.completion_grace_ns,
                now_ns=now_ns,
            )
            if skipped:
                state.counters["timer_skipped_intervals"] += skipped
                state.counters["empty_intervals"] += skipped
                self._publish_health(state, "DEGRADED", "timer_late_intervals", now_ns)
            self._schedule_cutoff(
                state,
                next_interval_end_ns,
            )

    def _accept_historical_batch(self, batch: HistoricalBatch, *, received_at_ns: int) -> None:
        state = self._by_request_id.get(batch.request.request_id)
        if state is None or state.terminal or not state.demand_started:
            return
        binding = state.config.historical_bootstrap
        if not binding.matches(batch.request):
            state.counters["historical_transport_rejected"] += 1
            return
        historical_input_identity = CompletedBarInputIdentity(
            provider_id=batch.provider_id,
            adapter_id=batch.adapter_id,
            source_stream_id=batch.source_stream_id,
            source_selector=(
                f"{batch.request.instrument_id}-{batch.request.selector}"
            ),
            source_schema_id=batch.source_schema_id,
        )
        if (
            historical_input_identity
            != binding.validation_request.expected_input_identity
        ):
            state.counters["historical_source_authority_rejected"] += 1
            return
        try:
            observations = tuple(
                _historical_observation_from_native_bar(
                    value,
                    state=state,
                    input_identity=historical_input_identity,
                    received_at_ns=batch.received_at_ns,
                    request_id=batch.request.request_id,
                )
                for value in batch.observations
            )
            result = _validate_historical_batch(binding.validation_request, observations)
        except (AttributeError, TypeError, ValueError, ArithmeticError):
            state.counters["historical_malformed"] += 1
            return
        bars = state.accept_historical(result, published_ts_ns=received_at_ns)
        self._publish_bars(state, bars)
        if state.terminal:
            self._publish_health(
                state,
                "FAILED",
                "historical_integrity_conflict",
                received_at_ns,
            )
        elif result.disposition is _HistoricalValidationDisposition.PARTIAL:
            self._publish_health(
                state,
                "DEGRADED",
                "historical_partial",
                received_at_ns,
            )

    def _publish_bars(
        self,
        state: _FoundationSeriesState,
        bars: tuple[CompletedBarV1, ...],
    ) -> None:
        route = self._routes[state.config.series_id]
        for bar in bars:
            if not self._active:
                return
            _validate_completed_bar_route(route, bar)
            self.publish_data(route, CustomData(route, bar))

    def _publish_health(
        self,
        state: _FoundationSeriesState,
        status: str,
        reason: str,
        occurred_at_ns: int,
    ) -> None:
        value = _FoundationHealthEvent(
            series_id=state.config.series_id,
            state=bounded_ascii(status, "health state"),
            reason=bounded_ascii(reason, "health reason"),
            occurred_at_ns=occurred_at_ns,
            counters=tuple(sorted(state.counters.items())),
        )
        self.publish_data(self._health_type, CustomData(self._health_type, value))


def _aggregate_live_bucket(
    bucket: _LiveBucket,
    *,
    series_identity: CompletedBarSeriesIdentity,
    context: _CalendarContext,
) -> _CompletedBarCandidate:
    ordered = tuple(bucket.slots[key] for key in sorted(bucket.slots))
    received = len(ordered)
    missing = tuple(
        (
            bucket.interval_start_ns + slot * _FIVE_SECONDS_NS,
            bucket.interval_start_ns + (slot + 1) * _FIVE_SECONDS_NS,
        )
        for slot in range(_EXPECTED_CONSTITUENTS)
        if slot not in bucket.slots
    )
    completion = (
        BarCompletionState.COMPLETE
        if received == _EXPECTED_CONSTITUENTS
        else BarCompletionState.PARTIAL
    )
    reasons = (
        ()
        if completion is BarCompletionState.COMPLETE
        else (
            MetricReasonCode.PARTIAL_COMPLETED_BAR,
            MetricReasonCode.MISSING_SUBINTERVALS,
        )
    )
    volume, volume_state = _aggregate_volume(ordered)
    return _CompletedBarCandidate(
        series_identity=series_identity,
        interval_start_ns=bucket.interval_start_ns,
        interval_end_ns=bucket.interval_end_ns,
        completion_state=completion,
        expected_constituent_count=_EXPECTED_CONSTITUENTS,
        received_constituent_count=received,
        missing_subintervals=missing,
        completion_reasons=tuple(sorted(reasons, key=_METRIC_REASON_ORDER.__getitem__)),
        open=ordered[0].open,
        high=max(item.high for item in ordered),
        low=min(item.low for item in ordered),
        close=ordered[-1].close,
        volume=volume,
        volume_state=volume_state,
        context=context,
        lineage=tuple(item.lineage for item in ordered),
        health=(
            MetricHealth.READY
            if completion is BarCompletionState.COMPLETE
            else MetricHealth.DEGRADED
        ),
        fidelity=(
            MetricFidelity.DERIVED
            if completion is BarCompletionState.COMPLETE
            else MetricFidelity.PARTIAL
        ),
        evidence_refs=tuple(
            dict.fromkeys(ref for item in ordered for ref in item.evidence_refs)
        ),
    )


def _next_cutoff_interval_end(
    *,
    interval_end_ns: int,
    interval_ns: int,
    grace_ns: int,
    now_ns: int,
) -> tuple[int, int]:
    """Return the next future cutoff in O(1) and count fully skipped intervals."""

    next_end_ns = interval_end_ns + interval_ns
    if next_end_ns + grace_ns > now_ns:
        return next_end_ns, 0
    skipped = (now_ns - (next_end_ns + grace_ns)) // interval_ns + 1
    return next_end_ns + skipped * interval_ns, skipped


def _aggregate_volume(
    ordered: tuple[_LiveConstituent, ...],
) -> tuple[Decimal | None, VolumeState]:
    states = {item.volume_state for item in ordered}
    available = tuple(item.volume for item in ordered if item.volume is not None)
    if states == {VolumeState.OBSERVED}:
        return sum(available, Decimal(0)), VolumeState.OBSERVED
    if available:
        return sum(available, Decimal(0)), VolumeState.PARTIAL
    if states == {VolumeState.UNSUPPORTED}:
        return None, VolumeState.UNSUPPORTED
    return None, VolumeState.MISSING


def _candidate_from_historical(
    value: _HistoricalBarObservation,
    *,
    context: _CalendarContext,
) -> _CompletedBarCandidate:
    lineage = tuple(sorted(value.lineage, key=_lineage_sort_key))
    other_refs = tuple(
        ref
        for ref in value.evidence_refs
        if not ref.startswith(("calendar-transition:", "calendar-projection:"))
    )
    reasons = (
        ()
        if value.completion_state is BarCompletionState.COMPLETE
        else (
            MetricReasonCode.PARTIAL_COMPLETED_BAR,
            MetricReasonCode.MISSING_SUBINTERVALS,
        )
    )
    return _CompletedBarCandidate(
        series_identity=value.series_identity,
        interval_start_ns=value.interval_start_ns,
        interval_end_ns=value.interval_end_ns,
        completion_state=value.completion_state,
        expected_constituent_count=value.expected_constituent_count,
        received_constituent_count=value.received_constituent_count,
        missing_subintervals=value.missing_subintervals,
        completion_reasons=tuple(sorted(reasons, key=_METRIC_REASON_ORDER.__getitem__)),
        open=value.open,
        high=value.high,
        low=value.low,
        close=value.close,
        volume=value.volume,
        volume_state=value.volume_state,
        context=context,
        lineage=lineage,
        health=value.health,
        fidelity=(
            MetricFidelity.DERIVED
            if value.completion_state is BarCompletionState.COMPLETE
            else MetricFidelity.PARTIAL
        ),
        evidence_refs=other_refs,
    )


def _constituent_from_native_bar(
    bar: Any,
    *,
    input_identity: CompletedBarInputIdentity,
    owner_received_at_ns: int,
) -> _LiveConstituent:
    if bool(getattr(bar, "is_revision", False)):
        raise ValueError("live source revisions are rejected by canonical policy")
    if str(getattr(bar, "bar_type", "")) != input_identity.source_selector:
        raise ValueError("live native BarType does not match admitted input identity")
    interval_end_ns = int(bar.ts_event)
    interval_start_ns = interval_end_ns - _FIVE_SECONDS_NS
    observed_ts_ns = interval_end_ns
    if owner_received_at_ns < observed_ts_ns:
        raise ValueError("foundation receipt cannot precede provider observation")
    evidence_ref = f"native-bar:{input_identity.source_stream_id}:{interval_end_ns}"
    lineage = CompletedBarLineageEntry(
        source_class="LIVE",
        input_identity=input_identity,
        provider_observation_ref=evidence_ref,
        evidence_refs=(evidence_ref,),
        source_observed_ts_ns=observed_ts_ns,
        source_received_ts_ns=owner_received_at_ns,
        normalized_ts_ns=owner_received_at_ns,
        transformation_chain=("native-bar", "five-second-constituent"),
    )
    return _LiveConstituent(
        interval_start_ns=interval_start_ns,
        interval_end_ns=interval_end_ns,
        open=_as_decimal(bar.open),
        high=_as_decimal(bar.high),
        low=_as_decimal(bar.low),
        close=_as_decimal(bar.close),
        volume=_as_decimal(bar.volume),
        volume_state=VolumeState.OBSERVED,
        lineage=lineage,
        evidence_refs=(evidence_ref,),
    )


def _historical_observation_from_native_bar(
    bar: Any,
    *,
    state: _FoundationSeriesState,
    input_identity: CompletedBarInputIdentity,
    received_at_ns: int,
    request_id: str,
) -> _HistoricalBarObservation:
    identity = state.config.series_identity
    expected_bar_type = (
        f"{identity.instrument_id}-"
        f"{state.config.historical_bootstrap.transport_request.selector}"
    )
    if str(getattr(bar, "bar_type", "")) != expected_bar_type:
        raise ValueError("historical native BarType does not match admitted request")
    interval_end_ns = int(bar.ts_event)
    interval_start_ns = interval_end_ns - identity.interval_ns
    if received_at_ns < interval_end_ns:
        raise ValueError("historical receipt cannot precede provider observation")
    context = state.calendar_context(interval_end_ns)
    if context is None:
        raise ValueError("historical bar lacks admitted calendar context")
    provider_ref = f"historical-bar:{request_id}:{interval_end_ns}"
    lineage = CompletedBarLineageEntry(
        source_class="HISTORICAL",
        input_identity=input_identity,
        provider_observation_ref=provider_ref,
        evidence_refs=(provider_ref,),
        source_observed_ts_ns=interval_end_ns,
        source_received_ts_ns=received_at_ns,
        normalized_ts_ns=received_at_ns,
        transformation_chain=("provider-historical-bar", "canonical-series-bootstrap"),
    )
    volume = _as_decimal(bar.volume)
    revision = 2 if bool(getattr(bar, "is_revision", False)) else 1
    return _HistoricalBarObservation(
        series_identity=identity,
        interval_start_ns=interval_start_ns,
        interval_end_ns=interval_end_ns,
        completion_state=BarCompletionState.COMPLETE,
        expected_constituent_count=_EXPECTED_CONSTITUENTS,
        received_constituent_count=_EXPECTED_CONSTITUENTS,
        missing_subintervals=(),
        open=_as_decimal(bar.open),
        high=_as_decimal(bar.high),
        low=_as_decimal(bar.low),
        close=_as_decimal(bar.close),
        volume=volume,
        volume_state=VolumeState.OBSERVED,
        source_revision=revision,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.REPORTED,
        lineage=(lineage,),
        evidence_refs=tuple(
            dict.fromkeys(
                (
                    provider_ref,
                    *context.state_evidence_refs,
                    *context.projection_evidence_refs,
                ),
            )
        ),
    )


def _as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    method = getattr(value, "as_decimal", None)
    if callable(method):
        result = method()
        if isinstance(result, Decimal):
            return result
    raise ValueError("native numeric value cannot be copied exactly as Decimal")


def _lineage_sort_key(value: CompletedBarLineageEntry) -> tuple[object, ...]:
    return (
        value.source_observed_ts_ns,
        value.source_class,
        value.input_identity.provider_id,
        value.provider_observation_ref,
    )


def _validate_counter_snapshot(value: tuple[tuple[str, int], ...]) -> None:
    if not isinstance(value, tuple):
        raise ValueError("counter snapshot must be a tuple")
    keys = tuple(item[0] for item in value)
    if keys != tuple(sorted(set(keys))):
        raise ValueError("counter snapshot keys must be unique and sorted")
    for key, count in value:
        bounded_ascii(key, "counter key")
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("counter values must be non-negative integers")
