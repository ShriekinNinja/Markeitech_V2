from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import StrEnum

from markeitech.acquisition import (
    CapabilityFeedRequirement,
    CapabilityHistoricalRequirement,
    FeedKind,
    HistoricalWindow,
)
from markeitech.intelligence._legacy_metric_value import LegacyMetricValue as MetricValue
from markeitech.intelligence.completed_bars import CompletedBarInput
from markeitech.intelligence.metrics import (
    MetricCadence,
    MetricDefinition,
    MetricDependency,
    MetricFailureBehavior,
    MetricFidelity,
    MetricHealth,
    MetricParameterDefinition,
    MetricRegistry,
    MetricResourcePolicy,
    MetricRetainedState,
    MetricValueKind,
    MetricWarmupPolicy,
    ParameterMutability,
    _validate_legacy_metric_value,
)

ACTIVE_SESSION_METRIC_IDS = (
    "active_session.start_ns",
    "active_session.end_ns",
    "active_session.complete",
    "active_session.open",
    "active_session.high",
    "active_session.low",
    "active_session.latest_close",
    "active_session.range",
    "active_session.location",
    "active_session.volume",
    "active_session.bar_vwap_estimate",
    "active_session.coverage_ratio",
)
"""Ordered identities of active-session reference metrics."""
PREVIOUS_SESSION_METRIC_IDS = (
    "previous_session.start_ns",
    "previous_session.end_ns",
    "previous_session.complete",
    "previous_session.open",
    "previous_session.high",
    "previous_session.low",
    "previous_session.close",
    "previous_session.range",
    "previous_session.simple_return",
    "previous_session.volume",
    "previous_session.bar_vwap_estimate",
    "previous_session.coverage_ratio",
)
"""Ordered identities of previous-session reference metrics."""
OVERNIGHT_METRIC_IDS = (
    "overnight.open",
    "overnight.high",
    "overnight.low",
    "overnight.latest_close",
    "overnight.range",
)
"""Ordered identities of optional overnight reference metrics."""
GAP_METRIC_IDS = (
    "gap.indicative.points",
    "gap.indicative.ratio",
    "gap.opening.points",
    "gap.opening.ratio",
)
"""Ordered identities of indicative and opening gap metrics."""
SESSION_REFERENCE_METRIC_IDS = (
    *ACTIVE_SESSION_METRIC_IDS,
    *PREVIOUS_SESSION_METRIC_IDS,
    *OVERNIGHT_METRIC_IDS,
    *GAP_METRIC_IDS,
)
"""Ordered identities of the complete session-reference metric family."""


class SessionReferenceRole(StrEnum):
    """Semantic roles assigned to configured session reference windows."""

    ACTIVE = "active"
    PREVIOUS = "previous"
    OVERNIGHT = "overnight"


@dataclass(frozen=True, slots=True)
class SessionReferenceCatalogPolicy:
    """Configure session-reference inputs, coverage, price basis, and resource bounds."""

    live_selector: str
    historical_selector: str
    active_window: HistoricalWindow
    previous_window: HistoricalWindow
    overnight_window: HistoricalWindow
    minimum_historical_observations: int
    maximum_historical_observations: int
    vwap_price_basis: str
    vwap_price_basis_dynamic: bool
    minimum_coverage_ratio: float
    minimum_coverage_ratio_floor: float
    minimum_coverage_ratio_ceiling: float
    minimum_coverage_ratio_step: float
    minimum_coverage_ratio_dynamic: bool
    parameter_source: str
    priority: int
    maximum_retained_sessions: int
    maximum_output_age_ms: int

    def __post_init__(self) -> None:
        for name in ("live_selector", "historical_selector", "parameter_source"):
            _text(getattr(self, name), name)
        for name in ("active_window", "previous_window", "overnight_window"):
            if not isinstance(getattr(self, name), HistoricalWindow):
                raise ValueError(f"{name} must be a HistoricalWindow")
        for name in (
            "minimum_historical_observations",
            "maximum_historical_observations",
            "maximum_retained_sessions",
            "maximum_output_age_ms",
        ):
            _positive_int(getattr(self, name), name)
        if self.maximum_historical_observations < self.minimum_historical_observations:
            raise ValueError("maximum historical observations cannot be below minimum")
        if self.vwap_price_basis not in {"typical", "close", "ohlc4"}:
            raise ValueError("unsupported VWAP price basis")
        for name in (
            "minimum_coverage_ratio",
            "minimum_coverage_ratio_floor",
            "minimum_coverage_ratio_ceiling",
        ):
            value = getattr(self, name)
            if not isinstance(value, int | float) or isinstance(value, bool) or not 0 <= value <= 1:
                raise ValueError(f"{name} must be between zero and one")
        if not (
            self.minimum_coverage_ratio_floor
            <= self.minimum_coverage_ratio
            <= self.minimum_coverage_ratio_ceiling
        ):
            raise ValueError("minimum coverage is outside its configured envelope")
        if self.minimum_coverage_ratio_step <= 0:
            raise ValueError("minimum coverage step must be positive")
        if not 0 <= self.priority <= 100:
            raise ValueError("priority must be between zero and 100")


