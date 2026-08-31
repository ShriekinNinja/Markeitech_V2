from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pandas_market_calendars as market_calendars
from pandas import isna

MARKET_STATES = frozenset({"OPEN", "BREAK", "CLOSED"})
CORRECTION_STATUSES = frozenset(
    {"APPLIED", "NOT_APPLICABLE", "BASE_ALREADY_CONFORMS", "CONFLICT"},
)
NORMALIZATION_STATUSES = frozenset({"APPLIED"})
TERMINAL_ZERO_LENGTH_BREAK_NORMALIZATION_ID = (
    "terminal_zero_length_break_at_market_close.v1"
)


@dataclass(frozen=True, slots=True)
class PhaseDefinition:
    name: str
    timezone: str
    start_kind: str
    start_value: str
    start_day_offset: int
    end_kind: str
    end_value: str
    end_day_offset: int
    exchange_constraint: str


@dataclass(frozen=True, slots=True)
class CalendarSource:
    source_id: str
    title: str
    url: str
    retrieved_at_ns: int
    content_sha256: str | None
    retrieval_status: str


@dataclass(frozen=True, slots=True)
class StructuralCorrection:
    correction_id: str
    kind: str
    source_id: str
    product_roots: tuple[str, ...]
    effective_from_trade_date: date
    timezone: str
    expected_start: time
    expected_end: time


@dataclass(frozen=True, slots=True)
class CanonicalCalendarDefinition:
    calendar_id: str
    calendar_engine: str
    calendar_engine_version: str
    provider_calendar: str
    provider_calendar_class: str
    exchange_timezone: str
    schedule_columns: tuple[str, ...]
    definition_version: int
    effective_from_ns: int
    definition_digest: str
    schedule_version: str
    phases: tuple[PhaseDefinition, ...]
    corrections: tuple[StructuralCorrection, ...]
    sources: tuple[CalendarSource, ...]


@dataclass(frozen=True, slots=True)
class CalendarCorrectionOutcome:
    trade_date: date
    correction_id: str
    status: str
    source_id: str

    def __post_init__(self) -> None:
        if self.status not in CORRECTION_STATUSES:
            raise ValueError(f"unsupported calendar correction status: {self.status}")


@dataclass(frozen=True, slots=True)
class CalendarNormalizationOutcome:
    trade_date: date
    normalization_id: str
    status: str
    original_break_start_ns: int
    original_break_end_ns: int
    market_close_ns: int

    def __post_init__(self) -> None:
        if self.normalization_id != TERMINAL_ZERO_LENGTH_BREAK_NORMALIZATION_ID:
            raise ValueError("unsupported calendar normalization")
        if self.status not in NORMALIZATION_STATUSES:
            raise ValueError(f"unsupported calendar normalization status: {self.status}")
        if not (
            self.original_break_start_ns
            == self.original_break_end_ns
            == self.market_close_ns
        ):
            raise ValueError("terminal break normalization endpoints must equal market close")


@dataclass(frozen=True, slots=True)
class ExchangeSessionSegment:
    trade_date: date
    market_state: str
    start_ns: int
    end_ns: int

    def __post_init__(self) -> None:
        if self.market_state not in {"OPEN", "BREAK"}:
            raise ValueError("exchange segment must be OPEN or BREAK")
        if self.end_ns <= self.start_ns:
            raise ValueError("exchange segment end must be after start")


@dataclass(frozen=True, slots=True)
class SessionWindow:
    trade_date: date
    phase: str
    start_ns: int
    end_ns: int

    def __post_init__(self) -> None:
        if not self.phase:
            raise ValueError("phase must be non-empty")
        if self.end_ns <= self.start_ns:
            raise ValueError("session window end must be after start")


