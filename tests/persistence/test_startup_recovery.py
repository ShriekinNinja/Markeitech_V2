from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from markeitech.domain import (
    AnalysisProfile,
    EquityLikeContractConfig,
    FuturesContractConfig,
    InstrumentDataMode,
    InstrumentRegistryConfig,
    InstrumentRole,
    InstrumentRuntimeConfig,
    InstrumentWarmupConfig,
    OneMinuteBar,
    SecurityType,
)
from markeitech.persistence import (
    ExplicitSessionCalendar,
    PersistenceConfig,
    RecoveryPlanningError,
    RecoveryStatus,
    SessionWindow,
    SQLiteMetadataStore,
    StartupRecoveryService,
    StartupRecoveryStatus,
)

NOW = datetime(2026, 7, 13, 12, 7, 30, tzinfo=UTC)
START = datetime(2026, 7, 13, 12, tzinfo=UTC)


class RecordingCatalog:
    def __init__(self, bars: dict[str, list[OneMinuteBar]]) -> None:
        self.bars = bars

    def query_one_minute_bars(self, instrument_id: str) -> tuple[OneMinuteBar, ...]:
        return tuple(self.bars.get(instrument_id, ()))


def persistence_config(tmp_path: Path, **updates: object) -> PersistenceConfig:
    return PersistenceConfig(
        catalog_path=tmp_path / "catalog",
        metadata_path=tmp_path / "metadata.sqlite3",
        journal_path=tmp_path / "journal",
        recovery_max_intervals_per_request=1,
        **updates,
    )


def registry() -> InstrumentRegistryConfig:
    warmup = InstrumentWarmupConfig(lookback_sessions=1, timeframes=("1m",))
    nq = FuturesContractConfig(
        root_symbol="NQ",
        exchange="CME",
        instrument_id="NQU6.CME",
        ib_symbol="NQ",
        ib_exchange="CME",
        expiry=date(2026, 9, 18),
        ib_last_trade_date_or_contract_month="20260918",
        calendar_id="CME_Equity",
        session_profile="full",
    )
    spy = EquityLikeContractConfig(
        root_symbol="SPY",
        exchange="ARCA",
        instrument_id="SPY.ARCA",
        security_type=SecurityType.ETF,
        ib_symbol="SPY",
        ib_exchange="ARCA",
        ib_security_type="ETF",
        calendar_id="NYSE",
        session_profile="full",
    )
    spx = EquityLikeContractConfig(
        root_symbol="SPX",
        exchange="CBOE",
        instrument_id="^SPX.CBOE",
        security_type=SecurityType.INDEX,
        ib_symbol="SPX",
        ib_exchange="CBOE",
        ib_security_type="IND",
        calendar_id="NYSE",
        session_profile="regular",
    )
    return InstrumentRegistryConfig(
        active_instrument_id="NQU6.CME",
        instruments=(
            InstrumentRuntimeConfig(
                contract=nq,
                role=InstrumentRole.ACTIVE,
                data_mode=InstrumentDataMode.TICK_BY_TICK,
                analysis_profile=AnalysisProfile.ACTIVE_TICK,
                warmup=warmup,
            ),
            InstrumentRuntimeConfig(
                contract=spy,
                role=InstrumentRole.BACKGROUND,
                data_mode=InstrumentDataMode.LIVE_1M_BARS,
                analysis_profile=AnalysisProfile.BACKGROUND_BAR,
                warmup=warmup,
            ),
            InstrumentRuntimeConfig(
                contract=spx,
                role=InstrumentRole.BACKGROUND,
                data_mode=InstrumentDataMode.LIVE_1M_BARS,
                analysis_profile=AnalysisProfile.BACKGROUND_BAR,
                warmup=warmup,
            ),
        ),
    )


def calendar() -> ExplicitSessionCalendar:
    window = SessionWindow(open_ts=START, close_ts=START + timedelta(minutes=6))
    return ExplicitSessionCalendar(
        {
            "NQU6.CME": (window,),
            "SPY.ARCA": (window,),
            "^SPX.CBOE": (window,),
        }
    )