@dataclass(frozen=True, slots=True)
class SessionWindowSpec:
    """Identify one exact session window and its UTC Unix nanosecond bounds."""

    role: SessionReferenceRole
    session_id: str
    start_ns: int
    end_ns: int
    complete: bool

    def __post_init__(self) -> None:
        if not isinstance(self.role, SessionReferenceRole):
            raise ValueError("role must be a SessionReferenceRole")
        _text(self.session_id, "session_id")
        if self.start_ns < 0 or self.end_ns <= self.start_ns:
            raise ValueError("session window bounds are invalid")
        if not isinstance(self.complete, bool):
            raise ValueError("complete must be a boolean")


@dataclass(frozen=True, slots=True)
class SessionReferenceSummary:
    """Summarize one bounded session window with explicit coverage and fidelity."""

    role: SessionReferenceRole
    session_id: str
    start_ns: int
    end_ns: int
    effective_end_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    bar_vwap_estimate: Decimal | None
    coverage_ratio: Decimal
    health: MetricHealth
    fidelity: MetricFidelity
    observed_ts_ns: int
    received_ts_ns: int
    evidence_refs: tuple[str, ...]
    missing_reasons: tuple[str, ...]
    complete: bool
    opening_observed: bool
    closing_observed: bool

    @property
    def range(self) -> Decimal:
        return self.high - self.low


@dataclass(frozen=True, slots=True)
class SessionReferenceSnapshot:
    """Carry current active, previous, and optional overnight session summaries."""

    instrument_id: str
    active: SessionReferenceSummary | None
    previous: SessionReferenceSummary | None
    overnight: SessionReferenceSummary | None
    active_missing_reason: str = "active_session_not_ready"
    previous_missing_reason: str = "previous_session_not_ready"
    overnight_missing_reason: str = "overnight_not_configured"


@dataclass(slots=True)
class _WindowBucket:
    spec: SessionWindowSpec
    historical: dict[tuple[str, str, int], CompletedBarInput] = field(default_factory=dict)
    live: dict[tuple[str, str, int], CompletedBarInput] = field(default_factory=dict)
    historical_cutoff_ns: int | None = None

    def bars(self) -> tuple[CompletedBarInput, ...]:
        selected = dict(self.historical)
        for key, bar in self.live.items():
            if (
                self.historical_cutoff_ns is None
                or bar.interval_start_ns >= self.historical_cutoff_ns
            ):
                selected[key] = bar
        return tuple(sorted(selected.values(), key=lambda item: item.interval_start_ns))


