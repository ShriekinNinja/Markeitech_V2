"""Synthetic host fixtures; no agent execution, host closure, or installed-cache access."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import tomllib
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
with patch.object(sys, "path", [str(SCRIPTS), *sys.path]):
    import resolve_advisor_allocation as allocation
    import resolve_advisor_dispatch as dispatch

REFERENCES = SCRIPTS.parent / "skills/markeitech-advisor-router/references"


class DispatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.council = tomllib.loads((REFERENCES / "council-policy.toml").read_text())
        self.policy = tomllib.loads((REFERENCES / "dispatch-policy.toml").read_text())
        self.allocation_request = json.loads(
            (REFERENCES / "allocation-request.example.json").read_text()
        )
        self.decision = allocation.resolve(self.council, self.allocation_request)
        self.cid = self.decision["consultation_id"]
        self.record = {
            "schema_version": 1,
            "plan_id": "synthetic-plan",
            "selected": [
                {
                    "consultation_id": self.cid,
                    "role": self.decision["role"],
                    "question": self.decision["question"],
                    "after": [],
                    "state": "pending",
                    "evidence": None,
                }
            ],
            "host": {
                "snapshot_id": "before-launch",
                "task_id": "synthetic-task",
                "evidence": "synthetic complete inventory and tool schema",
                "thread_limit": 4,
                "limit_scope": "including_primary",
                "primary_threads": 1,
                "inventory_complete": True,
                "close_supported": False,
                "threads": [],
            },
        }
        self.request = {
            "schema_version": 1,
            "plan": self.record,
            "consultation_id": self.cid,
            "decision": self.decision,
            "history": [],
        }

    def plan(self) -> dict:
        return dispatch.plan(self.record, self.council)

    def admit(self) -> dict:
        return dispatch.admit(self.request, self.council, self.policy)

    def thread(self, number: int, state: str = "completed") -> dict:
        return {
            "thread_id": f"child-{number}",
            "role": self.decision["role"],
            "consultation_id": None,
            "state": state,
            "owned_by_task": True,
            "retain": False,
            "result_evidence": "preserved findings" if state == "completed" else None,
            "release_evidence": "observed release" if state == "closed" else None,
        }

    def fill(self) -> None:
        self.record["host"]["threads"] = [self.thread(i) for i in range(3)]

    def add_pending(self, cid: str, after: list[str] | None = None) -> None:
        item = copy.deepcopy(self.record["selected"][0])
        item.update(consultation_id=cid, after=after or [])
        self.record["selected"].append(item)

    def refusal(self) -> dict:
        admission = copy.deepcopy(self.admit())
        after = copy.deepcopy(self.record["host"])
        after.update(snapshot_id="after-refusal", threads=[self.thread(i) for i in range(3)])
        receipt = {
            "admission": admission,
            "outcome": "capacity_rejected",
            "execution_id": None,
            "no_child_confirmed": True,
            "evidence": "host refused before creating a child",
            "host_after": after,
        }
        self.request["history"].append(receipt)
        self.record["host"]["snapshot_id"] = "after-observed-release"
        return receipt

    def fails(self, reason: str) -> None:
        with self.assertRaisesRegex(allocation.AllocationError, f"^{reason}$"):
            self.admit()

    def test_primary_count_scopes_and_zero_child_limit(self) -> None:
        self.assertEqual(self.plan()["free_slots"], 3)
        self.record["host"]["limit_scope"] = "spawned_only"
        self.assertEqual(self.plan()["free_slots"], 4)
        self.record["host"]["thread_limit"] = 0
        self.assertEqual(self.plan()["status"], "PLAN_CAPACITY_BLOCKED")

    def test_gate1_regression_completed_threads_do_not_release_capacity(self) -> None:
        self.fill()
        result = self.plan()
        self.assertEqual(result["status"], "PLAN_CAPACITY_BLOCKED")
        self.assertEqual(result["free_slots"], 0)
        self.assertEqual(result["pending"], [self.cid])
        self.assertEqual(result["close_candidates"], [])

    def test_impossible_plan_stops_before_first_spawn_even_when_sequential(self) -> None:
        for i in range(3):
            self.add_pending(f"later-{i}", [self.cid])
        self.assertEqual(self.plan()["status"], "PLAN_CAPACITY_BLOCKED")
        self.assertEqual(self.plan()["free_slots"], 3)
        self.fails("PLAN_CAPACITY_BLOCKED")

    def test_closure_allows_plan_waves_but_never_assumes_release(self) -> None:
        for i in range(3):
            self.add_pending(f"later-{i}", [self.cid])
        self.record["host"]["close_supported"] = True
        self.assertEqual(self.plan()["status"], "READY")
        self.fill()
        self.assertEqual(self.plan()["status"], "CLOSE_REQUIRED")
        self.fails("CLOSE_REQUIRED")
        self.record["host"]["threads"][0].update(
            state="closed", release_evidence="host close confirmed"
        )
        self.assertEqual(self.plan()["free_slots"], 1)
        self.assertEqual(self.admit()["status"], "DISPATCH_READY")

    def test_closure_preserves_results_ownership_and_followups(self) -> None:
        self.fill()
        self.record["host"]["close_supported"] = True
        threads = self.record["host"]["threads"]
        threads[0]["result_evidence"] = None
        threads[1]["owned_by_task"] = False
        threads[2]["retain"] = True
        self.assertEqual(self.plan()["status"], "CAPACITY_BLOCKED")
        self.assertEqual(self.plan()["close_candidates"], [])

    def test_close_without_release_evidence_rejected(self) -> None:
        thread = self.thread(1)
        thread["state"] = "closed"
        self.record["host"]["threads"] = [thread]
        self.fails("RELEASE_UNVERIFIED")

    def test_running_owned_threads_can_be_waited_for_not_closed(self) -> None:
        self.record["host"].update(
            close_supported=True, threads=[self.thread(i, "running") for i in range(3)]
        )
        self.assertEqual(self.plan()["status"], "WAITING")
        self.assertEqual(self.plan()["close_candidates"], [])

    def test_unknown_capacity_is_not_unlimited(self) -> None:
        original = copy.deepcopy(self.record["host"])
        for field, value in (
            ("thread_limit", None),
            ("limit_scope", "unknown"),
            ("inventory_complete", False),
        ):
            with self.subTest(field=field):
                self.record["host"] = {**original, field: value}
                self.assertEqual(self.plan()["status"], "CAPACITY_UNKNOWN")
        self.record["host"] = {**original, "close_supported": None}
        for i in range(3):
            self.add_pending(f"extra-{i}")
        self.assertEqual(self.plan()["status"], "PLAN_CAPACITY_BLOCKED")

    def test_only_ready_dependencies_are_eligible(self) -> None:
        self.add_pending("downstream", [self.cid])
        self.assertEqual(self.plan()["eligible"], [self.cid])
        self.request["consultation_id"] = "downstream"
        self.fails("DEPENDENCY_NOT_READY")
        self.record["selected"][0].update(state="completed", evidence="accepted result reference")
        result = self.plan()
        self.assertEqual(result["eligible"], ["downstream"])
        self.assertEqual(result["completed"][0]["evidence"], "accepted result reference")

    def test_missing_advisor_blocks_only_its_dependents(self) -> None:
        self.add_pending("blocked-advisor")
        self.add_pending("dependent", ["blocked-advisor"])
        self.record["selected"][1].update(state="blocked", evidence="missing exact role")
        result = self.plan()
        self.assertEqual(result["eligible"], [self.cid])
        self.assertEqual(result["blocked"], ["blocked-advisor", "dependent"])

    def test_running_and_completed_evidence_cannot_bypass_dependencies(self) -> None:
        self.add_pending("downstream", [self.cid])
        self.record["selected"][1].update(state="completed", evidence="premature acceptance")
        self.fails("DEPENDENCY_NOT_COMPLETED")

    def test_cycles_and_unknown_dependencies_fail(self) -> None:
        self.record["selected"][0]["after"] = [self.cid]
        self.fails("DEPENDENCY_CYCLE")
        self.record["selected"][0]["after"] = ["absent"]
        self.fails("UNKNOWN_DEPENDENCY")

    def test_existing_thread_requires_reconciliation_not_duplicate_spawn(self) -> None:
        thread = self.thread(1)
        thread["consultation_id"] = self.cid
        self.record["host"]["threads"] = [thread]
        self.fails("RECONCILE_REQUIRED")

    def test_exact_role_is_not_replaced_by_generic_agent(self) -> None:
        self.record["selected"][0]["role"] = "default"
        self.fails("UNKNOWN_ROLE")

    def test_dispatch_is_bound_to_original_question_and_allocation(self) -> None:
        self.record["selected"][0]["question"] = "different question"
        self.fails("CONSULTATION_MISMATCH")

    def test_confirmed_capacity_race_allows_one_same_decision_redispatch(self) -> None:
        receipt = self.refusal()
        result = self.admit()
        self.assertEqual(result["dispatch_number"], 2)
        self.assertEqual(result["decision_id"], receipt["admission"]["decision_id"])
        self.assertEqual(self.decision["attempt"], 1)
        self.assertEqual(self.council["allocation"]["retries"]["single_attempt"]["max_attempts"], 1)

    def test_capacity_increase_is_a_valid_recovery_observation(self) -> None:
        self.refusal()
        self.record["host"].update(thread_limit=5, threads=[self.thread(i) for i in range(3)])
        self.assertEqual(self.admit()["dispatch_number"], 2)

    def test_renaming_snapshot_without_capacity_change_is_not_recovery(self) -> None:
        receipt = self.refusal()
        receipt["host_after"]["threads"] = []
        self.fails("CAPACITY_UNCHANGED")

    def test_stale_snapshot_and_cross_task_recovery_fail(self) -> None:
        receipt = self.refusal()
        self.record["host"]["snapshot_id"] = receipt["host_after"]["snapshot_id"]
        self.fails("STALE_CAPACITY_SNAPSHOT")
        self.record["host"].update(snapshot_id="new", task_id="another-task")
        self.fails("TASK_MISMATCH")

    def test_unknown_or_unconfirmed_launch_must_be_reconciled(self) -> None:
        receipt = self.refusal()
        receipt["outcome"] = "unknown"
        self.fails("RECONCILE_REQUIRED")
        receipt.update(outcome="capacity_rejected", no_child_confirmed=False)
        self.fails("RECONCILE_REQUIRED")

    def test_started_or_failed_execution_does_not_use_dispatch_retries(self) -> None:
        receipt = self.refusal()
        receipt.update(outcome="started", execution_id="actual-child", no_child_confirmed=False)
        self.fails("ALREADY_STARTED")
        receipt["outcome"] = "failed"
        self.fails("EXECUTION_RETRY_NOT_AUTHORIZED")

    def test_retry_bound_applies_after_another_verified_release(self) -> None:
        self.refusal()
        second = copy.deepcopy(self.admit())
        after = copy.deepcopy(self.record["host"])
        after.update(snapshot_id="second-refusal", threads=[self.thread(i) for i in range(3)])
        self.request["history"].append(
            {
                "admission": second,
                "outcome": "capacity_rejected",
                "execution_id": None,
                "no_child_confirmed": True,
                "evidence": "second refusal",
                "host_after": after,
            }
        )
        self.record["host"]["snapshot_id"] = "second-release"
        self.fails("DISPATCH_BUDGET_EXHAUSTED")

    def test_policy_can_disable_recovery(self) -> None:
        self.policy["max_capacity_retries"] = 0
        self.refusal()
        self.fails("DISPATCH_BUDGET_EXHAUSTED")

    def test_zero_usable_limit_cannot_wait_for_a_slot_that_cannot_exist(self) -> None:
        self.record["host"].update(
            thread_limit=1, close_supported=True, threads=[self.thread(1, "running")]
        )
        self.assertEqual(self.plan()["status"], "CAPACITY_BLOCKED")

    def test_refusal_inventory_cannot_contain_the_claimed_absent_child(self) -> None:
        receipt = self.refusal()
        receipt["host_after"]["threads"][0]["consultation_id"] = self.cid
        self.fails("INCONSISTENT_LAUNCH")

    def test_recovery_policy_is_versioned_strict_and_bounded(self) -> None:
        original = copy.deepcopy(self.policy)
        for field, value, reason in (
            ("schema_version", 2, "DISPATCH_VERSION"),
            ("max_capacity_retries", 4, "INVALID_DISPATCH_BUDGET"),
            ("max_capacity_retries", True, "INVALID_INTEGER"),
            ("unknown", 1, "UNKNOWN_FIELD"),
        ):
            with self.subTest(field=field, value=value):
                self.policy = {**original, field: value}
                self.fails(reason)

    def test_admission_cli_uses_real_policy_and_unchanged_decision(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPTS / "resolve_advisor_dispatch.py"),
                "admit",
                "--record",
                "-",
            ],
            input=json.dumps(self.request),
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertEqual(json.loads(result.stdout), self.admit())

    def test_valid_but_different_allocation_cannot_replace_refused_decision(self) -> None:
        self.refusal()
        self.allocation_request["proposed_choice"]["reasoning_effort"] = "xhigh"
        self.request["decision"] = allocation.resolve(self.council, self.allocation_request)
        self.fails("DISPATCH_HISTORY_MISMATCH")

    def test_history_cannot_switch_plan_or_decision(self) -> None:
        self.refusal()
        self.record["plan_id"] = "replacement-plan"
        self.fails("DISPATCH_HISTORY_MISMATCH")

    def test_duplicate_threads_and_boolean_limits_are_rejected(self) -> None:
        self.record["host"]["threads"] = [self.thread(0), self.thread(0)]
        self.fails("DUPLICATE_THREAD")
        self.record["host"].update(threads=[], thread_limit=True)
        self.fails("INVALID_INTEGER")

    def test_cli_stdin_is_deterministic_and_errors_do_not_echo_payload(self) -> None:
        command = [
            sys.executable,
            "-B",
            str(SCRIPTS / "resolve_advisor_dispatch.py"),
            "plan",
            "--record",
            "-",
        ]
        first = subprocess.run(
            command, input=json.dumps(self.record), text=True, capture_output=True, check=True
        )
        self.assertEqual(json.loads(first.stdout), self.plan())
        bad = subprocess.run(
            command,
            input='{"schema_version":1,"schema_version":"private-marker"}',
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(bad.returncode, 1)
        self.assertEqual(json.loads(bad.stdout)["reason"], "DUPLICATE_KEY")
        self.assertNotIn("private-marker", bad.stdout + bad.stderr)


if __name__ == "__main__":
    unittest.main()