@dataclass(frozen=True, slots=True)
class CanonicalSessionSnapshot:
    """Canonical session state evaluated at a caller-owned observation cut.

    ``state_effective_from_ns`` is the exact admitted calendar boundary at which the
    returned state became authoritative. It is not the observation time.

    Attributes:
        calendar_id: Canonical calendar identity.
        schedule_version: Descriptive schedule version derived from the definition.
        definition_version: Positive canonical definition revision.
        definition_digest: Normalized canonical-definition SHA-256 digest.
        calendar_engine_version: Exact calendar-engine version used for evaluation.
        exchange_timezone: IANA timezone of the exchange calendar.
        trade_date: Exchange trade date associated with the state, when known.
        phase_memberships: Ordered active product-phase memberships.
        market_state: Canonical ``OPEN``, ``BREAK``, or ``CLOSED`` exchange state.
        segment_open_ns: Active semantic segment start as UTC Unix nanoseconds, when present.
        segment_close_ns: Active semantic segment end as UTC Unix nanoseconds, when present.
        next_transition_ns: Next admitted boundary as UTC Unix nanoseconds, when known.
        state_effective_from_ns: Exact admitted boundary which made this state authoritative.
    """

    calendar_id: str
    schedule_version: str
    definition_version: int
    definition_digest: str
    calendar_engine_version: str
    exchange_timezone: str
    trade_date: date | None
    phase_memberships: tuple[str, ...]
    market_state: str
    segment_open_ns: int | None
    segment_close_ns: int | None
    next_transition_ns: int | None
    state_effective_from_ns: int

    @property
    def is_open(self) -> bool:
        return self.market_state == "OPEN"

    @property
    def phase(self) -> str:
        if not self.phase_memberships:
            return "CLOSED" if self.market_state == "CLOSED" else self.market_state
        return "+".join(self.phase_memberships)

    @property
    def phase_open_ns(self) -> int | None:
        return self.segment_open_ns

    @property
    def phase_close_ns(self) -> int | None:
        return self.segment_close_ns


@dataclass(frozen=True, slots=True)
class CalendarProjection:
    """Bounded immutable calendar authority projected from one definition.

    Attributes:
        calendar_id: Canonical calendar identity.
        calendar_engine: Exact engine family used to build the projection.
        provider_calendar: Provider calendar selected inside the engine.
        schedule_version: Descriptive schedule version derived from the definition.
        definition_version: Positive canonical definition revision.
        definition_digest: Normalized canonical-definition SHA-256 digest.
        definition_effective_from_ns: UTC Unix nanosecond definition-activation boundary.
        calendar_engine_version: Exact calendar-engine version used for projection.
        exchange_timezone: IANA timezone of the exchange calendar.
        coverage_start_ns: Inclusive UTC Unix nanosecond coverage bound.
        coverage_end_ns: Exclusive UTC Unix nanosecond coverage bound.
        exchange_segments: Ordered admitted exchange-state segments.
        phase_windows: Ordered configured product-phase windows.
        correction_outcomes: Source-identified structural-correction outcomes.
        normalization_outcomes: Explicit admitted normalization outcomes.

    Raises:
        ValueError: If projection coverage is empty or negative.
    """

    calendar_id: str
    calendar_engine: str
    provider_calendar: str
    schedule_version: str
    definition_version: int
    definition_digest: str
    definition_effective_from_ns: int
    calendar_engine_version: str
    exchange_timezone: str
    coverage_start_ns: int
    coverage_end_ns: int
    exchange_segments: tuple[ExchangeSessionSegment, ...]
    phase_windows: tuple[SessionWindow, ...]
    correction_outcomes: tuple[CalendarCorrectionOutcome, ...]
    normalization_outcomes: tuple[CalendarNormalizationOutcome, ...]

    def __post_init__(self) -> None:
        if self.coverage_end_ns <= self.coverage_start_ns:
            raise ValueError("calendar projection coverage must be positive")


class CalendarProjectionUnavailable(ValueError):
    """Raised when a requested instant is outside projection coverage."""


class CalendarStateBoundaryUnavailable(ValueError):
    """Raised when a bounded projection cannot prove the state's effective boundary."""


