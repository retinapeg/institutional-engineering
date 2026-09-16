"""Synthetic-only checks of frozen inference, pairing and provenance refusal."""

from __future__ import annotations

import copy
import itertools
import math
import random
import unittest
from typing import Any

from experiments.roundtable_v1_bc.analysis.stats import (
    ANALYSIS_SEED,
    BOOTSTRAP_DRAWS,
    EXPERIMENT,
    RANDOMIZATION_DRAWS,
    analyze,
    pairs,
)
from experiments.roundtable_v1_bc.harness.records import encoded, sha

Json = dict[str, Any]


def synthetic_frame(task_count: int = 2, repetitions: int = 2) -> tuple[Json, list[Json]]:
    tasks = [f"synthetic_task_{i}" for i in range(task_count)]
    rng = random.Random(2026091601)
    blocks = [(task, rep) for task in tasks for rep in range(repetitions)]
    rng.shuffle(blocks)
    schedule_rows = []
    for task, rep in blocks:
        arms = ["B", "C"]
        rng.shuffle(arms)
        for position, arm in enumerate(arms):
            schedule_rows.append(
                {
                    "task_id": task,
                    "block": rep,
                    "condition": arm,
                    "position": position,
                    "run_id": f"{EXPERIMENT}--{task}--r{rep:02}--{arm}",
                }
            )
    payload = {"experiment_id": EXPERIMENT, "seed": 2026091601, "rows": schedule_rows}
    manifest: Json = {
        "experiment_id": EXPERIMENT,
        "phase": "main",
        "kind": "MOCK",
        "tasks": tasks,
        "repetitions": repetitions,
        "protocol_sha256": sha(b"synthetic protocol"),
        "task_hashes": {task: sha(task.encode()) for task in tasks},
        "schedule": {**payload, "sha256": sha(encoded(payload))},
    }
    records = []
    for cell in schedule_rows:
        records.append(
            {
                **cell,
                "experiment_id": EXPERIMENT,
                "phase": "main",
                "kind": "MOCK",
                "task_sha256": manifest["task_hashes"][cell["task_id"]],
                "protocol_sha256": manifest["protocol_sha256"],
                "schedule_sha256": manifest["schedule"]["sha256"],
                "score": 0.5,
                "full_pass": False,
                "artifact_sha256": sha(b"synthetic artifact"),
                "institution_completed": True,
                "evaluable": True,
                "schema_success": True,
                "failure": None,
                "state": "COMPLETED",
                "model_calls": 0,
                "stage_invocations": 5,
                "repair_count": 0,
                "seconds": 1.0,
                "tokens": None,
                "visible_initial": {"full_pass": True},
            }
        )
    return manifest, records


def run_analysis(manifest: Json, records: list[Json]) -> Json:
    return analyze(
        records, manifest["tasks"], manifest["repetitions"], manifest=manifest, allow_mock=True
    )


def validate(manifest: Json, records: list[Json]) -> dict[str, list[float]]:
    return pairs(
        records, manifest["tasks"], manifest["repetitions"], manifest=manifest, allow_mock=True
    )


