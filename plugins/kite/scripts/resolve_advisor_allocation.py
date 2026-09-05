"""Offline allocation validation for primary Kite; never spawns or calls a model.

Inputs are sanitized consultation records, not credentials or raw prompts. The host snapshot
and execution receipt are supplied evidence; this helper is not an authentication boundary.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tomllib
from pathlib import Path
from typing import Any

ADVISOR_FIELDS = {
    "role",
    "skill",
    "domain",
    "tier",
    "owns",
    "excludes",
    "inputs",
    "output",
    "default_after",
    "handoffs",
    "fresh_primary_sources",
    "network",
    "intent_version",
    "required_capabilities",
    "default_profile",
    "constraint_profile",
    "retry_profile",
}
PAIR_FIELDS = {"model", "reasoning_effort"}
OUTCOMES = {
    "completed",
    "model_unavailable",
    "execution_failure",
    "insufficient_resources",
    "unknown",
}


class AllocationError(ValueError):
    """A named allocation stop gate; messages do not echo input payloads."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise AllocationError(code)


def table(value: Any, required: set[str], optional: set[str] | None = None) -> dict:
    require(isinstance(value, dict), "INVALID_TABLE")
    require(required <= value.keys(), "MISSING_FIELD")
    require(value.keys() <= required | (optional or set()), "UNKNOWN_FIELD")
    return value


def text(value: Any) -> str:
    require(isinstance(value, str) and bool(value.strip()) and len(value) <= 4096, "INVALID_TEXT")
    return value


def integer(value: Any, minimum: int = 0) -> int:
    require(type(value) is int and minimum <= value <= 2**31 - 1, "INVALID_INTEGER")
    return value


def strings(value: Any, *, empty: bool = False) -> list[str]:
    require(isinstance(value, list) and len(value) <= 128, "INVALID_LIST")
    require(empty or bool(value), "EMPTY_LIST")
    for item in value:
        text(item)
    require(len(value) == len(set(value)), "DUPLICATE_VALUE")
    return value


def pair(value: Any, *, partial: bool = False) -> dict:
    table(value, set() if partial else PAIR_FIELDS, PAIR_FIELDS if partial else None)
    for item in value.values():
        text(item)
    return value


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def entries(value: Any) -> dict:
    require(isinstance(value, dict) and 0 < len(value) <= 128, "INVALID_REGISTRY")
    for key in value:
        text(key)
    return value


def validate_policy(policy: dict) -> None:
    """Validate the complete allocation registry without a host or model call."""
    table(
        policy,
        {
            "schema_version",
            "policy_version",
            "plugin_version",
            "router_skill",
            "allocation",
            "defaults",
            "advisors",
        },
    )
    require(
        type(policy["schema_version"]) is int and policy["schema_version"] == 3, "POLICY_VERSION"
    )
    text(policy["policy_version"])
    allocation = table(
        policy["allocation"], {"schema_version", "models", "profiles", "constraints", "retries"}
    )
    require(
        type(allocation["schema_version"]) is int and allocation["schema_version"] == 1,
        "ALLOCATION_VERSION",
    )
    models = entries(allocation["models"])
    profiles = entries(allocation["profiles"])
    constraints = entries(allocation["constraints"])
    retries = entries(allocation["retries"])
    for model in models.values():
        table(model, {"efforts", "capabilities", "evidence"})
        strings(model["efforts"])
        strings(model["capabilities"])
        text(model["evidence"])
    for profile in profiles.values():
        pair(profile)
        require(profile["model"] in models, "UNADMITTED_MODEL")
        require(
            profile["reasoning_effort"] in models[profile["model"]]["efforts"], "UNSUPPORTED_EFFORT"
        )
    require(len({digest(p) for p in profiles.values()}) == len(profiles), "DUPLICATE_PAIR")
    for constraint in constraints.values():
        table(constraint, {"profiles", "fork_modes"})
        require(set(strings(constraint["profiles"])) <= profiles.keys(), "UNKNOWN_PROFILE")
        require(set(strings(constraint["fork_modes"])) <= {"none", "bounded"}, "FORK_UNSUPPORTED")
    for retry in retries.values():
        table(
            retry,
            {
                "max_attempts",
                "max_fallbacks",
                "max_escalations",
                "fallback_profiles",
                "escalation_profiles",
            },
        )
        integer(retry["max_attempts"], 1)
        for kind in ("fallback", "escalation"):
            count = integer(retry[f"max_{kind}s"])
            names = strings(retry[f"{kind}_profiles"], empty=True)
            require(set(names) <= profiles.keys(), "UNKNOWN_PROFILE")
            require(count <= len(names) and count < retry["max_attempts"], "INVALID_RETRY_BOUNDS")
    advisors = policy["advisors"]
    require(isinstance(advisors, list) and 0 < len(advisors) <= 128, "INVALID_ADVISORS")
    roles = []
    for advisor in advisors:
        table(advisor, ADVISOR_FIELDS, {"cross_cutting"})
        roles.append(text(advisor["role"]))
        require(
            type(advisor["intent_version"]) is int and advisor["intent_version"] == 1,
            "INTENT_VERSION",
        )
        capabilities = set(strings(advisor["required_capabilities"]))
        require(advisor["constraint_profile"] in constraints, "UNKNOWN_CONSTRAINT")
        require(advisor["retry_profile"] in retries, "UNKNOWN_RETRY")
        constraint = constraints[advisor["constraint_profile"]]
        require(advisor["default_profile"] in constraint["profiles"], "DEFAULT_NOT_ALLOWED")
        default = profiles[advisor["default_profile"]]
        require(
            capabilities <= set(models[default["model"]]["capabilities"]),
            "DEFAULT_CAPABILITY_MISSING",
        )
        retry = retries[advisor["retry_profile"]]
        for name in retry["fallback_profiles"] + retry["escalation_profiles"]:
            require(name in constraint["profiles"], "RETRY_NOT_ALLOWED")
            require(
                capabilities <= set(models[profiles[name]["model"]]["capabilities"]),
                "RETRY_CAPABILITY_MISSING",
            )
    require(len(roles) == len(set(roles)), "DUPLICATE_ROLE")


