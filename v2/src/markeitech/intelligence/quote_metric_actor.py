from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation

from nautilus_trader.common import DataActor, DataActorConfig, Signal
from nautilus_trader.model import ActorId, CustomData, DataType

from markeitech.acquisition import FeedKind, FeedRequirement, NautilusSubscriptionPort
from markeitech.intelligence.messages import (
    EVIDENCE_HEALTH_SIGNAL,
    EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
    EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
    EvidenceHealthEvent,
    EvidenceHealthSnapshot,
    EvidenceHealthSnapshotRequest,
)
from markeitech.intelligence.metrics import METRIC_VALUE_TYPE_NAME, MetricRegistry
from markeitech.intelligence.quote_metrics import (
    QuoteMetricCatalogPolicy,
    QuoteMetricInput,
    calculate_quote_metrics,
    quote_metric_definitions,
)
from markeitech.system.messages import (
    ACQUISITION_STREAM_SIGNAL,
    ANALYTICAL_DEMAND_SIGNAL,
    AcquisitionStreamEvent,
    AnalyticalDemandEvent,
)

_DEMAND_RETRY_TIMER = "quote-metrics-demand-retry"
_EVIDENCE_RETRY_TIMER = "quote-metrics-evidence-retry"


class QuoteQualityMetricsActorConfig(DataActorConfig):
    def __new__(
        cls,
        instrument_ids: list[str],
        parameter_version: int,
        minimum_update_interval_ms: int,
        maximum_output_age_ms: int,
        demand_retry_interval_ms: int,
        evidence_snapshot_retry_interval_ms: int,
        priority: int,
        actor_id: str | ActorId = "QUOTE-QUALITY-METRICS",
    ) -> QuoteQualityMetricsActorConfig:
        resolved = actor_id if isinstance(actor_id, ActorId) else ActorId.from_str(actor_id)
        obj = super().__new__(cls, actor_id=resolved)
        obj.instrument_ids = tuple(instrument_ids)
        obj.parameter_version = parameter_version
        obj.minimum_update_interval_ms = minimum_update_interval_ms
        obj.maximum_output_age_ms = maximum_output_age_ms
        obj.demand_retry_interval_ms = demand_retry_interval_ms
        obj.evidence_snapshot_retry_interval_ms = evidence_snapshot_retry_interval_ms
        obj.priority = priority
        return obj