class SessionReferenceBook:
    """Bounded, order-independent historical/live session projection."""

    def __init__(
        self,
        *,
        instrument_id: str,
        price_basis: str,
        minimum_coverage_ratio: float,
        maximum_retained_sessions: int,
        maximum_observations_per_session: int,
    ) -> None:
        self._instrument_id = _text(instrument_id, "instrument_id")
        if price_basis not in {"typical", "close", "ohlc4"}:
            raise ValueError("unsupported price basis")
        if not 0 <= minimum_coverage_ratio <= 1:
            raise ValueError("minimum coverage ratio must be between zero and one")
        _positive_int(maximum_retained_sessions, "maximum_retained_sessions")
        _positive_int(maximum_observations_per_session, "maximum_observations_per_session")
        self._price_basis = price_basis
        self._minimum_coverage_ratio = Decimal(str(minimum_coverage_ratio))
        self._maximum_retained_sessions = maximum_retained_sessions
        self._maximum_observations = maximum_observations_per_session
        self._buckets: dict[tuple[SessionReferenceRole, str], _WindowBucket] = {}

    def ingest_historical(
        self,
        spec: SessionWindowSpec,
        bars: tuple[CompletedBarInput, ...],
        *,
        cutoff_ns: int,
    ) -> None:
        bucket = self._bucket(spec)
        for bar in bars:
            self._validate_bar(spec, bar)
            bucket.historical.setdefault(bar.key, bar)
        bucket.historical_cutoff_ns = max(bucket.historical_cutoff_ns or 0, cutoff_ns)
        self._trim_observations(bucket.historical)

    def ingest_live(self, spec: SessionWindowSpec, bar: CompletedBarInput) -> None:
        self._validate_bar(spec, bar)
        bucket = self._bucket(spec)
        bucket.live.setdefault(bar.key, bar)
        self._trim_observations(bucket.live)

    def summary(self, role: SessionReferenceRole) -> SessionReferenceSummary | None:
        matching = [bucket for (candidate, _), bucket in self._buckets.items() if candidate is role]
        if not matching:
            return None
        bucket = max(matching, key=lambda item: (item.spec.start_ns, item.spec.end_ns))
        bars = bucket.bars()
        if not bars:
            return None
        return _summarize(
            bucket.spec,
            bars,
            price_basis=self._price_basis,
            minimum_coverage_ratio=self._minimum_coverage_ratio,
        )

    def snapshot(
        self,
        *,
        overnight_missing_reason: str = "overnight_not_configured",
    ) -> SessionReferenceSnapshot:
        return SessionReferenceSnapshot(
            instrument_id=self._instrument_id,
            active=self.summary(SessionReferenceRole.ACTIVE),
            previous=self.summary(SessionReferenceRole.PREVIOUS),
            overnight=self.summary(SessionReferenceRole.OVERNIGHT),
            overnight_missing_reason=overnight_missing_reason,
        )

    def _bucket(self, spec: SessionWindowSpec) -> _WindowBucket:
        key = (spec.role, spec.session_id)
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _WindowBucket(spec)
            self._buckets[key] = bucket
            self._trim_sessions(spec.role)
        else:
            bucket.spec = SessionWindowSpec(
                role=spec.role,
                session_id=spec.session_id,
                start_ns=min(bucket.spec.start_ns, spec.start_ns),
                end_ns=max(bucket.spec.end_ns, spec.end_ns),
                complete=bucket.spec.complete or spec.complete,
            )
        return bucket

    def _trim_sessions(self, role: SessionReferenceRole) -> None:
        keys = [key for key in self._buckets if key[0] is role]
        while len(keys) > self._maximum_retained_sessions:
            oldest = min(keys, key=lambda key: self._buckets[key].spec.start_ns)
            del self._buckets[oldest]
            keys.remove(oldest)

    def _trim_observations(self, values: dict[tuple[str, str, int], CompletedBarInput]) -> None:
        while len(values) > self._maximum_observations:
            del values[min(values, key=lambda key: key[2])]

    def _validate_bar(self, spec: SessionWindowSpec, bar: CompletedBarInput) -> None:
        if not isinstance(bar, CompletedBarInput):
            raise ValueError("bar must be a CompletedBarInput")
        if bar.instrument_id != self._instrument_id or bar.session_id != spec.session_id:
            raise ValueError("bar does not match the session reference identity")
        if bar.interval_start_ns < spec.start_ns or bar.interval_end_ns > spec.end_ns:
            raise ValueError("bar falls outside the session reference window")


