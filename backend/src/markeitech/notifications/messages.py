from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from markeitech.analytics import AnalyticsTimeframe, MarketContextSnapshot
from markeitech.auction_pressure import (
    BarPressureProxySnapshot,
    SessionAuctionPressureSnapshot,
)
from markeitech.domain.market_data import ClassifiedTrade
from markeitech.markeitect_model import AggressionEpisode, AggressionOutcome
from markeitech.persistence import NotificationOutboxRecord
from markeitech.runtime.events import CommittedContextTransitionNotice
from markeitech.signals import (
    LocationEpisodeEventType,
    SignalEvaluationEvent,
    SignalLocationMatch,
)

SYSTEM_HEALTH_DESTINATION = "system-health"
MARKET_EVENTS_DESTINATION = "market-events"
ALERT_STREAM_DESTINATION = "alert-stream"
OPERATOR_FLOW_DESTINATION = "operator-flow"
_MAX_CONTENT = 2000


def build_health_notification(
    *,
    trader_id: str,
    event: str,
    detail: str | None = None,
    facts: Sequence[tuple[str, str]] = (),
    occurred_ts: datetime | None = None,
) -> NotificationOutboxRecord:
    now = datetime.now(UTC) if occurred_ts is None else occurred_ts
    status = event.upper()
    fields: list[dict[str, object]] = [
        {"name": "Runtime", "value": trader_id, "inline": True},
        *(
            {"name": name, "value": value, "inline": len(value) < 40}
            for name, value in facts
        ),
    ]
    if detail and not facts:
        fields.append({"name": "Details", "value": detail, "inline": False})
    return _record(
        destination=SYSTEM_HEALTH_DESTINATION,
        aggregate=trader_id,
        event_type=f"runtime.{event.lower()}",
        identity=f"{event}:{now.isoformat()}:{detail}:{facts}",
        content="",
        now=now,
        embeds=(
            {
                "title": status.replace("_", " ").title(),
                "color": _health_color(status),
                "fields": tuple(fields),
                "timestamp": now.isoformat(),
                "footer": {"text": "No Obstacles, Only Challenges"},
            },
        ),
    )


def build_market_context_notifications(
    snapshots: Sequence[MarketContextSnapshot],
    *,
    phase: str,
    active_instrument_id: str,
    pressure: SessionAuctionPressureSnapshot | None,
    bar_pressure: Mapping[str, BarPressureProxySnapshot] | None = None,
    occurred_ts: datetime | None = None,
) -> tuple[NotificationOutboxRecord, ...]:
    now = datetime.now(UTC) if occurred_ts is None else occurred_ts
    records: list[NotificationOutboxRecord] = []
    grouped: dict[str, list[MarketContextSnapshot]] = defaultdict(list)
    for snapshot in snapshots:
        grouped[snapshot.instrument_id].append(snapshot)
    for instrument, values in grouped.items():
        by_timeframe = {value.timeframe: value for value in values}
        reference = by_timeframe.get(AnalyticsTimeframe.ONE_MINUTE, values[-1])
        direction_reference = by_timeframe.get(AnalyticsTimeframe.FIVE_MINUTES)
        direction_score = 0 if direction_reference is None else direction_reference.direction_score
        direction_summary = (
            "Unavailable until 5m analytics are ready"
            if direction_reference is None
            else (
                f"**{_direction_name(direction_score)}**\n"
                f"Score: {direction_score:+d} of 2"
            )
        )
        is_active = instrument == active_instrument_id
        role = "Primary market" if is_active else "Watchlist market"
        fields: list[dict[str, object]] = [
            {
                "name": "5m directional bias",
                "value": direction_summary,
                "inline": True,
            },
            {
                "name": "Value location",
                "value": _profile_location_name(reference.profile_location.value),
                "inline": True,
            },
            {
                "name": "Price and value",
                "value": _price_and_value(reference),
                "inline": False,
            },
            {"name": "Trend map", "value": _trend_map(by_timeframe), "inline": False},
            {"name": "Key levels", "value": _key_levels(by_timeframe), "inline": False},
            {"name": "Auction structure", "value": _auction_structure(reference), "inline": False},
            {"name": "Fair value gaps", "value": _fair_value_gaps(by_timeframe), "inline": False},
        ]
        if pressure is not None and pressure.instrument_id == instrument:
            fields.append(
                {
                    "name": "Order flow",
                    "value": _order_flow(pressure),
                    "inline": False,
                }
            )
        proxy = None if bar_pressure is None else bar_pressure.get(instrument)
        if proxy is not None:
            fields.append(
                {
                    "name": "1m Bar Pressure Proxy",
                    "value": _bar_pressure(proxy),
                    "inline": False,
                }
            )
        identity_body = "|".join(value.model_dump_json() for value in values)
        content = f"**{_instrument_name(instrument)} market brief**"
        records.append(
            _record(
                destination=MARKET_EVENTS_DESTINATION,
                aggregate=instrument,
                event_type="market.context.report",
                identity=f"{instrument}:{phase}:{now.isoformat()}:{identity_body}",
                content=content,
                now=now,
                embeds=(
                    {
                        "title": f"{_instrument_name(instrument)} — Market Brief",
                        "description": f"{role} • {phase.title()} update",
                        "color": _direction_color(direction_score),
                        "fields": tuple(fields),
                        "timestamp": now.isoformat(),
                        "footer": {
                            "text": (
                                f"{instrument} • {reference.input_fidelity.value.title()} data • "
                                "Decision support"
                            )
                        },
                    },
                ),
            )
        )
    return tuple(records)