def check_receipt(decision: dict, receipt: dict) -> dict:
    """Bind effective execution evidence to a validated request; unknown is not a pass."""
    table(
        decision,
        {
            "schema_version",
            "decision_id",
            "consultation_id",
            "binding",
            "policy_version",
            "intent_version",
            "host_snapshot_id",
            "role",
            "question",
            "assessment",
            "rationale",
            "source",
            "attempt",
            "kind",
            "requested",
            "fork_turns",
            "effective",
            "status",
        },
    )
    require(
        decision["decision_id"]
        == digest({k: v for k, v in decision.items() if k != "decision_id"}),
        "DECISION_MISMATCH",
    )
    require(
        type(decision["schema_version"]) is int and decision["schema_version"] == 1,
        "DECISION_VERSION",
    )
    require(
        type(decision["intent_version"]) is int and decision["intent_version"] == 1,
        "INTENT_VERSION",
    )
    integer(decision["attempt"], 1)
    require(decision["effective"] is None, "DECISION_EFFECTIVE_NOT_EMPTY")
    require(decision["status"] == "REQUEST_VALIDATED_EXECUTION_UNVERIFIED", "DECISION_STATUS")
    require(decision["kind"] in {"initial", "fallback", "escalation"}, "HISTORY_KIND")
    for key in (
        "consultation_id",
        "binding",
        "policy_version",
        "host_snapshot_id",
        "role",
        "question",
        "rationale",
        "source",
        "fork_turns",
    ):
        text(decision[key])
    pair(decision["requested"])
    table(receipt, {"decision_id", "execution_id", "effective", "outcome", "evidence"})
    require(receipt["decision_id"] == decision["decision_id"], "RECEIPT_MISMATCH")
    text(receipt["execution_id"])
    text(receipt["evidence"])
    require(receipt["outcome"] in OUTCOMES, "INVALID_OUTCOME")
    effective = receipt["effective"]
    if effective is not None:
        pair(effective)
        require(effective == decision["requested"], "EFFECTIVE_MISMATCH")
    status = "EXECUTION_UNVERIFIED"
    if receipt["outcome"] == "completed" and effective is not None:
        status = "EXECUTION_VERIFIED"
    elif receipt["outcome"] != "completed":
        status = "OUTCOME_UNKNOWN" if receipt["outcome"] == "unknown" else "EXECUTION_FAILED"
    return {"schema_version": 1, "status": status, "decision": decision, "receipt": receipt}