@dataclass(frozen=True, slots=True)
class CalendarProjectionView:
    """Immutable consumer-side view; it never evaluates mcal or authors temporal meaning."""

    projection: CalendarProjection

    @property
    def definition_digest(self) -> str:
        return self.projection.definition_digest

    def evaluate(self, timestamp_ns: int) -> CanonicalSessionSnapshot:
        if not self.projection.coverage_start_ns <= timestamp_ns < self.projection.coverage_end_ns:
            raise CalendarProjectionUnavailable("timestamp is outside calendar projection coverage")
        active_exchange = next(
            (
                item
                for item in self.projection.exchange_segments
                if item.start_ns <= timestamp_ns < item.end_ns
            ),
            None,
        )
        active_phases = tuple(
            sorted(
                (
                    item
                    for item in self.projection.phase_windows
                    if item.start_ns <= timestamp_ns < item.end_ns
                ),
                key=lambda item: item.phase,
            ),
        )
        phases = tuple(item.phase for item in active_phases)
        boundaries = sorted(
            {
                boundary
                for item in (*self.projection.exchange_segments, *self.projection.phase_windows)
                for boundary in (item.start_ns, item.end_ns)
                if boundary > timestamp_ns
            },
        )
        future_window = next(
            (item for item in self.projection.phase_windows if item.start_ns > timestamp_ns),
            None,
        )
        admitted_boundaries = {
            boundary
            for item in (*self.projection.exchange_segments, *self.projection.phase_windows)
            for boundary in (item.start_ns, item.end_ns)
            if boundary <= timestamp_ns
        }
        if self.projection.definition_effective_from_ns <= timestamp_ns:
            admitted_boundaries.add(self.projection.definition_effective_from_ns)
        if not admitted_boundaries:
            raise CalendarStateBoundaryUnavailable(
                "calendar projection does not contain the state's effective boundary",
            )
        return CanonicalSessionSnapshot(
            calendar_id=self.projection.calendar_id,
            schedule_version=self.projection.schedule_version,
            definition_version=self.projection.definition_version,
            definition_digest=self.projection.definition_digest,
            calendar_engine_version=self.projection.calendar_engine_version,
            exchange_timezone=self.projection.exchange_timezone,
            trade_date=(
                active_exchange.trade_date
                if active_exchange is not None
                else _active_phase_trade_date(self.projection.phase_windows, timestamp_ns)
                or (future_window.trade_date if future_window is not None else None)
            ),
            phase_memberships=phases,
            market_state=active_exchange.market_state if active_exchange is not None else "CLOSED",
            segment_open_ns=(
                active_phases[0].start_ns
                if len(active_phases) == 1
                else active_exchange.start_ns
                if active_exchange is not None
                else None
            ),
            segment_close_ns=(
                active_phases[0].end_ns
                if len(active_phases) == 1
                else active_exchange.end_ns
                if active_exchange is not None
                else None
            ),
            next_transition_ns=boundaries[0] if boundaries else None,
            state_effective_from_ns=max(admitted_boundaries),
        )

    def windows(self, start: date, end: date) -> tuple[SessionWindow, ...]:
        if end < start:
            raise ValueError("end must not be before start")
        return tuple(
            item for item in self.projection.phase_windows if start <= item.trade_date <= end
        )