class DirectionalBiasNotifier:
    def __init__(self) -> None:
        self._scores: dict[str, int] = {}

    def observe(
        self,
        snapshots: Sequence[MarketContextSnapshot],
    ) -> tuple[NotificationOutboxRecord, ...]:
        grouped: dict[str, list[MarketContextSnapshot]] = defaultdict(list)
        for snapshot in snapshots:
            grouped[snapshot.instrument_id].append(snapshot)
        records: list[NotificationOutboxRecord] = []
        for instrument_id, values in grouped.items():
            by_timeframe = {value.timeframe: value for value in values}
            reference = by_timeframe.get(AnalyticsTimeframe.FIVE_MINUTES)
            if reference is None:
                continue
            price_reference = by_timeframe.get(AnalyticsTimeframe.ONE_MINUTE, reference)
            previous = self._scores.get(instrument_id)
            self._scores[instrument_id] = reference.direction_score
            if previous is None or previous == reference.direction_score:
                continue
            records.append(
                _record(
                    destination=ALERT_STREAM_DESTINATION,
                    aggregate=instrument_id,
                    event_type="market.directional_bias.changed",
                    identity=(
                        f"{instrument_id}:{reference.as_of.isoformat()}:"
                        f"{previous}:{reference.direction_score}"
                    ),
                    content="",
                    now=reference.as_of,
                    mention_here=True,
                    embeds=(
                        {
                            "title": (
                                f"{_instrument_name(instrument_id)} — "
                                "Directional Bias Changed"
                            ),
                            "description": (
                                f"{_direction_name(previous)} → "
                                f"**{_direction_name(reference.direction_score)}**"
                            ),
                            "color": _direction_color(reference.direction_score),
                            "fields": (
                                {
                                    "name": "Trend map",
                                    "value": _trend_map(by_timeframe),
                                    "inline": False,
                                },
                                {
                                    "name": "Value location",
                                    "value": _profile_location_name(
                                        reference.profile_location.value
                                    ),
                                    "inline": True,
                                },
                                {
                                    "name": "Last price",
                                    "value": _price(price_reference.close),
                                    "inline": True,
                                },
                            ),
                            "timestamp": reference.as_of.isoformat(),
                            "footer": {"text": "Context change • Decision support"},
                        },
                    ),
                )
            )
        return tuple(records)


def build_context_transition_notification(
    event: CommittedContextTransitionNotice,
    *,
    aligned_context: Sequence[tuple[str, str]] = (),
) -> NotificationOutboxRecord:
    kind = event.transition_kind.replace("_", " ").title()
    fields: list[dict[str, object]] = [
        {
            "name": "Evidence fidelity",
            "value": (
                f"{event.previous_input_fidelity.title()} → "
                f"{event.current_input_fidelity.title()}"
            ),
            "inline": True,
        },
        {
            "name": "Commit sequence",
            "value": str(event.commit_sequence),
            "inline": True,
        },
    ]
    if aligned_context:
        fields.append(
            {
                "name": "Higher-timeframe value context",
                "value": "  •  ".join(
                    f"**{_timeframe_label(timeframe)}:** {value}"
                    for timeframe, value in aligned_context
                ),
                "inline": False,
            }
        )
    return _record(
        destination=ALERT_STREAM_DESTINATION,
        aggregate=event.instrument_id or event.aggregate_id,
        event_type=f"market.context.{event.transition_kind}",
        identity=event.dedupe_key,
        content="",
        now=event.occurred_ts,
        mention_here=True,
        embeds=(
            {
                "title": f"{_instrument_name(event.instrument_id or '')} — {kind}",
                "description": (
                    f"**{_timeframe_label(event.timeframe)}**: "
                    f"{event.previous_value.replace('_', ' ').title()} → "
                    f"**{event.current_value.replace('_', ' ').title()}**"
                ),
                "color": _context_transition_color(event),
                "fields": tuple(fields),
                "timestamp": event.occurred_ts.isoformat(),
                "footer": {"text": "Durable context transition • Decision support"},
            },
        ),
    )