def session_reference_metric_definitions(
    policy: SessionReferenceCatalogPolicy,
) -> tuple[MetricDefinition, ...]:
    """Build definitions for active, previous, overnight, and gap metrics."""

    live = CapabilityFeedRequirement(kind=FeedKind.BARS, selector=policy.live_selector)
    historical = {
        SessionReferenceRole.ACTIVE: _historical_input(
            policy,
            policy.active_window,
            "analytical_profile.primary_phase",
        ),
        SessionReferenceRole.PREVIOUS: _historical_input(
            policy,
            policy.previous_window,
            "analytical_profile.primary_phase",
            session_count=1,
        ),
        SessionReferenceRole.OVERNIGHT: _historical_input(
            policy,
            policy.overnight_window,
            "analytical_profile.overnight_phase",
        ),
    }
    coverage_parameter = MetricParameterDefinition(
        parameter_id="minimum_coverage_ratio",
        meaning="Minimum represented-time coverage required for ready session output",
        value_kind=MetricValueKind.NUMBER,
        unit="ratio",
        default=policy.minimum_coverage_ratio,
        scope="instrument+analytical_profile+session_reference_family",
        dynamic=policy.minimum_coverage_ratio_dynamic,
        mutability=(
            ParameterMutability.POLICY_CONTROLLED_RUNTIME
            if policy.minimum_coverage_ratio_dynamic
            else ParameterMutability.STARTUP_ONLY
        ),
        source=policy.parameter_source,
        minimum=policy.minimum_coverage_ratio_floor,
        maximum=policy.minimum_coverage_ratio_ceiling,
        step=policy.minimum_coverage_ratio_step,
    )
    price_basis = MetricParameterDefinition(
        parameter_id="vwap_price_basis",
        meaning="Bar price basis used by the explicitly named VWAP estimate",
        value_kind=MetricValueKind.TEXT,
        unit="choice",
        default=policy.vwap_price_basis,
        scope="instrument+analytical_profile+session_reference_family",
        dynamic=policy.vwap_price_basis_dynamic,
        mutability=(
            ParameterMutability.POLICY_CONTROLLED_RUNTIME
            if policy.vwap_price_basis_dynamic
            else ParameterMutability.STARTUP_ONLY
        ),
        source=policy.parameter_source,
        allowed_values=("typical", "close", "ohlc4"),
    )
    definitions: list[MetricDefinition] = []
    for metric_id in ACTIVE_SESSION_METRIC_IDS:
        definitions.append(
            _definition(
                metric_id,
                cadence=MetricCadence.COMPLETED_BAR,
                live_inputs=(live,),
                historical_inputs=(historical[SessionReferenceRole.ACTIVE],),
                parameters=_parameters(metric_id, coverage_parameter, price_basis),
                policy=policy,
            ),
        )
    for metric_id in PREVIOUS_SESSION_METRIC_IDS:
        definitions.append(
            _definition(
                metric_id,
                cadence=MetricCadence.DEPENDENCY_READY,
                historical_inputs=(historical[SessionReferenceRole.PREVIOUS],),
                parameters=_parameters(metric_id, coverage_parameter, price_basis),
                policy=policy,
            ),
        )
    for metric_id in OVERNIGHT_METRIC_IDS:
        definitions.append(
            _definition(
                metric_id,
                cadence=MetricCadence.COMPLETED_BAR,
                live_inputs=(live,),
                historical_inputs=(historical[SessionReferenceRole.OVERNIGHT],),
                parameters=(coverage_parameter,),
                policy=policy,
            ),
        )
    definitions.extend(
        _definition(
            metric_id,
            cadence=MetricCadence.COMPLETED_BAR,
            metric_inputs=_gap_dependencies(metric_id),
            parameters=(coverage_parameter,),
            policy=policy,
        )
        for metric_id in GAP_METRIC_IDS
    )
    return tuple(definitions)


