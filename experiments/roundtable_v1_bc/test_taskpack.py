"""Task provenance, requirement coverage and independent guarded grading checks."""

from __future__ import annotations

import hashlib
import json
import math
import unittest
from collections import Counter

from experiments.roundtable_v1_bc.taskpack import (
    PUBLIC_FILES,
    ROOT,
    catalog,
    fixtures,
    public_snapshot,
    qualification_catalog,
)


class TaskPackTests(unittest.TestCase):
    def test_domains_and_operational_separation(self) -> None:
        candidates = catalog()
        operational = qualification_catalog()
        self.assertEqual(len(candidates), 12)
        self.assertEqual(len(operational), 5)
        self.assertEqual(
            Counter(row["family"] for row in candidates),
            {
                "numerical": 2,
                "statistics": 2,
                "defensive_parser": 2,
                "queue_idempotency": 2,
                "ml_evaluation": 1,
                "concurrency": 1,
                "ledger_state_invariant": 1,
                "protocol_client": 1,
            },
        )
        ids = [row["task_id"] for row in candidates + operational]
        self.assertEqual(len(ids), len(set(ids)))
        for row in candidates:
            self.assertEqual(fixtures(row["task_id"])["purpose"], "benchmark_candidate")
        for row in operational:
            self.assertEqual(fixtures(row["task_id"])["purpose"], "qualification_only")
            self.assertTrue(fixtures(row["task_id"])["mechanical_repair_allowed"])

    def test_public_bytes_match_recorded_source_hashes(self) -> None:
        # Works in a published checkout without the unpublished source commit present.
        for row in catalog():
            task_id = row["task_id"]
            fixture = fixtures(task_id)
            provenance = fixture["provenance"]
            self.assertEqual(len(provenance["source_commit"]), 40)
            snapshot = public_snapshot(task_id)
            self.assertEqual(set(snapshot), set(PUBLIC_FILES))
            for name in PUBLIC_FILES:
                original = f"experiments/roundtable_v1/tasks/{task_id}/{name}"
                actual = (ROOT / "tasks" / task_id / name).read_bytes()
                self.assertEqual(
                    hashlib.sha256(actual).hexdigest(),
                    provenance["source_files_sha256"][original],
                )

    def test_requirements_have_cases_and_targeted_defects(self) -> None:
        for row in catalog() + qualification_catalog():
            fixture = fixtures(row["task_id"])
            cases = fixture["hidden"]
            weights = fixture["requirement_weights"]
            self.assertTrue(math.isclose(sum(weights.values()), 1.0, abs_tol=1e-12))
            self.assertTrue(all(0 < value <= 1 for value in weights.values()))
            self.assertEqual(set(weights), set(fixture["requirements"]))
            self.assertEqual(set(weights), {case["requirement_id"] for case in cases})
            self.assertEqual(len(cases), len({case["id"] for case in cases}))
            self.assertEqual(
                set(weights),
                {
                    requirement
                    for control in fixture["negative_controls"]
                    for requirement in control["requirements"]
                },
            )
            for case in cases:
                self.assertNotEqual("expected" in case, "error" in case)
                self.assertEqual(case["rel_tol"], 1e-12)
                self.assertEqual(case["abs_tol"], 0.0)
                self.assertIs(type(case["nonmutation"]), bool)
            compile(fixture["reference"], "reference.py", "exec")
            for control in fixture["negative_controls"]:
                compile(control["code"], "negative.py", "exec")
            for name, text in public_snapshot(row["task_id"]).items():
                if name.endswith(".py"):
                    compile(text, name, "exec")
                if name.endswith(".json"):
                    json.loads(text)

    def test_path_validation_and_public_allowlist(self) -> None:
        for invalid in ("../evaluator/ledger_transfer", "/tmp/x", "a/b", "", "a.json"):
            with self.assertRaises(ValueError):
                public_snapshot(invalid)
            with self.assertRaises(ValueError):
                fixtures(invalid)
        for row in catalog() + qualification_catalog():
            directory = ROOT / "tasks" / row["task_id"]
            self.assertEqual({path.name for path in directory.iterdir()}, set(PUBLIC_FILES))
            self.assertNotIn("reference", public_snapshot(row["task_id"]))

    def test_sensitive_requirements_are_explicit(self) -> None:
        root_cases = fixtures("numerical_root")["hidden"]
        self.assertTrue(any(case.get("expected") == 1e-150 for case in root_cases))
        self.assertTrue(all(case["abs_tol"] == 0 for case in root_cases))
        ledger = fixtures("ledger_transfer")
        preservation = [case for case in ledger["hidden"] if case["nonmutation"]]
        self.assertTrue(any("expected" in case for case in preservation))
        self.assertTrue(any("error" in case for case in preservation))


class GuardedTaskGradingTests(unittest.TestCase):
    def test_all_references_and_each_targeted_negative_control(self) -> None:
        # The new study's qualified boundary owns execution. Never execute these programs
        # in this test process or in the historical trusted-only Roundtable grader.
        from experiments.roundtable_v1_bc.harness.grading import grade

        for row in catalog() + qualification_catalog():
            fixture = fixtures(row["task_id"])
            cases = fixture["hidden"]
            with self.subTest(task=row["task_id"], candidate="reference"):
                result = grade(fixture["reference"].encode(), cases, fixture["requirement_weights"])
                self.assertEqual(result["score"], 1.0)
                visible = json.loads(public_snapshot(row["task_id"])["visible.json"])
                # Original public case bytes lack requirement IDs; assign one only in the
                # trusted test input, preserving all copied public files byte-for-byte.
                visible = [{**case, "requirement_id": "visible"} for case in visible]
                public = grade(fixture["reference"].encode(), visible, {"visible": 1.0})
                self.assertEqual(public["score"], 1.0)
            for control in fixture["negative_controls"]:
                for requirement in control["requirements"]:
                    with self.subTest(
                        task=row["task_id"], defect=control["id"], requirement=requirement
                    ):
                        subset = [case for case in cases if case["requirement_id"] == requirement]
                        observed = grade(control["code"].encode(), subset, {requirement: 1.0})
                        self.assertLess(observed["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
