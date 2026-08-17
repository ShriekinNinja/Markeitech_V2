from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

from nautilus_trader.model import BarType, ClientId

from markeitech.acquisition.historical import HistoricalRequest


class NativeHistoricalActor(Protocol):
    def request_bars(
        self,
        bar_type: BarType,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
        client_id=None,  # noqa: ANN001
        params: dict | None = None,
    ) -> None: ...


class NautilusHistoricalPort:
    def __init__(
        self,
        actor: NativeHistoricalActor,
        client_id: ClientId | None = None,
    ) -> None:
        self._actor = actor
        self._client_id = client_id or ClientId.from_str("IB")

    def submit(self, request: HistoricalRequest) -> None:
        bar_type = BarType.from_str(f"{request.instrument_id}-{request.selector}")
        self._actor.request_bars(
            bar_type,
            start=_utc_datetime(request.start_ns),
            end=_utc_datetime(request.end_ns),
            limit=request.limit,
            client_id=self._client_id,
            params=dict(request.parameters) or None,
        )

    def cancel(self, _request: HistoricalRequest) -> None:
        # Nautilus does not expose cancellation for an in-flight historical bar request.
        # The coordinator expires local ownership and safely ignores a late callback.
        return


class HistoricalResponseMismatch(ValueError):
    pass


def validate_historical_bars(
    request: HistoricalRequest,
    observations: tuple[object, ...],
) -> None:
    if len(observations) > request.limit:
        raise HistoricalResponseMismatch(
            f"provider returned {len(observations)} observations above limit {request.limit}",
        )

    expected_bar_type = f"{request.instrument_id}-{request.selector}"
    interval_ns = BarType.from_str(expected_bar_type).spec.get_interval_ns()
    latest_allowed_ns = request.end_ns + interval_ns
    previous_ts_event: int | None = None
    for index, observation in enumerate(observations):
        actual_bar_type = str(getattr(observation, "bar_type", ""))
        if actual_bar_type != expected_bar_type:
            raise HistoricalResponseMismatch(
                "provider returned an unexpected bar type: "
                f"index={index}, expected={expected_bar_type}, "
                f"actual={actual_bar_type or 'missing'}",
            )
        ts_event = getattr(observation, "ts_event", None)
        if not isinstance(ts_event, int):
            raise HistoricalResponseMismatch(
                f"provider returned a bar without an integer ts_event: index={index}",
            )
        if not request.start_ns <= ts_event <= latest_allowed_ns:
            raise HistoricalResponseMismatch(
                "provider returned a bar outside the requested window: "
                f"index={index}, ts_event={ts_event}, "
                f"window={request.start_ns}-{request.end_ns}",
            )
        if previous_ts_event is not None and ts_event <= previous_ts_event:
            raise HistoricalResponseMismatch(
                "provider returned duplicate or unordered bars: "
                f"index={index}, previous={previous_ts_event}, current={ts_event}",
            )
        previous_ts_event = ts_event


def _utc_datetime(timestamp_ns: int) -> datetime:
    seconds = timestamp_ns // 1_000_000_000
    return datetime.fromtimestamp(seconds, UTC)
