"""Deterministic state, information and accounting checks; never model evidence."""

from __future__ import annotations

import json
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from unittest.mock import patch

from ..harness.budget import reserve_stage
from ..harness.core import FakeProvider, execute_mock, replay_evaluator, require_live_gate
from ..harness.design import (
    DOMAIN_ROLES,
    EXPERIMENT,
    STAGES,
    parse,
    schedule,
    select_tasks,
    stop_reason,
)
from ..harness.grading import grade
from ..harness.records import encoded, publish, sha
from ..taskpack import catalog, fixtures, qualification_catalog


class ControllerTests(unittest.TestCase):
    def test_independent_reviews_frozen_decision_and_repair(self) -> None:
        fixture = fixtures("qualification_double")
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder).resolve()
            for condition in ("B", "C"):
                provider = FakeProvider(fixture["reference"])
                row = execute_mock(
                    data, condition, "qualification_double", condition, provider, force_repair=True
                )
                self.assertEqual(row["score"], 1)
                self.assertEqual(row["stage_invocations"], 6)
                self.assertEqual(row["model_calls"], 0)
                self.assertTrue(row["schema_success"])
                self.assertNotIn("reports", provider.prompts[0])
                self.assertNotIn("reports", provider.prompts[1])
                self.assertEqual(len(provider.prompts[2]["reports"]), 2)
                self.assertNotIn("reports", provider.prompts[4])
                self.assertNotIn("challenge", provider.prompts[4])
                self.assertEqual(provider.prompts[4]["decision"], {"text": "MOCK DECISION"})
                self.assertNotIn("hidden", provider.prompts[5]["visible_feedback"])
            b = FakeProvider(fixture["reference"])
            c = FakeProvider(fixture["reference"])
            execute_mock(data, "b2", "qualification_double", "B", b)
            execute_mock(data, "c2", "qualification_double", "C", c)
            for i in range(2):
                before = dict(b.prompts[i])
                after = dict(c.prompts[i])
                self.assertNotEqual(before.pop("jurisdiction"), after.pop("jurisdiction"))
                self.assertEqual(before, after)
            self.assertEqual(b.prompts[2:], c.prompts[2:])

    def test_failure_retains_artifact_and_attempt_identity(self) -> None:
        fixture = fixtures("qualification_double")
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder).resolve()
            noartifact = execute_mock(
                data,
                "early",
                "qualification_double",
                "B",
                FakeProvider(fixture["reference"], fail_at=2),
            )
            self.assertFalse(noartifact["evaluable"])
            self.assertEqual(noartifact["score"], 0)
            self.assertEqual(noartifact["stage_invocations"], 2)
            repaired = execute_mock(
                data,
                "late",
                "qualification_double",
                "B",
                FakeProvider(fixture["reference"], fail_at=6),
                force_repair=True,
            )
            self.assertTrue(repaired["evaluable"])
            self.assertEqual(repaired["score"], 1)
            self.assertEqual(repaired["failure"], "PROVIDER_ERROR")
            self.assertFalse(repaired["schema_success"])
            with self.assertRaises(FileExistsError):
                execute_mock(
                    data, "late", "qualification_double", "B", FakeProvider(fixture["reference"])
                )
            self.assertEqual(
                len(list((data / "mock/qualification/reservations").glob("*.json"))), 8
            )

    def test_visible_failure_repairs_once(self) -> None:
        fixture = fixtures("qualification_double")
        with tempfile.TemporaryDirectory() as folder:
            provider = FakeProvider("def solve(x): return None", fixture["reference"])
            row = execute_mock(
                Path(folder).resolve(), "repair", "qualification_double", "C", provider
            )
            self.assertEqual(row["repair_count"], 1)
            self.assertFalse(row["visible_initial"]["full_pass"])
            self.assertTrue(row["visible_repair"]["full_pass"])
            self.assertEqual(row["score"], 1)
            feedback = provider.prompts[-1]["visible_feedback"]
            self.assertNotIn("reference", feedback)
            self.assertEqual(len(provider.prompts), 6)

    def test_evaluator_replay_same_artifact_no_provider(self) -> None:
        fixture = fixtures("qualification_double")
        calls = 0

        def first_visible_then_broken(
            code: bytes, cases: list[dict[str, Any]], weights: dict[str, float]
        ) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("injected evaluator malfunction")
            return grade(code, cases, weights)

        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder).resolve()
            provider = FakeProvider(fixture["reference"])
            row = execute_mock(
                data,
                "replay",
                "qualification_double",
                "B",
                provider,
                grader=first_visible_then_broken,
            )
            self.assertIsNone(row["score"])
            self.assertEqual(row["failure"], "EVALUATOR_ERROR")
            run = data / "mock/qualification/replay"
            before = (run / "terminal.json").read_bytes()
            result = replay_evaluator(run)
            self.assertEqual(result["score"], 1)
            self.assertEqual(len(provider.prompts), 5)
            self.assertEqual(before, (run / "terminal.json").read_bytes())
            changed = {**fixture, "requirement_weights": {"changed": 1.0}}
            with patch("experiments.roundtable_v1_bc.harness.core.fixtures", return_value=changed):
                with self.assertRaisesRegex(ValueError, "SCORING_CHANGED"):
                    replay_evaluator(run)
            with patch(
                "experiments.roundtable_v1_bc.harness.core.evaluator_fingerprint",
                return_value="changed",
            ):
                with self.assertRaisesRegex(ValueError, "SCORING_CHANGED"):
                    replay_evaluator(run)
            frozen = json.loads((run / "frozen-artifact.json").read_bytes())
            frozen["code"] += "\n"
            (run / "frozen-artifact.json").write_text(json.dumps(frozen))
            with self.assertRaisesRegex(ValueError, "ARTIFACT_CHANGED"):
                replay_evaluator(run)

    def test_phase_separation_and_closed_live_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder).resolve()
            provider = FakeProvider("def solve(x): return x")
            for task, phase, condition in [
                ("numerical_sum", "qualification", "B"),
                ("qualification_double", "main", "C"),
                ("numerical_sum", "calibration", "C"),
            ]:
                with self.assertRaises(ValueError):
                    execute_mock(data, "invalid", task, condition, provider, phase)
            self.assertFalse(provider.prompts)
        with self.assertRaisesRegex(RuntimeError, "NO LIVE MODEL CALL"):
            require_live_gate({})

    def test_schemas_serialization_and_no_overwrite(self) -> None:
        self.assertEqual(parse("BUILD", '{"code":"x"}'), {"code": "x"})
        for stage, text in [
            ("BUILD", "{}"),
            ("REVIEW_1", '{"text":"a","extra":1}'),
            ("BUILD", '{"code":1}'),
            ("UNKNOWN", '{"text":"ok"}'),
        ]:
            with self.assertRaises(ValueError):
                parse(stage, text)
        self.assertEqual(sha(encoded({"b": 2, "a": 1})), sha(encoded({"a": 1, "b": 2})))
        with self.assertRaises(ValueError):
            encoded(float("nan"))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "immutable.json"
            publish(path, {"value": 1})
            with self.assertRaises(FileExistsError):
                publish(path, {"value": 2})
            self.assertEqual(json.loads(path.read_bytes()), {"value": 1})


