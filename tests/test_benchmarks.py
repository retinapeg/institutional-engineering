import itertools
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.analysis import export, summary
from benchmarks.code_worker import validate
from benchmarks.graders import grade
from benchmarks.runner import (
    Store,
    clean_usage,
    empty_result,
    invoke,
    load_tasks,
    matrix,
    prompt_for,
    role_for,
    secondary_tasks,
    sweep,
)
from benchmarks.schemas import BenchmarkResponse
from institutional_workbench.runner import Blocked

PARSER = r"""def split_fields(text):
    fields = []
    current = ""
    escaped = False
    for char in text:
        if escaped:
            if char != "," and char != "\\":
                raise ValueError("invalid escape")
            current += char
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == ",":
            fields.append(current)
            current = ""
        else:
            current += char
    if escaped:
        raise ValueError("dangling escape")
    fields.append(current)
    return fields
"""
INTERVALS = """def merge_intervals(intervals):
    for start, end in intervals:
        if start > end:
            raise ValueError("reversed")
    merged = []
    for start, end in sorted(intervals):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
"""


def response(answer=None, code=None):
    return BenchmarkResponse(
        answer=answer or {},
        concise_method_summary="visible summary",
        assumptions=[],
        confidence=0.8,
        proposed_verification=["external checks"],
        files=[{"path": "solution.py", "content": code}] if code else [],
    )


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.tasks = load_tasks()
        self.lookup = {task.task_id: task for task in self.tasks}
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name) / "results"

    def test_task_loading_and_condition_matrix(self):
        cells = matrix(self.tasks)
        self.assertEqual(len(cells), 96)
        self.assertEqual(len({cell.key for cell in cells}), 96)
        self.assertEqual({cell.model for cell in cells}, {"sonnet", "gpt-5.6-terra"})
        self.assertEqual(cells, matrix(self.tasks))
        self.assertEqual(len(matrix(self.tasks[:4], secondary=True)), 16)

    def test_roles_only_change_constitution_not_task_or_grader(self):
        task = self.tasks[0]
        cell = matrix([task])[0]
        prompts = {}
        for condition in ("baseline", "matched", "mismatched"):
            adjusted = cell.model_copy(update={"condition": condition})
            prompts[condition] = json.loads(prompt_for(task, adjusted))
            self.assertNotIn("ground_truth_or_acceptance", prompts[condition])
            self.assertEqual(prompts[condition]["task"], task.task)
        self.assertNotIn("specialist_constitution", prompts["baseline"])
        self.assertEqual(prompts["matched"]["specialist_constitution"]["role"], "Physicist")
        self.assertEqual(prompts["mismatched"]["specialist_constitution"]["role"], "Statistician")
        self.assertEqual(prompts["matched"]["instruction"], prompts["baseline"]["instruction"])
        self.assertEqual(role_for(task, cell.model_copy(update={"condition": "baseline"})), "None")

    def test_numeric_graders_gold_wrong_and_tiny_root(self):
        for task in self.tasks:
            if task.fixture:
                continue
            self.assertEqual(grade(task, response(task.ground_truth_or_acceptance)).score, 1)
            self.assertLess(grade(task, response()).score, 1)
        task = self.lookup["math_cancellation"]
        wrong = dict(task.ground_truth_or_acceptance, positive_root_b1e16=0)
        self.assertEqual(grade(task, response(wrong)).tests_passed, 7)

    def test_ground_truth_independent_properties(self):
        task = self.lookup["math_independent_set"]
        cases = ([5, 1, 1, 5], [4, 5, 4, 5, 4], [-3, 0, -2, 0], [2, 2, 2, 2, 2, 2])
        for index, weights in enumerate(cases, 1):
            feasible = []
            for bits in itertools.product((0, 1), repeat=len(weights)):
                if any(a and b for a, b in zip(bits, bits[1:])):
                    continue
                indices = [i for i, b in enumerate(bits) if b]
                feasible.append((sum(weights[i] for i in indices), indices))
            best = sorted(feasible, key=lambda pair: (-pair[0], pair[1]))[0]
            self.assertEqual(
                task.ground_truth_or_acceptance[f"case{index}"],
                {"weight": best[0], "indices": best[1]},
            )
        for x, v, h in ((1, 0, 0.6), (2, 3, 0.2), (-1, 4, 1.7)):
            next_v = v - h * x
            next_x = x + h * next_v
            self.assertAlmostEqual(
                x * x + v * v - h * x * v, next_x**2 + next_v**2 - h * next_x * next_v
            )
        self.assertEqual((-1e16 + (1e32 + 4) ** 0.5) / 2, 0)

    def test_coding_graders_gold_and_broken_fixtures(self):
        for task_id, code in (
            ("software_escaped_fields", PARSER),
            ("software_merge_intervals", INTERVALS),
        ):
            task = self.lookup[task_id]
            actual = grade(task, response(code=code))
            self.assertEqual(actual.score, 1, actual)
            broken = (Path(__file__).parents[1] / "benchmarks/fixtures" / task.fixture).read_text()
            self.assertLess(grade(task, response(code=broken)).score, 1)

    def test_restricted_code_rejects_escape_surfaces(self):
        for code in (
            "import os",
            "def f(x):\n return open('/etc/passwd')",
            "def f(x):\n return x.__class__",
            "@print\ndef f(x):\n return x",
            "def f(x):\n return eval(x)",
        ):
            with self.assertRaises(ValueError):
                validate(code)

    def test_call_cap_and_invalid_budget(self):
        with self.assertRaises(ValueError):
            Store(self.output, time.time() + 60, max_calls=121)
        store = Store(self.output, time.time() + 60, max_calls=2)
        cells = matrix(self.tasks)
        self.assertTrue(store.reserve(cells[0]))
        self.assertFalse(store.reserve(cells[0]))
        self.assertTrue(store.reserve(cells[1]))
        self.assertFalse(store.reserve(cells[2]))

    def test_result_persistence_and_resume_skip(self):
        cell = matrix(self.tasks)[0]
        store = Store(self.output, time.time() + 60)
        self.assertTrue(store.reserve(cell))
        item = empty_result(self.lookup[cell.task_id], cell, store.manifest["run_id"], "MALFORMED")
        store.persist(item)
        resumed = Store(self.output, time.time() + 120)
        self.assertEqual(resumed.rows[cell.key], item)
        self.assertFalse(resumed.reserve(cell))
        self.assertEqual(resumed.manifest["deadline"], store.manifest["deadline"])
        with self.assertRaises(ValueError):
            resumed.persist(item)
        self.assertEqual(len((self.output / "responses.jsonl").read_text().splitlines()), 1)

    def test_interrupted_reservation_is_data_not_retry(self):
        store = Store(self.output, time.time() + 60)
        cell = matrix(self.tasks)[0]
        store.reserve(cell)
        resumed = Store(self.output, time.time() + 60)
        resumed.interrupted(self.lookup)
        self.assertEqual(resumed.rows[cell.key].error_category, "INTERRUPTED")
        self.assertFalse(resumed.reserve(cell))

    def test_concurrency_cap(self):
        store = Store(self.output, time.time() + 60)
        state = {"active": 0, "peak": 0}
        lock = threading.Lock()

        def fake(task, cell, run_id, output, deadline):
            with lock:
                state["active"] += 1
                state["peak"] = max(state["peak"], state["active"])
            time.sleep(0.02)
            result = empty_result(task, cell, run_id, "MALFORMED")
            with lock:
                state["active"] -= 1
            return result

        with patch("benchmarks.runner.invoke", side_effect=fake):
            sweep(store, self.lookup, matrix(self.tasks)[:6], concurrency=2)
        self.assertEqual(state["peak"], 2)
        self.assertEqual(len(store.rows), 6)
        with self.assertRaises(ValueError):
            sweep(store, self.lookup, [], concurrency=3)

    def test_failure_recording_no_retry_and_usage_sanitisation(self):
        cell = matrix(self.tasks)[0]
        with patch(
            "benchmarks.runner.CliProviders.ask", side_effect=Blocked("Malformed result")
        ) as ask:
            result = invoke(self.lookup[cell.task_id], cell, "test", self.output, time.time() + 60)
        self.assertEqual(ask.call_count, 1)
        self.assertEqual(result.error_category, "MALFORMED")
        self.assertFalse(result.call_success)
        self.assertEqual(result.objective_score, 0)
        cleaned = clean_usage(
            {
                "account_id": "secret",
                "usage": {"input_tokens": 5, "account": "secret"},
                "models": {"claude-sonnet-5": {"outputTokens": 2, "session_id": "secret"}},
            }
        )
        self.assertNotIn("secret", json.dumps(cleaned))

    def test_summary_exports_pairing_and_secondary_separation(self):
        rows = []
        for cell in matrix(self.tasks[:1]):
            item = empty_result(self.tasks[0], cell, "test", "MALFORMED")
            item.objective_score = {"baseline": 0.5, "matched": 1, "mismatched": 0.25}[
                cell.condition
            ]
            item.call_success = item.schema_success = True
            item.response_text = "visible response"
            rows.append(item)
        self.output.mkdir()
        report = export(self.output, rows)
        self.assertEqual(report["matched_minus_baseline"], 0.5)
        self.assertEqual(report["mismatched_minus_baseline"], -0.25)
        secondary = rows[0].model_copy(
            update={"sweep": "secondary", "model": "gpt-5.6-sol", "objective_score": 0}
        )
        self.assertEqual(summary(rows + [secondary])["matched_minus_baseline"], 0.5)
        for name in (
            "responses.jsonl",
            "results.csv",
            "summary.json",
            "SUMMARY.md",
            "router_prior_suggestions.json",
        ):
            self.assertTrue((self.output / name).exists())

    def test_secondary_selection_bounded_and_deterministic(self):
        selected = secondary_tasks(self.tasks, [])
        self.assertEqual(len(selected), 4)
        self.assertTrue(all(task.difficulty_prior == "high" for task in selected))
        self.assertEqual(selected, secondary_tasks(self.tasks, []))

    def test_deadline_and_cancel_do_not_invoke_models(self):
        store = Store(self.output, time.time() - 1)
        with patch("benchmarks.runner.invoke") as call:
            sweep(store, self.lookup, matrix(self.tasks))
        call.assert_not_called()
        self.assertEqual(len(store.manifest["reservations"]), 0)


if __name__ == "__main__":
    unittest.main()
