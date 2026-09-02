from __future__ import annotations

from markeitech.intelligence.quote_metric_actor import _format_evidence_counts


def test_evidence_counts_are_stable_and_explicit() -> None:
    assert _format_evidence_counts({"HEALTHY": 9, "DEGRADED": 3}) == "DEGRADED:3,HEALTHY:9"
    assert _format_evidence_counts({}) == "none"
