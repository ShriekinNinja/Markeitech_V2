from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from uuid import UUID

DASHBOARD_DEMAND_SIGNAL = "markeitech.dashboard.demand"
DASHBOARD_READY_SIGNAL = "markeitech.dashboard.ready"
WATCHLIST_MEMBERSHIP_REQUEST_SIGNAL = "markeitech.watchlist.membership.request"


@dataclass(frozen=True, slots=True)
class DashboardReadyEvent:
    """Announce an accepting loopback server, without asserting market-data readiness."""

    server_epoch: str
    port: int
    source: str = "DASHBOARD"
    schema_version: int = 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.server_epoch, str)
            or str(UUID(self.server_epoch)) != self.server_epoch
        ):
            raise ValueError("invalid dashboard server epoch")
        if type(self.port) is not int or not 1024 <= self.port <= 65535:
            raise ValueError("invalid dashboard port")
        if (
            self.source != "DASHBOARD"
            or type(self.schema_version) is not int
            or self.schema_version != 1
        ):
            raise ValueError("unsupported dashboard ready event")

    @property
    def url(self) -> str:
        """Return the fixed loopback origin for this server instance."""
        return f"http://127.0.0.1:{self.port}"

    def to_signal_value(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_signal_value(cls, value: str) -> DashboardReadyEvent:
        if not isinstance(value, str) or len(value) > 512:
            raise ValueError("invalid dashboard ready payload")
        try:
            data = json.loads(value)
            if not isinstance(data, dict) or data.keys() != {
                "server_epoch",
                "port",
                "source",
                "schema_version",
            }:
                raise ValueError("invalid dashboard ready fields")
            return cls(**data)
        except (TypeError, AttributeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid dashboard ready event") from exc


@dataclass(frozen=True, slots=True)
class DashboardDemand:
    """Request or release one configured display feed through acquisition only."""

    instrument_id: str
    feed_kind: str
    action: str = "REQUEST"
    schema_version: int = 1

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise ValueError("unsupported dashboard demand schema")
        if not isinstance(self.instrument_id, str) or not 1 <= len(self.instrument_id) <= 128:
            raise ValueError("invalid dashboard instrument identity")
        if self.feed_kind not in {"quotes", "bars"} or self.action not in {"REQUEST", "RELEASE"}:
            raise ValueError("unsupported dashboard demand")

    @property
    def selector(self) -> str:
        return "default" if self.feed_kind == "quotes" else "5-SECOND-LAST-EXTERNAL"

    @property
    def demand_id(self) -> str:
        return f"dashboard:{self.instrument_id}:{self.feed_kind}"

    def to_signal_value(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))

    @classmethod
    def from_signal_value(cls, value: str) -> DashboardDemand:
        if not isinstance(value, str) or len(value) > 1024:
            raise ValueError("invalid dashboard demand payload")
        try:
            data = json.loads(value)
            if not isinstance(data, dict) or data.keys() != {
                "instrument_id",
                "feed_kind",
                "action",
                "schema_version",
            }:
                raise ValueError("invalid dashboard demand fields")
            return cls(**data)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError("invalid dashboard demand") from exc
