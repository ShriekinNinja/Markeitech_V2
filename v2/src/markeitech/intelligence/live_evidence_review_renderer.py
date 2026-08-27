from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from textwrap import wrap
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from markeitech.intelligence.live_evidence_review import canonical_json

_BACKGROUND = "#0d1318"
_PANEL = "#131c23"
_GRID = "#31414b"
_TEXT = "#eef3f5"
_MUTED = "#aebcc5"
_UP = "#e5ecef"
_DOWN = "#e15b64"
_ACCENT = "#52a8e8"
_WARNING = "#f0c36b"
_FVG = "#3f9187"
_ZONE = "#9d6ab8"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render one Markeitech live evidence review")
    parser.add_argument("capture_directory", type=Path)
    parser.add_argument(
        "--output-root",
        type=Path,
        help="Optional alternate root for an immutable comparison render",
    )
    args = parser.parse_args(argv)
    try:
        render_review(args.capture_directory, output_root=args.output_root)
    except Exception as exc:
        print(f"live evidence review render failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


def render_review(pending_directory: Path, *, output_root: Path | None = None) -> Path:
    snapshot_path = pending_directory / "projection-snapshot.json"
    ledger_path = pending_directory / "review-ledger.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
    capture_id = _required_text(snapshot, "capture_id")
    run_id = _required_text(snapshot, "run_id")
    if pending_directory.name != capture_id or pending_directory.parent.name != run_id:
        raise ValueError("pending directory identity does not match projection snapshot")
    if ledger.get("capture_id") != capture_id:
        raise ValueError("review ledger capture identity mismatch")
    items = ledger.get("items")
    if not isinstance(items, list) or not items:
        raise ValueError("review ledger must contain items")
    digests = [item["identity_digest"] for item in items]
    if len(digests) != len(set(digests)):
        raise ValueError("review ledger contains duplicate identities")

    policy = snapshot["capture_policy"]
    width = int(policy["image_width"])
    height = int(policy["image_height"])
    if (width, height) != (1920, 1080):
        raise ValueError("review renderer requires 1920x1080 output")
    root = pending_directory.parents[2] if output_root is None else output_root
    final_directory = root / run_id / capture_id
    if final_directory.exists():
        raise FileExistsError(f"rendered capture already exists: {capture_id}")
    staging = root / run_id / f".{capture_id}.render-staging"
    if staging.exists():
        raise FileExistsError(f"render staging already exists: {capture_id}")
    staging.mkdir(parents=True)
    sources: dict[str, list[str]] = {}
    try:
        overview_path = staging / "overview.png"
        overview_sources = _render_frame(snapshot, None, overview_path, width, height)
        sources["overview.png"] = overview_sources
        for item in items:
            kind = item["review_key"]["item_kind"]
            digest = item["identity_digest"]
            relative = Path("focused") / kind / f"{digest}.png"
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            sources[str(relative)] = _render_frame(snapshot, item, path, width, height)
        report_path = staging / "review-report.md"
        report_path.write_text(_review_report(snapshot, items), encoding="utf-8")
        shutil.copy2(snapshot_path, staging / snapshot_path.name)
        shutil.copy2(ledger_path, staging / ledger_path.name)
        expected_pngs = 1 + len(items)
        pngs = sorted(staging.rglob("*.png"))
        if len(pngs) != expected_pngs:
            raise ValueError("focused artifact count does not reconcile with review inventory")
        for png in pngs:
            with Image.open(png) as image:
                if image.size != (width, height) or image.format != "PNG":
                    raise ValueError(f"invalid rendered image: {png.name}")
        manifest = {
            "schema_version": 2,
            "capture_id": capture_id,
            "run_id": run_id,
            "renderer": "Pillow",
            "renderer_version": 2,
            "pillow_version": Image.__version__,
            "dimensions": [width, height],
            "inventory_count": len(items),
            "artifact_count": expected_pngs,
            "source_to_mark_references": sources,
            "display_transform": {
                "bar_window": "configured visible_window_ms ending at latest trigger-selector bar",
                "price_domain": "visible candle low/high with eight-percent padding",
                "price_ticks": 6,
                "time_ticks": 5,
                "timezone": "UTC",
                "volume_domain": "zero to maximum visible captured bar volume",
            },
            "files": {
                str(path.relative_to(staging)): _sha256(path)
                for path in sorted(staging.rglob("*"))
                if path.is_file()
            },
        }
        (staging / "manifest.json").write_text(
            canonical_json(manifest) + "\n",
            encoding="utf-8",
        )
        staging.rename(final_directory)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return final_directory


def _render_frame(
    snapshot: dict[str, Any],
    selected: dict[str, Any] | None,
    path: Path,
    width: int,
    height: int,
) -> list[str]:
    image = Image.new("RGB", (width, height), _BACKGROUND)
    draw = ImageDraw.Draw(image)
    title_font = ImageFont.load_default(size=28)
    heading_font = ImageFont.load_default(size=20)
    body_font = ImageFont.load_default(size=18)
    small_font = ImageFont.load_default(size=16)
    chart = (70, 125, 1325, 800)
    volume = (70, 855, 1325, 1000)
    panel = (1440, 90, 1890, 1000)
    draw.rectangle(panel, fill=_PANEL, outline=_GRID, width=2)
    instrument = snapshot["identity"]["instrument_id"]
    draw.text((30, 25), "MARKEITECH LIVE EVIDENCE REVIEW", fill=_TEXT, font=title_font)
    draw.text(
        (30, 62),
        f"{instrument} · 5-minute view · CAPTURE FROZEN · bounded receive-cut",
        fill=_MUTED,
        font=body_font,
    )
    bars = _five_minute_bars(snapshot)
    refs = _draw_candles(draw, bars, chart, volume, small_font)
    if selected is None:
        refs.extend(_draw_overview_geometry(draw, snapshot, chart, bars, small_font))
        panel_lines = _overview_panel(snapshot, len(bars))
    else:
        refs.extend(_draw_selected_geometry(draw, snapshot, selected, chart, bars, small_font))
        panel_lines, panel_refs = _selected_panel(snapshot, selected)
        refs.extend(panel_refs)
    _draw_panel(draw, panel, panel_lines, heading_font, body_font, small_font)
    image.save(path, format="PNG", optimize=False, compress_level=9)
    image.close()
    return sorted(set(refs))


def _five_minute_bars(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    selector = snapshot["identity"]["trigger_bar"]["bar_specification"]
    bars = [
        item for item in snapshot["canonical_records"]["completed_bars"]
        if item["bar_specification"] == selector
    ]
    bars.sort(key=lambda item: (item["interval_end_ns"], item["revision"]))
    if not bars:
        return []
    window_ns = int(snapshot["capture_policy"]["visible_window_ms"]) * 1_000_000
    cutoff = bars[-1]["interval_end_ns"] - window_ns
    return [item for item in bars if item["interval_end_ns"] > cutoff]


def _draw_candles(draw, bars, chart, volume, font) -> list[str]:  # noqa: ANN001
    x0, y0, x1, y1 = chart
    vx0, vy0, vx1, vy1 = volume
    draw.rectangle(chart, outline=_GRID, width=2)
    draw.rectangle(volume, outline=_GRID, width=2)
    for step in range(6):
        y = y0 + (y1 - y0) * step // 5
        draw.line((x0, y, x1, y), fill=_GRID, width=1)
    if not bars:
        draw.text(
            (x0 + 30, y0 + 30),
            "No canonical five-minute bars in capture",
            fill=_WARNING,
            font=font,
        )
        return []
    lows = [_decimal(item["low"]) for item in bars]
    highs = [_decimal(item["high"]) for item in bars]
    low, high = min(lows), max(highs)
    span = high - low or 1.0
    padding = span * 0.08
    low -= padding
    high += padding
    volumes = [0.0 if item["volume"] is None else _decimal(item["volume"]) for item in bars]
    max_volume = max(volumes) or 1.0
    slot = (x1 - x0) / max(len(bars), 1)
    candle_width = max(2, int(slot * 0.55))
    refs = []

    def price_y(value: float) -> int:
        return int(y1 - (value - low) / (high - low) * (y1 - y0))

    for step in range(6):
        price = high - (high - low) * step / 5
        y = y0 + (y1 - y0) * step // 5
        draw.text((x1 + 10, y - 9), f"{price:.2f}", fill=_MUTED, font=font)

    for index, item in enumerate(bars):
        center = int(x0 + slot * (index + 0.5))
        open_y = price_y(_decimal(item["open"]))
        close_y = price_y(_decimal(item["close"]))
        high_y = price_y(_decimal(item["high"]))
        low_y = price_y(_decimal(item["low"]))
        color = _UP if close_y <= open_y else _DOWN
        draw.line((center, high_y, center, low_y), fill=color, width=2)
        draw.rectangle(
            (center - candle_width // 2, min(open_y, close_y),
             center + candle_width // 2, max(open_y, close_y) + 1),
            outline=color,
            fill=_BACKGROUND if color == _UP else color,
            width=2,
        )
        volume_top = int(vy1 - volumes[index] / max_volume * (vy1 - vy0))
        draw.rectangle(
            (center - candle_width // 2, volume_top, center + candle_width // 2, vy1),
            fill=_GRID,
        )
        refs.extend(item.get("evidence_refs", []))
    draw.text((x0 + 10, y0 + 8), "Canonical completed 5m candles", fill=_MUTED, font=font)
    draw.text((vx0 + 10, vy0 + 8), "Bar volume", fill=_MUTED, font=font)
    draw.text((vx1 + 10, vy0), f"{max_volume:,.0f}", fill=_MUTED, font=font)
    draw.text((vx1 + 10, vy1 - 18), "0", fill=_MUTED, font=font)
    close_label = f"latest completed 5m close: {_decimal_text(bars[-1]['close'])}"
    draw.text((x1 - 270, y0 + 8), close_label, fill=_TEXT, font=font)
    time_indexes = sorted({round((len(bars) - 1) * step / 4) for step in range(5)})
    for index in time_indexes:
        item = bars[index]
        center = int(x0 + slot * (index + 0.5))
        label = _utc(item["interval_end_ns"], "%H:%M")
        draw.text((center - 22, y1 + 8), label, fill=_MUTED, font=font)
    window_label = (
        f"UTC {_utc(bars[0]['interval_start_ns'], '%Y-%m-%d %H:%M')} to "
        f"{_utc(bars[-1]['interval_end_ns'], '%Y-%m-%d %H:%M')}"
    )
    draw.text((x0 + 10, y1 + 30), window_label, fill=_MUTED, font=font)
    return refs


def _draw_overview_geometry(draw, snapshot, chart, bars, font) -> list[str]:  # noqa: ANN001
    latest = _latest_entities(snapshot)
    by_type = defaultdict(list)
    for entity in latest:
        by_type[entity["identity"]["entity_type"]].append(entity)
    labels = {
        "objective_level.previous_session_high": "PSH",
        "objective_level.previous_session_low": "PSL",
        "objective_level.opening_range_high": "ORH",
        "objective_level.opening_range_low": "ORL",
    }
    selected: list[tuple[dict[str, Any], str]] = []
    for entity_type, label in labels.items():
        compatible = [item for item in by_type[entity_type] if item.get("payload")]
        selected.extend((item, label) for item in _newest(compatible, 1))
    five_minute = [item for item in latest if _is_five_minute_entity(item)]
    swings = _newest(
        [item for item in five_minute if item["identity"]["entity_type"] == "confirmed_swing"],
        2,
    )
    selected.extend(
        (item, "H" if item["payload"].get("kind") == "HIGH" else "L")
        for item in swings
    )
    pivots = _newest(
        [
            item
            for item in five_minute
            if item["identity"]["entity_type"] == "pivot_structure_state"
        ],
        1,
    )
    selected.extend((item, "P") for item in pivots)
    active_fvgs = _newest(
        [
            item
            for item in five_minute
            if item["identity"]["entity_type"] == "fair_value_gap"
            and item["lifecycle"] == "ACTIVE"
        ],
        2,
    )
    selected.extend((item, f"F{index + 1}") for index, item in enumerate(active_fvgs))
    active_zones = _newest(
        [
            item
            for item in five_minute
            if item["identity"]["entity_type"] == "derived_zone"
            and item["lifecycle"] == "ACTIVE"
        ],
        2,
    )
    selected.extend((item, f"Z{index + 1}") for index, item in enumerate(active_zones))
    refs = []
    used_label_y: list[int] = []
    for entity, label in selected:
        refs.extend(
            _draw_entity_hint(
                draw,
                entity,
                chart,
                bars,
                font,
                label=label,
                used_label_y=used_label_y,
            ),
        )
    return refs


def _draw_selected_geometry(draw, snapshot, selected, chart, bars, font) -> list[str]:  # noqa: ANN001
    if selected["representation"] != "geometry":
        return []
    if selected["review_key"]["item_kind"] == "metric":
        records = _matching_records(snapshot, selected)
        if not records:
            return []
        return _draw_metric_hint(draw, records[-1], chart, bars, font)
    entities = [
        item
        for item in _matching_records(snapshot, selected)
        if item["lifecycle"] == "ACTIVE"
    ]
    entities = _newest(entities, 6)
    refs = []
    used_label_y: list[int] = []
    for index, entity in enumerate(entities):
        prefix = "F" if entity["identity"]["entity_type"] == "fair_value_gap" else "Z"
        refs.extend(
            _draw_entity_hint(
                draw,
                entity,
                chart,
                bars,
                font,
                label=f"{prefix}{index + 1}",
                focused=True,
                used_label_y=used_label_y,
            ),
        )
    return refs


def _draw_metric_hint(draw, metric, chart, bars, font) -> list[str]:  # noqa: ANN001
    if not bars:
        return []
    raw_value = metric.get("value")
    if not isinstance(raw_value, dict) or "decimal" not in raw_value:
        return []
    value = float(raw_value["decimal"])
    prices = [_decimal(item[key]) for item in bars for key in ("low", "high")]
    low, high = min(prices), max(prices)
    span = high - low or 1.0
    low -= span * 0.08
    high += span * 0.08
    if not low <= value <= high:
        return []
    x0, y0, x1, y1 = chart
    y = int(y1 - (value - low) / (high - low) * (y1 - y0))
    draw.line((x0, y, x1, y), fill=_ACCENT, width=2)
    label = f"VALUE {raw_value['decimal']}"
    draw.rectangle((x0 + 8, y - 22, x0 + 175, y + 3), fill=_PANEL)
    draw.text((x0 + 13, y - 20), label, fill=_ACCENT, font=font)
    return [_reference_text(value) for value in metric.get("evidence_refs", [])]


def _draw_entity_hint(  # noqa: ANN001
    draw,
    entity,
    chart,
    bars,
    font,
    *,
    label: str,
    used_label_y: list[int],
    focused: bool = False,
) -> list[str]:
    payload = entity.get("payload") or {}
    x0, y0, x1, y1 = chart
    prices = [_decimal(item[key]) for item in bars for key in ("low", "high")] if bars else []
    if not prices:
        return []
    low, high = min(prices), max(prices)
    span = high - low or 1.0
    low -= span * 0.08
    high += span * 0.08
    def price_y(value: float) -> int:
        return int(y1 - (value - low) / (high - low) * (y1 - y0))

    entity_type = entity["identity"]["entity_type"]
    color = _ACCENT if focused else _MUTED
    entity_ref = f"{label}:{entity['identity']['entity_id']}@{entity['revision']}"
    for key in ("price", "high", "low", "pivot_price", "value"):
        if key in payload and payload[key] is not None:
            price = _decimal(payload[key])
            if low <= price <= high:
                y = price_y(price)
                draw.line((x0, y, x1, y), fill=color, width=3 if focused else 1)
                label_y = _label_lane(y - 9, used_label_y, y0, y1)
                draw.text((x1 - 55, label_y), label, fill=color, font=font)
            return [entity_ref]
    if entity_type == "fair_value_gap" and entity["lifecycle"] == "ACTIVE":
        lower_key = "remaining_lower"
        upper_key = "remaining_upper"
    else:
        lower_key = "lower_bound" if "lower_bound" in payload else "lower"
        upper_key = "upper_bound" if "upper_bound" in payload else "upper"
    if lower_key in payload and upper_key in payload:
        lower, upper = _decimal(payload[lower_key]), _decimal(payload[upper_key])
        if upper < low or lower > high:
            return []
        top, bottom = price_y(upper), price_y(lower)
        fill = _FVG if entity_type == "fair_value_gap" else _ZONE
        start_ns = _entity_start_ns(entity, bars[0]["interval_start_ns"])
        end_ns = bars[-1]["interval_end_ns"]
        if entity["lifecycle"] != "ACTIVE" and payload.get("terminal_ts_ns") is not None:
            end_ns = payload["terminal_ts_ns"]
        visible_start = bars[0]["interval_start_ns"]
        visible_end = bars[-1]["interval_end_ns"]
        start_ns = max(start_ns, visible_start)
        end_ns = min(end_ns, visible_end)
        if end_ns <= start_ns:
            return []
        left = _time_x(start_ns, visible_start, visible_end, x0, x1)
        right = _time_x(end_ns, visible_start, visible_end, x0, x1)
        draw.rectangle(
            (left, top, right, bottom),
            outline=fill,
            width=3 if focused else 2,
        )
        label_y = _label_lane(top + 3, used_label_y, y0, y1)
        direction = payload.get("direction", "")
        symbol = "B" if direction == "BULLISH" else ("S" if direction == "BEARISH" else "")
        draw.text((max(left + 4, x0 + 4), label_y), f"{label}{symbol}", fill=fill, font=font)
        return [entity_ref]
    return []


def _is_five_minute_entity(entity: dict[str, Any]) -> bool:
    dimensions = _dimensions(entity)
    payload = entity.get("payload") or {}
    return (
        dimensions.get("bar_specification") == "5-MINUTE-LAST-EXTERNAL"
        or dimensions.get("horizon") == "intraday_5m"
        or dimensions.get("application_id", "").endswith("-5m")
        or payload.get("bar_specification") == "5-MINUTE-LAST-EXTERNAL"
        or "intraday_5m" in payload.get("horizons", [])
    )


def _dimensions(entity: dict[str, Any]) -> dict[str, str]:
    return {
        entry["name"]: entry["value"]
        for entry in entity["identity"].get("dimensions", [])
    }


def _entity_start_ns(entity: dict[str, Any], fallback: int) -> int:
    payload = entity.get("payload") or {}
    for key in (
        "formation_start_ts_ns",
        "formation_ts_ns",
        "created_ts_ns",
        "pivot_ts_ns",
        "start_ns",
    ):
        value = payload.get(key)
        if isinstance(value, int):
            return value
    return entity.get("effective_ts_ns", fallback)


def _time_x(timestamp_ns: int, start_ns: int, end_ns: int, x0: int, x1: int) -> int:
    if end_ns <= start_ns:
        return x0
    ratio = (timestamp_ns - start_ns) / (end_ns - start_ns)
    return int(x0 + max(0.0, min(1.0, ratio)) * (x1 - x0))


def _label_lane(candidate: int, used: list[int], minimum: int, maximum: int) -> int:
    resolved = max(minimum + 2, min(candidate, maximum - 20))
    for _ in range(16):
        if all(abs(resolved - other) >= 18 for other in used):
            used.append(resolved)
            return resolved
        resolved += 18
        if resolved > maximum - 20:
            resolved = minimum + 2
    return max(minimum + 2, min(candidate, maximum - 20))


def _overview_panel(snapshot: dict[str, Any], bar_count: int) -> list[tuple[str, str]]:
    metrics = snapshot["canonical_records"]["metric_values"]
    entities = snapshot["canonical_records"]["entity_revisions"]
    ledger_items = snapshot["inventory"]["items"]
    midpoint = _latest_metric(metrics, "quote.midpoint")
    spread = _latest_metric(metrics, "quote.spread_absolute")
    lines = [
        ("heading", "CAPTURE SCOPE"),
        ("body", snapshot["identity"]["instrument_id"]),
        ("body", f"cutoff: {_utc(snapshot['frozen_at_ns'])}"),
        ("warning", "Bounded receive-cut; not transactionally complete"),
        ("heading", "LATEST KNOWLEDGE"),
        (
            "body",
            "completed 5m close: "
            f"{_decimal_text(snapshot['identity']['trigger_bar']['close'])}",
        ),
    ]
    if midpoint is not None:
        lines.append(("body", f"quote midpoint: {_display_value(midpoint['value'])}"))
    if spread is not None:
        lines.append(("body", f"quote spread: {_display_value(spread['value'])}"))
    health = Counter(item["health"] for item in metrics)
    lifecycle = Counter(item["lifecycle"] for item in entities)
    lines.extend([
        ("heading", "CAPTURED RECORDS"),
        ("body", f"five-minute bars: {bar_count}"),
        ("body", f"metric values: {len(metrics)}"),
        ("body", f"metric health: READY {health['READY']} · WARMING {health['WARMING']}"),
        ("body", f"entity revisions: {len(entities)}"),
        ("body", f"entities: ACTIVE {lifecycle['ACTIVE']} · COMPLETE {lifecycle['COMPLETE']}"),
        ("heading", "REVIEW INVENTORY"),
        ("body", f"items: {len(ledger_items)}"),
        ("body", "Human PASS/FAIL remains pending"),
    ])
    return lines


def _selected_panel(
    snapshot: dict[str, Any],
    item: dict[str, Any],
) -> tuple[list[tuple[str, str]], list[str]]:
    key = item["review_key"]
    lines = [
        ("heading", "SELECTED REVIEW ITEM"),
        ("body", key["definition_or_metric_id"]),
        ("body", f"kind: {key['item_kind']}"),
        ("body", f"application: {key['application_id']}"),
        ("body", f"horizon: {key['analytical_horizon']}"),
        ("body", f"source: {key['source_bar_specification']}"),
        ("body", f"producer: {key['producer_id']}"),
        ("heading", "CAPTURE STATUS"),
        ("warning" if "NOT_OBSERVED" in item["capture_status"] else "body", item["capture_status"]),
        ("body", f"activation: {item['activation_state']}"),
        ("body", f"representation: {item['representation']}"),
        ("heading", "HUMAN REVIEW"),
        ("body", item["human_review_outcome"]),
        ("body", f"identity: {item['identity_digest'][:16]}…"),
    ]
    records = _matching_records(snapshot, item)
    refs: list[str] = []
    lines.extend([("heading", "MATCHING CANONICAL RECORD"), ("body", f"count: {len(records)}")])
    if not records:
        empty_message = {
            "PURE_ONLY_NO_RUNTIME_PRODUCER": "No runtime producer by design",
            "DEFERRED_BY_ACCEPTED_PLAN": "Deferred by accepted plan",
            "NOT_IMPLEMENTED": "Not implemented",
        }.get(item["capture_status"], "No compatible record by capture cutoff")
        lines.append(("warning", empty_message))
        return lines, refs
    record = records[-1]
    if key["item_kind"] == "metric":
        lines.extend(
            [
                ("body", f"value: {_display_value(record.get('value'))} {record['unit']}"),
                ("body", f"health/fidelity: {record['health']} / {record['fidelity']}"),
                ("body", f"revision: {record['revision']}"),
                ("body", f"effective: {_utc(record['effective_ts_ns'])}"),
                ("body", f"published: {_utc(record['published_ts_ns'])}"),
                (
                    "body",
                    "age at cutoff: "
                    f"{_age(snapshot['frozen_at_ns'], record['published_ts_ns'])}",
                ),
                ("body", f"missing: {', '.join(record['missing_reasons']) or 'none'}"),
                ("body", f"record: {record['metric_id']}@r{record['revision']}"),
            ],
        )
        refs.extend(_reference_text(value) for value in record.get("evidence_refs", []))
    else:
        lifecycle_counts = Counter(value["lifecycle"] for value in records)
        state_summary = " · ".join(
            f"{key} {value}" for key, value in sorted(lifecycle_counts.items())
        )
        lines.extend([
            ("body", f"states: {state_summary}"),
            ("body", f"latest lifecycle: {record['lifecycle']}"),
            ("body", f"health/fidelity: {record['health']} / {record['fidelity']}"),
            ("body", f"revision: {record['revision']}"),
            ("body", f"effective: {_utc(record['effective_ts_ns'])}"),
            ("body", f"published: {_utc(record['published_ts_ns'])}"),
            ("body", f"missing: {', '.join(record['missing_reasons']) or 'none'}"),
            ("body", f"conflicts: {', '.join(record['conflict_reasons']) or 'none'}"),
            *_entity_summary_lines(record),
            ("body", f"entity: {record['identity']['entity_id'][-16:]}@r{record['revision']}"),
            ("body", "Exact payload and evidence refs: projection-snapshot.json"),
        ])
        dimensions = _dimensions(record)
        if "application_id" not in dimensions:
            lines.append(("warning", "Application ID not canonically distinguishable"))
        refs.extend(canonical_json(value) for value in record.get("evidence_refs", []))
    return lines, refs


def _matching_records(
    snapshot: dict[str, Any],
    item: dict[str, Any],
) -> list[dict[str, Any]]:
    key = item["review_key"]
    if key["item_kind"] == "metric":
        parameter_version = int(key["parameter_identity"].rsplit(":", 1)[-1])
        records = [
            record
            for record in snapshot["canonical_records"]["metric_values"]
            if record["metric_id"] == key["definition_or_metric_id"]
            and record["metric_version"] == key["definition_or_metric_version"]
            and record["parameter_version"] == parameter_version
            and record["instrument_id"] == key["instrument_id"]
        ]
        return sorted(records, key=lambda record: (record["published_ts_ns"], record["revision"]))
    if key["item_kind"] != "entity_application":
        return []
    records = []
    for record in snapshot["canonical_records"]["entity_revisions"]:
        identity = record["identity"]
        if (
            identity["entity_type"] != item["canonical_subject_id"]
            or identity["entity_version"] != key["definition_or_metric_version"]
            or identity["instrument_id"] != key["instrument_id"]
            or identity["analytical_profile_id"] != key["analytical_profile_id"]
            or identity["analytical_profile_version"] != key["analytical_profile_version"]
        ):
            continue
        dimensions = {entry["name"]: entry["value"] for entry in identity["dimensions"]}
        constraints = {
            "definition_id": key["definition_or_metric_id"],
            "horizon": key["analytical_horizon"],
            "bar_specification": key["source_bar_specification"],
            "application_id": key["application_id"],
        }
        mismatched = any(
            name in dimensions and dimensions[name] != value
            for name, value in constraints.items()
        )
        if mismatched:
            continue
        records.append(record)
    return sorted(records, key=lambda record: (record["published_ts_ns"], record["revision"]))


def _display_value(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict) and set(value) == {"decimal"}:
        return value["decimal"]
    if isinstance(value, str | int | float | bool):
        return str(value)
    return canonical_json(value)


def _reference_text(value: Any) -> str:
    return value if isinstance(value, str) else canonical_json(value)


def _latest_metric(metrics: list[dict[str, Any]], metric_id: str) -> dict[str, Any] | None:
    candidates = [item for item in metrics if item["metric_id"] == metric_id]
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item["published_ts_ns"], item["revision"]))


def _entity_summary_lines(record: dict[str, Any]) -> list[tuple[str, str]]:
    payload = record.get("payload") or {}
    entity_type = record["identity"]["entity_type"]
    lines: list[tuple[str, str]] = []
    if entity_type == "fair_value_gap":
        lines.extend([
            ("body", f"direction: {payload.get('direction', 'n/a')}"),
            ("body", f"remaining: {_bounds(payload, 'remaining_lower', 'remaining_upper')}"),
            ("body", f"fill ratio: {_display_value(payload.get('fill_ratio'))}"),
            ("body", f"formed: {_utc_optional(payload.get('formation_ts_ns'))}"),
            ("body", f"terminal: {_utc_optional(payload.get('terminal_ts_ns'))}"),
        ])
    elif entity_type == "derived_zone":
        lines.extend([
            ("body", f"bounds: {_bounds(payload, 'lower', 'upper')}"),
            ("body", f"constituents: {len(payload.get('constituents', []))}"),
            ("body", f"created: {_utc_optional(payload.get('created_ts_ns'))}"),
        ])
    elif "pivot_price" in payload:
        lines.extend([
            ("body", f"pivot: {_display_value(payload.get('pivot_price'))}"),
            ("body", f"kind: {payload.get('kind', 'n/a')}"),
            ("body", f"pivot time: {_utc_optional(payload.get('pivot_ts_ns'))}"),
        ])
    elif "price" in payload:
        lines.append(("body", f"price: {_display_value(payload.get('price'))}"))
    elif "lower" in payload and "upper" in payload:
        lines.append(("body", f"bounds: {_bounds(payload, 'lower', 'upper')}"))
    return lines


def _bounds(payload: dict[str, Any], lower_key: str, upper_key: str) -> str:
    lower = payload.get(lower_key)
    upper = payload.get(upper_key)
    if lower is None or upper is None:
        return "n/a"
    return f"{_display_value(lower)} to {_display_value(upper)}"


def _draw_panel(draw, panel, lines, heading_font, body_font, small_font) -> None:  # noqa: ANN001
    x0, y0, _, y1 = panel
    y = y0 + 24
    for style, value in lines:
        font = heading_font if style == "heading" else body_font
        fill = _WARNING if style == "warning" else (_TEXT if style == "heading" else _MUTED)
        width = 30 if style == "heading" else 42
        wrapped = wrap(
            str(value),
            width=width,
            break_long_words=True,
            break_on_hyphens=False,
        ) or [""]
        line_height = 30 if style == "heading" else 25
        required = len(wrapped) * line_height + (10 if style == "heading" else 4)
        if y + required > y1 - 42:
            draw.text(
                (x0 + 20, y1 - 34),
                "Additional exact detail: review-report.md / JSON",
                fill=_WARNING,
                font=small_font,
            )
            return
        for line in wrapped:
            draw.text((x0 + 20, y), line, fill=fill, font=font)
            y += line_height
        y += 10 if style == "heading" else 4


def _review_report(snapshot: dict[str, Any], items: list[dict[str, Any]]) -> str:
    activation = Counter(item["activation_state"] for item in items)
    capture_status = Counter(item["capture_status"] for item in items)
    human = Counter(item["human_review_outcome"] for item in items)
    trigger_end = snapshot["identity"]["trigger_bar"]["interval_end_ns"]
    timing_delta = snapshot["frozen_at_ns"] - trigger_end
    lines = [
        "# Markeitech Live Evidence Review — Renderer V2",
        "",
        f"- Run ID: `{snapshot['run_id']}`",
        f"- Capture ID: `{snapshot['capture_id']}`",
        f"- Instrument: `{snapshot['identity']['instrument_id']}`",
        f"- Frozen at: `{_utc(snapshot['frozen_at_ns'])}` (`{snapshot['frozen_at_ns']}` ns)",
        f"- Trigger interval ended at: `{_utc(trigger_end)}`",
        f"- Freeze minus trigger end: `{timing_delta}` ns",
        f"- Completeness: `{snapshot['capture_completeness']}`",
        f"- Inventory digest: `{snapshot['identity']['inventory_digest']}`",
        "- Human review outcomes remain pending until Markeitect reviews each focused frame.",
        "",
        "## Reconciliation summary",
        "",
        f"- Total inventory: **{len(items)}**",
        f"- Activation: `{dict(sorted(activation.items()))}`",
        f"- Capture status: `{dict(sorted(capture_status.items()))}`",
        f"- Human outcome: `{dict(sorted(human.items()))}`",
        "",
    ]
    if timing_delta < 0:
        lines.extend([
            "> **Temporal warning:** this V1 capture froze before the trigger bar's declared "
            "interval end. Retain it as renderer evidence; do not treat its cutoff as temporal "
            "acceptance.",
            "",
        ])
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in items:
        grouped[_report_group(item)].append(item)
    lines.extend(["## Review groups", ""])
    for group in _REPORT_GROUPS:
        group_items = grouped.get(group, [])
        if group_items:
            lines.append(f"- [{group}](#{_anchor(group)}) — {len(group_items)}")
    lines.append("")
    for group in _REPORT_GROUPS:
        group_items = grouped.get(group, [])
        if not group_items:
            continue
        lines.extend([
            f"## {group}",
            "",
            "| Item | Application | Horizon | Status | Latest value/state | Health/fidelity | "
            "UTC effective | Focused frame |",
            "|---|---|---|---|---|---|---|---|",
        ])
        for item in sorted(group_items, key=_report_sort_key):
            key = item["review_key"]
            records = _matching_records(snapshot, item)
            latest = records[-1] if records else None
            value, health, effective = _report_record_summary(latest)
            cells = (
                key["definition_or_metric_id"],
                key["application_id"],
                key["analytical_horizon"],
                item["capture_status"],
                value,
                health,
                effective,
                f"[{item['identity_digest'][:12]}]({item['focused_artifact']})",
            )
            lines.append("| " + " | ".join(_md(value) for value in cells) + " |")
        lines.append("")
    lines.extend(
        [
            "",
            "## Review boundary",
            "",
            "This report is a source-faithful projection of a bounded receive-cut "
            "containing records received before the capture cutoff. It is not canonical "
            "market truth, a transactionally complete analytical snapshot, formula "
            "validation, a signal, an opportunity, or Sir Loke output.",
            "",
        ],
    )
    return "\n".join(lines)


_REPORT_GROUPS = (
    "Quote metrics",
    "Completed-bar foundation",
    "Session and reference metrics",
    "Opening range",
    "Power hour",
    "Rolling fast",
    "Rolling tactical",
    "Rolling structural",
    "Entity applications",
    "Missing enabled items",
    "Pure-only components",
    "Deferred components",
)


def _report_group(item: dict[str, Any]) -> str:
    key = item["review_key"]
    if item["capture_status"] == "NOT_OBSERVED_BY_CAPTURE_CUTOFF":
        return "Missing enabled items"
    if key["item_kind"] == "pure_component":
        return "Pure-only components"
    if key["item_kind"] == "deferred_component":
        return "Deferred components"
    if key["item_kind"] == "entity_application":
        return "Entity applications"
    metric_id = key["definition_or_metric_id"]
    if metric_id.startswith("quote."):
        return "Quote metrics"
    if metric_id.startswith("completed_bar."):
        return "Completed-bar foundation"
    if metric_id.startswith("opening_range."):
        return "Opening range"
    if metric_id.startswith("power_hour."):
        return "Power hour"
    if metric_id.startswith("rolling.fast."):
        return "Rolling fast"
    if metric_id.startswith("rolling.tactical."):
        return "Rolling tactical"
    if metric_id.startswith("rolling.structural_intraday."):
        return "Rolling structural"
    return "Session and reference metrics"


def _report_sort_key(item: dict[str, Any]) -> tuple[str, ...]:
    key = item["review_key"]
    return (
        key["analytical_horizon"],
        key["application_id"],
        key["definition_or_metric_id"],
        key["parameter_identity"],
        item["identity_digest"],
    )


def _report_record_summary(record: dict[str, Any] | None) -> tuple[str, str, str]:
    if record is None:
        return "not observed", "n/a", "n/a"
    if "metric_id" in record:
        value = f"{_display_value(record.get('value'))} {record['unit']}"
    else:
        value = f"{record['lifecycle']} r{record['revision']}"
    return (
        value,
        f"{record['health']} / {record['fidelity']}",
        _utc(record["effective_ts_ns"]),
    )


def _anchor(value: str) -> str:
    return value.lower().replace(" ", "-")


def _latest_entities(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    latest = {}
    for item in snapshot["canonical_records"]["entity_revisions"]:
        entity_id = item["identity"]["entity_id"]
        existing = latest.get(entity_id)
        if existing is None or item["revision"] > existing["revision"]:
            latest[entity_id] = item
    return sorted(
        latest.values(),
        key=lambda item: (item["effective_ts_ns"], item["identity"]["entity_id"]),
    )


def _newest(items: list[dict[str, Any]], count: int) -> list[dict[str, Any]]:
    ordered = sorted(
        items,
        key=lambda item: (item["effective_ts_ns"], item["identity"]["entity_id"]),
    )
    return ordered[-count:]


def _decimal(value: Any) -> float:
    if isinstance(value, dict) and set(value) == {"decimal"}:
        return float(value["decimal"])
    raise ValueError("expected exact decimal wrapper")


def _decimal_text(value: Any) -> str:
    if isinstance(value, dict) and set(value) == {"decimal"}:
        return value["decimal"]
    raise ValueError("expected exact decimal wrapper")


def _utc(timestamp_ns: int, pattern: str = "%Y-%m-%d %H:%M:%S.%f UTC") -> str:
    value = datetime.fromtimestamp(timestamp_ns / 1_000_000_000, tz=UTC)
    rendered = value.strftime(pattern)
    if "%f" in pattern:
        rendered = rendered.replace(f"{value.microsecond:06d}", f"{value.microsecond // 1000:03d}")
    return rendered


def _utc_optional(timestamp_ns: Any) -> str:
    return "n/a" if not isinstance(timestamp_ns, int) else _utc(timestamp_ns)


def _age(cutoff_ns: int, timestamp_ns: int) -> str:
    delta_ns = cutoff_ns - timestamp_ns
    sign = "future by " if delta_ns < 0 else ""
    return f"{sign}{abs(delta_ns) / 1_000_000_000:.3f}s"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _required_text(value: dict[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"missing {key}")
    return result


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


if __name__ == "__main__":
    raise SystemExit(main())