def build_operator_flow_notification(
    pressure: SessionAuctionPressureSnapshot,
    *,
    role: str,
    previous_cvd: Decimal | None = None,
    occurred_ts: datetime | None = None,
) -> NotificationOutboxRecord:
    now = datetime.now(UTC) if occurred_ts is None else occurred_ts
    delta_ratio = (
        "Unavailable" if pressure.delta_ratio is None else f"{pressure.delta_ratio:+.1%}"
    )
    role_name = "Active market" if role.upper() == "ACTIVE" else "Order-flow cohort"
    cvd_change = _percentage_change(pressure.cvd, previous_cvd)
    return _record(
        destination=OPERATOR_FLOW_DESTINATION,
        aggregate=pressure.instrument_id,
        event_type="market.order_flow.summary",
        identity=f"{role}:{pressure.model_dump_json()}",
        content="",
        now=now,
        embeds=(
            {
                "title": f"{_instrument_name(pressure.instrument_id)} — Order Flow",
                "description": f"{role_name} • Product-session cumulative flow",
                "color": _flow_color(pressure.delta),
                "fields": (
                    {
                        "name": "Aggressive volume",
                        "value": (
                            f"Buy: **{pressure.buy_volume:,.0f}**\n"
                            f"Sell: **{pressure.sell_volume:,.0f}**"
                        ),
                        "inline": True,
                    },
                    {
                        "name": "Delta",
                        "value": (
                            f"Session: **{pressure.delta:+,.0f}**\n"
                            f"Ratio: **{delta_ratio}**"
                        ),
                        "inline": True,
                    },
                    {
                        "name": "CVD",
                        "value": f"**{pressure.cvd:+,.0f}** ({cvd_change})",
                        "inline": True,
                    },
                    {
                        "name": "Classification quality",
                        "value": (
                            f"Coverage: **{pressure.classified_volume_ratio:.1%}**  •  "
                            f"Fidelity: **{pressure.fidelity.value.title()}**\n"
                            f"Trades: {pressure.classified_trade_count:,} classified / "
                            f"{pressure.trade_count:,} total  •  "
                            f"Unknown volume: {pressure.unknown_volume:,.0f}"
                        ),
                        "inline": False,
                    },
                ),
                "timestamp": pressure.as_of.isoformat(),
                "footer": {
                    "text": (
                        f"{pressure.instrument_id} • IB trade/quote classification • "
                        "Observation only"
                    )
                },
            },
        ),
    )


def build_large_trade_notification(
    trade: ClassifiedTrade,
    *,
    threshold: Decimal,
    role: str,
    occurred_ts: datetime | None = None,
) -> NotificationOutboxRecord:
    now = datetime.now(UTC) if occurred_ts is None else occurred_ts
    side = trade.side.value.upper()
    role_name = "Active" if role.upper() == "ACTIVE" else "Cohort"
    return _record(
        destination=OPERATOR_FLOW_DESTINATION,
        aggregate=trade.instrument_id,
        event_type="market.order_flow.large_trade",
        identity=f"{trade.trade.dedupe_key}:{threshold}:{role}",
        content="",
        now=now,
        mention_here=True,
        embeds=(
            {
                "title": f"{_instrument_name(trade.instrument_id)} — Large {side.title()}",
                "description": "A classified print or rapid same-side burst met the threshold.",
                "color": 0x2ECC71 if side == "BUY" else 0xE74C3C,
                "fields": (
                    {
                        "name": "Trade",
                        "value": (
                            f"Price: **{_price(trade.trade.price)}**\n"
                            f"Size: **{trade.trade.size:,.0f} contracts**"
                        ),
                        "inline": True,
                    },
                    {
                        "name": "Threshold",
                        "value": f"≥ {threshold:,.0f} contracts",
                        "inline": True,
                    },
                    {
                        "name": "Classification",
                        "value": trade.classification_reason.replace("_", " ").title(),
                        "inline": True,
                    },
                    {
                        "name": "Instrument role",
                        "value": role_name,
                        "inline": True,
                    },
                ),
                "timestamp": trade.event_ts.isoformat(),
                "footer": {
                    "text": (
                        f"{trade.instrument_id} • Inferred from IB trade/quote data • "
                        "Observation only"
                    )
                },
            },
        ),
    )


def build_aggression_episode_notification(
    episode: AggressionEpisode,
    *,
    role: str,
    occurred_ts: datetime | None = None,
) -> NotificationOutboxRecord:
    now = datetime.now(UTC) if occurred_ts is None else occurred_ts
    outcome = episode.outcome.value.replace("_", " ").title()
    location = (
        "No nearby mapped location"
        if episode.location_label is None
        else f"{_location_label(episode.location_label)}: "
        f"{_price(episode.location_price)}"
    )
    return _record(
        destination=OPERATOR_FLOW_DESTINATION,
        aggregate=episode.instrument_id,
        event_type=f"markeitect.aggression.{episode.outcome.value}",
        identity=f"{episode.episode_id}:{episode.outcome.value}",
        content="",
        now=now,
        mention_here=True,
        embeds=(
            {
                "title": (
                    f"{_instrument_name(episode.instrument_id)} — "
                    f"{outcome} {episode.side.value.title()} Aggression"
                ),
                "description": "Observed effort and subsequent price/CVD response.",
                "color": _aggression_episode_color(episode),
                "fields": (
                    {
                        "name": "Aggression",
                        "value": (
                            f"Anchor: **{_price(episode.anchor_price)}**\n"
                            f"Size: **{episode.observed_size:,.0f}** across "
                            f"**{episode.print_count}** print(s)"
                        ),
                        "inline": True,
                    },
                    {
                        "name": "Observed response",
                        "value": (
                            f"Last: **{_price(episode.latest_price)}**\n"
                            f"CVD change: **{episode.cvd_change:+,.0f}**"
                        ),
                        "inline": True,
                    },
                    {
                        "name": "Excursion",
                        "value": (
                            f"Favorable: **{episode.max_favorable_excursion:,.2f}**\n"
                            f"Adverse: **{episode.max_adverse_excursion:,.2f}**"
                        ),
                        "inline": True,
                    },
                    {"name": "Nearest location", "value": location, "inline": False},
                    {
                        "name": "Evidence",
                        "value": " • ".join(
                            reason.replace("_", " ").title()
                            for reason in episode.reason_codes
                        ),
                        "inline": False,
                    },
                ),
                "timestamp": episode.as_of.isoformat(),
                "footer": {
                    "text": (
                        f"{role.title()} • {episode.source.upper()} inferred flow • "
                        "Observation, not a signal"
                    )
                },
            },
        ),
    )


