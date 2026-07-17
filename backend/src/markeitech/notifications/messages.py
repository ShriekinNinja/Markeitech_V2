from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from uuid import NAMESPACE_URL, uuid5

from markeitech.analytics import AnalyticsTimeframe, MarketContextSnapshot
from markeitech.auction_pressure import SessionAuctionPressureSnapshot
from markeitech.persistence import NotificationOutboxRecord
from markeitech.signals import LocationEpisodeEventType, SignalEvaluationEvent

SYSTEM_HEALTH_DESTINATION = "system-health"
MARKET_EVENTS_DESTINATION = "market-events"
SIGNAL_LIFECYCLE_DESTINATION = "signal-lifecycle"
_MAX_CONTENT = 2000


def build_health_notification(
    *,
    trader_id: str,
    event: str,
    detail: str,
    occurred_ts: datetime | None = None,
) -> NotificationOutboxRecord:
    now = datetime.now(UTC) if occurred_ts is None else occurred_ts
    content = f"**SYSTEM {event.upper()} | {trader_id}**\n{detail}"
    return _record(
        destination=SYSTEM_HEALTH_DESTINATION,
        aggregate=trader_id,
        event_type=f"runtime.{event.lower()}",
        identity=f"{event}:{now.isoformat()}:{detail}",
        content=content,
        now=now,
    )


def build_market_context_notifications(
    lines: tuple[str, ...],
    *,
    phase: str,
    pressure: SessionAuctionPressureSnapshot | None,
    occurred_ts: datetime | None = None,
) -> tuple[NotificationOutboxRecord, ...]:
    now = datetime.now(UTC) if occurred_ts is None else occurred_ts
    records: list[NotificationOutboxRecord] = []
    for index in range(0, len(lines), 3):
        group = lines[index : index + 3]
        if not group:
            continue
        instrument = _instrument_from_operator_line(group[0])
        body = "\n".join(_readable_operator_line(line) for line in group)
        if pressure is not None and pressure.instrument_id == instrument:
            ratio = "n/a" if pressure.delta_ratio is None else f"{pressure.delta_ratio:+.3f}"
            body += (
                "\n**ORDER FLOW (inferred)**"
                f"\nCVD `{pressure.cvd:+}` | Delta `{pressure.delta:+}` | "
                f"Delta ratio `{ratio}` | Classified `{pressure.classified_volume_ratio:.1%}` | "
                f"Trades `{pressure.trade_count}` | Fidelity `{pressure.fidelity.value}`"
            )
        content = f"**MARKET CONTEXT | {instrument} | {phase.upper()}**\n{body}"
        records.append(
            _record(
                destination=MARKET_EVENTS_DESTINATION,
                aggregate=instrument,
                event_type="market.context.report",
                identity=f"{instrument}:{phase}:{now.isoformat()}:{body}",
                content=content,
                now=now,
            )
        )
    return tuple(records)


def build_location_narrative_notification(
    event: SignalEvaluationEvent,
    *,
    role: str,
) -> NotificationOutboxRecord | None:
    narrative = {
        LocationEpisodeEventType.ENTERED: "ENTERED",
        LocationEpisodeEventType.ACTIVE: "HOLDING",
        LocationEpisodeEventType.FAVORABLE_DEPARTURE: "REJECTED",
        LocationEpisodeEventType.DEPARTURE_UNRESOLVED: "HOLDING",
        LocationEpisodeEventType.EXIT_PENDING: "EXIT WARNING",
        LocationEpisodeEventType.EXITED: "EXITED",
        LocationEpisodeEventType.REPLACED: "ROTATED",
    }.get(event.episode_event)
    if narrative is None:
        return None
    detail = (
        f"Role `{role}` | Direction `{event.direction_status.value}` | "
        f"Location `{event.location_status.value if event.location_status else 'n/a'}`\n"
        f"Episode `{event.episode_event.value}` | Definition `{event.definition_id}` | "
        f"As of `{event.evaluation_ts.isoformat()}`"
    )
    return _record(
        destination=SIGNAL_LIFECYCLE_DESTINATION,
        aggregate=f"{event.definition_id}:{event.instrument_id}",
        event_type=f"location.{event.episode_event.value}",
        identity=(
            f"{event.definition_id}:{event.instrument_id}:"
            f"{event.episode_event.value}:{event.evaluation_ts.isoformat()}"
        ),
        content=f"**{narrative} | {event.instrument_id}**\n{detail}",
        now=event.evaluation_ts,
    )


class ApproachingLocationNotifier:
    """Presentation-only proximity alert; it never changes signal qualification."""

    def __init__(self, *, atr_fraction: Decimal = Decimal("0.25")) -> None:
        self._atr_fraction = atr_fraction
        self._active_keys: dict[str, str] = {}

    def observe(self, snapshot: MarketContextSnapshot) -> NotificationOutboxRecord | None:
        if snapshot.timeframe != AnalyticsTimeframe.ONE_MINUTE or not snapshot.atr_14:
            return None
        candidates = tuple(
            level
            for level in (snapshot.nearest_support, snapshot.nearest_resistance)
            if level is not None
        )
        if not candidates:
            self._active_keys.pop(snapshot.instrument_id, None)
            return None
        level = min(candidates, key=lambda item: abs(snapshot.close - item.price))
        distance = abs(snapshot.close - level.price)
        threshold = snapshot.atr_14 * self._atr_fraction
        key = f"{level.kind.value}:{level.price}"
        if distance > threshold:
            if distance > threshold * 2:
                self._active_keys.pop(snapshot.instrument_id, None)
            return None
        if self._active_keys.get(snapshot.instrument_id) == key:
            return None
        self._active_keys[snapshot.instrument_id] = key
        return _record(
            destination=SIGNAL_LIFECYCLE_DESTINATION,
            aggregate=snapshot.instrument_id,
            event_type="location.approaching",
            identity=f"{snapshot.instrument_id}:{key}:{snapshot.as_of.isoformat()}",
            content=(
                f"**APPROACHING LOCATION | {snapshot.instrument_id}**\n"
                f"Price `{snapshot.close}` approaching `{level.kind.value}` at `{level.price}`\n"
                f"Distance `{distance}` | Alert threshold `{threshold}` (0.25 ATR) | "
                f"Trend `{snapshot.trend.value}` | Direction `{snapshot.direction_score:+d}`\n"
                "Context warning only; no entry instruction."
            ),
            now=snapshot.as_of,
        )


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
) -> NotificationOutboxRecord:
    digest = hashlib.sha256(identity.encode()).hexdigest()
    outbox_id = uuid5(NAMESPACE_URL, f"markeitech:discord:{destination}:{digest}")
    return NotificationOutboxRecord(
        outbox_id=outbox_id,
        topic="discord",
        destination_key=destination,
        aggregate_key=aggregate,
        event_type=event_type,
        event_schema_version="1.0",
        payload={"content": content[:_MAX_CONTENT], "allowed_mentions": {"parse": []}},
        dedupe_key=f"discord:{destination}:{digest}",
        available_ts=now,
        created_ts=now,
        updated_ts=now,
    )


def _instrument_from_operator_line(line: str) -> str:
    fields = [field.strip() for field in line.split("|")]
    return fields[3] if len(fields) > 3 else "UNKNOWN"


def _readable_operator_line(line: str) -> str:
    label, _, detail = line.partition("|")
    title = label.removeprefix("OPERATOR_").replace("_", " ").title()
    return f"**{title}**\n{detail.strip().replace(' | ', ' · ')}"