class AnalysisTests(unittest.TestCase):
    def test_zero_effect_and_unknown_resources(self) -> None:
        manifest, records = synthetic_frame()
        result = run_analysis(manifest, records)
        self.assertTrue(result["synthetic_only"])
        self.assertEqual(result["delta_C_minus_B"], 0)
        self.assertEqual(result["two_sided_randomization_p"], 1)
        self.assertEqual(result["paired_hierarchical_bootstrap_interval"], [0, 0])
        self.assertEqual(result["randomization_draws"], 100_000)
        self.assertEqual(result["analysis_seed"], 2026091602)
        self.assertEqual(result["bootstrap_draws"], 19_999)
        self.assertEqual(result["bootstrap_seed"], 2026091603)
        self.assertFalse(result["equivalence_established"])
        for arm in ("B", "C"):
            self.assertEqual(result["secondary"][arm]["planned"], 4)
            self.assertEqual(result["secondary"][arm]["model_calls"], 0)
            self.assertEqual(
                result["secondary"][arm]["tokens"]["total_tokens"],
                {"known_sum": None, "observed_runs": 0, "missing_runs": 4},
            )

    def test_known_sign_symmetric_p_and_interval(self) -> None:
        manifest, records = synthetic_frame()
        for row in records:
            row["score"] = float(row["condition"] == "C")
            row["full_pass"] = row["score"] == 1
        positive = run_analysis(manifest, records)
        for row in records:
            row["score"] = 1 - row["score"]
            row["full_pass"] = row["score"] == 1
        negative = run_analysis(manifest, records)
        self.assertEqual(positive["delta_C_minus_B"], 1)
        self.assertEqual(negative["delta_C_minus_B"], -1)
        # Four paired signs: two of sixteen assignments are as extreme as all +1.
        self.assertAlmostEqual(positive["two_sided_randomization_p"], 2 / 16, delta=0.005)
        self.assertEqual(
            positive["two_sided_randomization_p"], negative["two_sided_randomization_p"]
        )
        self.assertEqual(positive["paired_hierarchical_bootstrap_interval"], [1, 1])
        self.assertEqual(negative["paired_hierarchical_bootstrap_interval"], [-1, -1])

    def test_exact_small_pair_distribution_and_record_order_invariance(self) -> None:
        manifest, records = synthetic_frame()
        contrasts = {
            ("synthetic_task_0", 0): 0.5,
            ("synthetic_task_0", 1): -0.25,
            ("synthetic_task_1", 0): 0.75,
            ("synthetic_task_1", 1): 0,
        }
        for row in records:
            difference = contrasts[row["task_id"], row["block"]]
            row["score"] = max(-difference, 0) if row["condition"] == "B" else max(difference, 0)
            row["full_pass"] = row["score"] == 1
        before = copy.deepcopy(records)
        result = run_analysis(manifest, records)
        terms = [value / 4 for value in contrasts.values()]
        exact = (
            sum(
                abs(math.fsum(sign * term for sign, term in zip(signs, terms, strict=True))) >= 0.25
                for signs in itertools.product((-1, 1), repeat=4)
            )
            / 16
        )
        self.assertEqual(result["delta_C_minus_B"], 0.25)
        self.assertEqual(
            result["task_effects"], {"synthetic_task_0": 0.125, "synthetic_task_1": 0.375}
        )
        self.assertAlmostEqual(result["two_sided_randomization_p"], exact, delta=0.005)
        self.assertEqual(result, run_analysis(manifest, list(reversed(records))))
        self.assertEqual(records, before)
        self.assertEqual(
            (RANDOMIZATION_DRAWS, BOOTSTRAP_DRAWS, ANALYSIS_SEED), (100_000, 19_999, 2026091602)
        )

    def test_no_missing_excess_duplicate_or_unscheduled_run(self) -> None:
        manifest, records = synthetic_frame()
        variants = [records[:-1], records + [records[0]], records[:-1] + [records[0]]]
        foreign = copy.deepcopy(records)
        foreign[0]["run_id"] = "historical-calibration-run"
        variants.append(foreign)
        for value in variants:
            with self.subTest(records=value), self.assertRaises(ValueError):
                validate(manifest, value)

    def test_provenance_and_cell_mutations_rejected(self) -> None:
        manifest, records = synthetic_frame()
        for field, value in [
            ("phase", "calibration"),
            ("experiment_id", "single_task_role_effect"),
            ("kind", "LIVE"),
            ("block", True),
            ("block", 99),
            ("condition", "A"),
            ("task_id", "other"),
            ("protocol_sha256", "0" * 64),
            ("schedule_sha256", "0" * 64),
            ("task_sha256", "0" * 64),
        ]:
            modified = copy.deepcopy(records)
            modified[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate(manifest, modified)
        with self.assertRaisesRegex(ValueError, "MOCK_REQUIRES"):
            pairs(records, manifest["tasks"], 2, manifest=manifest)
        for field in ("phase", "kind", "experiment_id", "protocol_sha256", "task_hashes"):
            broken = copy.deepcopy(manifest)
            broken.pop(field)
            with self.subTest(missing=field), self.assertRaises(ValueError):
                validate(broken, records)

    def test_invalid_scores_statuses_resources_and_grader_rejected(self) -> None:
        manifest, records = synthetic_frame()
        for field, value in [
            ("score", None),
            ("score", float("nan")),
            ("score", True),
            ("score", -0.1),
            ("score", 1.1),
            ("score", "0.5"),
            ("failure", "EVALUATOR_ERROR"),
            ("full_pass", True),
            ("evaluable", False),
            ("schema_success", "yes"),
            ("state", "STARTED"),
            ("model_calls", 1),
            ("model_calls", True),
            ("stage_invocations", 6),
            ("repair_count", 2),
            ("seconds", -1),
            ("tokens", {"output_tokens": -1}),
            ("tokens", True),
            ("visible_initial", {"full_pass": "yes"}),
        ]:
            modified = copy.deepcopy(records)
            modified[0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                validate(manifest, modified)

    def test_infrastructure_failure_keeps_denominator_and_existing_artifact(self) -> None:
        manifest, records = synthetic_frame()
        failed = next(row for row in records if row["condition"] == "B")
        failed.update(
            score=0,
            full_pass=False,
            artifact_sha256=None,
            institution_completed=False,
            evaluable=False,
            schema_success=False,
            failure="PROVIDER_ERROR",
            state="FAILED",
            stage_invocations=1,
        )
        failed.pop("visible_initial")
        salvage = next(row for row in records if row["condition"] == "C")
        salvage.update(
            institution_completed=False,
            schema_success=False,
            failure="PROVIDER_ERROR",
            state="FAILED",
            repair_count=1,
            stage_invocations=6,
            tokens={"input_tokens": 10, "output_tokens": 5},
        )
        salvage["visible_initial"] = {"full_pass": False}
        result = run_analysis(manifest, records)
        self.assertEqual(result["delta_C_minus_B"], 0.125)
        self.assertEqual(result["secondary"]["B"]["planned"], 4)
        self.assertEqual(result["secondary"]["B"]["evaluable"], 3)
        self.assertEqual(result["secondary"]["C"]["evaluable"], 4)
        self.assertEqual(result["secondary"]["B"]["failure_rate"], 0.25)
        self.assertEqual(result["secondary"]["B"]["visible_unobserved_runs"], 1)
        self.assertEqual(result["secondary"]["C"]["repair_rate"], 0.25)
        self.assertEqual(
            result["secondary"]["C"]["tokens"]["input_tokens"],
            {"known_sum": 10, "observed_runs": 1, "missing_runs": 3},
        )

    def test_manifest_schedule_integrity_and_duplicate_position(self) -> None:
        manifest, records = synthetic_frame()
        for rehash in (False, True):
            broken = copy.deepcopy(manifest)
            schedule = broken["schedule"]
            schedule["rows"][1]["position"] = schedule["rows"][0]["position"]
            if rehash:
                schedule["sha256"] = sha(
                    encoded({key: value for key, value in schedule.items() if key != "sha256"})
                )
            with self.subTest(rehash=rehash), self.assertRaises(ValueError):
                validate(broken, records)
        with self.assertRaises(ValueError):
            pairs(records, [manifest["tasks"][0]] * 2, 2, manifest=manifest, allow_mock=True)

    def test_live_frame_requires_frozen_commit_and_exact_main_size(self) -> None:
        # Structural rejection tests only: synthetic records never analysed as LIVE.
        manifest, records = synthetic_frame(8, 8)
        manifest["kind"] = "LIVE"
        for row in records:
            row["kind"] = "LIVE"
            row["model_calls"] = 5
        with self.assertRaisesRegex(ValueError, "FROZEN_COMMITTED"):
            validate(manifest, records)
        small, small_records = synthetic_frame()
        small["kind"] = "LIVE"
        with self.assertRaisesRegex(ValueError, "EXACT_MAIN_DESIGN"):
            validate(small, small_records)


if __name__ == "__main__":
    unittest.main()
