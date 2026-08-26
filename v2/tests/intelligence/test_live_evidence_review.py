from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

from PIL import Image

from markeitech.intelligence.completed_bars import CompletedBarInput, CompletedBarSource
from markeitech.intelligence.live_evidence_review import (
    ProjectionCollector,
    ReviewInventory,
    ReviewItemKind,
    build_projection_payload,
    build_review_inventory,
    publish_projection_payload,
    review_inventory_from_json,
    to_json_value,
)
from markeitech.intelligence.live_evidence_review_actor import (
    LiveEvidenceReviewActor,
    LiveEvidenceReviewActorConfig,
)
from markeitech.intelligence.live_evidence_review_renderer import render_review
from markeitech.intelligence.metrics import MetricFidelity, MetricHealth, MetricValue
from markeitech.system.config import load_system_config


def _bar(revision: int = 1) -> CompletedBarInput:
    return CompletedBarInput(
        instrument_id="ESU6.CME",
        bar_specification="5-MINUTE-LAST-EXTERNAL",
        calendar_id="cme_equity",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        trade_date=date(2026, 8, 26),
        session_id="cme_equity:2026-08-26:OPEN",
        window_id="primary",
        interval_start_ns=1_000_000_000,
        interval_end_ns=301_000_000_000,
        open=Decimal("6500.00"),
        high=Decimal("6502.25"),
        low=Decimal("6499.75"),
        close=Decimal("6501.50"),
        volume=Decimal("1234"),
        source=CompletedBarSource.LIVE_AGGREGATE,
        observed_ts_ns=301_000_000_000,
        received_ts_ns=301_000_000_001,
        normalized_ts_ns=301_000_000_002,
        health=MetricHealth.READY,
        fidelity=MetricFidelity.DERIVED,
        evidence_refs=("bar:es:5m:1",),
        complete=True,
        revision=revision,
    )


def _inventory() -> ReviewInventory:
    config = load_system_config("v2/config/system.example.toml")
    complete = build_review_inventory(
        config,
        checkout_identity="test-checkout",
        configuration_identity="test-config",
    )
    return ReviewInventory(
        schema_version=complete.schema_version,
        checkout_identity=complete.checkout_identity,
        configuration_identity=complete.configuration_identity,
        items=(
            next(
                item
                for item in complete.items
                if item.key.item_kind is ReviewItemKind.METRIC
            ),
        ),
    )


def test_inventory_is_deterministic_and_round_trips() -> None:
    config = load_system_config("v2/config/system.example.toml")
    first = build_review_inventory(
        config,
        checkout_identity="test-checkout",
        configuration_identity="test-config",
    )
    second = build_review_inventory(
        config,
        checkout_identity="test-checkout",
        configuration_identity="test-config",
    )

    assert len(first.items) == 365
    assert first.digest == second.digest
    assert review_inventory_from_json(to_json_value(first)) == first
    assert len({item.key.digest for item in first.items}) == len(first.items)


def test_collector_detects_duplicate_conflict_stale_and_freezes() -> None:
    collector = ProjectionCollector(
        instrument_id="ESU6.CME",
        bar_specifications=("5-MINUTE-LAST-EXTERNAL",),
        maximum_bars_per_series=2,
        maximum_metric_subjects=2,
        maximum_entity_subjects=2,
    )
    bar = _bar()
    assert collector.accept(bar) is True
    assert collector.accept(bar) is False
    conflicting = CompletedBarInput(**{
        field: getattr(bar, field)
        for field in bar.__dataclass_fields__
        if field != "close"
    }, close=Decimal("6501.75"))
    assert collector.accept(conflicting) is False
    collector.freeze()
    assert collector.accept(_bar(revision=2)) is False
    assert collector.counters["duplicates"] == 1
    assert collector.counters["conflicts"] == 1
    assert collector.counters["after_freeze_ignored"] == 1


