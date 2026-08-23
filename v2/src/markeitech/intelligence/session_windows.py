from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from markeitech.acquisition import (
    CapabilityFeedRequirement,
    CapabilityHistoricalRequirement,
    FeedKind,
    HistoricalWindow,
)
from markeitech.intelligence.completed_bars import CompletedBarInput
from markeitech.intelligence.metrics import (
    MetricCadence,
    MetricDefinition,
    MetricFailureBehavior,
    MetricFidelity,
    MetricHealth,
    MetricParameterDefinition,
    MetricRegistry,
    MetricResourcePolicy,
    MetricRetainedState,
    MetricValue,
    MetricValueKind,
    MetricWarmupPolicy,
    ParameterMutability,
)
from markeitech.intelligence.session import SessionCalendar, SessionWindow

_SECOND_NS = 1_000_000_000

OPENING_RANGE_FIELDS = (
    "start_ns",
    "end_ns",
    "complete",
    "open",
    "high",
    "low",
    "close",
    "range",
    "volume",
    "distance_above_high_points",
    "distance_above_high_ratio",
    "distance_below_low_points",
    "distance_below_low_ratio",
    "coverage_ratio",
)
POWER_HOUR_FIELDS = (
    "start_ns",
    "end_ns",
    "complete",
    "open",
    "high",
    "low",
    "close",
    "range",
    "simple_return",
    "volume",
    "bar_vwap_estimate",
    "directional_efficiency",
    "coverage_ratio",
)


@dataclass(frozen=True, slots=True)
class AnalyticalWindowPolicy:
    profile_id: str
    profile_version: int
    window_id: str
    purpose: str
    anchor_phase: str
    anchor_boundary: str
    offset_seconds: int
    duration_seconds: int
    minimum_duration_seconds: int
    maximum_duration_seconds: int
    duration_step_seconds: int
    duration_dynamic: bool
    live_selector: str
    historical_selector: str
    minimum_historical_observations: int
    maximum_historical_observations: int
    price_basis: str
    price_basis_dynamic: bool
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
        for name in (
            "profile_id",
            "window_id",
            "anchor_phase",
            "live_selector",
            "historical_selector",
            "parameter_source",
        ):
            _text(getattr(self, name), name)
        _positive_int(self.profile_version, "profile_version")
        if self.purpose not in {"opening_range", "power_hour"}:
            raise ValueError("purpose must be opening_range or power_hour")
        if self.anchor_boundary not in {"start", "end"}:
            raise ValueError("anchor_boundary must be start or end")
        if not isinstance(self.offset_seconds, int) or isinstance(self.offset_seconds, bool):
            raise ValueError("offset_seconds must be an integer")
        for name in (
            "duration_seconds",
            "minimum_duration_seconds",
            "maximum_duration_seconds",
            "duration_step_seconds",
            "minimum_historical_observations",
            "maximum_historical_observations",
            "maximum_retained_sessions",
            "maximum_output_age_ms",
        ):
            _positive_int(getattr(self, name), name)
        if not (
            self.minimum_duration_seconds
            <= self.duration_seconds
            <= self.maximum_duration_seconds
        ):
            raise ValueError("duration is outside its configured envelope")
        if (self.duration_seconds - self.minimum_duration_seconds) % self.duration_step_seconds:
            raise ValueError("duration does not align to its configured step")
        if self.maximum_historical_observations < self.minimum_historical_observations:
            raise ValueError("maximum historical observations cannot be below minimum")
        if self.price_basis not in {"typical", "close", "ohlc4"}:
            raise ValueError("unsupported price basis")
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

    @property
    def metric_prefix(self) -> str:
        return f"{self.purpose}.{self.profile_id}.{self.window_id}"

    @property
    def historical_window(self) -> HistoricalWindow:
        return (
            HistoricalWindow.OPENING_RANGE
            if self.purpose == "opening_range"
            else HistoricalWindow.POWER_HOUR
        )

    @property
    def metric_ids(self) -> tuple[str, ...]:
        fields = OPENING_RANGE_FIELDS if self.purpose == "opening_range" else POWER_HOUR_FIELDS
        return tuple(f"{self.metric_prefix}.{field}" for field in fields)