def bar(instrument_id: str, minute: int) -> OneMinuteBar:
    open_ts = START + timedelta(minutes=minute)
    close_ts = open_ts + timedelta(minutes=1)
    return OneMinuteBar(
        instrument_id=instrument_id,
        event_ts=close_ts,
        ts_init=NOW,
        open_ts=open_ts,
        close_ts=close_ts,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("10"),
        buy_volume=Decimal("0"),
        sell_volume=Decimal("0"),
        unknown_volume=Decimal("10"),
        source="ib",
    )


def test_recovery_is_fair_across_futures_etf_and_cash_index(tmp_path: Path) -> None:
    catalog = RecordingCatalog(
        {
            "NQU6.CME": [bar("NQU6.CME", minute) for minute in (0, 2, 4)],
            "SPY.ARCA": [bar("SPY.ARCA", minute) for minute in (1, 3, 5)],
            "^SPX.CBOE": [bar("^SPX.CBOE", minute) for minute in range(6)],
        }
    )
    flush_count = 0

    def flush() -> bool:
        nonlocal flush_count
        flush_count += 1
        return True

    config = persistence_config(tmp_path)
    with SQLiteMetadataStore(config) as metadata:
        service = StartupRecoveryService(
            config,
            registry(),
            catalog,
            metadata,
            calendar(),
            flush_pending=flush,
        )

        requests = service.prepare(NOW)

        assert [request.instrument_id for request in requests] == [
            "NQU6.CME",
            "SPY.ARCA",
            "NQU6.CME",
            "SPY.ARCA",
            "NQU6.CME",
            "SPY.ARCA",
        ]
        assert service.snapshot.status == StartupRecoveryStatus.RECOVERING
        assert flush_count == 1

        catalog.bars["NQU6.CME"] = [bar("NQU6.CME", minute) for minute in range(6)]
        catalog.bars["SPY.ARCA"].extend(bar("SPY.ARCA", minute) for minute in (0, 2))
        result = service.finish(NOW + timedelta(seconds=1))

        by_instrument = {item.instrument_id: item for item in result.instruments}
        assert result.status == StartupRecoveryStatus.DEGRADED
        assert by_instrument["NQU6.CME"].status == RecoveryStatus.COMPLETE
        assert by_instrument["SPY.ARCA"].status == RecoveryStatus.DEGRADED
        assert by_instrument["SPY.ARCA"].missing_after == 1
        assert "provider_returned_no_bar" in by_instrument["SPY.ARCA"].reason_codes
        assert by_instrument["^SPX.CBOE"].status == RecoveryStatus.COMPLETE
        assert flush_count == 2

        retry = StartupRecoveryService(
            config,
            registry(),
            catalog,
            metadata,
            calendar(),
            flush_pending=flush,
        )
        retry_requests = retry.prepare(NOW + timedelta(minutes=1))
        assert [(request.instrument_id, request.start_ts) for request in retry_requests] == [
            ("SPY.ARCA", START + timedelta(minutes=4))
        ]

        confirmed = retry.finish(NOW + timedelta(minutes=1, seconds=1))
        confirmed_by_instrument = {item.instrument_id: item for item in confirmed.instruments}
        assert confirmed.status == StartupRecoveryStatus.COMPLETE
        assert confirmed_by_instrument["SPY.ARCA"].missing_after == 0
        assert confirmed_by_instrument["SPY.ARCA"].confirmed_provider_empty_count == 1


def test_recovery_fails_closed_when_startup_flush_fails(tmp_path: Path) -> None:
    config = persistence_config(tmp_path)
    with SQLiteMetadataStore(config) as metadata:
        service = StartupRecoveryService(
            config,
            registry(),
            RecordingCatalog({}),
            metadata,
            calendar(),
            flush_pending=lambda: False,
        )

        with pytest.raises(RuntimeError, match="flush failed"):
            service.prepare(NOW)

        assert service.snapshot.status == StartupRecoveryStatus.FAILED


def test_recovery_enforces_aggregate_request_limit(tmp_path: Path) -> None:
    config = persistence_config(tmp_path, recovery_max_total_requests=2)
    with SQLiteMetadataStore(config) as metadata:
        service = StartupRecoveryService(
            config,
            registry(),
            RecordingCatalog({}),
            metadata,
            calendar(),
            flush_pending=lambda: True,
        )

        with pytest.raises(RecoveryPlanningError, match="total request limit"):
            service.prepare(NOW)

        assert service.snapshot.status == StartupRecoveryStatus.FAILED
