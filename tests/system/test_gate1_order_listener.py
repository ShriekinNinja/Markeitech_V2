"""Synthetic callback projection and genuine native construction; no provider delivery claim."""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from dataclasses import FrozenInstanceError, fields, is_dataclass
from pathlib import Path

import pytest
from nautilus_trader import model
from nautilus_trader.core import UUID4

ROOT = Path(__file__).parents[2]
TOOL = ROOT / "tools/gate1/order_listener.py"
SPEC = importlib.util.spec_from_file_location("gate1_order_listener", TOOL)
assert SPEC is not None and SPEC.loader is not None
listener_module = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = listener_module
SPEC.loader.exec_module(listener_module)
ListenerConfig = listener_module.ListenerConfig
OrderListenerStrategy = listener_module.OrderListenerStrategy


def config(**overrides):
    values = {
        "account_id": "GATE1-SYNTHETIC",
        "account_alias": "synthetic",
        "instrument_ids": ("QQQ.NASDAQ",),
    }
    return ListenerConfig(**(values | overrides))


def event_identity(**overrides):
    return {
        "trader_id": model.TraderId("GATE1-001"),
        "strategy_id": model.StrategyId("OrderListener-001"),
        "instrument_id": model.InstrumentId.from_str("QQQ.NASDAQ"),
        "client_order_id": model.ClientOrderId("SYNTHETIC-ORDER"),
        "venue_order_id": model.VenueOrderId("SYNTHETIC-VENUE"),
        "account_id": model.AccountId("GATE1-SYNTHETIC"),
        "event_id": UUID4(),
        "ts_event": 100,
        "ts_init": 200,
        "reconciliation": False,
    } | overrides


def filled_event(**overrides):
    values = dict(
        **event_identity(),
        trade_id=model.TradeId("SYNTHETIC-FILL"),
        order_side=model.OrderSide.BUY,
        order_type=model.OrderType.MARKET,
        last_qty=model.Quantity.from_str("1"),
        last_px=model.Price.from_str("100.00"),
        currency=model.Currency.from_str("USD"),
        liquidity_side=model.LiquiditySide.TAKER,
        commission=None,
        position_id=model.PositionId("SYNTHETIC-POSITION"),
    )
    return model.OrderFilled(**(values | overrides))


def assert_immutable_values(value):
    if is_dataclass(value):
        assert value.__dataclass_params__.frozen
        for item in fields(value):
            assert_immutable_values(getattr(value, item.name))
    elif type(value) is tuple:
        for item in value:
            assert_immutable_values(item)
    else:
        assert type(value) in (str, int, float, bool, type(None))


def test_order_callback_copies_native_fields_without_claiming_broker_origin():
    listener = OrderListenerStrategy(config())
    event = model.OrderAccepted(**event_identity(reconciliation=True))
    listener.on_order_event(event)  # Synthetic projection test, not native event dispatch.
    record, = listener.observations()
    assert dict(record.values)["venue_order_id"] == "SYNTHETIC-VENUE"
    assert dict(record.values)["reconciliation"] is True
    assert dict(record.values)["ts_event"] == 100
    assert record.received_ns > 200
    assert record.account_alias == "synthetic"
    assert record.account_environment == record.broker_origin == "unverified"
    assert record.origin == "strategy_order_projection"
    assert "commission" in record.absent_fields
    assert "account_id" not in dict(record.values)
    assert_immutable_values(listener.observations())
    with pytest.raises(FrozenInstanceError):
        record.event_type = "changed"


def test_missing_commission_stays_null_and_distinct_from_absent_property():
    listener = OrderListenerStrategy(config())
    listener.on_order_event(filled_event())
    record, = listener.observations()
    assert dict(record.values)["last_qty"] == "1"
    assert dict(record.values)["commission"] is None
    assert "commission" in record.null_fields
    assert "commission" not in record.absent_fields
    assert "opening_order_id" in record.absent_fields


@pytest.mark.parametrize("event_type", [model.OrderUpdated, model.OrderCanceled])
def test_manual_change_and_cancellation_projection(event_type):
    listener = OrderListenerStrategy(config())
    arguments = event_identity()
    if event_type is model.OrderUpdated:
        arguments.update(
            quantity=model.Quantity.from_str("2"), price=model.Price.from_str("101.00"),
        )
    listener.on_order_event(event_type(**arguments))
    record, = listener.observations()
    assert record.event_type == event_type.__name__
    if event_type is model.OrderUpdated:
        assert dict(record.values)["quantity"] == "2"
        assert dict(record.values)["price"] == "101.00"


