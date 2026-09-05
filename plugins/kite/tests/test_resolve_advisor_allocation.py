from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "scripts/resolve_advisor_allocation.py"
REFERENCES = PLUGIN / "skills/markeitech-advisor-router/references"
SPEC = importlib.util.spec_from_file_location("allocation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
ALLOCATION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ALLOCATION)


class AllocationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = tomllib.loads((REFERENCES / "council-policy.toml").read_text())
        self.request = json.loads((REFERENCES / "allocation-request.example.json").read_text())

    def resolve(self) -> dict:
        return ALLOCATION.resolve(self.policy, self.request)

    def fails(self, reason: str) -> None:
        with self.assertRaisesRegex(ALLOCATION.AllocationError, f"^{reason}$"):
            self.resolve()

    def receipt(self, decision: dict, outcome: str, effective: dict | None = None) -> dict:
        return {
            "decision_id": decision["decision_id"],
            "execution_id": f"child-{decision['attempt']}",
            "effective": effective,
            "outcome": outcome,
            "evidence": "synthetic receipt",
        }

    def authorize_retries(self) -> None:
        self.policy["allocation"]["retries"]["single_attempt"] = {
            "max_attempts": 3,
            "max_fallbacks": 1,
            "max_escalations": 1,
            "fallback_profiles": ["sol_high"],
            "escalation_profiles": ["sol_xhigh"],
        }
        self.request["limits"]["max_attempts"] = 3

    def append_failure(self, outcome: str) -> dict:
        decision = self.resolve()
        self.request["history"].append(
            {"decision": decision, "receipt": self.receipt(decision, outcome)}
        )
        self.request.pop("proposed_choice", None)
        return decision

    def test_one_unchanged_advisor_resolves_simple_and_ambiguous_questions(self) -> None:
        original = copy.deepcopy(self.policy["advisors"][0])
        simple = self.resolve()
        self.request["question"] = "Review conflicting ownership across three supplied components."
        self.request["assessment"] = dict.fromkeys(self.request["assessment"], "high")
        self.request["rationale"] = "Multiple contradictory owners require deeper source analysis."
        self.request["proposed_choice"]["reasoning_effort"] = "xhigh"
        ambiguous = self.resolve()
        self.assertEqual(simple["role"], ambiguous["role"])
        self.assertNotEqual(simple["requested"], ambiguous["requested"])
        self.assertEqual(original, self.policy["advisors"][0])
        self.assertEqual(simple["source"], "judgment")
        self.assertIsNone(simple["effective"])

    def test_default_is_complete_and_deterministic(self) -> None:
        self.request.pop("proposed_choice")
        decision = self.resolve()
        self.assertEqual(
            decision["requested"], {"model": "gpt-5.6-sol", "reasoning_effort": "xhigh"}
        )
        self.assertEqual(decision["source"], "default")
        self.assertEqual(decision, self.resolve())

    def test_explicit_partial_and_complete_choices(self) -> None:
        self.request.pop("proposed_choice")
        for choice in (
            {"reasoning_effort": "high"},
            {"model": "gpt-5.6-sol", "reasoning_effort": "high"},
        ):
            with self.subTest(choice=choice):
                self.request["user_choice"] = choice
                self.assertEqual(self.resolve()["requested"]["reasoning_effort"], "high")
                self.assertEqual(self.resolve()["source"], "user")

    def test_user_choice_overrides_conflicting_discretionary_proposal(self) -> None:
        self.request["user_choice"] = {"reasoning_effort": "high"}
        self.assertEqual(self.resolve()["requested"]["reasoning_effort"], "high")
        self.assertEqual(self.resolve()["source"], "user")

    def test_partial_user_model_selects_compatible_effort(self) -> None:
        self.request.pop("proposed_choice")
        self.request["user_choice"] = {"model": "gpt-5.6-sol"}
        self.request["host"]["models"]["gpt-5.6-sol"]["efforts"] = ["high"]
        self.assertEqual(self.resolve()["requested"]["reasoning_effort"], "high")

    def test_unknown_request_field_is_rejected(self) -> None:
        self.request["unexpected"] = True
        self.fails("UNKNOWN_FIELD")

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            path.write_text('{"schema_version": 1, "schema_version": 2}')
            with self.assertRaisesRegex(ALLOCATION.AllocationError, "DUPLICATE_KEY"):
                ALLOCATION.read_json(path)

    def test_unadmitted_explicit_model_stops(self) -> None:
        self.request.pop("proposed_choice")
        self.request["user_choice"] = {"model": "unadmitted-model"}
        self.fails("USER_CHOICE_UNAVAILABLE")

    def test_missing_policy_and_host_capability(self) -> None:
        self.request["required_capabilities"] = ["image_input"]
        self.fails("POLICY_CAPABILITY_MISSING")
        self.request["required_capabilities"] = []
        self.request["host"]["models"]["gpt-5.6-sol"]["capabilities"] = ["source_analysis"]
        self.fails("HOST_CAPABILITY_MISSING")

    def test_unavailable_model_and_unsupported_effort(self) -> None:
        model = self.request["host"]["models"].pop("gpt-5.6-sol")
        self.request["host"]["models"]["different-model"] = model
        self.fails("MODEL_UNAVAILABLE")
        self.request["host"]["models"] = {"gpt-5.6-sol": model}
        model["efforts"] = ["high"]
        self.fails("HOST_EFFORT_UNSUPPORTED")
        self.request["proposed_choice"]["reasoning_effort"] = "unsupported"
        self.fails("PAIR_NOT_ALLOWED")

    def test_inheritance_and_fixed_role_conflict(self) -> None:
        for overrides in ({"model": "gpt-5.6-sol"}, {"model_reasoning_effort": "medium"}):
            self.request["host"]["role_overrides"] = overrides
            self.fails("ROLE_OVERRIDE_CONFLICT")
        self.request["host"]["role_overrides"] = {}
        self.request["proposed_choice"] = {"model": "gpt-5.6-sol"}
        self.fails("MISSING_FIELD")

    def test_context_modes_and_exact_role(self) -> None:
        for value in ("all", "0", "-1", 3, True):
            self.request["fork_turns"] = value
            self.fails("FORK_UNSUPPORTED")
        self.request["fork_turns"] = "3"
        self.assertEqual(self.resolve()["fork_turns"], "3")
        self.request["host"]["fork_modes"] = ["none"]
        self.fails("FORK_UNSUPPORTED")
        self.request["fork_turns"] = "none"
        self.request["host"]["role"] = "default"
        self.fails("EXACT_ROLE_UNAVAILABLE")

    def test_unknown_and_insufficient_context(self) -> None:
        self.request["required_context_tokens"] = 100
        self.fails("CONTEXT_UNVERIFIED_OR_INSUFFICIENT")
        model = self.request["host"]["models"]["gpt-5.6-sol"]
        model["context_tokens"] = 99
        self.fails("CONTEXT_UNVERIFIED_OR_INSUFFICIENT")
        model["context_tokens"] = 100
        self.resolve()

    def test_budget_exhaustion_and_unenforceable_limit(self) -> None:
        self.request["limits"]["max_attempts"] = 0
        self.fails("BUDGET_EXHAUSTED")
        self.request["limits"] = {"max_attempts": 1, "max_cost_usd": 1}
        self.fails("HARD_BUDGET_UNSUPPORTED")

    def test_initial_policy_has_no_retry(self) -> None:
        self.append_failure("execution_failure")
        self.request["retry_kind"] = "fallback"
        self.fails("BUDGET_EXHAUSTED")

    def test_authorized_fallback_then_escalation_share_budget(self) -> None:
        self.authorize_retries()
        self.append_failure("execution_failure")
        self.request["retry_kind"] = "fallback"
        fallback = self.append_failure("insufficient_resources")
        self.assertEqual(fallback["requested"]["reasoning_effort"], "high")
        self.request["retry_kind"] = "escalation"
        escalation = self.append_failure("insufficient_resources")
        self.assertEqual(escalation["attempt"], 3)
        self.assertEqual(escalation["requested"]["reasoning_effort"], "xhigh")
        self.fails("BUDGET_EXHAUSTED")

    def test_escalation_limit_and_wrong_reason(self) -> None:
        self.authorize_retries()
        self.append_failure("execution_failure")
        self.request["retry_kind"] = "escalation"
        self.fails("RETRY_REASON")
        self.request["retry_kind"] = "fallback"
        self.append_failure("execution_failure")
        self.fails("RETRY_LIMIT")

    def test_fallback_selects_first_eligible_authorized_alternative(self) -> None:
        self.authorize_retries()
        self.policy["allocation"]["retries"]["single_attempt"]["fallback_profiles"] = [
            "sol_high",
            "sol_xhigh",
        ]
        self.append_failure("execution_failure")
        self.request["host"]["models"]["gpt-5.6-sol"]["efforts"] = ["medium", "xhigh"]
        self.request["retry_kind"] = "fallback"
        self.assertEqual(self.resolve()["requested"]["reasoning_effort"], "xhigh")

    def test_user_choice_prohibits_unauthorized_fallback(self) -> None:
        self.authorize_retries()
        self.request["user_choice"] = {"reasoning_effort": "medium"}
        self.append_failure("execution_failure")
        self.request["retry_kind"] = "fallback"
        self.fails("NO_AUTHORIZED_ALTERNATIVE")

    def test_authorized_user_alternative(self) -> None:
        self.authorize_retries()
        self.request["user_choice"] = {"reasoning_effort": "medium"}
        self.request["user_alternatives"] = ["sol_high"]
        self.append_failure("execution_failure")
        self.request["retry_kind"] = "fallback"
        self.assertEqual(self.resolve()["requested"]["reasoning_effort"], "high")

    def test_history_cannot_change_question_or_identity(self) -> None:
        self.authorize_retries()
        self.append_failure("execution_failure")
        self.request["retry_kind"] = "fallback"
        original = self.request["question"]
        self.request["question"] = "A different question."
        self.fails("HISTORY_BINDING_MISMATCH")
        self.request["question"] = original
        self.request["consultation_id"] = "new-id-to-reset-budget"
        self.fails("HISTORY_BINDING_MISMATCH")

    def test_completed_or_unknown_outcome_prevents_relaunch(self) -> None:
        for outcome in ("completed", "unknown"):
            self.setUp()
            self.authorize_retries()
            self.append_failure(outcome)
            self.request["retry_kind"] = "fallback"
            self.fails("PRIOR_OUTCOME_BLOCKS_RETRY")

    def test_receipt_mismatch_unknown_and_verified(self) -> None:
        decision = self.resolve()
        receipt = self.receipt(decision, "completed")
        self.assertEqual(
            ALLOCATION.check_receipt(decision, receipt)["status"], "EXECUTION_UNVERIFIED"
        )
        receipt["effective"] = decision["requested"]
        self.assertEqual(
            ALLOCATION.check_receipt(decision, receipt)["status"], "EXECUTION_VERIFIED"
        )
        receipt["effective"] = {"model": "gpt-5.6-sol", "reasoning_effort": "high"}
        with self.assertRaisesRegex(ALLOCATION.AllocationError, "EFFECTIVE_MISMATCH"):
            ALLOCATION.check_receipt(decision, receipt)
        receipt["decision_id"] = "other"
        with self.assertRaisesRegex(ALLOCATION.AllocationError, "RECEIPT_MISMATCH"):
            ALLOCATION.check_receipt(decision, receipt)

    def test_activation_source_and_dependency_gates(self) -> None:
        for field, reason in (
            ("kite_active", "KITE_INACTIVE"),
            ("sources_ready", "SOURCE_GATE"),
            ("dependencies_ready", "DEPENDENCY_GATE"),
        ):
            self.request[field] = False
            self.fails(reason)
            self.request[field] = True

    def test_second_model_catalog_without_advisor_edits(self) -> None:
        advisor = copy.deepcopy(self.policy["advisors"][0])
        allocation = self.policy["allocation"]
        model = {
            "efforts": ["low"],
            "capabilities": advisor["required_capabilities"],
            "evidence": "synthetic eligibility fixture, not production admission",
        }
        allocation["models"]["synthetic-model"] = model
        choice = {"model": "synthetic-model", "reasoning_effort": "low"}
        allocation["profiles"]["synthetic"] = choice
        allocation["constraints"]["standard"]["profiles"].append("synthetic")
        self.request["host"]["models"]["synthetic-model"] = {
            "efforts": ["low"],
            "capabilities": model["capabilities"],
            "context_tokens": None,
        }
        self.request["proposed_choice"] = choice
        self.assertEqual(self.resolve()["requested"], choice)
        self.assertEqual(advisor, self.policy["advisors"][0])

    def test_policy_strict_fields_capabilities_versions_and_retry_bounds(self) -> None:
        original = copy.deepcopy(self.policy)
        mutations = [
            (lambda p: p["advisors"][0].update(default_profile="missing"), "DEFAULT_NOT_ALLOWED"),
            (
                lambda p: p["advisors"][0].update(required_capabilities=["missing"]),
                "DEFAULT_CAPABILITY_MISSING",
            ),
            (lambda p: p["advisors"][0].update(unknown=True), "UNKNOWN_FIELD"),
            (lambda p: p["allocation"].update(schema_version=2), "ALLOCATION_VERSION"),
            (
                lambda p: p["allocation"]["retries"]["single_attempt"].update(max_attempts=True),
                "INVALID_INTEGER",
            ),
            (
                lambda p: p["allocation"]["retries"]["single_attempt"].update(max_fallbacks=1),
                "INVALID_RETRY_BOUNDS",
            ),
        ]
        for mutate, reason in mutations:
            with self.subTest(reason=reason):
                self.policy = copy.deepcopy(original)
                mutate(self.policy)
                self.fails(reason)

    def test_cli_success_and_redacted_malformed_input(self) -> None:
        completed = subprocess.run(
            [
                sys.executable,
                "-B",
                str(SCRIPT),
                "resolve",
                "--request",
                str(REFERENCES / "allocation-request.example.json"),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(json.loads(completed.stdout)["requested"]["reasoning_effort"], "medium")
        with tempfile.TemporaryDirectory() as directory:
            request = Path(directory) / "request.json"
            request.write_text('{"fake_secret_canary":')
            failed = subprocess.run(
                [sys.executable, "-B", str(SCRIPT), "resolve", "--request", str(request)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(failed.returncode, 1)
            self.assertEqual(json.loads(failed.stdout)["reason"], "INVALID_INPUT")
            self.assertNotIn("fake_secret_canary", failed.stdout + failed.stderr)


if __name__ == "__main__":
    unittest.main()