def calculate_session_reference_metrics(
    snapshot: SessionReferenceSnapshot,
    *,
    registry: MetricRegistry,
    parameter_version: int,
    calculated_ts_ns: int,
    published_ts_ns: int,
    source: str,
    revision: int,
) -> tuple[MetricValue, ...]:
    """Calculate session-reference values or explicit unavailable outcomes.

    The function preserves calendar-derived session identity, completed-bar
    lineage, coverage, missing volume, and historical/live evidence quality.
    """

    values: dict[str, tuple[object | None, MetricHealth, MetricFidelity, tuple[str, ...]]] = {}
    _summary_values(values, "active_session", snapshot.active, snapshot.active_missing_reason)
    _summary_values(values, "previous_session", snapshot.previous, snapshot.previous_missing_reason)
    _summary_values(values, "overnight", snapshot.overnight, snapshot.overnight_missing_reason)
    previous_close = (
        snapshot.previous.close
        if snapshot.previous is not None and snapshot.previous.closing_observed
        else None
    )
    _gap_values(values, snapshot, previous_close)

    result: list[MetricValue] = []
    for metric_id in SESSION_REFERENCE_METRIC_IDS:
        contexts = _metric_contexts(metric_id, snapshot)
        observed_ns = (
            max(item.observed_ts_ns for item in contexts) if contexts else calculated_ts_ns
        )
        received_ns = (
            max(item.received_ts_ns for item in contexts) if contexts else calculated_ts_ns
        )
        effective_ns = (
            max(item.effective_end_ns for item in contexts) if contexts else calculated_ts_ns
        )
        safe_calculated = max(calculated_ts_ns, received_ns)
        safe_published = max(published_ts_ns, safe_calculated)
        evidence_refs = (
            tuple(dict.fromkeys(ref for item in contexts for ref in item.evidence_refs))
            if contexts
            else ("session_reference:pending",)
        )
        result.append(
            MetricValue(
                metric_id=metric_id,
                metric_version=1,
                parameter_version=parameter_version,
                instrument_id=snapshot.instrument_id,
                session_id=contexts[0].session_id if contexts else None,
                value=values[metric_id][0],  # type: ignore[arg-type]
                unit=registry.get(metric_id, 1).unit,
                effective_ts_ns=effective_ns,
                observed_ts_ns=observed_ns,
                received_ts_ns=received_ns,
                calculated_ts_ns=safe_calculated,
                published_ts_ns=safe_published,
                health=values[metric_id][1],
                fidelity=values[metric_id][2],
                source=source,
                evidence_refs=evidence_refs,
                missing_reasons=values[metric_id][3],
                revision=revision,
            ),
        )
    for value in result:
        _validate_legacy_metric_value(registry, value)
    return tuple(result)


def metric_value_signature(value: MetricValue) -> tuple[object, ...]:
    return (
        value.metric_id,
        value.session_id,
        value.value,
        value.health,
        value.fidelity,
        value.missing_reasons,
        value.effective_ts_ns,
    )


def _summarize(
    spec: SessionWindowSpec,
    bars: tuple[CompletedBarInput, ...],
    *,
    price_basis: str,
    minimum_coverage_ratio: Decimal,
) -> SessionReferenceSummary:
    effective_end_ns = spec.end_ns if spec.complete else max(bar.interval_end_ns for bar in bars)
    expected_ns = effective_end_ns - spec.start_ns
    covered_ns = _covered_duration_ns(bars, spec.start_ns, effective_end_ns)
    coverage = Decimal(covered_ns) / Decimal(expected_ns) if expected_ns > 0 else Decimal(0)
    health = _worst_health(tuple(bar.health for bar in bars))
    missing: list[str] = []
    opening_observed = bars[0].interval_start_ns == spec.start_ns
    closing_observed = bars[-1].interval_end_ns == spec.end_ns
    if not opening_observed:
        missing.append("session_open_not_observed")
    if spec.complete and not closing_observed:
        missing.append("session_close_not_observed")
    if coverage < minimum_coverage_ratio:
        health = MetricHealth.DEGRADED
        missing.append("session_coverage_below_threshold")
    volume: Decimal | None
    vwap: Decimal | None
    if any(bar.volume is None for bar in bars):
        volume = None
        vwap = None
        missing.append(
            "volume_unsupported"
            if all("volume_unsupported" in bar.missing_reasons for bar in bars)
            else "volume_partial"
        )
    else:
        volume = sum((bar.volume or Decimal(0) for bar in bars), Decimal(0))
        weighted = sum(
            (_bar_price(bar, price_basis) * (bar.volume or Decimal(0)) for bar in bars),
            Decimal(0),
        )
        vwap = weighted / volume if volume > 0 else None
        if vwap is None:
            missing.append("zero_session_volume")
    fidelity = (
        MetricFidelity.DERIVED
        if health is MetricHealth.READY and coverage >= minimum_coverage_ratio
        else MetricFidelity.PARTIAL
    )
    return SessionReferenceSummary(
        role=spec.role,
        session_id=spec.session_id,
        start_ns=spec.start_ns,
        end_ns=spec.end_ns,
        effective_end_ns=effective_end_ns,
        open=bars[0].open,
        high=max(bar.high for bar in bars),
        low=min(bar.low for bar in bars),
        close=bars[-1].close,
        volume=volume,
        bar_vwap_estimate=vwap,
        coverage_ratio=coverage,
        health=health,
        fidelity=fidelity,
        observed_ts_ns=max(bar.observed_ts_ns for bar in bars),
        received_ts_ns=max(bar.received_ts_ns for bar in bars),
        evidence_refs=tuple(dict.fromkeys(ref for bar in bars for ref in bar.evidence_refs)),
        missing_reasons=tuple(missing),
        complete=spec.complete,
        opening_observed=opening_observed,
        closing_observed=closing_observed,
    )