@pytest.mark.parametrize("override", [
    {"account_id": model.AccountId("OTHER-SYNTHETIC")},
    {"instrument_id": model.InstrumentId.from_str("OTHER.NASDAQ")},
])
def test_identity_mismatch_retains_no_payload(override):
    listener = OrderListenerStrategy(config())
    listener.on_order_event(model.OrderAccepted(**event_identity(**override)))
    assert listener.observations() == ()
    assert listener.listener_status().last_rejection == "missing_or_mismatched_identity"


def test_missing_identity_is_rejected_without_assuming_configured_account():
    listener = OrderListenerStrategy(config())
    event = model.OrderUpdated(
        **event_identity(account_id=None, venue_order_id=None),
        quantity=model.Quantity.from_str("2"),
    )
    listener.on_order_event(event)
    assert listener.observations() == ()
    assert listener.listener_status().rejected == 1


def test_unsupported_event_is_not_stringified():
    class Unknown:
        def __str__(self):
            raise AssertionError("Do not stringify arbitrary input")

    listener = OrderListenerStrategy(config())
    listener.on_order_event(Unknown())
    assert listener.observations() == ()
    assert listener.listener_status().last_rejection == "unsupported_event"


def test_duplicates_are_preserved_and_overflow_does_not_evict():
    listener = OrderListenerStrategy(config(max_records=2))
    event = model.OrderAccepted(**event_identity())
    listener.on_order_event(event)
    snapshot = listener.observations()
    listener.on_order_event(event)
    listener.on_order_event(event)
    assert len(snapshot) == 1
    assert [row.sequence for row in listener.observations()] == [1, 2]
    assert listener.observations()[0] == snapshot[0]
    assert listener.listener_status().overflowed == 1


def test_oversized_native_field_rejects_whole_row():
    listener = OrderListenerStrategy(config(max_field_bytes=64))
    event = model.OrderAccepted(**event_identity(client_order_id=model.ClientOrderId("X" * 65)))
    listener.on_order_event(event)
    assert listener.observations() == ()
    assert listener.listener_status().last_rejection == "unsupported_or_oversized_field"


@pytest.mark.parametrize("override", [
    {"client_id": 0}, {"client_id": 1000}, {"client_id": True},
    {"host": "example.com"}, {"host": "192.0.2.1"}, {"port": True}, {"port": 0},
    {"instrument_ids": ()}, {"instrument_ids": ("QQQ.NASDAQ", "QQQ.NASDAQ")},
    {"instrument_ids": ["QQQ.NASDAQ"]}, {"max_records": 0}, {"max_field_bytes": 0},
    {"account_alias": "private payload\n"}, {"account_id": "private payload without separator"},
])
def test_invalid_configuration_has_sanitized_error(override):
    with pytest.raises(ValueError, match="^Invalid offline listener configuration$"):
        config(**override)


