from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import defaultdict
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
    args = parser.parse_args(argv)
    try:
        render_review(args.capture_directory)
    except Exception as exc:
        print(f"live evidence review render failed: {type(exc).__name__}", file=sys.stderr)
        return 1
    return 0


def render_review(pending_directory: Path) -> Path:
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
    root = pending_directory.parents[2]
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
            "schema_version": 1,
            "capture_id": capture_id,
            "run_id": run_id,
            "renderer": "Pillow",
            "pillow_version": Image.__version__,
            "dimensions": [width, height],
            "inventory_count": len(items),
            "artifact_count": expected_pngs,
            "source_to_mark_references": sources,
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
    chart = (70, 125, 1410, 840)
    volume = (70, 855, 1410, 1000)
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
    for step in range(1, 5):
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
    close_label = f"latest completed 5m close: {_decimal_text(bars[-1]['close'])}"
    draw.text((x1 - 260, y0 + 8), close_label, fill=_TEXT, font=font)
    return refs


def _draw_overview_geometry(draw, snapshot, chart, bars, font) -> list[str]:  # noqa: ANN001
    latest = _latest_entities(snapshot)
    selected: list[dict[str, Any]] = []
    by_type = defaultdict(list)
    for entity in latest:
        by_type[entity["identity"]["entity_type"]].append(entity)
    primary = {
        "previous_session_reference", "opening_range",
        "objective_level.previous_session_high", "objective_level.previous_session_low",
        "objective_level.opening_range_high", "objective_level.opening_range_low",
    }
    for entity_type in sorted(primary):
        selected.extend(by_type[entity_type])
    selected.extend(_newest(by_type["confirmed_swing"], 2))
    selected.extend(_newest(by_type["pivot_structure_state"], 1))
    selected.extend(_newest(by_type["fair_value_gap"], 2))
    selected.extend(_newest(by_type["derived_zone"], 2))
    selected.extend(_newest([
        item for item in latest if item["identity"]["entity_type"].startswith("reference_state.")
    ], 1))
    refs = []
    for index, entity in enumerate(selected):
        refs.extend(_draw_entity_hint(draw, entity, chart, bars, font, index))
    return refs


def _draw_selected_geometry(draw, snapshot, selected, chart, bars, font) -> list[str]:  # noqa: ANN001
    if selected["representation"] != "geometry":
        return []
    subject = selected["canonical_subject_id"]
    entities = [
        item for item in _latest_entities(snapshot)
        if item["identity"]["entity_type"] == subject
    ]
    refs = []
    for index, entity in enumerate(entities):
        refs.extend(_draw_entity_hint(draw, entity, chart, bars, font, index, focused=True))
    return refs


def _draw_entity_hint(draw, entity, chart, bars, font, index, focused=False) -> list[str]:  # noqa: ANN001
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
    for key in ("price", "high", "low", "pivot_price", "value"):
        if key in payload and payload[key] is not None:
            price = _decimal(payload[key])
            if low <= price <= high:
                y = price_y(price)
                draw.line((x0, y, x1, y), fill=color, width=3 if focused else 1)
                draw.text((x0 + 8, y - 20), entity_type, fill=color, font=font)
            return [entity["identity"]["entity_id"]]
    lower_key = "lower_bound" if "lower_bound" in payload else "lower"
    upper_key = "upper_bound" if "upper_bound" in payload else "upper"
    if lower_key in payload and upper_key in payload:
        lower, upper = _decimal(payload[lower_key]), _decimal(payload[upper_key])
        top, bottom = price_y(upper), price_y(lower)
        fill = _FVG if entity_type == "fair_value_gap" else _ZONE
        draw.rectangle(
            (x0 + 25 + index * 8, top, x1 - 25, bottom),
            outline=fill,
            width=3 if focused else 2,
        )
        draw.text((x0 + 35, top + 4), entity_type, fill=fill, font=font)
        return [entity["identity"]["entity_id"]]
    return []


