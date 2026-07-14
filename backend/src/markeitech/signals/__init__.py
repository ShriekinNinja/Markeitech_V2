"""Deterministic signal contracts and lifecycle rules."""

from markeitech.signals.contracts import (
    SignalDirection,
    SignalEvidenceFidelity,
    SignalEvidenceReference,
    SignalEvidenceStage,
    SignalEvidenceType,
    SignalFamily,
    SignalSnapshot,
    SignalStatus,
    SignalTransitionEvent,
    signal_setup_key,
)
from markeitech.signals.lifecycle import transition_signal

__all__ = [
    "SignalDirection",
    "SignalEvidenceFidelity",
    "SignalEvidenceReference",
    "SignalEvidenceStage",
    "SignalEvidenceType",
    "SignalFamily",
    "SignalSnapshot",
    "SignalStatus",
    "SignalTransitionEvent",
    "signal_setup_key",
    "transition_signal",
]
