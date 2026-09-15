import itertools
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from benchmarks.analysis import atomic_json
from experiments.single_task_role_effect import study
from experiments.single_task_role_effect.analysis import comparisons, proportion, wilson
from experiments.single_task_role_effect.design import (
    CONDITIONS,
    MODEL,
    candidates,
    extract,
    select,
)


class SingleTaskTests(unittest.TestCase):
    def test_finite_oracles_independently_enumerated(self):
        for task in candidates():
            if task["kind"] == "independent_set":
                feasible = []
                for size in range(13):
                    for chosen in itertools.combinations(range(1, 13), size):
                        if all(not {a, b} <= set(chosen) for a, b in task["edges"]):
                            feasible.append(sum(task["weights"][i - 1] for i in chosen))
                expected = max(feasible)
            elif task["kind"] == "knapsack":
                feasible = []
                for chosen in itertools.combinations(range(1, 13), 5):
                    if (2 in chosen and 10 in chosen) or (6 in chosen and 9 not in chosen):
                        continue
                    w, v, score = map(sum, zip(*(task["items"][i - 1] for i in chosen)))
                    if w <= 26 and v <= 25:
                        feasible.append(score)
                expected = max(feasible)
            else:
                feasible = []

                def visit(assign):
                    if len(assign) == 6:
                        if (
                            assign[0] != 1
                            and assign[3] != 4
                            and sum(i == j for i, j in enumerate(assign)) == 2
                            and assign[1] % 2 != assign[4] % 2
                        ):
                            feasible.append(sum(task["costs"][i][j] for i, j in enumerate(assign)))
                        return
                    for job in range(6):
                        if job not in assign:
                            visit(assign + [job])

                visit([])
                expected = min(feasible)
            self.assertEqual(task["ground_truth"], expected)

    def test_extractor_harmless_format_and_ambiguity(self):
        for text in (
            "FINAL_ANSWER: 42",
            "**FINAL_ANSWER:** `42`",
            "Method summary.\n42",
            "answer: 42.",
            "The answer is 42",
            "```\nFINAL_ANSWER: 42\n```",
            "FINAL_ANSWER: 42\nFINAL_ANSWER: 42",
        ):
            self.assertEqual(extract(text), 42, text)
        self.assertEqual(extract("FINAL_ANSWER: 1,234"), 1234)
        for text in (
            "FINAL_ANSWER: 4 or 5",
            "FINAL_ANSWER: 4\nFINAL_ANSWER: 5",
            "FINAL_ANSWER: 1.5",
            "Maybe 42?",
            "",
            "FINAL_ANSWER: 1,23",
        ):
            self.assertIsNone(extract(text), text)

    def test_task_bytes_constant_role_only_changes_wrapper(self):
        task = candidates()[0]["task"].encode()
        for condition in CONDITIONS:
            p = study.prompt(task, condition)
            self.assertEqual(p.split("<TASK>\n")[1].split("</TASK>")[0].encode(), task)
        self.assertNotIn("Mathematician", study.prompt(task, "baseline"))
        self.assertNotIn("ground_truth", study.prompt(task, "matched"))

    def test_schedule_caps_balance_and_seed(self):
        rows = study.schedule(["test"], False)
        self.assertEqual(len(rows), 1000)
        self.assertEqual(rows, study.schedule(["test"], False))
        for block in range(250):
            self.assertEqual(
                {r["condition"] for r in rows if r["block_index"] == block}, set(CONDITIONS)
            )
        self.assertEqual(len(study.schedule(["a", "b", "c"], True)), 60)
        self.assertEqual(len({(r["block_index"], r["condition"]) for r in rows}), 1000)

    def test_selection_no_ceiling_and_fixed_tie(self):
        rows = []
        ids = [t["task_id"] for t in candidates()]
        for task in ids:
            rows += [
                dict(
                    task_id=task,
                    protocol_valid=True,
                    substantive_correct=i < 13,
                    error_type_if_any=None,
                )
                for i in range(20)
            ]
        self.assertEqual(select(rows)[0], min(ids))
        for r in rows:
            r["substantive_correct"] = True
        self.assertIsNone(select(rows)[0])
        with self.assertRaises(ValueError):
            select(rows[:-1])

    def test_wilson_denominators_and_paired_contrasts(self):
        self.assertIsNone(wilson(0, 0))
        self.assertAlmostEqual(wilson(0, 20)[1], 0.161125158, places=7)
        self.assertAlmostEqual(wilson(20, 20)[0], 0.838874842, places=7)
        rows = [
            dict(
                block_index=b,
                condition=c,
                substantive_correct=c == "matched",
                protocol_valid=c != "baseline",
                error_type_if_any=None,
            )
            for b in range(3)
            for c in CONDITIONS
        ]
        self.assertEqual(proportion(rows)["n"], 12)
        self.assertEqual(proportion(rows, True)["n"], 9)
        result = comparisons(rows, draws=100)
        self.assertEqual(result["end_to_end:matched-baseline"]["risk_difference"], 1)
        self.assertIsNone(result["parsed:matched-baseline"]["risk_difference"])
        self.assertEqual(result["complete_blocks"], 3)

    def test_visible_output_only_no_hidden_or_account_metadata(self):
        events = [
            dict(type="item.completed", item=dict(type="reasoning", text="PRIVATE")),
            dict(type="item.completed", item=dict(type="agent_message", text="FINAL_ANSWER: 42")),
            dict(type="turn.completed", usage=dict(input_tokens=10, account_id="SECRET")),
        ]
        result = study.parse_events("\n".join(json.dumps(e) for e in events), "", 0)
        self.assertNotIn("PRIVATE", str(result))
        self.assertNotIn("SECRET", str(result))
        self.assertEqual(result["input_tokens_if_known"], 10)
        self.assertIsNone(result["error_type_if_any"])
        events.append(dict(type="error", message="usage limit exceeded"))
        result = study.parse_events("\n".join(json.dumps(e) for e in events), "", 1)
        self.assertEqual(result["error_type_if_any"], "RATE_LIMITED")

    def test_single_model_no_tools_no_schema_constraint(self):
        argv = study.argv()
        self.assertEqual(argv[argv.index("--model") + 1], MODEL)
        self.assertIn("read-only", argv)
        self.assertIn("--ephemeral", argv)
        self.assertNotIn("--output-schema", argv)
        self.assertIn("shell_tool", argv)

    def make_root(self, directory):
        root = Path(directory)
        (root / "PROTOCOL.md").write_bytes((study.ROOT / "PROTOCOL.md").read_bytes())
        with patch.object(study, "version", return_value="mock-cli"):
            study.prepare(root)
        return root

    def test_hash_mutation_blocks_before_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            study.verify(root)
            candidate = next((root / "candidates").glob("*.txt"))
            candidate.write_text(candidate.read_text() + "changed")
            with self.assertRaisesRegex(ValueError, "hash mismatch"):
                study.verify(root)

    def test_calibration_freeze_task_and_schedule_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            folder = root / "calibration_records"
            folder.mkdir()
            for cell in study.schedule([t["task_id"] for t in candidates()], True):
                row = dict(
                    **cell,
                    key=str(cell["call_index"]),
                    terminal=True,
                    protocol_valid=True,
                    substantive_correct=cell["block_index"] < 13,
                    error_type_if_any=None,
                )
                atomic_json(folder / f"{cell['call_index']:04d}.json", row)
            study.freeze(root)
            protocol = study.verify(root, True)
            self.assertEqual(
                (root / "task.txt").read_bytes(),
                (root / "candidates" / (protocol["task_id"] + ".txt")).read_bytes(),
            )
            self.assertEqual(len(study.read(root / "schedule.json")), 1000)
            before = (root / "protocol.json").read_bytes()
            study.freeze(root)
            self.assertEqual(before, (root / "protocol.json").read_bytes())
            (root / "task.txt").write_text("changed")
            with self.assertRaisesRegex(ValueError, "task.txt changed"):
                study.verify(root, True)

    def test_uncommitted_protocol_blocks_without_model_call(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            with patch.object(study, "invoke") as call:
                with self.assertRaises(ValueError):
                    study.batch(root, True)
                call.assert_not_called()

    def test_timeout_is_observation_not_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(
                study.Runner, "run", side_effect=RuntimeError("Command timed out")
            ) as run:
                result = study.invoke("synthetic", Path(directory))
            self.assertEqual(run.call_count, 1)
            self.assertEqual(result["error_type_if_any"], "TIMEOUT")

    def test_resume_failure_stop_and_reservation_no_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            original_verify = study.verify

            def fake_verify(root, full=False, committed=False):
                return original_verify(root, full, committed=False)

            failure = dict(response_text="", error_type_if_any="RATE_LIMITED", latency_seconds=0.1)
            with (
                patch.object(study, "verify", side_effect=fake_verify),
                patch.object(study, "version", return_value="mock-cli"),
                patch.object(study, "invoke", return_value=failure) as call,
            ):
                study.batch(root, True)
                self.assertEqual(call.call_count, 1)
                study.batch(root, True)
                self.assertEqual(call.call_count, 2)
            rows = study.observations(root, True)
            self.assertEqual(len(rows), 2)
            self.assertNotEqual(rows[0]["key"], rows[1]["key"])
            path = root / "calibration_records/0001.json"
            row = study.read(path)
            row["terminal"] = False
            atomic_json(path, row)
            (root / "cancel").touch()
            with (
                patch.object(study, "verify", side_effect=fake_verify),
                patch.object(study, "version", return_value="mock-cli"),
                patch.object(study, "invoke") as call,
            ):
                study.batch(root, True)
                call.assert_not_called()
            (root / "cancel").unlink()
            with (
                patch.object(study, "verify", side_effect=fake_verify),
                patch.object(study, "version", return_value="mock-cli"),
                patch.object(study, "invoke", return_value=failure),
            ):
                study.batch(root, True)
            self.assertEqual(study.read(path)["error_type_if_any"], "INTERRUPTED")
            self.assertEqual(len((root / "calibration_results.jsonl").read_text().splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