def build_location_narrative_notification(
    event: SignalEvaluationEvent,
    *,
    role: str,
) -> NotificationOutboxRecord | None:
    narrative = {
        LocationEpisodeEventType.ENTERED: "TOUCHED",
        LocationEpisodeEventType.ACTIVE: "ENGAGED",
        LocationEpisodeEventType.FAVORABLE_DEPARTURE: "DEPARTURE PENDING",
        LocationEpisodeEventType.REJECTED: "REJECTION CONFIRMED",
        LocationEpisodeEventType.DEPARTURE_UNRESOLVED: "HOLDING",
        LocationEpisodeEventType.EXIT_PENDING: "ACCEPTANCE PENDING",
        LocationEpisodeEventType.EXITED: "ACCEPTED THROUGH",
        LocationEpisodeEventType.REPLACED: "ROTATED",
    }.get(event.episode_event)
    if narrative is None or not event.location_matches:
        return None
    direction = (
        "Unresolved"
        if event.signal_direction is None
        else event.signal_direction.value.title()
    )
    primary = event.location_matches[0].zone
    location_name = (
        f"{primary.timeframe.value} "
        f"{primary.zone_kind.value.replace('_', ' ').title()}"
    )
    detail = _narrative_explanation(event, location_name)
    fields: list[dict[str, object]] = [
        {"name": "Direction", "value": direction, "inline": True},
        {"name": "Instrument role", "value": role.title(), "inline": True},
        {"name": "Observed price", "value": _price(event.observed_price), "inline": True},
        {
            "name": "Location",
            "value": _signal_locations(event.location_matches),
            "inline": False,
        },
    ]
    if event.location_cluster is not None:
        cluster = event.location_cluster
        fields.append(
            {
                "name": "Location quality",
                "value": (
                    f"Sources: **{cluster.distinct_source_count}**  •  "
                    f"Timeframes: **{cluster.distinct_timeframe_count}**  •  "
                    f"Exact touches: **{cluster.exact_touch_count}**\n"
                    f"Reported matches: {cluster.reported_match_count}  •  "
                    "Inferred/partial matches: "
                    f"{cluster.inferred_or_partial_match_count}  •  "
                    f"Mean distance: {cluster.mean_normalized_distance:.0%} of tolerance"
                ),
                "inline": False,
            }
        )
    fields.append(
        {
            "name": "Evidence",
            "value": _signal_evidence_summary(event),
            "inline": False,
        }
    )
    if event.reason_codes:
        fields.append(
            {
                "name": "Reason",
                "value": _human_reasons(event.reason_codes),
                "inline": False,
            }
        )
    return _record(
        destination=ALERT_STREAM_DESTINATION,
        aggregate=f"{event.definition_id}:{event.instrument_id}",
        event_type=f"location.{event.episode_event.value}",
        identity=(
            f"{event.definition_id}:{event.instrument_id}:"
            f"{event.episode_event.value}:{event.evaluation_ts.isoformat()}"
        ),
        content="",
        now=event.evaluation_ts,
        embeds=(
            {
                "title": (
                    f"{_instrument_name(event.instrument_id)} — "
                    f"{narrative.title()} {location_name}"
                ),
                "description": detail,
                "color": _narrative_color(event),
                "fields": tuple(fields),
                "timestamp": event.evaluation_ts.isoformat(),
                "footer": {
                    "text": (
                        f"{event.definition_id.replace('_', ' ').title()} • "
                        "Decision support, not execution"
                    )
                },
            },
        ),
    )