def _summary_values(
    target: dict[str, tuple[object | None, MetricHealth, MetricFidelity, tuple[str, ...]]],
    prefix: str,
    summary: SessionReferenceSummary | None,
    missing_reason: str,
) -> None:
    ids = {
        "active_session": ACTIVE_SESSION_METRIC_IDS,
        "previous_session": PREVIOUS_SESSION_METRIC_IDS,
        "overnight": OVERNIGHT_METRIC_IDS,
    }[prefix]
    if summary is None:
        for metric_id in ids:
            target[metric_id] = (
                None,
                MetricHealth.UNAVAILABLE,
                MetricFidelity.UNAVAILABLE,
                (missing_reason,),
            )
        return
    values: dict[str, object | None] = {
        f"{prefix}.start_ns": summary.start_ns,
        f"{prefix}.end_ns": summary.end_ns,
        f"{prefix}.complete": summary.complete,
        f"{prefix}.open": summary.open if summary.opening_observed else None,
        f"{prefix}.high": summary.high,
        f"{prefix}.low": summary.low,
        f"{prefix}.range": summary.range,
    }
    close_name = "close" if prefix == "previous_session" else "latest_close"
    values[f"{prefix}.{close_name}"] = (
        summary.close if prefix != "previous_session" or summary.closing_observed else None
    )
    if prefix == "active_session":
        values[f"{prefix}.location"] = (
            (summary.close - summary.low) / summary.range if summary.range else None
        )
    if prefix != "overnight":
        values[f"{prefix}.volume"] = summary.volume
        values[f"{prefix}.bar_vwap_estimate"] = summary.bar_vwap_estimate
        values[f"{prefix}.coverage_ratio"] = summary.coverage_ratio
    if prefix == "previous_session":
        values[f"{prefix}.simple_return"] = (
            summary.close / summary.open - 1
            if summary.opening_observed and summary.closing_observed and summary.open != 0
            else None
        )
    for metric_id in ids:
        value = values[metric_id]
        if value is None:
            reason = (
                "zero_session_range"
                if metric_id.endswith(".location")
                else "session_open_not_observed"
                if metric_id.endswith(".open") and not summary.opening_observed
                else "session_close_not_observed"
                if prefix == "previous_session"
                and metric_id.endswith((".close", ".simple_return"))
                and not summary.closing_observed
                else "session_open_not_observed"
                if metric_id.endswith(".simple_return") and not summary.opening_observed
                else "zero_session_open"
                if metric_id.endswith(".simple_return") and summary.open == 0
                else next(
                    (
                        item
                        for item in summary.missing_reasons
                        if item in {"volume_unsupported", "volume_partial", "zero_session_volume"}
                    ),
                    "value_unavailable",
                )
            )
            health = (
                MetricHealth.UNSUPPORTED
                if reason == "volume_unsupported"
                else MetricHealth.UNAVAILABLE
            )
            target[metric_id] = (None, health, MetricFidelity.UNAVAILABLE, (reason,))
        else:
            target[metric_id] = (
                value,
                summary.health,
                summary.fidelity,
                tuple(
                    reason
                    for reason in summary.missing_reasons
                    if reason == "session_coverage_below_threshold"
                ),
            )