@dataclass(frozen=True, slots=True)
class AnalyticalWindowSpec:
    policy: AnalyticalWindowPolicy
    session_id: str
    start_ns: int
    end_ns: int

    def __post_init__(self) -> None:
        if not isinstance(self.policy, AnalyticalWindowPolicy):
            raise ValueError("policy must be an AnalyticalWindowPolicy")
        _text(self.session_id, "session_id")
        if self.start_ns < 0 or self.end_ns <= self.start_ns:
            raise ValueError("analytical window bounds are invalid")


@dataclass(frozen=True, slots=True)
class AnalyticalWindowSummary:
    policy: AnalyticalWindowPolicy
    session_id: str
    start_ns: int
    end_ns: int
    effective_end_ns: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    latest_close: Decimal
    volume: Decimal | None
    bar_vwap_estimate: Decimal | None
    directional_efficiency: Decimal | None
    coverage_ratio: Decimal
    complete: bool
    health: MetricHealth
    fidelity: MetricFidelity
    observed_ts_ns: int
    received_ts_ns: int
    evidence_refs: tuple[str, ...]
    missing_reasons: tuple[str, ...]
    volume_missing_reasons: tuple[str, ...]

    @property
    def range(self) -> Decimal:
        return self.high - self.low

    @property
    def metric_session_id(self) -> str:
        return f"{self.session_id}:{self.policy.window_id}"


@dataclass(slots=True)
class _WindowBucket:
    spec: AnalyticalWindowSpec
    historical: dict[tuple[str, str, int], CompletedBarInput] = field(default_factory=dict)
    live: dict[tuple[str, str, int], CompletedBarInput] = field(default_factory=dict)
    historical_cutoff_ns: int | None = None
    latest: CompletedBarInput | None = None

    def bars(self) -> tuple[CompletedBarInput, ...]:
        selected = dict(self.historical)
        for key, bar in self.live.items():
            if (
                self.historical_cutoff_ns is None
                or bar.interval_start_ns >= self.historical_cutoff_ns
            ):
                selected[key] = bar
        return tuple(sorted(selected.values(), key=lambda item: item.interval_start_ns))