class ApproachingLocationNotifier:
    """Presentation-only proximity alert; it never changes signal qualification."""

    def __init__(self, *, atr_fraction: Decimal = Decimal("0.25")) -> None:
        self._atr_fraction = atr_fraction
        self._active_levels: dict[str, tuple[Decimal, ...]] = {}
        self._snapshots: dict[
            str,
            dict[AnalyticsTimeframe, MarketContextSnapshot],
        ] = defaultdict(dict)

    def observe(
        self,
        snapshot: MarketContextSnapshot,
        *,
        notify: bool = True,
    ) -> NotificationOutboxRecord | None:
        values = self._snapshots[snapshot.instrument_id]
        values[snapshot.timeframe] = snapshot
        if not notify or snapshot.timeframe != AnalyticsTimeframe.ONE_MINUTE:
            return None
        reference = values.get(AnalyticsTimeframe.ONE_MINUTE)
        if reference is None or not reference.atr_14:
            return None
        candidates = _approaching_candidates(values)
        if not candidates:
            self._active_levels.pop(snapshot.instrument_id, None)
            return None
        threshold = reference.atr_14 * self._atr_fraction
        active_levels = self._active_levels.get(snapshot.instrument_id)
        if active_levels is not None:
            active_distance = min(abs(reference.close - price) for price in active_levels)
            if active_distance <= threshold * 2:
                return None
            self._active_levels.pop(snapshot.instrument_id, None)
        nearby = tuple(
            sorted(
                (
                    candidate
                    for candidate in candidates
                    if abs(reference.close - candidate[1]) <= threshold
                ),
                key=lambda item: (item[1], item[0]),
            )
        )
        if not nearby:
            return None
        label, level_price = min(nearby, key=lambda item: abs(reference.close - item[1]))
        distance = abs(reference.close - level_price)
        key = "|".join(f"{item_label}:{price}" for item_label, price in nearby)
        self._active_levels[snapshot.instrument_id] = tuple(price for _, price in nearby)
        location_names = tuple(dict.fromkeys(_location_label(item[0]) for item in nearby))
        location_name = " + ".join(location_names[:3])
        if len(location_names) > 3:
            location_name += f" + {len(location_names) - 3} more"
        level_summary = "\n".join(
            f"**{_location_label(item_label)}:** {_price(price)}"
            for item_label, price in nearby[:6]
        )
        direction_reference = values.get(AnalyticsTimeframe.FIVE_MINUTES)
        direction_summary = (
            "5m analytics unavailable"
            if direction_reference is None
            else (
                f"{_direction_name(direction_reference.direction_score)} "
                f"({direction_reference.direction_score:+d})"
            )
        )
        return _record(
            destination=ALERT_STREAM_DESTINATION,
            aggregate=snapshot.instrument_id,
            event_type="location.approaching",
            identity=f"{snapshot.instrument_id}:{key}:{snapshot.as_of.isoformat()}",
            content="",
            now=reference.as_of,
            mention_here=True,
            embeds=(
                {
                    "title": (
                        f"{_instrument_name(snapshot.instrument_id)} — "
                        f"Approaching {location_name}"
                    ),
                    "description": "Price is nearing a meaningful market location.",
                    "color": _location_color(label),
                    "fields": (
                        {"name": "Last price", "value": _price(reference.close), "inline": True},
                        {"name": "Nearest", "value": _price(level_price), "inline": True},
                        {"name": "Distance", "value": _price(distance), "inline": True},
                        {
                            "name": "Location confluence",
                            "value": level_summary,
                            "inline": False,
                        },
                        {
                            "name": "5m directional context",
                            "value": direction_summary,
                            "inline": False,
                        },
                    ),
                    "timestamp": reference.as_of.isoformat(),
                    "footer": {
                        "text": "Proximity threshold: 0.25 ATR • Warning only, not an entry"
                    },
                },
            ),
        )


def _percentage_change(current: Decimal, previous: Decimal | None) -> str:
    if previous is None or previous == 0:
        return "n/a"
    return f"{(current - previous) / abs(previous):+.1%}"


class LocationNarrativeNotifier:
    def __init__(self) -> None:
        self._last_narrative: dict[tuple[str, str], LocationEpisodeEventType] = {}

    def observe(
        self,
        event: SignalEvaluationEvent,
        *,
        role: str,
    ) -> NotificationOutboxRecord | None:
        if event.episode_event is None:
            return None
        key = (event.definition_id, event.instrument_id)
        repeated = self._last_narrative.get(key) == event.episode_event
        self._last_narrative[key] = event.episode_event
        if repeated and event.episode_event in {
            LocationEpisodeEventType.ACTIVE,
            LocationEpisodeEventType.DEPARTURE_UNRESOLVED,
            LocationEpisodeEventType.REJECTED,
            LocationEpisodeEventType.EXIT_PENDING,
        }:
            return None
        return build_location_narrative_notification(event, role=role)


def _record(
    *,
    destination: str,
    aggregate: str,
    event_type: str,
    identity: str,
    content: str,
    now: datetime,
    embeds: tuple[dict[str, object], ...] = (),
    mention_here: bool = False,
) -> NotificationOutboxRecord:
    digest = hashlib.sha256(identity.encode()).hexdigest()
    outbox_id = uuid5(NAMESPACE_URL, f"markeitech:discord:{destination}:{digest}")
    notification_title = (
        str(embeds[0].get("title", "")) if mention_here and embeds else ""
    )
    message_content = "\n".join(
        value
        for value in (
            f"**{notification_title}**" if notification_title else "",
            "@here" if mention_here else "",
            content,
        )
        if value
    )
    return NotificationOutboxRecord(
        outbox_id=outbox_id,
        topic="discord",
        destination_key=destination,
        aggregate_key=aggregate,
        event_type=event_type,
        event_schema_version="1.0",
        payload={
            **(
                {"content": message_content[:_MAX_CONTENT]}
                if message_content
                else {}
            ),
            "allowed_mentions": {"parse": ["everyone"] if mention_here else []},
            **({"embeds": _json_native_embeds(embeds)} if embeds else {}),
        },
        dedupe_key=f"discord:{destination}:{digest}",
        available_ts=now,
        created_ts=now,
        updated_ts=now,
    )