def _gap_values(
    target: dict[str, tuple[object | None, MetricHealth, MetricFidelity, tuple[str, ...]]],
    snapshot: SessionReferenceSnapshot,
    previous_close: Decimal | None,
) -> None:
    pairs = (
        ("gap.indicative", snapshot.overnight.close if snapshot.overnight else None),
        (
            "gap.opening",
            snapshot.active.open
            if snapshot.active is not None and snapshot.active.opening_observed
            else None,
        ),
    )
    for prefix, reference in pairs:
        if previous_close is None or reference is None:
            reason = (
                "previous_session_close_not_observed"
                if snapshot.previous is not None and not snapshot.previous.closing_observed
                else snapshot.previous_missing_reason
                if previous_close is None
                else snapshot.overnight_missing_reason
                if prefix == "gap.indicative"
                else "active_session_open_not_observed"
                if snapshot.active is not None and not snapshot.active.opening_observed
                else snapshot.active_missing_reason
            )
            for suffix in ("points", "ratio"):
                target[f"{prefix}.{suffix}"] = (
                    None,
                    MetricHealth.UNAVAILABLE,
                    MetricFidelity.UNAVAILABLE,
                    (reason,),
                )
            continue
        points = reference - previous_close
        source_summary = snapshot.overnight if prefix == "gap.indicative" else snapshot.active
        assert source_summary is not None
        assert snapshot.previous is not None
        health = _worst_health((source_summary.health, snapshot.previous.health))
        fidelity = (
            MetricFidelity.DERIVED if health is MetricHealth.READY else MetricFidelity.PARTIAL
        )
        target[f"{prefix}.points"] = (points, health, fidelity, ())
        target[f"{prefix}.ratio"] = (
            (points / previous_close, health, fidelity, ())
            if previous_close != 0
            else (
                None,
                MetricHealth.UNAVAILABLE,
                MetricFidelity.UNAVAILABLE,
                ("zero_previous_session_close",),
            )
        )


def _historical_input(
    policy: SessionReferenceCatalogPolicy,
    window: HistoricalWindow,
    phase_source: str,
    *,
    session_count: int | None = None,
) -> CapabilityHistoricalRequirement:
    window_parameters: dict[str, str | int] = {"phase_source": phase_source}
    if session_count is not None:
        window_parameters["session_count"] = session_count
    return CapabilityHistoricalRequirement(
        kind=FeedKind.BARS,
        selector=policy.historical_selector,
        window=window,
        minimum_observations=policy.minimum_historical_observations,
        maximum_observations=policy.maximum_historical_observations,
        window_parameters=window_parameters,
        parameters={"purpose": "session_reference"},
    )


def _definition(
    metric_id: str,
    *,
    cadence: MetricCadence,
    policy: SessionReferenceCatalogPolicy,
    live_inputs: tuple[CapabilityFeedRequirement, ...] = (),
    historical_inputs: tuple[CapabilityHistoricalRequirement, ...] = (),
    metric_inputs: tuple[MetricDependency, ...] = (),
    parameters: tuple[MetricParameterDefinition, ...] = (),
) -> MetricDefinition:
    if metric_id.endswith((".start_ns", ".end_ns")):
        unit = "unix_ns"
        value_kind = MetricValueKind.INTEGER
    elif metric_id.endswith(".complete"):
        unit = "boolean"
        value_kind = MetricValueKind.BOOLEAN
    elif metric_id.endswith((".ratio", ".location", ".simple_return", ".coverage_ratio")):
        unit = "ratio"
        value_kind = MetricValueKind.NUMBER
    elif metric_id.endswith(".volume"):
        unit = "volume"
        value_kind = MetricValueKind.NUMBER
    else:
        unit = "price"
        value_kind = MetricValueKind.NUMBER
    return MetricDefinition(
        metric_id=metric_id,
        version=1,
        decision_question=f"What is the current validated value of {metric_id}?",
        implementation_id=f"markeitech.{metric_id}.v1",
        formula=metric_id,
        normalization="none" if unit != "ratio" else "dimensionless ratio",
        applicability="instruments bound to an explicit analytical session profile",
        value_kind=value_kind,
        unit=unit,
        cadence=cadence,
        horizon="configured analytical session reference",
        nullable=True,
        retained_state=MetricRetainedState.SESSION,
        fidelity=MetricFidelity.DERIVED,
        allowed_fidelities=(
            MetricFidelity.DERIVED,
            MetricFidelity.PARTIAL,
            MetricFidelity.UNAVAILABLE,
        ),
        failure_behavior=MetricFailureBehavior.EMIT_NULL,
        failure_modes=(
            "historical dependency unavailable",
            "session coverage below configured threshold",
            "unsupported or incomplete volume",
            "historical/live overlap conflict",
        ),
        priority=policy.priority,
        warmup=MetricWarmupPolicy(1, 0, True),
        resources=MetricResourcePolicy(
            maximum_retained_observations=policy.maximum_retained_sessions,
            minimum_update_interval_ms=0,
            maximum_output_age_ms=policy.maximum_output_age_ms,
        ),
        live_inputs=live_inputs,
        historical_inputs=historical_inputs,
        metric_inputs=metric_inputs,
        parameters=parameters,
    )