class AnalyticalWindowBook:
    """Bounded historical/live state for one configured analytical window."""

    def __init__(
        self,
        *,
        instrument_id: str,
        policy: AnalyticalWindowPolicy,
        maximum_observations_per_session: int,
    ) -> None:
        self._instrument_id = _text(instrument_id, "instrument_id")
        if not isinstance(policy, AnalyticalWindowPolicy):
            raise ValueError("policy must be an AnalyticalWindowPolicy")
        _positive_int(maximum_observations_per_session, "maximum_observations_per_session")
        self._policy = policy
        self._maximum_observations = maximum_observations_per_session
        self._buckets: dict[str, _WindowBucket] = {}

    def ingest_historical(
        self,
        spec: AnalyticalWindowSpec,
        bars: tuple[CompletedBarInput, ...],
        *,
        cutoff_ns: int,
    ) -> None:
        bucket = self._bucket(spec)
        for bar in bars:
            self._validate_bar(spec, bar, require_overlap=True)
            bucket.historical.setdefault(bar.key, bar)
            self._update_latest(bucket, bar)
        bucket.historical_cutoff_ns = max(bucket.historical_cutoff_ns or 0, cutoff_ns)
        self._trim(bucket.historical)

    def ingest_live(self, spec: AnalyticalWindowSpec, bar: CompletedBarInput) -> None:
        self._validate_bar(spec, bar, require_overlap=False)
        if bar.interval_end_ns <= spec.start_ns:
            return
        bucket = self._bucket(spec)
        if bar.interval_end_ns > spec.start_ns and bar.interval_start_ns < spec.end_ns:
            bucket.live.setdefault(bar.key, bar)
            self._trim(bucket.live)
        self._update_latest(bucket, bar)

    def summary(self, *, as_of_ns: int) -> AnalyticalWindowSummary | None:
        matching = tuple(self._buckets.values())
        if not matching:
            return None
        bucket = max(matching, key=lambda item: item.spec.start_ns)
        if as_of_ns <= bucket.spec.start_ns:
            return None
        bars = bucket.bars()
        if not bars:
            return None
        effective_end_ns = min(bucket.spec.end_ns, as_of_ns)
        covered_ns = _covered_duration_ns(bars, bucket.spec.start_ns, effective_end_ns)
        expected_ns = effective_end_ns - bucket.spec.start_ns
        coverage = Decimal(covered_ns) / Decimal(expected_ns) if expected_ns > 0 else Decimal(0)
        health = _worst_health(tuple(bar.health for bar in bars))
        complete = as_of_ns >= bucket.spec.end_ns
        missing: list[str] = []
        if coverage < Decimal(str(self._policy.minimum_coverage_ratio)):
            health = MetricHealth.DEGRADED
            missing.append("window_coverage_below_threshold")
        if complete and max(bar.interval_end_ns for bar in bars) < bucket.spec.end_ns:
            health = MetricHealth.DEGRADED
            missing.append("window_close_not_observed")
        volume: Decimal | None = None
        vwap: Decimal | None = None
        efficiency: Decimal | None = None
        volume_missing: list[str] = []
        if self._policy.purpose == "power_hour":
            volume, vwap = _volume_values(bars, self._policy.price_basis, volume_missing)
            missing.extend(volume_missing)
            efficiency = _directional_efficiency(bars)
            if efficiency is None:
                missing.append("zero_close_path")
        else:
            volume, _ = _volume_values(bars, self._policy.price_basis, volume_missing)
        latest = bucket.latest or bars[-1]
        contexts = (*bars, latest)
        fidelity = (
            MetricFidelity.DERIVED
            if health is MetricHealth.READY and not missing
            else MetricFidelity.PARTIAL
        )
        return AnalyticalWindowSummary(
            policy=self._policy,
            session_id=bucket.spec.session_id,
            start_ns=bucket.spec.start_ns,
            end_ns=bucket.spec.end_ns,
            effective_end_ns=effective_end_ns,
            open=bars[0].open,
            high=max(bar.high for bar in bars),
            low=min(bar.low for bar in bars),
            close=bars[-1].close,
            latest_close=latest.close,
            volume=volume,
            bar_vwap_estimate=vwap,
            directional_efficiency=efficiency,
            coverage_ratio=coverage,
            complete=complete,
            health=health,
            fidelity=fidelity,
            observed_ts_ns=max(bar.observed_ts_ns for bar in contexts),
            received_ts_ns=max(bar.received_ts_ns for bar in contexts),
            evidence_refs=tuple(
                dict.fromkeys(ref for bar in contexts for ref in bar.evidence_refs),
            ),
            missing_reasons=tuple(dict.fromkeys(missing)),
            volume_missing_reasons=tuple(dict.fromkeys(volume_missing)),
        )

    def _bucket(self, spec: AnalyticalWindowSpec) -> _WindowBucket:
        if spec.policy != self._policy:
            raise ValueError("window spec policy does not match book policy")
        bucket = self._buckets.get(spec.session_id)
        if bucket is None:
            bucket = _WindowBucket(spec)
            self._buckets[spec.session_id] = bucket
            while len(self._buckets) > self._policy.maximum_retained_sessions:
                oldest = min(self._buckets, key=lambda key: self._buckets[key].spec.start_ns)
                del self._buckets[oldest]
        elif bucket.spec != spec:
            raise ValueError("window bounds changed for an existing session identity")
        return bucket

    def _validate_bar(
        self,
        spec: AnalyticalWindowSpec,
        bar: CompletedBarInput,
        *,
        require_overlap: bool,
    ) -> None:
        if bar.instrument_id != self._instrument_id:
            raise ValueError("bar instrument does not match analytical window book")
        if bar.analytical_profile_id != self._policy.profile_id:
            raise ValueError("bar profile does not match analytical window policy")
        if bar.session_id != spec.session_id:
            raise ValueError("bar session does not match analytical window spec")
        if require_overlap and not (
            bar.interval_end_ns > spec.start_ns and bar.interval_start_ns < spec.end_ns
        ):
            raise ValueError("historical bar does not overlap analytical window")

    def _trim(self, values: dict[tuple[str, str, int], CompletedBarInput]) -> None:
        while len(values) > self._maximum_observations:
            del values[min(values, key=lambda key: values[key].interval_end_ns)]

    @staticmethod
    def _update_latest(bucket: _WindowBucket, bar: CompletedBarInput) -> None:
        if bucket.latest is None or bar.interval_end_ns > bucket.latest.interval_end_ns:
            bucket.latest = bar