@dataclass(frozen=True, slots=True)
class CanonicalCalendar:
    """Pure source-composed evaluator. SessionStateActor is its only runtime owner.

    Markeitech Metadata:
        architecture.component.id: component.canonical-calendar
        architecture.component.label: Canonical Calendar
        architecture.component.kind: engine
        architecture.component.boundary: boundary.intelligence
        architecture.component.responsibilities:
            - Evaluate one immutable versioned calendar definition from admitted mcal schedule
              facts and configured product phases.
            - Produce UTC exchange segments, phase windows, trade-date assignments, and bounded
              projections.
            - Record source-cited corrections and the exact admitted terminal-break normalization
              outcome.
    """

    definition: CanonicalCalendarDefinition
    _provider: Any = field(init=False, repr=False, compare=False)
    _exchange_timezone: ZoneInfo = field(init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.definition.calendar_engine != "pandas_market_calendars":
            raise ValueError("unsupported canonical calendar engine")
        if self.definition.calendar_engine_version != market_calendars.__version__:
            raise ValueError("canonical calendar engine version does not match runtime")
        provider = market_calendars.get_calendar(self.definition.provider_calendar)
        provider_class = f"{provider.__class__.__module__}.{provider.__class__.__qualname__}"
        if provider_class != self.definition.provider_calendar_class:
            raise ValueError("canonical provider calendar class does not match definition")
        if str(provider.tz) != self.definition.exchange_timezone:
            raise ValueError("canonical exchange timezone does not match provider calendar")
        if not set(self.definition.schedule_columns) <= set(provider.regular_market_times):
            raise ValueError("canonical schedule columns are unavailable from provider calendar")
        source_ids = {source.source_id for source in self.definition.sources}
        if any(item.source_id not in source_ids for item in self.definition.corrections):
            raise ValueError("calendar correction source is absent from definition")
        object.__setattr__(self, "_provider", provider)
        object.__setattr__(
            self,
            "_exchange_timezone",
            ZoneInfo(self.definition.exchange_timezone),
        )

    def evaluate(self, timestamp_ns: int) -> CanonicalSessionSnapshot:
        now = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, UTC)
        exchange_date = now.astimezone(self._exchange_timezone).date()
        projection = self.projection(
            exchange_date - timedelta(days=3),
            exchange_date + timedelta(days=3),
        )
        return CalendarProjectionView(projection).evaluate(timestamp_ns)

    def projection(self, start: date, end: date) -> CalendarProjection:
        if end < start:
            raise ValueError("end must not be before start")
        schedule = self._provider.schedule(
            start_date=start,
            end_date=end,
            tz="UTC",
            market_times=list(self.definition.schedule_columns),
        )
        exchange_segments: list[ExchangeSessionSegment] = []
        phase_windows: list[SessionWindow] = []
        outcomes: list[CalendarCorrectionOutcome] = []
        normalization_outcomes: list[CalendarNormalizationOutcome] = []
        for index, row in schedule.iterrows():
            trade_date = index.date()
            market_open = _row_datetime(row["market_open"])
            market_close = _row_datetime(row["market_close"])
            break_start, break_end = _row_break(row)
            break_start, break_end, row_outcomes = self._apply_corrections(
                trade_date,
                market_open,
                market_close,
                break_start,
                break_end,
            )
            outcomes.extend(row_outcomes)
            break_start, break_end, normalization_outcome = _normalize_break(
                trade_date,
                market_open,
                market_close,
                break_start,
                break_end,
            )
            if normalization_outcome is not None:
                normalization_outcomes.append(normalization_outcome)
            if break_start is not None and break_end is not None:
                exchange_segments.extend(
                    (
                        ExchangeSessionSegment(
                            trade_date,
                            "OPEN",
                            _to_ns(market_open),
                            _to_ns(break_start),
                        ),
                        ExchangeSessionSegment(
                            trade_date,
                            "BREAK",
                            _to_ns(break_start),
                            _to_ns(break_end),
                        ),
                        ExchangeSessionSegment(
                            trade_date,
                            "OPEN",
                            _to_ns(break_end),
                            _to_ns(market_close),
                        ),
                    ),
                )
            else:
                exchange_segments.append(
                    ExchangeSessionSegment(
                        trade_date,
                        "OPEN",
                        _to_ns(market_open),
                        _to_ns(market_close),
                    ),
                )
            for phase in self.definition.phases:
                window = self._phase_window(
                    phase,
                    trade_date,
                    row,
                    market_open,
                    market_close,
                )
                if window is not None:
                    phase_windows.append(window)
        coverage_start = datetime.combine(start - timedelta(days=2), time.min, UTC)
        coverage_end = datetime.combine(end + timedelta(days=2), time.min, UTC)
        definition = self.definition
        return CalendarProjection(
            calendar_id=definition.calendar_id,
            calendar_engine=definition.calendar_engine,
            provider_calendar=definition.provider_calendar,
            schedule_version=definition.schedule_version,
            definition_version=definition.definition_version,
            definition_digest=definition.definition_digest,
            definition_effective_from_ns=definition.effective_from_ns,
            calendar_engine_version=definition.calendar_engine_version,
            exchange_timezone=definition.exchange_timezone,
            coverage_start_ns=_to_ns(coverage_start),
            coverage_end_ns=_to_ns(coverage_end),
            exchange_segments=tuple(
                sorted(exchange_segments, key=lambda item: (item.start_ns, item.end_ns)),
            ),
            phase_windows=tuple(
                sorted(
                    phase_windows,
                    key=lambda item: (item.start_ns, item.end_ns, item.phase),
                ),
            ),
            correction_outcomes=tuple(
                sorted(outcomes, key=lambda item: (item.trade_date, item.correction_id)),
            ),
            normalization_outcomes=tuple(
                sorted(
                    normalization_outcomes,
                    key=lambda item: (item.trade_date, item.normalization_id),
                ),
            ),
        )

    def _apply_corrections(
        self,
        trade_date: date,
        market_open: datetime,
        market_close: datetime,
        break_start: datetime | None,
        break_end: datetime | None,
    ) -> tuple[
        datetime | None,
        datetime | None,
        tuple[CalendarCorrectionOutcome, ...],
    ]:
        outcomes: list[CalendarCorrectionOutcome] = []
        current_start, current_end = break_start, break_end
        for correction in self.definition.corrections:
            status = "NOT_APPLICABLE"
            if trade_date >= correction.effective_from_trade_date:
                timezone = ZoneInfo(correction.timezone)
                expected_start = datetime.combine(
                    trade_date,
                    correction.expected_start,
                    timezone,
                ).astimezone(UTC)
                expected_end = datetime.combine(
                    trade_date,
                    correction.expected_end,
                    timezone,
                ).astimezone(UTC)
                if market_close <= expected_start or market_open >= expected_end:
                    status = "NOT_APPLICABLE"
                elif current_start is None and current_end is None:
                    status = "BASE_ALREADY_CONFORMS"
                elif current_start == expected_start and current_end == expected_end:
                    current_start = None
                    current_end = None
                    status = "APPLIED"
                else:
                    status = "CONFLICT"
            outcomes.append(
                CalendarCorrectionOutcome(
                    trade_date=trade_date,
                    correction_id=correction.correction_id,
                    status=status,
                    source_id=correction.source_id,
                ),
            )
            if status == "CONFLICT":
                raise ValueError(
                    "calendar correction conflicts with provider schedule: "
                    f"{correction.correction_id}/{trade_date.isoformat()}",
                )
        return current_start, current_end, tuple(outcomes)

    def _phase_window(
        self,
        phase: PhaseDefinition,
        trade_date: date,
        row: Any,
        market_open: datetime,
        market_close: datetime,
    ) -> SessionWindow | None:
        start = self._phase_boundary(
            phase.start_kind,
            phase.start_value,
            phase.start_day_offset,
            phase.timezone,
            trade_date,
            row,
        )
        end = self._phase_boundary(
            phase.end_kind,
            phase.end_value,
            phase.end_day_offset,
            phase.timezone,
            trade_date,
            row,
        )
        if phase.exchange_constraint == "clip":
            start = max(start, market_open)
            end = min(end, market_close)
        elif phase.exchange_constraint == "omit_if_exchange_closes_before_start":
            if market_close < start:
                return None
        elif phase.exchange_constraint != "none":
            raise ValueError("unsupported phase exchange constraint")
        if end <= start:
            return None
        return SessionWindow(trade_date, phase.name, _to_ns(start), _to_ns(end))

    def _phase_boundary(
        self,
        kind: str,
        value: str,
        day_offset: int,
        timezone_name: str,
        trade_date: date,
        row: Any,
    ) -> datetime:
        if kind == "schedule_boundary":
            boundary = _row_datetime(row[value])
            return boundary + timedelta(days=day_offset)
        if kind != "local_time":
            raise ValueError("unsupported phase boundary kind")
        timezone = (
            self._exchange_timezone if timezone_name == "provider" else ZoneInfo(timezone_name)
        )
        return datetime.combine(
            trade_date + timedelta(days=day_offset),
            time.fromisoformat(value),
            timezone,
        ).astimezone(UTC)