def _health_color(status: str) -> int:
    if "FAILED" in status or "CRITICAL" in status:
        return 0xE74C3C
    if "DEGRADED" in status or "BLOCKED" in status or "STALE" in status:
        return 0xF39C12
    if "READY" in status or "HEALTHY" in status:
        return 0x2ECC71
    if "STOPPED" in status:
        return 0x95A5A6
    return 0x3498DB


def _direction_color(score: int) -> int:
    if score > 0:
        return 0x2ECC71
    if score < 0:
        return 0xE74C3C
    return 0xFFFFFF


def _context_transition_color(event: CommittedContextTransitionNotice) -> int:
    value = event.current_value.lower()
    if value in {"bullish", "above"}:
        return 0x2ECC71
    if value in {"bearish", "below"}:
        return 0xE74C3C
    return 0xF1C40F


def _location_color(label: str) -> int:
    if any(token in label for token in ("support", "low", "val")):
        return 0x2ECC71
    if any(token in label for token in ("resistance", "high", "vah")):
        return 0xE74C3C
    return 0xF1C40F


def _flow_color(delta: Decimal) -> int:
    if delta > 0:
        return 0x2ECC71
    if delta < 0:
        return 0xE74C3C
    return 0xFFFFFF


def _aggression_episode_color(episode: AggressionEpisode) -> int:
    if episode.outcome == AggressionOutcome.PENDING:
        return 0xF1C40F
    if episode.outcome in {AggressionOutcome.ABSORBED, AggressionOutcome.UNRESOLVED}:
        return 0xFFFFFF
    bullish = (
        episode.side.value == "buy"
        if episode.outcome == AggressionOutcome.WITH_FLOW
        else episode.side.value == "sell"
    )
    return 0x2ECC71 if bullish else 0xE74C3C


def _direction_name(score: int) -> str:
    return {
        2: "Strong bullish alignment",
        1: "Bullish lean",
        0: "Balanced / mixed",
        -1: "Bearish lean",
        -2: "Strong bearish alignment",
    }[score]


def _instrument_name(instrument_id: str) -> str:
    if instrument_id.startswith("NQ"):
        return "Nasdaq 100 Futures"
    if instrument_id.startswith("ES"):
        return "S&P 500 Futures"
    return instrument_id.split(".")[0]


def _profile_location_name(value: str) -> str:
    return value.replace("_", " ").title()


def _timeframe_label(value: str) -> str:
    return {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "1d": "Daily",
    }.get(value, value)


def _location_label(value: str) -> str:
    label = value.replace("_", " ").title()
    for rendered, preferred in (
        ("1M", "1m"),
        ("5M", "5m"),
        ("15M", "15m"),
        ("30M", "30m"),
        ("1H", "1h"),
    ):
        label = label.replace(rendered, preferred)
    return label


def _price(value: Decimal | None) -> str:
    return "Unavailable" if value is None else f"{value:,.2f}"


def _approaching_candidates(
    values: Mapping[AnalyticsTimeframe, MarketContextSnapshot],
) -> tuple[tuple[str, Decimal], ...]:
    reference = values.get(AnalyticsTimeframe.ONE_MINUTE)
    if reference is None:
        return ()
    candidates: list[tuple[str, Decimal]] = []
    structural_timeframes = (
        AnalyticsTimeframe.FIFTEEN_MINUTES,
        AnalyticsTimeframe.THIRTY_MINUTES,
        AnalyticsTimeframe.ONE_HOUR,
        AnalyticsTimeframe.DAILY,
    )
    for timeframe in structural_timeframes:
        snapshot = values.get(timeframe)
        if snapshot is None:
            continue
        timeframe_label = timeframe.value
        for level in (snapshot.nearest_support, snapshot.nearest_resistance):
            if level is not None:
                candidates.append(
                    (f"{timeframe_label}_{level.kind.value}", level.price)
                )
        for gap in snapshot.fair_value_gaps:
            candidates.extend(
                (
                    (f"{timeframe_label}_{gap.direction.value}_fvg_lower", gap.lower),
                    (f"{timeframe_label}_{gap.direction.value}_fvg_upper", gap.upper),
                )
            )
    if reference.session_vwap is not None:
        candidates.append(("session_vwap", reference.session_vwap))
    for label, profile in (
        ("current", reference.volume_profile),
        ("prior", reference.prior_volume_profile),
        ("london", reference.london_volume_profile),
        ("new_york", reference.new_york_volume_profile),
    ):
        if profile is None:
            continue
        candidates.extend(
            (
                (f"{label}_val", profile.value_area_low),
                (f"{label}_poc", profile.poc),
                (f"{label}_vah", profile.value_area_high),
            )
        )
    for composite in reference.composite_volume_profiles:
        profile = composite.profile
        label = f"composite_{composite.session_count}s"
        candidates.extend(
            (
                (f"{label}_val", profile.value_area_low),
                (f"{label}_poc", profile.poc),
                (f"{label}_vah", profile.value_area_high),
            )
        )
    for label, value in (
        ("prior_session_low", reference.prior_session_low),
        ("prior_session_high", reference.prior_session_high),
    ):
        if value is not None:
            candidates.append((label, value))
    for label, range_value in (
        ("london", reference.london_range),
        ("new_york", reference.new_york_range),
        ("london_or15", reference.london_opening_range_15),
        ("london_or30", reference.london_opening_range_30),
        ("new_york_or15", reference.new_york_opening_range_15),
        ("new_york_or30", reference.new_york_opening_range_30),
    ):
        if range_value is not None:
            candidates.extend(
                ((f"{label}_low", range_value.low), (f"{label}_high", range_value.high))
            )
    return tuple(candidates)