def resolve(policy: dict, request: dict) -> dict:
    """Resolve defaults or validate a discretionary choice, returning explicit spawn settings."""
    validate_policy(policy)
    table(
        request,
        {
            "schema_version",
            "consultation_id",
            "role",
            "question",
            "assessment",
            "rationale",
            "required_capabilities",
            "required_context_tokens",
            "kite_active",
            "sources_ready",
            "dependencies_ready",
            "host",
            "history",
            "limits",
        },
        {"user_choice", "proposed_choice", "fork_turns", "retry_kind", "user_alternatives"},
    )
    require(
        type(request["schema_version"]) is int and request["schema_version"] == 1, "REQUEST_VERSION"
    )
    for key in ("consultation_id", "role", "question", "rationale"):
        text(request[key])
    assessment = table(
        request["assessment"], {"complexity", "ambiguity", "evidence_volume", "consequence"}
    )
    for value in assessment.values():
        require(value in {"low", "medium", "high"}, "INVALID_ASSESSMENT")
    require(request["kite_active"] is True, "KITE_INACTIVE")
    require(request["sources_ready"] is True, "SOURCE_GATE")
    require(request["dependencies_ready"] is True, "DEPENDENCY_GATE")
    advisor = next((a for a in policy["advisors"] if a["role"] == request["role"]), None)
    require(advisor is not None, "UNKNOWN_ROLE")
    allocation = policy["allocation"]
    profiles = allocation["profiles"]
    constraint = allocation["constraints"][advisor["constraint_profile"]]
    retry = allocation["retries"][advisor["retry_profile"]]
    capabilities = set(strings(request["required_capabilities"], empty=True)) | set(
        advisor["required_capabilities"]
    )
    context = integer(request["required_context_tokens"])
    limits = table(request["limits"], {"max_attempts"}, {"max_cost_usd", "max_tokens"})
    max_attempts = min(integer(limits["max_attempts"]), retry["max_attempts"])
    require(not ({"max_cost_usd", "max_tokens"} & limits.keys()), "HARD_BUDGET_UNSUPPORTED")
    host = table(
        request["host"],
        {"snapshot_id", "evidence", "role", "role_overrides", "models", "fork_modes"},
    )
    text(host["snapshot_id"])
    text(host["evidence"])
    require(host["role"] == request["role"], "EXACT_ROLE_UNAVAILABLE")
    table(host["role_overrides"], set(), PAIR_FIELDS | {"model_reasoning_effort"})
    require(not host["role_overrides"], "ROLE_OVERRIDE_CONFLICT")
    host_models = entries(host["models"])
    for model in host_models.values():
        table(model, {"efforts", "capabilities", "context_tokens"})
        strings(model["efforts"])
        strings(model["capabilities"], empty=True)
        if model["context_tokens"] is not None:
            integer(model["context_tokens"], 1)
    modes = strings(host["fork_modes"])
    require(set(modes) <= {"none", "bounded"}, "FORK_UNSUPPORTED")
    fork = request.get("fork_turns", "none")
    mode = "none" if fork == "none" else "bounded"
    if mode == "bounded":
        require(
            isinstance(fork, str) and fork.isascii() and fork.isdigit() and int(fork) > 0,
            "FORK_UNSUPPORTED",
        )
        integer(int(fork), 1)
    require(mode in modes and mode in constraint["fork_modes"], "FORK_UNSUPPORTED")
    user = pair(request.get("user_choice", {}), partial=True)
    proposal = request.get("proposed_choice")
    if proposal is not None:
        pair(proposal)
    alternatives = strings(request.get("user_alternatives", []), empty=True)
    require(set(alternatives) <= set(constraint["profiles"]), "USER_ALTERNATIVE_NOT_ALLOWED")

    def check_choice(chosen: dict) -> None:
        require(chosen in [profiles[n] for n in constraint["profiles"]], "PAIR_NOT_ALLOWED")
        model_id, effort = chosen["model"], chosen["reasoning_effort"]
        require(model_id in host_models, "MODEL_UNAVAILABLE")
        require(effort in host_models[model_id]["efforts"], "HOST_EFFORT_UNSUPPORTED")
        require(
            capabilities <= set(allocation["models"][model_id]["capabilities"]),
            "POLICY_CAPABILITY_MISSING",
        )
        require(
            capabilities <= set(host_models[model_id]["capabilities"]), "HOST_CAPABILITY_MISSING"
        )
        capacity = host_models[model_id]["context_tokens"]
        require(
            context == 0 or (capacity is not None and context <= capacity),
            "CONTEXT_UNVERIFIED_OR_INSUFFICIENT",
        )

    def first_eligible(candidates: list[dict], reason: str) -> dict:
        for candidate in candidates:
            try:
                check_choice(candidate)
            except AllocationError:
                continue
            return candidate
        raise AllocationError(reason)

    binding = digest(
        {
            "policy": digest(policy),
            **{
                k: request[k]
                for k in (
                    "consultation_id",
                    "role",
                    "question",
                    "required_capabilities",
                    "required_context_tokens",
                    "limits",
                )
            },
            "user_choice": user,
            "user_alternatives": alternatives,
        }
    )
    history = request["history"]
    require(isinstance(history, list) and len(history) <= 128, "INVALID_HISTORY")
    counts = {"fallback": 0, "escalation": 0}
    previous_pairs = []
    execution_ids = set()
    for index, entry in enumerate(history):
        table(entry, {"decision", "receipt"})
        decision, receipt = entry["decision"], entry["receipt"]
        check_receipt(decision, receipt)
        require(
            decision["binding"] == binding
            and decision["consultation_id"] == request["consultation_id"],
            "HISTORY_BINDING_MISMATCH",
        )
        require(decision["attempt"] == index + 1, "HISTORY_ORDER")
        require(receipt["execution_id"] not in execution_ids, "DUPLICATE_EXECUTION")
        execution_ids.add(receipt["execution_id"])
        require(receipt["outcome"] not in {"completed", "unknown"}, "PRIOR_OUTCOME_BLOCKS_RETRY")
        kind = decision["kind"]
        require(kind == "initial" if index == 0 else kind in counts, "HISTORY_KIND")
        if kind in counts:
            counts[kind] += 1
            require(counts[kind] <= retry[f"max_{kind}s"], "HISTORY_RETRY_LIMIT")
            require(
                decision["requested"] in [profiles[n] for n in retry[f"{kind}_profiles"]],
                "HISTORY_RETRY_PAIR",
            )
        previous_pairs.append(decision["requested"])
    require(len(history) < max_attempts, "BUDGET_EXHAUSTED")
    kind = request.get("retry_kind", "initial")
    if history:
        require(kind in counts, "RETRY_KIND_REQUIRED")
        require(counts[kind] < retry[f"max_{kind}s"], "RETRY_LIMIT")
        outcome = history[-1]["receipt"]["outcome"]
        allowed_outcomes = (
            {"model_unavailable", "execution_failure"}
            if kind == "fallback"
            else {"insufficient_resources"}
        )
        require(outcome in allowed_outcomes, "RETRY_REASON")
        candidates = [
            profiles[name] for name in retry[f"{kind}_profiles"] if not user or name in alternatives
        ]
        candidates = [p for p in candidates if p not in previous_pairs]
        require(bool(candidates), "NO_AUTHORIZED_ALTERNATIVE")
        chosen = first_eligible(candidates, "NO_ELIGIBLE_ALTERNATIVE")
        require(proposal is None or proposal == chosen, "RETRY_ORDER_CONFLICT")
        source = kind
    else:
        require(kind == "initial", "INVALID_INITIAL_KIND")
        default = profiles[advisor["default_profile"]]
        if user:
            candidates = [
                p
                for p in [default, *[profiles[n] for n in constraint["profiles"]]]
                if all(p[k] == v for k, v in user.items())
            ]
            compatible_proposal = proposal is not None and all(
                proposal[k] == v for k, v in user.items()
            )
            if compatible_proposal:
                candidates = [proposal]
            require(bool(candidates), "USER_CHOICE_UNAVAILABLE")
            if len(user) == 2 or compatible_proposal:
                chosen = candidates[0]
            else:
                chosen = first_eligible(candidates, "USER_CHOICE_UNAVAILABLE")
            source = "user"
        else:
            chosen = default if proposal is None else proposal
            source = "default" if proposal is None else "judgment"
    check_choice(chosen)
    decision = {
        "schema_version": 1,
        "consultation_id": request["consultation_id"],
        "binding": binding,
        "policy_version": policy["policy_version"],
        "intent_version": advisor["intent_version"],
        "host_snapshot_id": host["snapshot_id"],
        "role": request["role"],
        "question": request["question"],
        "assessment": assessment,
        "rationale": request["rationale"],
        "source": source,
        "attempt": len(history) + 1,
        "kind": kind,
        "requested": dict(chosen),
        "fork_turns": fork,
        "effective": None,
        "status": "REQUEST_VALIDATED_EXECUTION_UNVERIFIED",
    }
    return {**decision, "decision_id": digest(decision)}


