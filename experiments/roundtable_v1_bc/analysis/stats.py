"""Frozen, equal-task C−B analysis of complete, provenance-checked main records.

The caller supplies the independently verified frozen main manifest and raw
terminal records. Hash agreement checks consistency, not authenticity of an
arbitrary caller-created manifest. MOCK requires explicit opt-in and is always
labelled synthetic. No filesystem discovery, historical imports or inference.
"""

from __future__ import annotations

import math
import random
import re
from collections import Counter, defaultdict
from typing import Any

from ..harness.records import encoded, sha

EXPERIMENT = "roundtable-v1-bc-20260916-v1"
RANDOMIZATION_DRAWS = 100_000
BOOTSTRAP_DRAWS = 19_999
ANALYSIS_SEED = 2026091602
BOOTSTRAP_SEED = 2026091603
INFRASTRUCTURE_FAILURES = {"STARTUP", "CONFIGURATION", "PROVIDER_ERROR", "TRANSPORT_TIMEOUT"}
TOKEN_FIELDS = {
    "input_tokens",
    "output_tokens",
    "cached_input_tokens",
    "reasoning_output_tokens",
    "total_tokens",
}
Json = dict[str, Any]


def _number(value: object, name: str, maximum: float = math.inf) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(name)
    result = float(value)
    if not math.isfinite(result) or not 0 <= result <= maximum:
        raise ValueError(name)
    return result