def canonical_definition_from_config(value: dict[str, object]) -> CanonicalCalendarDefinition:
    return CanonicalCalendarDefinition(
        calendar_id=str(value["calendar_id"]),
        calendar_engine=str(value["calendar_engine"]),
        calendar_engine_version=str(value["calendar_engine_version"]),
        provider_calendar=str(value["provider_calendar"]),
        provider_calendar_class=str(value["provider_calendar_class"]),
        exchange_timezone=str(value["exchange_timezone"]),
        schedule_columns=tuple(str(item) for item in value["schedule_columns"]),  # type: ignore[union-attr]
        definition_version=int(value["definition_version"]),
        effective_from_ns=int(value["effective_from_ns"]),
        definition_digest=str(value["definition_digest"]),
        schedule_version=str(value["schedule_version"]),
        phases=tuple(
            PhaseDefinition(
                name=str(item["name"]),
                timezone=str(item["timezone"]),
                start_kind=str(item["start_kind"]),
                start_value=str(item["start_value"]),
                start_day_offset=int(item["start_day_offset"]),
                end_kind=str(item["end_kind"]),
                end_value=str(item["end_value"]),
                end_day_offset=int(item["end_day_offset"]),
                exchange_constraint=str(item["exchange_constraint"]),
            )
            for item in value["phases"]  # type: ignore[union-attr]
        ),
        corrections=tuple(
            StructuralCorrection(
                correction_id=str(item["correction_id"]),
                kind=str(item["kind"]),
                source_id=str(item["source_id"]),
                product_roots=tuple(str(root) for root in item["product_roots"]),
                effective_from_trade_date=date.fromisoformat(
                    str(item["effective_from_trade_date"]),
                ),
                timezone=str(item["timezone"]),
                expected_start=time.fromisoformat(str(item["expected_start"])),
                expected_end=time.fromisoformat(str(item["expected_end"])),
            )
            for item in value["corrections"]  # type: ignore[union-attr]
        ),
        sources=tuple(
            CalendarSource(
                source_id=str(item["source_id"]),
                title=str(item["title"]),
                url=str(item["url"]),
                retrieved_at_ns=int(item["retrieved_at_ns"]),
                content_sha256=(
                    None if item["content_sha256"] is None else str(item["content_sha256"])
                ),
                retrieval_status=str(item["retrieval_status"]),
            )
            for item in value["sources"]  # type: ignore[union-attr]
        ),
    )