def read_json(path: Path) -> dict:
    # Sanitized control records only, bounded to 1 MiB. Do not read model prompts or logs.
    with path.open("rb") as handle:
        payload = handle.read(1024 * 1024 + 1)
    require(len(payload) <= 1024 * 1024, "INPUT_TOO_LARGE")

    def unique_keys(items: list[tuple[str, Any]]) -> dict:
        result = {}
        for key, value in items:
            require(key not in result, "DUPLICATE_KEY")
            result[key] = value
        return result

    return json.loads(payload, object_pairs_hook=unique_keys)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    resolution = sub.add_parser("resolve")
    resolution.add_argument("--request", type=Path, required=True)
    resolution.add_argument(
        "--policy",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "skills/markeitech-advisor-router/references/council-policy.toml",
    )
    receipt = sub.add_parser("receipt")
    receipt.add_argument("--decision", type=Path, required=True)
    receipt.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve":
            with args.policy.open("rb") as handle:
                policy = tomllib.load(handle)
            result = resolve(policy, read_json(args.request))
        else:
            result = check_receipt(read_json(args.decision), read_json(args.receipt))
    except (AllocationError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        reason = str(exc) if isinstance(exc, AllocationError) else "INVALID_INPUT"
        print(json.dumps({"schema_version": 1, "status": "BLOCKED", "reason": reason}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