def _integer(value: object, name: str, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= maximum:
        raise ValueError(name)
    return value


def _hash(value: object) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _validate(
    records: list[Json], tasks: list[str], repetitions: int, manifest: Json, allow_mock: bool
) -> None:
    if (
        type(manifest) is not dict
        or type(records) is not list
        or any(type(row) is not dict for row in records)
    ):
        raise ValueError("INVALID_RECORD_CONTAINER")
    if (
        not tasks
        or any(type(task) is not str or not task for task in tasks)
        or len(set(tasks)) != len(tasks)
        or type(repetitions) is not int
        or repetitions < 1
    ):
        raise ValueError("INVALID_TASK_FRAME")
    kind = manifest.get("kind")
    if (
        type(kind) is not str
        or kind not in {"LIVE", "MOCK"}
        or (kind == "MOCK" and allow_mock is not True)
    ):
        raise ValueError("MOCK_REQUIRES_EXPLICIT_OPT_IN")
    if manifest.get("experiment_id") != EXPERIMENT or manifest.get("phase") != "main":
        raise ValueError("FOREIGN_EXPERIMENT_OR_PHASE")
    if kind == "LIVE" and (len(tasks) != 8 or repetitions != 8):
        raise ValueError("EXACT_MAIN_DESIGN_REQUIRED")
    if (
        manifest.get("tasks") != tasks
        or manifest.get("repetitions") != repetitions
        or not _hash(manifest.get("protocol_sha256"))
    ):
        raise ValueError("MANIFEST_FRAME_MISMATCH")
    if kind == "LIVE" and (
        manifest.get("frozen") is not True
        or re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("freeze_commit", ""))) is None
    ):
        raise ValueError("FROZEN_COMMITTED_MANIFEST_REQUIRED")
    task_hashes = manifest.get("task_hashes")
    if (
        type(task_hashes) is not dict
        or set(task_hashes) != set(tasks)
        or not all(_hash(value) for value in task_hashes.values())
    ):
        raise ValueError("INVALID_TASK_HASHES")
    schedule = manifest.get("schedule")
    if type(schedule) is not dict or set(schedule) != {"experiment_id", "seed", "rows", "sha256"}:
        raise ValueError("INVALID_SCHEDULE")
    payload = {key: value for key, value in schedule.items() if key != "sha256"}
    if (
        schedule["experiment_id"] != EXPERIMENT
        or type(schedule["seed"]) is not int
        or schedule["sha256"] != sha(encoded(payload))
    ):
        raise ValueError("SCHEDULE_HASH_MISMATCH")
    expected: dict[str, Json] = {}
    cells: set[tuple[str, int, str]] = set()
    slots: set[tuple[str, int, int]] = set()
    if type(schedule["rows"]) is not list:
        raise ValueError("INVALID_SCHEDULE_ROWS")
    for row in schedule["rows"]:
        if type(row) is not dict or set(row) != {
            "task_id",
            "block",
            "condition",
            "position",
            "run_id",
        }:
            raise ValueError("INVALID_SCHEDULE_ROW")
        task, block, arm, position, run_id = (
            row[key] for key in ("task_id", "block", "condition", "position", "run_id")
        )
        if (
            type(task) is not str
            or task not in tasks
            or type(block) is not int
            or not 0 <= block < repetitions
            or type(arm) is not str
            or arm not in {"B", "C"}
            or type(position) is not int
            or position not in {0, 1}
            or run_id != f"{EXPERIMENT}--{task}--r{block:02}--{arm}"
        ):
            raise ValueError("FOREIGN_SCHEDULE_CELL")
        cell, slot = (task, block, arm), (task, block, position)
        if run_id in expected or cell in cells or slot in slots:
            raise ValueError("DUPLICATE_SCHEDULE_CELL")
        expected[run_id] = row
        cells.add(cell)
        slots.add(slot)
    if len(expected) != len(tasks) * repetitions * 2 or len(records) != len(expected):
        raise ValueError("INCOMPLETE_OR_EXCESS_MAIN")
    seen: set[str] = set()
    for row in records:
        run_id = row.get("run_id")
        if type(run_id) is not str or run_id not in expected:
            raise ValueError("UNSCHEDULED_RUN")
        if run_id in seen:
            raise ValueError("DUPLICATE_RUN")
        seen.add(run_id)
        if any(row.get(key) != expected[run_id][key] for key in ("task_id", "block", "condition")):
            raise ValueError("RUN_CELL_MISMATCH")
        if type(row.get("block")) is not int:
            raise ValueError("INVALID_BLOCK_TYPE")
        if any(
            row.get(key) != manifest[key]
            for key in ("experiment_id", "phase", "kind", "protocol_sha256")
        ):
            raise ValueError("FOREIGN_RECORD_PROVENANCE")
        if (
            row.get("schedule_sha256") != schedule["sha256"]
            or row.get("task_sha256") != task_hashes[row["task_id"]]
        ):
            raise ValueError("RECORD_HASH_MISMATCH")
        _number(row.get("score"), "UNRESOLVED_EVALUATOR_SCORE", 1)
        for key in ("institution_completed", "evaluable", "schema_success"):
            if type(row.get(key)) is not bool:
                raise ValueError("MISSING_OR_INVALID_STATUS")
        if "failure" not in row:
            raise ValueError("MISSING_FAILURE_STATUS")
        if row.get("failure") == "EVALUATOR_ERROR":
            raise ValueError("EVALUATOR_REPLAY_REQUIRED")
        if row.get("failure") is not None and (
            type(row["failure"]) is not str or not row["failure"]
        ):
            raise ValueError("INVALID_FAILURE")
        if type(row.get("state")) is not str or row.get("state") not in {"COMPLETED", "FAILED"}:
            raise ValueError("TERMINAL_RECORD_REQUIRED")
        completed = row["institution_completed"] and row["failure"] is None
        if (row["state"] == "COMPLETED") != completed:
            raise ValueError("INCONSISTENT_COMPLETION")
        if row["schema_success"] != row["institution_completed"]:
            raise ValueError("INCONSISTENT_SCHEMA_SUCCESS")
        if row["evaluable"]:
            if not _hash(row.get("artifact_sha256")) or type(row.get("full_pass")) is not bool:
                raise ValueError("MISSING_ARTIFACT_OR_GRADER_RESULT")
            if row["full_pass"] != (row["score"] == 1):
                raise ValueError("INCONSISTENT_FULL_PASS")
        elif (
            row["score"] != 0
            or row.get("artifact_sha256") is not None
            or row.get("full_pass", False) is not False
            or row["failure"] is None
        ):
            raise ValueError("NON_EVALUABLE_FAILURE_MUST_SCORE_ZERO")
        calls = _integer(row.get("model_calls"), "INVALID_CALL_COUNT", 6)
        invocations = _integer(row.get("stage_invocations"), "INVALID_STAGE_COUNT", 6)
        repairs = _integer(row.get("repair_count"), "INVALID_REPAIR_COUNT", 1)
        if invocations > 5 + repairs or (
            row["institution_completed"] and invocations != 5 + repairs
        ):
            raise ValueError("STAGE_BUDGET_OR_COMPLETION_MISMATCH")
        if (kind == "LIVE" and calls != invocations) or (kind == "MOCK" and calls != 0):
            raise ValueError("LIVE_MOCK_CALL_COUNT_MISMATCH")
        _number(row.get("seconds"), "INVALID_LATENCY")
        for key in ("visible_initial", "visible_repair"):
            if key in row and (
                type(row[key]) is not dict or type(row[key].get("full_pass")) is not bool
            ):
                raise ValueError("INVALID_VISIBLE_RESULT")
        tokens = row.get("tokens")
        if tokens is not None:
            if type(tokens) is int:
                _integer(tokens, "INVALID_TOKENS", 2**63 - 1)
            elif type(tokens) is dict and set(tokens) <= TOKEN_FIELDS and tokens:
                for value in tokens.values():
                    if value is not None:
                        _integer(value, "INVALID_TOKENS", 2**63 - 1)
            else:
                raise ValueError("INVALID_TOKENS")


def pairs(
    records: list[Json],
    tasks: list[str],
    repetitions: int = 8,
    *,
    manifest: Json,
    allow_mock: bool = False,
) -> dict[str, list[float]]:
    _validate(records, tasks, repetitions, manifest, allow_mock)
    blocks: dict[tuple[str, int], dict[str, float]] = defaultdict(dict)
    for row in records:
        blocks[row["task_id"], row["block"]][row["condition"]] = float(row["score"])
    return {
        task: [blocks[task, rep]["C"] - blocks[task, rep]["B"] for rep in range(repetitions)]
        for task in sorted(tasks)
    }