class QuoteQualityMetricsActor(DataActor):
    """Publishes bounded quote-quality metrics without retaining raw market data."""

    def __init__(self, config: QuoteQualityMetricsActorConfig) -> None:
        super().__init__(config)
        if not config.instrument_ids or len(set(config.instrument_ids)) != len(
            config.instrument_ids,
        ):
            raise ValueError("quote metrics require unique configured instruments")
        self._instrument_ids = tuple(sorted(config.instrument_ids))
        self._instrument_set = frozenset(self._instrument_ids)
        self._parameter_version = config.parameter_version
        policy = QuoteMetricCatalogPolicy(
            minimum_update_interval_ms=config.minimum_update_interval_ms,
            maximum_output_age_ms=config.maximum_output_age_ms,
            priority=config.priority,
        )
        self._registry = MetricRegistry(quote_metric_definitions(policy))
        self._minimum_update_interval_ns = config.minimum_update_interval_ms * 1_000_000
        self._demand_retry_interval_ns = config.demand_retry_interval_ms * 1_000_000
        self._evidence_retry_interval_ns = config.evidence_snapshot_retry_interval_ms * 1_000_000
        self._priority = config.priority
        self._port = NautilusSubscriptionPort(self)
        self._data_type = DataType(METRIC_VALUE_TYPE_NAME)
        self._demand_ids = {
            instrument_id: f"metric:quote-quality:{instrument_id}:quotes:default"
            for instrument_id in self._instrument_ids
        }
        self._acknowledged_demands: set[str] = set()
        self._attached: set[str] = set()
        self._evidence: dict[str, EvidenceHealthEvent] = {}
        self._last_published_ns: dict[str, int] = {}
        self._revisions: defaultdict[str, int] = defaultdict(int)
        self._quotes_received = 0
        self._quotes_suppressed = 0
        self._values_published = 0
        self._evidence_values_published: defaultdict[str, int] = defaultdict(int)
        self._calculation_failures = 0

    def on_start(self) -> None:
        for signal_name in (
            ACQUISITION_STREAM_SIGNAL,
            EVIDENCE_HEALTH_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
        ):
            self.subscribe_signal(signal_name)
        self._attach_consumers()
        self._publish_demands(None)
        self._request_evidence_snapshot(None)
        self.clock.set_timer_ns(
            _DEMAND_RETRY_TIMER,
            self._demand_retry_interval_ns,
            callback=self._publish_demands,
        )
        self.clock.set_timer_ns(
            _EVIDENCE_RETRY_TIMER,
            self._evidence_retry_interval_ns,
            callback=self._request_evidence_snapshot,
        )

    def on_signal(self, signal: Signal) -> None:
        if signal.name == ACQUISITION_STREAM_SIGNAL:
            self._observe_acquisition(signal.value)
            return
        if signal.name == EVIDENCE_HEALTH_SIGNAL:
            try:
                event = EvidenceHealthEvent.from_signal_value(signal.value)
            except ValueError:
                return
            self._retain_evidence(event)
            return
        if signal.name == EVIDENCE_HEALTH_SNAPSHOT_SIGNAL:
            try:
                snapshot = EvidenceHealthSnapshot.from_signal_value(signal.value)
            except ValueError:
                return
            if snapshot.requester != str(self.actor_id):
                return
            for event in snapshot.events:
                self._retain_evidence(event)

    def on_quote(self, quote) -> None:  # noqa: ANN001
        instrument_id = str(quote.instrument_id)
        if instrument_id not in self._instrument_set:
            return
        self._quotes_received += 1
        now_ns = self.clock.timestamp_ns()
        last_published_ns = self._last_published_ns.get(instrument_id)
        if (
            last_published_ns is not None
            and now_ns - last_published_ns < self._minimum_update_interval_ns
        ):
            self._quotes_suppressed += 1
            return
        evidence = self._evidence.get(instrument_id)
        evidence_state = evidence.state if evidence is not None else "NOT_EVALUATED"
        evidence_ref = (
            event_ref(evidence)
            if evidence is not None
            else f"evidence:{instrument_id}:quotes:default:pending"
        )
        observed_ns = int(quote.ts_event)
        received_ns = max(observed_ns, now_ns)
        self._revisions[instrument_id] += 1
        revision = self._revisions[instrument_id]
        try:
            values = calculate_quote_metrics(
                QuoteMetricInput(
                    instrument_id=instrument_id,
                    bid=_decimal_price(quote.bid_price),
                    ask=_decimal_price(quote.ask_price),
                    observed_ts_ns=observed_ns,
                    received_ts_ns=received_ns,
                    session_id=_session_id(evidence),
                    evidence_state=evidence_state,
                    evidence_ref=evidence_ref,
                ),
                registry=self._registry,
                parameter_version=self._parameter_version,
                calculated_ts_ns=received_ns,
                published_ts_ns=received_ns,
                source=str(self.actor_id),
                revision=revision,
            )
        except (ValueError, ArithmeticError) as exc:
            self._calculation_failures += 1
            self.log.error(
                "QUOTE_METRIC_CALCULATION_FAILED"
                f" | instrument_id={instrument_id} | error={type(exc).__name__}",
            )
            return
        for value in values:
            self.publish_data(self._data_type, CustomData(self._data_type, value))
        self._last_published_ns[instrument_id] = received_ns
        self._values_published += len(values)
        self._evidence_values_published[evidence_state] += len(values)

    def on_stop(self) -> None:
        for timer_name in (_DEMAND_RETRY_TIMER, _EVIDENCE_RETRY_TIMER):
            if timer_name in self.clock.timer_names():
                self.clock.cancel_timer(timer_name)
        for instrument_id in reversed(self._instrument_ids):
            self.publish_signal(
                ANALYTICAL_DEMAND_SIGNAL,
                self._demand(instrument_id, "RELEASE").to_signal_value(),
            )
            if instrument_id in self._attached:
                self._port.unsubscribe(
                    FeedRequirement(instrument_id, FeedKind.QUOTES),
                )
        for signal_name in (
            ACQUISITION_STREAM_SIGNAL,
            EVIDENCE_HEALTH_SIGNAL,
            EVIDENCE_HEALTH_SNAPSHOT_SIGNAL,
        ):
            self.unsubscribe_signal(signal_name)
        self.log.info(
            "QUOTE_METRICS_STOPPED"
            f" | instruments={len(self._instrument_ids)}"
            f" | quotes={self._quotes_received} | suppressed={self._quotes_suppressed}"
            f" | values={self._values_published}"
            f" | evidence_values={_format_evidence_counts(self._evidence_values_published)}"
            f" | failures={self._calculation_failures}",
        )

    def _attach_consumers(self) -> None:
        for instrument_id in self._instrument_ids:
            if instrument_id in self._attached:
                continue
            try:
                self._port.subscribe(FeedRequirement(instrument_id, FeedKind.QUOTES))
            except Exception as exc:  # noqa: BLE001
                self.log.error(
                    "QUOTE_METRIC_CONSUMER_REGISTRATION_FAILED"
                    f" | instrument_id={instrument_id} | error={type(exc).__name__}",
                )
                continue
            self._attached.add(instrument_id)

    def _publish_demands(self, _event) -> None:  # noqa: ANN001
        self._attach_consumers()
        pending = [
            instrument_id
            for instrument_id, demand_id in self._demand_ids.items()
            if demand_id not in self._acknowledged_demands
        ]
        for instrument_id in pending:
            self.publish_signal(
                ANALYTICAL_DEMAND_SIGNAL,
                self._demand(instrument_id, "REQUEST").to_signal_value(),
            )
        if (
            not pending
            and len(self._attached) == len(self._instrument_ids)
            and _DEMAND_RETRY_TIMER in self.clock.timer_names()
        ):
            self.clock.cancel_timer(_DEMAND_RETRY_TIMER)

    def _request_evidence_snapshot(self, _event) -> None:  # noqa: ANN001
        missing = tuple(
            instrument_id
            for instrument_id in self._instrument_ids
            if instrument_id not in self._evidence
        )
        if not missing:
            if _EVIDENCE_RETRY_TIMER in self.clock.timer_names():
                self.clock.cancel_timer(_EVIDENCE_RETRY_TIMER)
            return
        self.publish_signal(
            EVIDENCE_HEALTH_SNAPSHOT_REQUEST_SIGNAL,
            EvidenceHealthSnapshotRequest(
                requester=str(self.actor_id),
                instrument_ids=missing,
                feed_kind="quotes",
                selector="default",
            ).to_signal_value(),
        )

    def _observe_acquisition(self, value: str) -> None:
        try:
            event = AcquisitionStreamEvent.from_signal_value(value)
        except ValueError:
            return
        if event.feed_kind != "quotes" or event.selector != "default":
            return
        demand_id = self._demand_ids.get(event.instrument_id)
        if demand_id is None:
            return
        if event.demand_id == demand_id or demand_id in event.consumer_ids:
            self._acknowledged_demands.add(demand_id)

    def _retain_evidence(self, event: EvidenceHealthEvent) -> None:
        if (
            event.instrument_id in self._instrument_set
            and event.feed_kind == "quotes"
            and event.selector == "default"
        ):
            self._evidence[event.instrument_id] = event

    def _demand(self, instrument_id: str, action: str) -> AnalyticalDemandEvent:
        return AnalyticalDemandEvent(
            demand_id=self._demand_ids[instrument_id],
            action=action,
            instrument_id=instrument_id,
            capability_id="metric:quote-quality",
            capability_version=1,
            feed_kind="quotes",
            selector="default",
            owner_id=str(self.actor_id),
            purpose="calculate bounded quote-quality metrics",
            priority=self._priority,
        )


def _decimal_price(value: object) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("quote price cannot be converted to Decimal") from exc


def _format_evidence_counts(counts: dict[str, int]) -> str:
    if not counts:
        return "none"
    return ",".join(f"{state}:{counts[state]}" for state in sorted(counts))


def _session_id(event: EvidenceHealthEvent | None) -> str | None:
    if event is None or event.session_trade_date is None or event.session_phase is None:
        return None
    return f"{event.calendar_id}:{event.session_trade_date}:{event.session_phase}"


def event_ref(event: EvidenceHealthEvent) -> str:
    return f"signal:{EVIDENCE_HEALTH_SIGNAL}:{event.event_id}"