def test_genuine_ib_client_and_listener_construct_without_lifecycle():
    result = subprocess.run(
        [sys.executable, "-B", str(TOOL)], capture_output=True, text=True, timeout=15, check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == (
        "OFFLINE_LISTENER_BUILT; NOT CONNECTED; ACCOUNT ENVIRONMENT UNVERIFIED"
    )
    assert "SYNTHETIC" not in result.stderr


def test_client_bearing_tool_has_no_lifecycle_or_order_calls():
    forbidden = {
        "connect", "disconnect", "start", "stop", "run", "run_async", "shutdown",
        "submit_order", "submit_order_list", "modify_order", "cancel_order", "cancel_all_orders",
        "close_position", "close_all_positions", "generate_mass_status",
        "generate_order_status_reports",
    }
    calls = {
        node.func.attr for node in ast.walk(ast.parse(TOOL.read_text()))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert not calls.intersection(forbidden)  # Source guard, not a compiled attempt audit.
    assert "add_exec_client" in calls and "add_strategy" in calls


def test_position_lifecycle_projection_copies_state_before_later_mutation():
    listener = OrderListenerStrategy(config())
    instrument = model.Equity(
        instrument_id=model.InstrumentId.from_str("QQQ.NASDAQ"),
        raw_symbol=model.Symbol("QQQ"), currency=model.Currency.from_str("USD"),
        price_precision=2, price_increment=model.Price.from_str("0.01"),
        ts_event=0, ts_init=0,
    )
    opening = filled_event()
    position = model.Position(instrument, opening)
    listener.on_position_event(model.PositionOpened.create(position, opening, UUID4(), 300))
    original = listener.observations()[0]
    addition = filled_event(trade_id=model.TradeId("SYNTHETIC-ADD"), ts_event=400)
    position.apply(addition)
    listener.on_position_event(model.PositionChanged.create(position, addition, UUID4(), 500))
    closing = filled_event(
        trade_id=model.TradeId("SYNTHETIC-CLOSE"), ts_event=600,
        client_order_id=model.ClientOrderId("SYNTHETIC-CLOSE-ORDER"),
        order_side=model.OrderSide.SELL, last_qty=model.Quantity.from_str("2"),
    )
    position.apply(closing)
    listener.on_position_event(model.PositionClosed.create(position, closing, UUID4(), 700))
    rows = listener.observations()
    assert [row.event_type for row in rows] == [
        "PositionOpened", "PositionChanged", "PositionClosed",
    ]
    assert [dict(row.values)["quantity"] for row in rows] == ["1", "2", "0"]
    assert original == rows[0] and dict(original.values)["quantity"] == "1"
    assert all(row.origin == "engine_position_lifecycle" for row in rows)
    assert all("reconciliation" in row.absent_fields for row in rows)
    assert all(row.broker_origin == "unverified" for row in rows)
    assert_immutable_values(rows)


def test_cli_rejects_unknown_arguments_without_echoing_private_text():
    sentinel = "SYNTHETIC_PRIVATE_SENTINEL"
    result = subprocess.run(
        [sys.executable, "-B", str(TOOL), "--account-id", sentinel],
        capture_output=True, text=True, timeout=15, check=False,
    )
    assert result.returncode == 2
    assert sentinel not in result.stdout + result.stderr
    assert result.stderr.strip() == "OFFLINE_LISTENER_ARGUMENTS_REJECTED"


def test_cli_build_failure_does_not_print_native_exception(monkeypatch, capsys):
    def fail(config):
        raise RuntimeError("SYNTHETIC_PRIVATE_BUILD_ERROR")

    monkeypatch.setattr(sys, "argv", [str(TOOL)])
    monkeypatch.setattr(listener_module, "build_listener_node", fail)
    assert listener_module.main() == 1
    output = capsys.readouterr()
    assert output.out.strip() == "OFFLINE_LISTENER_BUILD_FAILED"
    assert output.err == ""


@pytest.mark.parametrize("quote_quantity", [False, True])
def test_order_update_preserves_quantity_unit_flag(quote_quantity):
    listener = OrderListenerStrategy(config())
    listener.on_order_event(model.OrderUpdated(
        **event_identity(), quantity=model.Quantity.from_str("2"),
        is_quote_quantity=quote_quantity,
    ))
    assert dict(listener.observations()[0].values)["is_quote_quantity"] is quote_quantity


def test_fill_correction_copies_identity_and_missing_commission_without_free_text():
    listener = OrderListenerStrategy(config())
    event = model.OrderFillVoided(
        **event_identity(), correction_id="SYNTHETIC-CORRECTION",
        trade_id=model.TradeId("SYNTHETIC-FILL"), voided_qty=model.Quantity.from_str("1"),
        order_side=model.OrderSide.BUY, order_type=model.OrderType.MARKET,
        last_px=model.Price.from_str("100.00"), currency=model.Currency.from_str("USD"),
        liquidity_side=model.LiquiditySide.TAKER, is_reopened=True,
        reason="SYNTHETIC_PRIVATE_REASON", info={"secret": "SYNTHETIC_PRIVATE_INFO"},
    )
    listener.on_order_event(event)
    record, = listener.observations()
    values = dict(record.values)
    assert values["correction_id"] == "SYNTHETIC-CORRECTION"
    assert values["trade_id"] == "SYNTHETIC-FILL"
    assert values["voided_qty"] == "1"
    assert values["is_reopened"] is True
    assert "commission_voided" in record.null_fields
    assert "reason" not in values and "info" not in values
    assert "SYNTHETIC_PRIVATE" not in repr(record)