def _parameters(
    metric_id: str,
    coverage: MetricParameterDefinition,
    price_basis: MetricParameterDefinition,
) -> tuple[MetricParameterDefinition, ...]:
    if metric_id.endswith(".bar_vwap_estimate"):
        return (coverage, price_basis)
    return (coverage,)


def _gap_dependencies(metric_id: str) -> tuple[MetricDependency, ...]:
    if metric_id.startswith("gap.indicative"):
        return (
            MetricDependency("overnight.latest_close", 1),
            MetricDependency("previous_session.close", 1),
        )
    return (
        MetricDependency("active_session.open", 1),
        MetricDependency("previous_session.close", 1),
    )


def _metric_contexts(
    metric_id: str,
    snapshot: SessionReferenceSnapshot,
) -> tuple[SessionReferenceSummary, ...]:
    candidates: tuple[SessionReferenceSummary | None, ...]
    if metric_id.startswith("active_session."):
        candidates = (snapshot.active,)
    elif metric_id.startswith("previous_session."):
        candidates = (snapshot.previous,)
    elif metric_id.startswith("overnight."):
        candidates = (snapshot.overnight,)
    elif metric_id.startswith("gap.indicative."):
        candidates = (snapshot.overnight, snapshot.previous)
    else:
        candidates = (snapshot.active, snapshot.previous)
    return tuple(item for item in candidates if item is not None)


def _covered_duration_ns(
    bars: tuple[CompletedBarInput, ...],
    start_ns: int,
    end_ns: int,
) -> int:
    intervals = sorted(
        (max(start_ns, bar.interval_start_ns), min(end_ns, bar.interval_end_ns))
        for bar in bars
        if bar.interval_end_ns > start_ns and bar.interval_start_ns < end_ns
    )
    if not intervals:
        return 0
    total = 0
    current_start, current_end = intervals[0]
    for candidate_start, candidate_end in intervals[1:]:
        if candidate_start <= current_end:
            current_end = max(current_end, candidate_end)
        else:
            total += current_end - current_start
            current_start, current_end = candidate_start, candidate_end
    return total + current_end - current_start


def _bar_price(bar: CompletedBarInput, basis: str) -> Decimal:
    if basis == "typical":
        return (bar.high + bar.low + bar.close) / Decimal(3)
    if basis == "ohlc4":
        return (bar.open + bar.high + bar.low + bar.close) / Decimal(4)
    return bar.close


def _worst_health(values: tuple[MetricHealth, ...]) -> MetricHealth:
    order = {
        MetricHealth.READY: 0,
        MetricHealth.WARMING: 1,
        MetricHealth.DEGRADED: 2,
        MetricHealth.STALE: 3,
        MetricHealth.UNAVAILABLE: 4,
        MetricHealth.UNSUPPORTED: 5,
        MetricHealth.FAILED: 6,
    }
    return max(values, key=order.__getitem__)


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _positive_int(value: object, label: str) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