def test_actor_qualifies_only_exact_live_completed_es_bar(tmp_path) -> None:  # noqa: ANN001
    inventory = _inventory()
    config = LiveEvidenceReviewActorConfig(
        run_id="00000000-0000-0000-0000-000000000001",
        inventory=to_json_value(inventory),
        instrument_id="ESU6.CME",
        analytical_profile_id="cme_equity_primary",
        analytical_profile_version=1,
        bar_specification="5-MINUTE-LAST-EXTERNAL",
        output_directory=str(tmp_path),
        capture_policy_version=1,
        coalescing_interval_ms=2000,
        readiness_deadline_ms=2_700_000,
        live_bar_deadline_ms=600_000,
        output_drain_timeout_ms=30_000,
        visible_window_ms=28_800_000,
        image_width=1920,
        image_height=1080,
        maximum_bars_per_series=1000,
        maximum_metric_subjects=20_000,
        maximum_entity_subjects=20_000,
        contextual_bar_specifications=["5-MINUTE-LAST-EXTERNAL"],
    )
    actor = LiveEvidenceReviewActor(config)
    live = _bar()
    historical = CompletedBarInput(
        **{
            field: getattr(live, field)
            for field in live.__dataclass_fields__
            if field != "source"
        },
        source=CompletedBarSource.HISTORICAL_PROVIDER,
    )

    assert actor._qualifies(live) is True
    assert actor._qualifies(historical) is False
    actor.on_dispose()


def test_projection_publication_and_sequential_renderer_are_reconciled(tmp_path) -> None:  # noqa: ANN001
    inventory = _inventory()
    collector = ProjectionCollector(
        instrument_id="ESU6.CME",
        bar_specifications=("5-MINUTE-LAST-EXTERNAL",),
        maximum_bars_per_series=10,
        maximum_metric_subjects=10,
        maximum_entity_subjects=10,
    )
    bar = _bar()
    collector.accept(bar)
    review_item = inventory.items[0]
    collector.accept(
        MetricValue(
            metric_id=review_item.key.definition_or_metric_id,
            metric_version=review_item.key.definition_or_metric_version,
            parameter_version=int(review_item.key.parameter_identity.rsplit(":", 1)[-1]),
            instrument_id="ESU6.CME",
            session_id="cme_equity:2026-08-26:OPEN",
            value=Decimal("1.25"),
            unit="test-unit",
            effective_ts_ns=301_000_000_000,
            observed_ts_ns=301_000_000_000,
            received_ts_ns=301_000_000_001,
            calculated_ts_ns=301_000_000_002,
            published_ts_ns=301_000_000_003,
            health=MetricHealth.READY,
            fidelity=MetricFidelity.DERIVED,
            source="test-producer",
            evidence_refs=("metric:evidence:1",),
            missing_reasons=(),
            revision=1,
        ),
    )
    collector.freeze()
    payload = build_projection_payload(
        run_id="00000000-0000-0000-0000-000000000001",
        frozen_at_ns=303_000_000_000,
        trigger_bar=bar,
        readiness={"system_state": "READY", "historical_state_counts": {"READY": 1}},
        inventory=inventory,
        collector=collector,
        capture_policy={
            "capture_policy_version": 1,
            "coalescing_interval_ms": 2000,
            "readiness_deadline_ms": 2_700_000,
            "live_bar_deadline_ms": 600_000,
            "output_drain_timeout_ms": 30_000,
            "visible_window_ms": 28_800_000,
            "image_width": 1920,
            "image_height": 1080,
        },
    )
    pending = publish_projection_payload(payload, tmp_path)
    final = render_review(pending)

    assert final == tmp_path / payload["run_id"] / payload["capture_id"]
    assert (final / "overview.png").exists()
    focused = list((final / "focused").rglob("*.png"))
    assert len(focused) == 1
    with Image.open(final / "overview.png") as image:
        assert image.size == (1920, 1080)
    manifest = json.loads((final / "manifest.json").read_text())
    assert manifest["artifact_count"] == 2
    assert manifest["inventory_count"] == 1
    focused_path = next(
        path
        for path in manifest["source_to_mark_references"]
        if path != "overview.png"
    )
    assert "metric:evidence:1" in manifest["source_to_mark_references"][focused_path]
    report = (final / "review-report.md").read_text()
    assert "bounded receive-cut" in report
    assert "Sir Loke output" in report