def _secondary(records: list[Json]) -> Json:
    result: Json = {}
    for arm in ("B", "C"):
        rows = sorted(
            (row for row in records if row["condition"] == arm), key=lambda row: row["run_id"]
        )
        n = len(rows)
        visible = [row.get("visible_repair", row.get("visible_initial")) for row in rows]
        tested = sum(value is not None for value in visible)
        passed = sum(value is not None and value["full_pass"] for value in visible)
        token_sums: dict[str, int] = defaultdict(int)
        token_observed: dict[str, int] = defaultdict(int)
        for row in rows:
            tokens = row.get("tokens")
            usage = {"total_tokens": tokens} if type(tokens) is int else tokens or {}
            for key, value in usage.items():
                if value is not None:
                    token_sums[key] += value
                    token_observed[key] += 1
        result[arm] = {
            "planned": n,
            "attempted": n,
            "completed": sum(row["institution_completed"] for row in rows),
            "evaluable": sum(row["evaluable"] for row in rows),
            "failed": sum(row["state"] == "FAILED" for row in rows),
            "failure_rate": sum(row["state"] == "FAILED" for row in rows) / n,
            "failure_classes": dict(
                sorted(
                    Counter(row["failure"] for row in rows if row["failure"] is not None).items()
                )
            ),
            "infrastructure_provider_failures": sum(
                row["failure"] in INFRASTRUCTURE_FAILURES for row in rows
            ),
            "full_pass_rate": sum(row.get("full_pass", False) for row in rows) / n,
            "protocol_schema_success_rate": sum(row["schema_success"] for row in rows) / n,
            "visible_pass_rate_all_runs": passed / n,
            "visible_pass_rate_tested_runs": passed / tested if tested else None,
            "visible_tested_runs": tested,
            "visible_unobserved_runs": n - tested,
            "repairs": sum(row["repair_count"] for row in rows),
            "repair_rate": sum(row["repair_count"] for row in rows) / n,
            "model_calls": sum(row["model_calls"] for row in rows),
            "stage_invocations": sum(row["stage_invocations"] for row in rows),
            "tokens": {
                key: {
                    "known_sum": token_sums.get(key),
                    "observed_runs": token_observed[key],
                    "missing_runs": n - token_observed[key],
                }
                for key in sorted(TOKEN_FIELDS)
            },
            "run_latency_seconds": {
                "total": math.fsum(row["seconds"] for row in rows),
                "mean": math.fsum(row["seconds"] for row in rows) / n,
            },
        }
    return result


def analyze(
    records: list[Json],
    tasks: list[str],
    repetitions: int = 8,
    *,
    manifest: Json,
    allow_mock: bool = False,
) -> Json:
    grouped = pairs(records, tasks, repetitions, manifest=manifest, allow_mock=allow_mock)
    effects = {task: math.fsum(values) / len(values) for task, values in grouped.items()}
    terms = [value / len(values) / len(grouped) for values in grouped.values() for value in values]
    delta = math.fsum(terms)
    rng = random.Random(ANALYSIS_SEED)
    exceed = sum(
        abs(math.fsum(value if rng.getrandbits(1) else -value for value in terms)) >= abs(delta)
        for _ in range(RANDOMIZATION_DRAWS)
    )
    bootstrap = []
    rng = random.Random(BOOTSTRAP_SEED)
    for _ in range(BOOTSTRAP_DRAWS):
        selected = rng.choices(sorted(grouped), k=len(grouped))
        bootstrap.append(
            math.fsum(
                math.fsum(rng.choices(grouped[task], k=len(grouped[task]))) / len(grouped[task])
                for task in selected
            )
            / len(selected)
        )
    bootstrap.sort()
    interval = [
        bootstrap[int(0.025 * (BOOTSTRAP_DRAWS - 1))],
        bootstrap[int(0.975 * (BOOTSTRAP_DRAWS - 1))],
    ]
    return {
        "kind": manifest["kind"],
        "synthetic_only": manifest["kind"] == "MOCK",
        "experiment_id": manifest["experiment_id"],
        "phase": "main",
        "protocol_sha256": manifest["protocol_sha256"],
        "schedule_sha256": manifest["schedule"]["sha256"],
        "records_sha256": sha(encoded(sorted(records, key=lambda row: row["run_id"]))),
        "delta_C_minus_B": delta,
        "two_sided_randomization_p": (1 + exceed) / (1 + RANDOMIZATION_DRAWS),
        "randomization_draws": RANDOMIZATION_DRAWS,
        "analysis_seed": ANALYSIS_SEED,
        "randomization_method": "independent B/C swaps within each task-repetition block; plus-one Monte Carlo p",
        "task_effects": effects,
        "paired_hierarchical_bootstrap_interval": interval,
        "bootstrap_draws": BOOTSTRAP_DRAWS,
        "bootstrap_seed": BOOTSTRAP_SEED,
        "bootstrap_method": "95% percentile interval; resample tasks, then paired repetitions within sampled task; floor(p*(n-1)) quantiles",
        "secondary": _secondary(records),
        "practical_effect_threshold": 0.05,
        "equivalence_established": False,
        "scope": "fixed authored benchmark; hierarchical task/paired-repetition bootstrap is approximate, not a claim of all-coding-task representativeness",
    }