class DesignTests(unittest.TestCase):
    def test_schedule_pairing_hash_and_reproducibility(self) -> None:
        tasks = [
            min(t["task_id"] for t in catalog() if t["family"] == domain) for domain in DOMAIN_ROLES
        ]
        one = schedule(tasks)
        self.assertEqual(one, schedule(list(reversed(tasks))))
        self.assertEqual(len(one["rows"]), 128)
        self.assertEqual(len({r["run_id"] for r in one["rows"]}), 128)
        self.assertEqual(sum(r["condition"] == "B" for r in one["rows"]), 64)
        self.assertEqual(
            one["sha256"], sha(encoded({k: v for k, v in one.items() if k != "sha256"}))
        )
        for task in tasks:
            for block in range(8):
                pair = [r for r in one["rows"] if r["task_id"] == task and r["block"] == block]
                self.assertEqual({r["condition"] for r in pair}, {"B", "C"})

    def test_selection_mean_threshold_distance_and_stop(self) -> None:
        candidates = [dict(t) for t in catalog()]
        rows = [
            {
                "experiment_id": EXPERIMENT,
                "phase": "calibration",
                "kind": "MOCK",
                "run_id": t["task_id"] + str(i),
                "task_id": t["task_id"],
                "condition": "B",
                "score": 0.5,
            }
            for t in candidates
            for i in range(3)
        ]
        with self.assertRaisesRegex(ValueError, "MOCK_OR_UNKNOWN_CALIBRATION_EVIDENCE"):
            select_tasks(candidates, rows)
        chosen = select_tasks(candidates, rows, allow_mock=True)
        self.assertEqual(len(chosen), 8)
        self.assertEqual(
            set(chosen),
            {
                min(t["task_id"] for t in candidates if t["family"] == domain)
                for domain in DOMAIN_ROLES
            },
        )
        for row in rows:
            if row["task_id"] == "numerical_root":
                row["score"] = 0.25
        self.assertIn("numerical_sum", select_tasks(candidates, rows, allow_mock=True))
        for row in rows:
            if row["task_id"] == "numerical_sum":
                row["score"] = 1
        self.assertIn("numerical_root", select_tasks(candidates, rows, allow_mock=True))
        for row in rows:
            if row["task_id"] == "numerical_root":
                row["score"] = 0.249
        with self.assertRaisesRegex(ValueError, "CALIBRATION_INSUFFICIENT"):
            select_tasks(candidates, rows, allow_mock=True)
        rows[0]["phase"] = "historical"
        with self.assertRaisesRegex(ValueError, "FOREIGN_CALIBRATION"):
            select_tasks(candidates, rows, allow_mock=True)

    def test_qualification_task_exclusion(self) -> None:
        self.assertFalse(
            {t["task_id"] for t in catalog()} & {t["task_id"] for t in qualification_catalog()}
        )
        for roles in DOMAIN_ROLES.values():
            self.assertEqual(len(set(roles)), 2)

    def test_exact_stop_boundaries(self) -> None:
        one = {"failure": "STARTUP", "failure_detail": "invalid config"}
        self.assertEqual(stop_reason([one, one]), "TWO_IDENTICAL_STARTUP_FAILURES")
        self.assertIsNone(stop_reason([one, {"failure": "STARTUP", "failure_detail": "other"}]))
        rows = [{"failure": None} for _ in range(18)] + [{"failure": "PROVIDER_ERROR"}]
        self.assertIsNone(stop_reason(rows))
        rows.append({"failure": None})
        self.assertIsNone(stop_reason(rows))
        rows[0] = {"failure": "PROVIDER_ERROR"}
        self.assertEqual(stop_reason(rows), "INFRASTRUCTURE_FAILURE_RATE")

    def test_concurrent_budget_and_no_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder).resolve()

            def reserve(i: int) -> bool:
                try:
                    reserve_stage(data, "qualification", f"run{i}", "REVIEW_1")
                    return True
                except ValueError:
                    return False

            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sum(pool.map(reserve, range(32))), 30)
            with self.assertRaisesRegex(ValueError, "PHASE_CALL_BUDGET"):
                reserve_stage(data, "qualification", "other", "REVIEW_1")
        with tempfile.TemporaryDirectory() as folder:
            data = Path(folder).resolve()
            reserve_stage(data, "main", "run", "REVIEW_1")
            with self.assertRaisesRegex(ValueError, "DUPLICATE_OR_OUT_OF_ORDER_STAGE"):
                reserve_stage(data, "main", "run", "REVIEW_1")
            for stage in STAGES[1:]:
                reserve_stage(data, "main", "run", stage)
            with self.assertRaisesRegex(ValueError, "RUN_CALL_BUDGET"):
                reserve_stage(data, "main", "run", "REPAIR")


if __name__ == "__main__":
    unittest.main()
