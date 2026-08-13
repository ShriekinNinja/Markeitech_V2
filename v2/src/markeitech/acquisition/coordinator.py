from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from markeitech.acquisition.demand import (
    AcquisitionLifecycleState,
    DemandReconciler,
    FeedRequirement,
    ObservationDemand,
    ProviderDemand,
    StreamKey,
)


class SubscriptionPort(Protocol):
    def subscribe(self, requirement: FeedRequirement) -> None: ...

    def unsubscribe(self, requirement: FeedRequirement) -> None: ...


@dataclass(frozen=True, slots=True)
class AcquisitionLifecycleEvent:
    state: AcquisitionLifecycleState
    stream_key: StreamKey
    demand_id: str | None
    consumer_ids: tuple[str, ...]
    detail: str


class AcquisitionCoordinator:
    """Owns logical demand and the lifetime of provider subscriptions."""

    def __init__(self, subscription_port: SubscriptionPort) -> None:
        self._subscription_port = subscription_port
        self._reconciler = DemandReconciler()
        self._active: dict[StreamKey, ProviderDemand] = {}

    @property
    def demands(self) -> tuple[ObservationDemand, ...]:
        return self._reconciler.demands

    @property
    def active_provider_demands(self) -> tuple[ProviderDemand, ...]:
        return tuple(self._active[key] for key in sorted(self._active))

    def request(
        self,
        demand: ObservationDemand,
        *,
        now: datetime,
    ) -> tuple[AcquisitionLifecycleEvent, ...]:
        events = [
            self._event(
                AcquisitionLifecycleState.REQUESTED,
                demand.requirement,
                demand_id=demand.demand_id,
                detail="observation demand received",
            ),
        ]
        added = self._reconciler.add(demand, now=now)
        if not added:
            events.extend(self.reconcile(now=now))
            return tuple(events)
        events.append(
            self._event(
                AcquisitionLifecycleState.ACCEPTED,
                demand.requirement,
                demand_id=demand.demand_id,
                detail="observation demand accepted",
            ),
        )
        events.extend(self.reconcile(now=now))
        return tuple(events)

    def cancel(
        self,
        demand_id: str,
        *,
        now: datetime,
    ) -> tuple[AcquisitionLifecycleEvent, ...]:
        demand = next(
            (
                candidate
                for candidate in self._reconciler.demands
                if candidate.demand_id == demand_id
            ),
            None,
        )
        if demand is None or not self._reconciler.remove(demand_id):
            return ()
        events = [
            self._event(
                AcquisitionLifecycleState.CANCELED,
                demand.requirement,
                demand_id=demand.demand_id,
                detail="observation demand canceled",
            ),
        ]
        events.extend(self.reconcile(now=now))
        return tuple(events)

    def expire(self, *, now: datetime) -> tuple[AcquisitionLifecycleEvent, ...]:
        by_id = {demand.demand_id: demand for demand in self._reconciler.demands}
        expired_ids = self._reconciler.expire(now=now)
        events = [
            self._event(
                AcquisitionLifecycleState.EXPIRED,
                by_id[demand_id].requirement,
                demand_id=demand_id,
                detail="observation demand expired",
            )
            for demand_id in expired_ids
        ]
        events.extend(self.reconcile(now=now))
        return tuple(events)

    def reconcile(self, *, now: datetime) -> tuple[AcquisitionLifecycleEvent, ...]:
        desired = {
            demand.requirement.stream_key: demand
            for demand in self._reconciler.provider_demands(now=now)
        }
        events: list[AcquisitionLifecycleEvent] = []

        changed = {
            key
            for key in self._active.keys() & desired.keys()
            if self._active[key].requirement != desired[key].requirement
        }
        for key in sorted((self._active.keys() - desired.keys()) | changed):
            active = self._active[key]
            try:
                self._subscription_port.unsubscribe(active.requirement)
            except Exception as exc:  # Provider ports define their own exception types.
                events.append(
                    self._provider_failure(active, "unsubscribe", exc),
                )
            else:
                del self._active[key]
                events.append(
                    self._event(
                        AcquisitionLifecycleState.COMPLETED,
                        active.requirement,
                        consumer_ids=active.consumer_ids,
                        detail="provider subscription stopped",
                    ),
                )

        for key in sorted(desired):
            provider_demand = desired[key]
            if key in self._active:
                if self._active[key].requirement == provider_demand.requirement:
                    self._active[key] = provider_demand
                continue
            try:
                self._subscription_port.subscribe(provider_demand.requirement)
            except Exception as exc:  # Provider ports define their own exception types.
                events.append(
                    self._provider_failure(provider_demand, "subscribe", exc),
                )
            else:
                self._active[key] = provider_demand
                events.append(
                    self._event(
                        AcquisitionLifecycleState.ACTIVE,
                        provider_demand.requirement,
                        consumer_ids=provider_demand.consumer_ids,
                        detail="provider subscription active",
                    ),
                )
        return tuple(events)

    @staticmethod
    def _provider_failure(
        demand: ProviderDemand,
        operation: str,
        error: Exception,
    ) -> AcquisitionLifecycleEvent:
        return AcquisitionCoordinator._event(
            AcquisitionLifecycleState.FAILED,
            demand.requirement,
            consumer_ids=demand.consumer_ids,
            detail=f"provider {operation} failed: {type(error).__name__}",
        )

    @staticmethod
    def _event(
        state: AcquisitionLifecycleState,
        requirement: FeedRequirement,
        *,
        demand_id: str | None = None,
        consumer_ids: tuple[str, ...] = (),
        detail: str,
    ) -> AcquisitionLifecycleEvent:
        return AcquisitionLifecycleEvent(
            state=state,
            stream_key=requirement.stream_key,
            demand_id=demand_id,
            consumer_ids=consumer_ids,
            detail=detail,
        )