def _price_and_value(snapshot: MarketContextSnapshot) -> str:
    position = snapshot.vwap_position.value.replace("_", " ").title()
    return (
        f"Last: **{_price(snapshot.close)}**\n"
        f"VWAP: {_price(snapshot.session_vwap)} ({position})\n"
        f"Session: {_price(snapshot.session_low)} – {_price(snapshot.session_high)} "
        f"({snapshot.session_range_position:.0%} of range)"
    )


def _trend_map(values: dict[AnalyticsTimeframe, MarketContextSnapshot]) -> str:
    labels = {
        AnalyticsTimeframe.DAILY: "Daily",
        AnalyticsTimeframe.ONE_HOUR: "1 Hour",
        AnalyticsTimeframe.THIRTY_MINUTES: "30 Minute",
        AnalyticsTimeframe.FIFTEEN_MINUTES: "15 Minute",
        AnalyticsTimeframe.FIVE_MINUTES: "5 Minute",
    }
    return "  •  ".join(
        f"**{label}:** {values[timeframe].trend.value.replace('_', ' ').title()}"
        for timeframe, label in labels.items()
        if timeframe in values
    ) or "No trend data available"


def _key_levels(values: dict[AnalyticsTimeframe, MarketContextSnapshot]) -> str:
    labels = {
        AnalyticsTimeframe.DAILY: "Daily",
        AnalyticsTimeframe.ONE_HOUR: "1 Hour",
        AnalyticsTimeframe.FIFTEEN_MINUTES: "15 Minute",
        AnalyticsTimeframe.FIVE_MINUTES: "5 Minute",
    }
    rows = []
    for timeframe, label in labels.items():
        snapshot = values.get(timeframe)
        if snapshot is None:
            continue
        support = None if snapshot.nearest_support is None else snapshot.nearest_support.price
        resistance = (
            None if snapshot.nearest_resistance is None else snapshot.nearest_resistance.price
        )
        if support is not None or resistance is not None:
            rows.append(
                f"**{label}:** Support {_price(support)}  •  Resistance {_price(resistance)}"
            )
    return "\n".join(rows) or "No nearby structural levels"


def _auction_structure(snapshot: MarketContextSnapshot) -> str:
    rows = []
    if snapshot.volume_profile is not None:
        profile = snapshot.volume_profile
        rows.append(
            f"**Current value:** {_price(profile.value_area_low)} – "
            f"{_price(profile.value_area_high)}  •  POC {_price(profile.poc)}"
        )
    if snapshot.prior_volume_profile is not None:
        profile = snapshot.prior_volume_profile
        rows.append(
            f"**Prior value:** {_price(profile.value_area_low)} – "
            f"{_price(profile.value_area_high)}  •  POC {_price(profile.poc)}"
        )
    if snapshot.london_range is not None:
        rows.append(
            f"**London range:** {_price(snapshot.london_range.low)} – "
            f"{_price(snapshot.london_range.high)}"
        )
    if snapshot.new_york_range is not None:
        rows.append(
            f"**New York range:** {_price(snapshot.new_york_range.low)} – "
            f"{_price(snapshot.new_york_range.high)}"
        )
    return "\n".join(rows) or "Auction structure is still developing"


def _fair_value_gaps(values: dict[AnalyticsTimeframe, MarketContextSnapshot]) -> str:
    labels = {
        AnalyticsTimeframe.ONE_HOUR: "1 Hour",
        AnalyticsTimeframe.FIFTEEN_MINUTES: "15 Minute",
        AnalyticsTimeframe.FIVE_MINUTES: "5 Minute",
    }
    rows = []
    for timeframe, label in labels.items():
        snapshot = values.get(timeframe)
        if snapshot is None:
            continue
        nearest = sorted(
            snapshot.fair_value_gaps,
            key=lambda gap: min(abs(snapshot.close - gap.lower), abs(snapshot.close - gap.upper)),
        )[:2]
        rows.extend(
            f"**{label}:** {gap.direction.value.title()} {_price(gap.lower)} – {_price(gap.upper)}"
            for gap in nearest
        )
    return "\n".join(rows) or "No nearby fair value gaps"