def _overview_panel(snapshot: dict[str, Any], bar_count: int) -> list[tuple[str, str]]:
    metrics = snapshot["canonical_records"]["metric_values"]
    entities = snapshot["canonical_records"]["entity_revisions"]
    return [
        ("heading", "CAPTURE SCOPE"),
        ("body", snapshot["identity"]["instrument_id"]),
        ("body", f"cutoff ns: {snapshot['frozen_at_ns']}"),
        ("warning", "Bounded receive-cut; not transactionally complete"),
        ("heading", "CAPTURED RECORDS"),
        ("body", f"five-minute bars: {bar_count}"),
        ("body", f"metric values: {len(metrics)}"),
        ("body", f"entity revisions: {len(entities)}"),
        ("heading", "REVIEW INVENTORY"),
        ("body", f"items: {len(snapshot['inventory']['items'])}"),
        ("body", "Human PASS/FAIL remains pending"),
        ("heading", "LIMITS"),
        ("body", "No display-derived analysis"),
        ("body", "No Sir Loke, signal, setup, or opportunity semantics"),
    ]


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
        lines.append(("warning", "No compatible record by capture cutoff"))
        return lines, refs
    record = records[-1]
    if key["item_kind"] == "metric":
        lines.extend(
            [
                ("body", f"value: {_display_value(record.get('value'))} {record['unit']}"),
                ("body", f"health/fidelity: {record['health']} / {record['fidelity']}"),
                ("body", f"revision: {record['revision']}"),
                ("body", f"effective ns: {record['effective_ts_ns']}"),
                ("body", f"published ns: {record['published_ts_ns']}"),
                ("body", f"missing: {', '.join(record['missing_reasons']) or 'none'}"),
            ],
        )
        refs.extend(str(value) for value in record.get("evidence_refs", []))
    else:
        lines.extend(
            [
                ("body", f"lifecycle: {record['lifecycle']}"),
                ("body", f"health/fidelity: {record['health']} / {record['fidelity']}"),
                ("body", f"revision: {record['revision']}"),
                ("body", f"effective ns: {record['effective_ts_ns']}"),
                ("body", f"published ns: {record['published_ts_ns']}"),
                ("body", f"missing: {', '.join(record['missing_reasons']) or 'none'}"),
                ("body", f"conflicts: {', '.join(record['conflict_reasons']) or 'none'}"),
                ("body", f"payload: {_display_value(record.get('payload'))}"),
            ],
        )
        refs.extend(canonical_json(value) for value in record.get("evidence_refs", []))
    return lines, refs


def _matching_records(
    snapshot: dict[str, Any],
    item: dict[str, Any],
) -> list[dict[str, Any]]:
    key = item["review_key"]
    if key["item_kind"] == "metric":
        records = [
            record
            for record in snapshot["canonical_records"]["metric_values"]
            if record["metric_id"] == key["definition_or_metric_id"]
            and record["metric_version"] == key["definition_or_metric_version"]
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


def _draw_panel(draw, panel, lines, heading_font, body_font, small_font) -> None:  # noqa: ANN001
    x0, y0, x1, _ = panel
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
        for line in wrapped:
            draw.text((x0 + 20, y), line, fill=fill, font=font)
            y += 30 if style == "heading" else 25
        y += 10 if style == "heading" else 4
        if y > 960:
            draw.text(
                (x0 + 20, 960),
                "Additional detail in review-report.md",
                fill=_WARNING,
                font=small_font,
            )
            return


def _review_report(snapshot: dict[str, Any], items: list[dict[str, Any]]) -> str:
    lines = [
        "# Markeitech Live Evidence Review",
        "",
        f"- Run ID: `{snapshot['run_id']}`",
        f"- Capture ID: `{snapshot['capture_id']}`",
        f"- Instrument: `{snapshot['identity']['instrument_id']}`",
        f"- Frozen at ns: `{snapshot['frozen_at_ns']}`",
        f"- Completeness: `{snapshot['capture_completeness']}`",
        f"- Inventory digest: `{snapshot['identity']['inventory_digest']}`",
        "- Human review outcomes remain pending until Markeitect reviews each focused frame.",
        "",
        "| Item | Kind | Application | Horizon | Source | Activation | "
        "Capture status | Human outcome | Focused frame |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in items:
        key = item["review_key"]
        path = item["focused_artifact"]
        cells = (
            key["definition_or_metric_id"], key["item_kind"], key["application_id"],
            key["analytical_horizon"], key["source_bar_specification"],
            item["activation_state"], item["capture_status"], item["human_review_outcome"],
            f"[{item['identity_digest'][:12]}]({path})",
        )
        lines.append("| " + " | ".join(_md(value) for value in cells) + " |")
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