def resolve_analytical_window(
    policy: AnalyticalWindowPolicy,
    session: SessionWindow,
    *,
    session_id: str,
) -> AnalyticalWindowSpec:
    if session.phase != policy.anchor_phase:
        raise ValueError("session phase does not match analytical window anchor")
    anchor_ns = session.start_ns if policy.anchor_boundary == "start" else session.end_ns
    start_ns = anchor_ns + policy.offset_seconds * _SECOND_NS
    end_ns = start_ns + policy.duration_seconds * _SECOND_NS
    start_ns = max(session.start_ns, start_ns)
    end_ns = min(session.end_ns, end_ns)
    if end_ns <= start_ns:
        raise ValueError("configured analytical window is outside the session phase")
    return AnalyticalWindowSpec(policy, session_id, start_ns, end_ns)


def resolve_historical_analytical_window(
    policy: AnalyticalWindowPolicy,
    calendar: SessionCalendar,
    *,
    calendar_id: str,
    request_start_ns: int,
) -> tuple[date, AnalyticalWindowSpec]:
    """Resolve durable session identity from the requested window, not provider bar labels."""
    snapshot = calendar.evaluate(request_start_ns)
    if snapshot.trade_date is None:
        raise ValueError("calendar did not assign the historical window a trade date")
    sessions = calendar.windows(snapshot.trade_date, snapshot.trade_date)
    session = next(
        (
            item
            for item in sessions
            if item.phase == policy.anchor_phase
            and item.start_ns <= request_start_ns < item.end_ns
        ),
        None,
    )
    if session is None:
        raise ValueError("historical request does not start inside its anchor phase")
    session_id = f"{calendar_id}:{session.trade_date.isoformat()}:{session.phase}"
    return session.trade_date, resolve_analytical_window(
        policy,
        session,
        session_id=session_id,
    )


def analytical_window_metric_definitions(
    policies: tuple[AnalyticalWindowPolicy, ...],
) -> tuple[MetricDefinition, ...]:
    definitions: list[MetricDefinition] = []
    for policy in policies:
        historical = CapabilityHistoricalRequirement(
            kind=FeedKind.BARS,
            selector=policy.historical_selector,
            window=policy.historical_window,
            minimum_observations=policy.minimum_historical_observations,
            maximum_observations=policy.maximum_historical_observations,
            window_parameters={
                "phase_source": f"analytical_profile:{policy.profile_id}:{policy.anchor_phase}",
                "anchor_boundary": policy.anchor_boundary,
                "offset_seconds": policy.offset_seconds,
                "duration_seconds": policy.duration_seconds,
                **(
                    {"fallback_to_previous": True}
                    if policy.purpose == "power_hour"
                    else {}
                ),
            },
            parameters={"purpose": policy.purpose, "window_id": policy.window_id},
        )
        live = CapabilityFeedRequirement(kind=FeedKind.BARS, selector=policy.live_selector)
        duration = MetricParameterDefinition(
            parameter_id="duration_seconds",
            meaning="Configured duration of the analytical session window",
            value_kind=MetricValueKind.INTEGER,
            unit="seconds",
            default=policy.duration_seconds,
            scope="analytical_profile+window",
            dynamic=policy.duration_dynamic,
            mutability=(
                ParameterMutability.POLICY_CONTROLLED_RUNTIME
                if policy.duration_dynamic
                else ParameterMutability.STARTUP_ONLY
            ),
            source=policy.parameter_source,
            minimum=policy.minimum_duration_seconds,
            maximum=policy.maximum_duration_seconds,
            step=policy.duration_step_seconds,
        )
        coverage = MetricParameterDefinition(
            parameter_id="minimum_coverage_ratio",
            meaning="Minimum represented window duration required for ready fidelity",
            value_kind=MetricValueKind.NUMBER,
            unit="ratio",
            default=policy.minimum_coverage_ratio,
            scope="analytical_profile+window",
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
            parameter_id="price_basis",
            meaning="Bar price basis used by the volume-weighted estimate",
            value_kind=MetricValueKind.TEXT,
            unit="category",
            default=policy.price_basis,
            scope="analytical_profile+window",
            dynamic=policy.price_basis_dynamic,
            mutability=(
                ParameterMutability.POLICY_CONTROLLED_RUNTIME
                if policy.price_basis_dynamic
                else ParameterMutability.STARTUP_ONLY
            ),
            source=policy.parameter_source,
            allowed_values=("typical", "close", "ohlc4"),
        )
        for metric_id in policy.metric_ids:
            parameters = (duration, coverage)
            if metric_id.endswith(".bar_vwap_estimate"):
                parameters = (*parameters, price_basis)
            definitions.append(
                MetricDefinition(
                    metric_id=metric_id,
                    version=1,
                    decision_question=f"What is the validated {metric_id} value?",
                    implementation_id=f"markeitech.{metric_id}.v1",
                    formula=metric_id,
                    normalization="dimensionless ratio" if metric_id.endswith("_ratio") else "none",
                    applicability=f"analytical profile {policy.profile_id}",
                    value_kind=_value_kind(metric_id),
                    unit=_unit(metric_id),
                    cadence=MetricCadence.COMPLETED_BAR,
                    horizon="configured calendar-relative session window",
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
                        "window not started",
                        "historical dependency unavailable",
                        "window coverage below configured threshold",
                        "unsupported or incomplete volume",
                    ),
                    priority=policy.priority,
                    warmup=MetricWarmupPolicy(1, 0, True),
                    resources=MetricResourcePolicy(
                        maximum_retained_observations=policy.maximum_retained_sessions,
                        minimum_update_interval_ms=0,
                        maximum_output_age_ms=policy.maximum_output_age_ms,
                    ),
                    live_inputs=(live,),
                    historical_inputs=(historical,),
                    parameters=parameters,
                ),
            )
    return tuple(definitions)


