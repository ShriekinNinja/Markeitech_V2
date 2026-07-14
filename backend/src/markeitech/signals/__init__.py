"""Deterministic signal contracts and lifecycle rules."""

from markeitech.signals.config import (
    OpposingContextPolicy,
    SignalDefinitionConfig,
    SignalRuntimeConfig,
    intraday_context_definition,
)
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
from markeitech.signals.direction import (
    CommittedMarketContextBundle,
    DirectionCandidateDecision,
    DirectionQualification,
    DirectionQualificationStatus,
    DirectionRegimeTracker,
    qualify_direction,
)
from markeitech.signals.lifecycle import transition_signal

__all__ = [
    "SignalDirection",
    "CommittedMarketContextBundle",
    "DirectionCandidateDecision",
    "DirectionQualification",
    "DirectionQualificationStatus",
    "DirectionRegimeTracker",
    "OpposingContextPolicy",
    "SignalDefinitionConfig",
    "SignalEvidenceFidelity",
    "SignalEvidenceReference",
    "SignalEvidenceStage",
    "SignalEvidenceType",
    "SignalFamily",
    "SignalSnapshot",
    "SignalRuntimeConfig",
    "SignalStatus",
    "SignalTransitionEvent",
    "signal_setup_key",
    "qualify_direction",
    "intraday_context_definition",
    "transition_signal",
]
