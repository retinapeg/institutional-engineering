"""Regression evidence for an unqualified observer, plus real OS-boundary checks."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from typing import Any

from experiments.roundtable_v1_bc.harness.grading import (
    GraderIntegrityError,
    grade,
    integrity_audit,
    matches,
    require_qualified,
)
from experiments.roundtable_v1_bc.harness.process_boundary import (
    negative_access_check,
    run_python,
)


class GradingTests(unittest.TestCase):
    def test_adversarial_observer_is_reproducibly_unqualified(self) -> None:
        audit = integrity_audit()
        self.assertFalse(audit["qualified"])
        self.assertEqual(audit["blocker"], "CANDIDATE_CAN_FORGE_INPUT_AFTER")
        self.assertEqual(
            audit["false_passes"],
            ["json_monkeypatch", "caller_globals", "stdout_then_exit"],
        )
        self.assertEqual(audit["checks"]["honest_reference"]["result"]["score"], 1.0)
        self.assertEqual(audit["checks"]["ordinary_mutation"]["result"]["score"], 0.0)
        self.assertEqual(audit["checks"]["counterfeit_score_only"]["result"]["score"], 0.0)
        with self.assertRaisesRegex(GraderIntegrityError, "CANDIDATE_CAN_FORGE_INPUT_AFTER"):
            require_qualified()

    def test_real_negative_access_boundary(self) -> None:
        result = negative_access_check()
        self.assertEqual(
            set(result["checks"]),
            {"hidden", "prior_attempt", "credentials", "researcher", "symlink", "network", "fork"},
        )
        self.assertTrue(all(value is True for value in result["checks"].values()))
        self.assertIn("hard resident-memory cap", result["not_enforced"])
        self.assertIn("read-metadata secrecy", result["not_enforced"])

    def test_candidate_failure_is_scored_not_evaluator_failure(self) -> None:
        cases: list[dict[str, Any]] = [
            {"id": "value", "requirement_id": "contract", "input": 2, "expected": 2}
        ]
        for candidate in (
            b"def solve(x):\n    raise SystemExit(7)\n",
            b"def solve(x):\n    print('extra output')\n    return x\n",
        ):
            result = grade(candidate, cases, {"contract": 1.0})
            self.assertTrue(result["grader_success"])
            self.assertFalse(result["integrity_qualified"])
            self.assertEqual(result["score"], 0.0)

    def test_requirement_weighting_and_relative_tolerance(self) -> None:
        cases: list[dict[str, Any]] = [
            {"id": "small", "requirement_id": "small_values", "input": 1, "expected": 1},
            {"id": "other", "requirement_id": "small_values", "input": 2, "expected": 2},
            {"id": "large", "requirement_id": "large_values", "input": 10, "expected": 10},
        ]
        result = grade(
            b"def solve(x):\n    return x if x==1 else 0\n",
            cases,
            {"small_values": 0.5, "large_values": 0.5},
        )
        # Passing one case does not pass the containing multi-case requirement.
        self.assertEqual(result["score"], 0.0)
        self.assertFalse(matches(0.0, 1e-150, 1e-12, 0.0))
        self.assertTrue(matches(1e-150, 1e-150, 1e-12, 0.0))
        self.assertFalse(matches(True, 1.0, 1e-12, 0.0))

    def test_candidate_wall_time_and_output_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory(prefix="roundtable-limits-") as temp:
            workspace = Path(temp).resolve()
            timeout = run_python(workspace, "while True: pass", seconds=0.15, writable=False)
            self.assertEqual(timeout["failure"], "CANDIDATE_TIMEOUT")
            output = run_python(workspace, "print('x'*1200000)", seconds=5, writable=False)
            self.assertEqual(output["failure"], "OUTPUT_LIMIT")
            self.assertLessEqual(len(output["stdout"].encode()), 1048576)


if __name__ == "__main__":
    unittest.main()
