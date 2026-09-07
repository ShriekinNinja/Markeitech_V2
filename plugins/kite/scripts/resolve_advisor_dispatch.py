"""Offline advisor-capacity preflight and bounded dispatch admission.

Consumes sanitized host evidence; never spawns, closes threads, polls, or changes host settings.
Digests detect inconsistent records, not forged evidence. The primary owns evidence collection.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

from resolve_advisor_allocation import (
    AllocationError,
    digest,
    integer,
    read_json,
    require,
    strings,
    table,
    text,
    validate_decision,
    validate_policy,
)

REFERENCES = Path(__file__).resolve().parents[1] / "skills/markeitech-advisor-router/references"


def boolean(value: object) -> bool:
    require(type(value) is bool, "INVALID_BOOLEAN")
    return value


def records(value: object) -> list:
    require(isinstance(value, list) and len(value) <= 128, "INVALID_LIST")
    return value


def version(value: object) -> None:
    require(type(value) is int and value == 1, "DISPATCH_VERSION")


def host_snapshot(host: dict) -> dict:
    """Count all open threads, including completed ones; closed requires release evidence."""
    table(
        host,
        {
            "snapshot_id",
            "task_id",
            "evidence",
            "thread_limit",
            "limit_scope",
            "primary_threads",
            "inventory_complete",
            "close_supported",
            "threads",
        },
    )
    for key in ("snapshot_id", "task_id", "evidence"):
        text(host[key])
    require(
        host["limit_scope"] in {"including_primary", "spawned_only", "unknown"},
        "INVALID_LIMIT_SCOPE",
    )
    if host["thread_limit"] is not None:
        integer(host["thread_limit"])
    primary = integer(host["primary_threads"], 1)
    boolean(host["inventory_complete"])
    if host["close_supported"] is not None:
        boolean(host["close_supported"])
    ids, consultations, open_ids, closable, reclaimable = set(), set(), set(), [], []
    for thread in records(host["threads"]):
        table(
            thread,
            {
                "thread_id",
                "role",
                "consultation_id",
                "state",
                "owned_by_task",
                "retain",
                "result_evidence",
                "release_evidence",
            },
        )
        tid = text(thread["thread_id"])
        text(thread["role"])
        require(tid not in ids, "DUPLICATE_THREAD")
        ids.add(tid)
        if thread["consultation_id"] is not None:
            cid = text(thread["consultation_id"])
            require(cid not in consultations, "DUPLICATE_CONSULTATION_THREAD")
            consultations.add(cid)
        require(
            thread["state"] in {"running", "completed", "closed", "unknown"}, "INVALID_THREAD_STATE"
        )
        boolean(thread["owned_by_task"])
        boolean(thread["retain"])
        for key in ("result_evidence", "release_evidence"):
            if thread[key] is not None:
                text(thread[key])
        if thread["state"] == "closed":
            require(thread["release_evidence"] is not None, "RELEASE_UNVERIFIED")
        else:
            require(thread["release_evidence"] is None, "INCONSISTENT_RELEASE")
            open_ids.add(tid)
            if thread["owned_by_task"] and not thread["retain"]:
                if thread["state"] == "running":
                    reclaimable.append(tid)
                elif thread["state"] == "completed" and thread["result_evidence"] is not None:
                    reclaimable.append(tid)
                    closable.append(tid)
    known = (
        host["inventory_complete"]
        and host["thread_limit"] is not None
        and host["limit_scope"] != "unknown"
    )
    slots = None
    if known:
        slots = host["thread_limit"] - (
            primary if host["limit_scope"] == "including_primary" else 0
        )
        require(slots >= 0, "INVALID_THREAD_LIMIT")
    return {
        "slots": slots,
        "free": None if slots is None else max(0, slots - len(open_ids)),
        "open_ids": sorted(open_ids),
        "closable": sorted(closable),
        "reclaimable": sorted(reclaimable),
    }


def plan(record: dict, council: dict) -> dict:
    """Preflight the entire selected DAG before consuming any of its remaining slots."""
    table(record, {"schema_version", "plan_id", "selected", "host"})
    version(record["schema_version"])
    text(record["plan_id"])
    validate_policy(council)
    roles = {a["role"] for a in council["advisors"]}
    selected = {}
    for item in records(record["selected"]):
        table(item, {"consultation_id", "role", "question", "after", "state", "evidence"})
        cid = text(item["consultation_id"])
        require(cid not in selected, "DUPLICATE_CONSULTATION")
        require(text(item["role"]) in roles, "UNKNOWN_ROLE")
        text(item["question"])
        strings(item["after"], empty=True)
        require(
            item["state"] in {"pending", "running", "completed", "blocked"},
            "INVALID_CONSULTATION_STATE",
        )
        if item["evidence"] is not None:
            text(item["evidence"])
        require(
            item["state"] == "pending" or item["evidence"] is not None,
            "CONSULTATION_EVIDENCE_MISSING",
        )
        selected[cid] = item
    remaining, ordered = set(selected), []
    for item in selected.values():
        require(set(item["after"]) <= selected.keys(), "UNKNOWN_DEPENDENCY")
    while remaining:
        ready = sorted(
            (cid for cid in remaining if set(selected[cid]["after"]) <= set(ordered)),
            key=lambda cid: (selected[cid]["role"], cid),
        )
        require(bool(ready), "DEPENDENCY_CYCLE")
        ordered.extend(ready)
        remaining.difference_update(ready)
    host = record["host"]
    capacity = host_snapshot(host)
    linked = {t["consultation_id"]: t for t in host["threads"] if t["consultation_id"] in selected}
    for cid, thread in linked.items():
        require(thread["role"] == selected[cid]["role"], "THREAD_ROLE_MISMATCH")
        require(thread["owned_by_task"], "THREAD_OWNERSHIP_MISMATCH")
    blocked, completed, pending, eligible = [], [], [], []
    reconcile = False
    for cid in ordered:
        item = selected[cid]
        thread = linked.get(cid)
        if item["state"] == "completed":
            require(
                all(selected[d]["state"] == "completed" for d in item["after"]),
                "DEPENDENCY_NOT_COMPLETED",
            )
            require(
                thread is None or thread["state"] in {"completed", "closed"},
                "THREAD_STATE_MISMATCH",
            )
            completed.append({"consultation_id": cid, "evidence": item["evidence"]})
        elif item["state"] == "blocked" or any(d in blocked for d in item["after"]):
            blocked.append(cid)
        elif item["state"] == "running":
            require(thread is not None, "RUNNING_THREAD_MISSING")
            require(
                all(selected[d]["state"] == "completed" for d in item["after"]),
                "DEPENDENCY_NOT_COMPLETED",
            )
            reconcile |= thread["state"] != "running"
        else:
            pending.append(cid)
            reconcile |= thread is not None
            if all(selected[d]["state"] == "completed" for d in item["after"]):
                eligible.append(cid)
    status = "READY"
    if reconcile:
        status = "RECONCILE_REQUIRED"
    elif not pending:
        status = (
            "WAITING"
            if any(i["state"] == "running" for i in selected.values())
            else "BLOCKED_DEPENDENCIES"
            if blocked
            else "COMPLETE"
        )
    elif capacity["free"] is None:
        status = "CAPACITY_UNKNOWN"
    elif host["close_supported"] is not True and len(pending) > capacity["free"]:
        status = "PLAN_CAPACITY_BLOCKED"
    elif capacity["slots"] == 0:
        status = "CAPACITY_BLOCKED"
    elif capacity["free"] == 0:
        status = (
            "CLOSE_REQUIRED"
            if host["close_supported"] and capacity["closable"]
            else "WAITING"
            if host["close_supported"] and capacity["reclaimable"]
            else "CAPACITY_BLOCKED"
        )
    elif not eligible:
        status = "WAITING"
    return {
        "schema_version": 1,
        "status": status,
        "plan_id": record["plan_id"],
        "host_snapshot_id": host["snapshot_id"],
        "free_slots": capacity["free"],
        "eligible": eligible,
        "pending": pending,
        "blocked": blocked,
        "completed": completed,
        "close_candidates": capacity["closable"] if host["close_supported"] else [],
    }


def capacity_changed(before: dict, after: dict) -> None:
    """Require a fresh observation of fewer open threads or a larger usable limit."""
    old, new = host_snapshot(before), host_snapshot(after)
    require(before["task_id"] == after["task_id"], "TASK_MISMATCH")
    require(before["snapshot_id"] != after["snapshot_id"], "STALE_CAPACITY_SNAPSHOT")
    require(old["slots"] is not None and new["slots"] is not None, "CAPACITY_UNKNOWN")
    require(
        new["free"] > 0
        and (new["slots"] > old["slots"] or len(new["open_ids"]) < len(old["open_ids"])),
        "CAPACITY_UNCHANGED",
    )


def admit(request: dict, council: dict, policy: dict) -> dict:
    """Authorize one serialized dispatch; a refused launch is not a model execution retry."""
    table(policy, {"schema_version", "policy_version", "max_capacity_retries"})
    version(policy["schema_version"])
    text(policy["policy_version"])
    require(integer(policy["max_capacity_retries"]) <= 3, "INVALID_DISPATCH_BUDGET")
    table(request, {"schema_version", "plan", "consultation_id", "decision", "history"})
    version(request["schema_version"])
    result = plan(request["plan"], council)
    require(result["status"] == "READY", result["status"])
    cid = text(request["consultation_id"])
    require(cid in result["eligible"], "DEPENDENCY_NOT_READY")
    decision = request["decision"]
    validate_decision(decision)
    item = next(i for i in request["plan"]["selected"] if i["consultation_id"] == cid)
    require(decision["policy_version"] == council["policy_version"], "POLICY_MISMATCH")
    for key in ("consultation_id", "role", "question"):
        require(decision[key] == item[key], "CONSULTATION_MISMATCH")
    binding = digest(
        {
            "plan_id": request["plan"]["plan_id"],
            "council": digest(council),
            "dispatch_policy": policy,
            "selected": sorted(
                [
                    {k: v for k, v in i.items() if k not in {"state", "evidence"}}
                    for i in request["plan"]["selected"]
                ],
                key=lambda i: i["consultation_id"],
            ),
        }
    )
    history = records(request["history"])
    previous = None
    for index, entry in enumerate(history):
        table(
            entry,
            {
                "admission",
                "outcome",
                "execution_id",
                "no_child_confirmed",
                "evidence",
                "host_after",
            },
        )
        prior = table(
            entry["admission"],
            {
                "schema_version",
                "status",
                "admission_id",
                "binding",
                "decision_id",
                "consultation_id",
                "role",
                "host",
                "dispatch_number",
            },
        )
        version(prior["schema_version"])
        require(
            prior["admission_id"]
            == digest({k: v for k, v in prior.items() if k != "admission_id"}),
            "ADMISSION_MISMATCH",
        )
        require(prior["status"] == "DISPATCH_READY", "ADMISSION_STATUS")
        require(
            prior["binding"] == binding
            and prior["decision_id"] == decision["decision_id"]
            and prior["consultation_id"] == cid
            and prior["role"] == decision["role"],
            "DISPATCH_HISTORY_MISMATCH",
        )
        require(integer(prior["dispatch_number"], 1) == index + 1, "DISPATCH_HISTORY_ORDER")
        text(entry["evidence"])
        boolean(entry["no_child_confirmed"])
        require(
            entry["outcome"] in {"capacity_rejected", "started", "failed", "unknown"},
            "INVALID_DISPATCH_OUTCOME",
        )
        if entry["execution_id"] is not None:
            text(entry["execution_id"])
            require(not entry["no_child_confirmed"], "INCONSISTENT_LAUNCH")
        require(entry["outcome"] != "started", "ALREADY_STARTED")
        require(entry["outcome"] != "unknown", "RECONCILE_REQUIRED")
        require(entry["outcome"] == "capacity_rejected", "EXECUTION_RETRY_NOT_AUTHORIZED")
        require(entry["execution_id"] is None and entry["no_child_confirmed"], "RECONCILE_REQUIRED")
        host_snapshot(prior["host"])
        host_snapshot(entry["host_after"])
        require(prior["host"]["task_id"] == entry["host_after"]["task_id"], "TASK_MISMATCH")
        require(
            prior["host"]["snapshot_id"] != entry["host_after"]["snapshot_id"],
            "STALE_CAPACITY_SNAPSHOT",
        )
        require(
            not any(
                t["consultation_id"] == cid
                for h in (prior["host"], entry["host_after"])
                for t in h["threads"]
            ),
            "INCONSISTENT_LAUNCH",
        )
        if previous is not None:
            capacity_changed(previous, prior["host"])
        previous = entry["host_after"]
    require(len(history) <= policy["max_capacity_retries"], "DISPATCH_BUDGET_EXHAUSTED")
    if previous is not None:
        capacity_changed(previous, request["plan"]["host"])
    admission = {
        "schema_version": 1,
        "status": "DISPATCH_READY",
        "binding": binding,
        "decision_id": decision["decision_id"],
        "consultation_id": cid,
        "role": decision["role"],
        "host": request["plan"]["host"],
        "dispatch_number": len(history) + 1,
    }
    admission["admission_id"] = digest(admission)
    return admission


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "admit"))
    parser.add_argument("--record", type=Path, required=True, help="JSON path or - for stdin")
    args = parser.parse_args(argv)
    try:
        council = tomllib.loads((REFERENCES / "council-policy.toml").read_text())
        record = read_json(args.record)
        if args.command == "plan":
            result = plan(record, council)
        else:
            policy = tomllib.loads((REFERENCES / "dispatch-policy.toml").read_text())
            result = admit(record, council, policy)
    except (AllocationError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        reason = str(exc) if isinstance(exc, AllocationError) else "INVALID_INPUT"
        print(json.dumps({"schema_version": 1, "status": "BLOCKED", "reason": reason}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
