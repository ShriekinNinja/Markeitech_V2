from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from markeitech.persistence import NotificationOutboxRecord
from markeitech.signals import SignalStatus, SignalTransitionEvent

SIGNAL_LIFECYCLE_DESTINATION = "signal-lifecycle"
def build_signal_transition_notification(
    event: SignalTransitionEvent,
    *,
    role: str,
) -> NotificationOutboxRecord:
    signal = event.current
    direction = signal.direction.value.title()
    state = event.to_status.value.title()
    title = f"{direction} Setup {state} — {_instrument_name(signal.instrument_id)}"
    fields = [
        {
            "name": "Lifecycle",
            "value": f"{event.from_status.value.title()} → {state}",
            "inline": True,
        },
        {"name": "Instrument role", "value": role.title(), "inline": True},
        {
            "name": "Location",
            "value": _locations(event),
            "inline": False,
        },
        {
            "name": "Evidence",
            "value": _evidence(event),
            "inline": False,
        },
        {
            "name": "Why it changed",
            "value": _reasons(event.reason_codes),
            "inline": False,
        },
    ]
    now = event.occurred_ts
    return NotificationOutboxRecord(
        outbox_id=uuid5(
            NAMESPACE_URL,
            f"markeitech:discord:{SIGNAL_LIFECYCLE_DESTINATION}:{event.transition_id}",
        ),
        topic="discord",
        destination_key=SIGNAL_LIFECYCLE_DESTINATION,
        aggregate_key=event.signal_id,
        event_type="signal.transition",
        event_schema_version=event.schema_version,
        payload={
            "content": f"**{title}**",
            "allowed_mentions": {"parse": []},
            "embeds": [
                {
                    "title": title,
                    "description": _transition_explanation(event.to_status),
                    "color": _transition_color(event),
                    "fields": fields,
                    "timestamp": now.isoformat(),
                    "footer": {
                        "text": (
                            f"{signal.definition_id.replace('_', ' ').title()} • "
                            "Decision support, not execution"
                        )
                    },
                },
            ],
        },
        dedupe_key=f"discord:{SIGNAL_LIFECYCLE_DESTINATION}:{event.transition_id}",
        available_ts=now,
        created_ts=now,
        updated_ts=now,
    )


def _instrument_name(instrument_id: str) -> str:
    if instrument_id.startswith("NQ"):
        return "Nasdaq 100 Futures"
    if instrument_id.startswith("ES"):
        return "S&P 500 Futures"
    return instrument_id.split(".")[0]


def _locations(event: SignalTransitionEvent) -> str:
    if not event.current.location_matches:
        return "No detailed location available"
    return "\n".join(
        f"**{match.zone.timeframe.value} "
        f"{match.zone.zone_kind.value.replace('_', ' ').title()}:** "
        f"{match.zone.lower_price:,.2f} – {match.zone.upper_price:,.2f}"
        for match in event.current.location_matches[:4]
    )


def _evidence(event: SignalTransitionEvent) -> str:
    stages: dict[str, set[str]] = {}
    for evidence in event.current.evidence:
        stages.setdefault(evidence.stage.value, set()).add(evidence.fidelity.value)
    return "  •  ".join(
        f"{stage.replace('_', ' ').title()}: {', '.join(sorted(values)).title()}"
        for stage, values in stages.items()
    )


def _reasons(reasons: tuple[str, ...]) -> str:
    return "\n".join(f"• {reason.replace('_', ' ').capitalize()}" for reason in reasons[:5])


def _transition_explanation(status: SignalStatus) -> str:
    return {
        SignalStatus.CANDIDATE: "A directional setup is being evaluated.",
        SignalStatus.ARMED: "Direction and location are qualified; confirmation is pending.",
        SignalStatus.TRIGGERED: "The required confirmation evidence has arrived.",
        SignalStatus.INVALIDATED: "The setup conditions no longer hold.",
        SignalStatus.EXPIRED: "The confirmation window ended without a valid trigger.",
    }[status]


def _transition_color(event: SignalTransitionEvent) -> int:
    if event.to_status == SignalStatus.ARMED:
        return 0xF1C40F
    if event.to_status == SignalStatus.INVALIDATED:
        return 0xE67E22
    if event.to_status == SignalStatus.EXPIRED:
        return 0x95A5A6
    return 0x2ECC71 if event.current.direction.value == "long" else 0xE74C3C