def calculate_analytical_window_metrics(
    instrument_id: str,
    policy: AnalyticalWindowPolicy,
    summary: AnalyticalWindowSummary | None,
    *,
    registry: MetricRegistry,
    parameter_version: int,
    calculated_ts_ns: int,
    published_ts_ns: int,
    source: str,
    revision: int,
    missing_reason: str = "window_not_started",
) -> tuple[MetricValue, ...]:
    _text(instrument_id, "instrument_id")
    raw = _values(policy, summary, missing_reason)
    observed_ns = summary.observed_ts_ns if summary is not None else calculated_ts_ns
    received_ns = summary.received_ts_ns if summary is not None else calculated_ts_ns
    safe_calculated = max(calculated_ts_ns, received_ns)
    safe_published = max(published_ts_ns, safe_calculated)
    evidence_refs = summary.evidence_refs if summary is not None else (f"window:{missing_reason}",)
    session_id = summary.metric_session_id if summary is not None else None
    effective_ns = summary.effective_end_ns if summary is not None else calculated_ts_ns
    result = tuple(
        MetricValue(
            metric_id=metric_id,
            metric_version=1,
            parameter_version=parameter_version,
            instrument_id=instrument_id,
            session_id=session_id,
            value=value,
            unit=registry.get(metric_id, 1).unit,
            effective_ts_ns=effective_ns,
            observed_ts_ns=observed_ns,
            received_ts_ns=received_ns,
            calculated_ts_ns=safe_calculated,
            published_ts_ns=safe_published,
            health=health,
            fidelity=fidelity,
            source=source,
            evidence_refs=evidence_refs,
            missing_reasons=reasons,
            revision=revision,
        )
        for metric_id, (value, health, fidelity, reasons) in raw.items()
    )
    for value in result:
        registry.validate_value(value)
    return result


def analytical_window_value_signature(value: MetricValue) -> tuple[object, ...]:
    return (
        value.metric_id,
        value.session_id,
        value.value,
        value.health,
        value.fidelity,
        value.missing_reasons,
        value.effective_ts_ns,
    )