def _active_phase_trade_date(
    windows: tuple[SessionWindow, ...],
    timestamp_ns: int,
) -> date | None:
    active = next(
        (item for item in windows if item.start_ns <= timestamp_ns < item.end_ns),
        None,
    )
    return active.trade_date if active is not None else None


def _row_break(row: Any) -> tuple[datetime | None, datetime | None]:
    start = row.get("break_start")
    end = row.get("break_end")
    start_missing = start is None or isna(start)
    end_missing = end is None or isna(end)
    if start_missing and end_missing:
        return None, None
    if start_missing != end_missing:
        raise ValueError("calendar break boundaries must both be present or absent")
    return _row_datetime(start), _row_datetime(end)


def _row_datetime(value: Any) -> datetime:
    resolved = value.to_pydatetime() if hasattr(value, "to_pydatetime") else value
    if not isinstance(resolved, datetime):
        raise ValueError("calendar schedule boundary must be a datetime")
    if resolved.tzinfo is None or resolved.utcoffset() is None:
        raise ValueError("calendar schedule boundary must be timezone-aware")
    return resolved.astimezone(UTC)


def _normalize_break(
    trade_date: date,
    market_open: datetime,
    market_close: datetime,
    break_start: datetime | None,
    break_end: datetime | None,
) -> tuple[
    datetime | None,
    datetime | None,
    CalendarNormalizationOutcome | None,
]:
    if market_close <= market_open:
        raise ValueError("calendar market close must be after market open")
    if break_start is None and break_end is None:
        return None, None, None
    if break_start is None or break_end is None:
        raise ValueError("calendar break boundaries must both be present or absent")
    if break_start == break_end == market_close:
        market_close_ns = _to_ns(market_close)
        return (
            None,
            None,
            CalendarNormalizationOutcome(
                trade_date=trade_date,
                normalization_id=TERMINAL_ZERO_LENGTH_BREAK_NORMALIZATION_ID,
                status="APPLIED",
                original_break_start_ns=market_close_ns,
                original_break_end_ns=market_close_ns,
                market_close_ns=market_close_ns,
            ),
        )
    if not market_open < break_start < break_end < market_close:
        raise ValueError("calendar break must be positive and strictly inside the market session")
    return break_start, break_end, None


def _to_ns(value: datetime) -> int:
    delta = value.astimezone(UTC) - datetime(1970, 1, 1, tzinfo=UTC)
    return (
        delta.days * 86_400 * 1_000_000_000
        + delta.seconds * 1_000_000_000
        + delta.microseconds * 1_000
    )