def _order_flow(pressure: SessionAuctionPressureSnapshot) -> str:
    ratio = "Unavailable" if pressure.delta_ratio is None else f"{pressure.delta_ratio:+.1%}"
    return (
        f"**Cumulative delta:** {pressure.cvd:+,.0f}  •  **Delta ratio:** {ratio}\n"
        f"Buy volume: {pressure.buy_volume:,.0f}  •  Sell volume: {pressure.sell_volume:,.0f}\n"
        f"Classification coverage: {pressure.classified_volume_ratio:.1%}  •  "
        f"Fidelity: {pressure.fidelity.value.title()}"
    )


def _bar_pressure(pressure: BarPressureProxySnapshot) -> str:
    atr_move = (
        "ATR unavailable"
        if pressure.atr_fraction is None
        else f"{pressure.atr_fraction:+.2f} ATR"
    )
    pace = (
        "Building 10-bar baseline"
        if pressure.pace_ratio is None
        else f"{pressure.pace_ratio:.2f}x baseline"
    )
    return (
        f"**{pressure.direction.value.title()} price pressure** over "
        f"{pressure.window_bars} completed bars\n"
        f"Net move: {pressure.price_change:+,.2f}  •  {atr_move}\n"
        f"Candles: {pressure.up_bar_count} up / {pressure.down_bar_count} down / "
        f"{pressure.flat_bar_count} flat  •  Close: {pressure.close_location:.0%} of range\n"
        f"Volume pace: {pace}\n"
        "*Partial • Reported OHLCV • Not bid/ask delta*"
    )


def _narrative_explanation(event: SignalEvaluationEvent, location_name: str) -> str:
    zone = event.location_matches[0].zone
    price_range = f"{_price(zone.lower_price)} – {_price(zone.upper_price)}"
    direction = (
        "the qualified direction"
        if event.signal_direction is None
        else f"the {event.signal_direction.value} direction"
    )
    return {
        LocationEpisodeEventType.ENTERED: (
            f"Price entered {location_name} at {price_range}."
        ),
        LocationEpisodeEventType.ACTIVE: (
            f"Price remains engaged with {location_name} at {price_range}."
        ),
        LocationEpisodeEventType.FAVORABLE_DEPARTURE: (
            f"Price departed {location_name} at {price_range} in {direction}; "
            "another close is required to confirm rejection."
        ),
        LocationEpisodeEventType.REJECTED: (
            f"Price rejected {location_name} at {price_range} with confirmed "
            f"closes in {direction}."
        ),
        LocationEpisodeEventType.DEPARTURE_UNRESOLVED: (
            f"Price moved away from {location_name} at {price_range}, "
            "but the interaction remains unresolved."
        ),
        LocationEpisodeEventType.EXIT_PENDING: (
            f"Price closed through {location_name} at {price_range}; "
            "another close is required to confirm acceptance."
        ),
        LocationEpisodeEventType.EXITED: (
            f"Price was accepted through {location_name} at {price_range}; "
            "the rejection thesis ended."
        ),
        LocationEpisodeEventType.REPLACED: (
            f"{location_name} at {price_range} replaced the prior decision area."
        ),
    }[event.episode_event]


def _narrative_color(event: SignalEvaluationEvent) -> int:
    if event.episode_event == LocationEpisodeEventType.EXIT_PENDING:
        return 0xF39C12
    if event.episode_event in {LocationEpisodeEventType.EXITED, LocationEpisodeEventType.REPLACED}:
        return 0x95A5A6
    if event.signal_direction is None:
        return 0xFFFFFF
    return 0x2ECC71 if event.signal_direction.value == "long" else 0xE74C3C


def _signal_locations(matches: Sequence[SignalLocationMatch]) -> str:
    if not matches:
        return "No detailed location available"
    rows = []
    for match in matches:
        zone = match.zone
        rows.append(
            f"**{zone.timeframe.value} {zone.zone_kind.value.replace('_', ' ').title()}:** "
            f"{_price(zone.lower_price)} – {_price(zone.upper_price)}"
        )
    return "\n".join(rows[:4])


def _signal_evidence_summary(event: SignalEvaluationEvent) -> str:
    direction = event.direction_status.value.replace("_", " ").title()
    location = (
        "Unavailable"
        if event.location_status is None
        else event.location_status.value.replace("_", " ").title()
    )
    values = [f"Direction: {direction}", f"Location: {location}"]
    if event.aggression_status is not None:
        values.append(f"Order flow: {event.aggression_status.value.replace('_', ' ').title()}")
    return "  •  ".join(values)


def _human_reasons(reasons: Sequence[str]) -> str:
    return "\n".join(f"• {reason.replace('_', ' ').capitalize()}" for reason in reasons[:5])


def _json_native_embeds(
    embeds: tuple[dict[str, object], ...],
) -> list[dict[str, object]]:
    normalized = []
    for embed in embeds:
        value = dict(embed)
        fields = value.get("fields")
        if isinstance(fields, tuple):
            value["fields"] = list(fields)
        normalized.append(value)
    return normalized