def _values(
    policy: AnalyticalWindowPolicy,
    summary: AnalyticalWindowSummary | None,
    missing_reason: str,
) -> dict[str, tuple[object | None, MetricHealth, MetricFidelity, tuple[str, ...]]]:
    if summary is None:
        return {
            metric_id: (
                None,
                MetricHealth.UNAVAILABLE,
                MetricFidelity.UNAVAILABLE,
                (missing_reason,),
            )
            for metric_id in policy.metric_ids
        }
    prefix = policy.metric_prefix
    common = (summary.health, summary.fidelity, summary.missing_reasons)
    values: dict[str, object | None] = {
        f"{prefix}.start_ns": summary.start_ns,
        f"{prefix}.end_ns": summary.end_ns,
        f"{prefix}.complete": summary.complete,
        f"{prefix}.high": summary.high,
        f"{prefix}.low": summary.low,
        f"{prefix}.range": summary.range,
        f"{prefix}.coverage_ratio": summary.coverage_ratio,
    }
    reasons: dict[str, tuple[str, ...]] = {}
    if policy.purpose == "opening_range":
        above = max(summary.latest_close - summary.high, Decimal(0))
        below = max(summary.low - summary.latest_close, Decimal(0))
        values.update(
            {
                f"{prefix}.open": summary.open,
                f"{prefix}.close": summary.close,
                f"{prefix}.volume": summary.volume,
                f"{prefix}.distance_above_high_points": above,
                f"{prefix}.distance_above_high_ratio": (
                    above / summary.high if summary.high != 0 else None
                ),
                f"{prefix}.distance_below_low_points": below,
                f"{prefix}.distance_below_low_ratio": (
                    below / summary.low if summary.low != 0 else None
                ),
            },
        )
        if summary.volume is None:
            reasons[f"{prefix}.volume"] = summary.volume_missing_reasons or (
                "volume_unavailable",
            )
    else:
        values.update(
            {
                f"{prefix}.open": summary.open,
                f"{prefix}.close": summary.close,
                f"{prefix}.simple_return": (
                    summary.close / summary.open - 1 if summary.open != 0 else None
                ),
                f"{prefix}.volume": summary.volume,
                f"{prefix}.bar_vwap_estimate": summary.bar_vwap_estimate,
                f"{prefix}.directional_efficiency": summary.directional_efficiency,
            },
        )
        if summary.volume is None:
            reason = next(
                (
                    item
                    for item in summary.missing_reasons
                    if item in {"volume_unsupported", "volume_partial", "zero_window_volume"}
                ),
                "volume_unavailable",
            )
            reasons[f"{prefix}.volume"] = (reason,)
            reasons[f"{prefix}.bar_vwap_estimate"] = (reason,)
        if summary.directional_efficiency is None:
            reasons[f"{prefix}.directional_efficiency"] = ("zero_close_path",)
    result = {}
    for metric_id in policy.metric_ids:
        value = values.get(metric_id)
        if value is None:
            result[metric_id] = (
                None,
                MetricHealth.UNSUPPORTED
                if reasons.get(metric_id) == ("volume_unsupported",)
                else MetricHealth.UNAVAILABLE,
                MetricFidelity.UNAVAILABLE,
                reasons.get(metric_id, ("value_unavailable",)),
            )
        else:
            result[metric_id] = (value, common[0], common[1], common[2])
    return result


def _volume_values(
    bars: tuple[CompletedBarInput, ...],
    price_basis: str,
    missing: list[str],
) -> tuple[Decimal | None, Decimal | None]:
    if any(bar.volume is None for bar in bars):
        missing.append(
            "volume_unsupported"
            if all("volume_unsupported" in bar.missing_reasons for bar in bars)
            else "volume_partial"
        )
        return None, None
    volume = sum((bar.volume or Decimal(0) for bar in bars), Decimal(0))
    if volume == 0:
        missing.append("zero_window_volume")
        return volume, None
    weighted = sum(
        (_bar_price(bar, price_basis) * (bar.volume or Decimal(0)) for bar in bars),
        Decimal(0),
    )
    return volume, weighted / volume


def _directional_efficiency(bars: tuple[CompletedBarInput, ...]) -> Decimal | None:
    if len(bars) < 2:
        return None
    denominator = sum(
        (
            abs(current.close - previous.close)
            for previous, current in zip(bars, bars[1:], strict=False)
        ),
        Decimal(0),
    )
    return abs(bars[-1].close - bars[0].close) / denominator if denominator != 0 else None


def _bar_price(bar: CompletedBarInput, basis: str) -> Decimal:
    if basis == "typical":
        return (bar.high + bar.low + bar.close) / Decimal(3)
    if basis == "ohlc4":
        return (bar.open + bar.high + bar.low + bar.close) / Decimal(4)
    return bar.close


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


def _value_kind(metric_id: str) -> MetricValueKind:
    if metric_id.endswith((".start_ns", ".end_ns")):
        return MetricValueKind.INTEGER
    if metric_id.endswith(".complete"):
        return MetricValueKind.BOOLEAN
    return MetricValueKind.NUMBER


def _unit(metric_id: str) -> str:
    if metric_id.endswith((".start_ns", ".end_ns")):
        return "unix_ns"
    if metric_id.endswith(".complete"):
        return "boolean"
    if metric_id.endswith(
        ("_ratio", ".simple_return", ".directional_efficiency", ".coverage_ratio"),
    ):
        return "ratio"
    if metric_id.endswith(".volume"):
        return "volume"
    return "price"


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
