"""Frozen domain mappings, stage schema and B/C scheduling policy."""

from __future__ import annotations

import math
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from .records import encoded, sha

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = "roundtable-v1-bc-20260916-v1"
ROLE_BANK = {
    "security": "Security engineering: review trust boundaries, input validity, access assumptions and safe failure behavior.",
    "statistics": "Statistics: review estimands, denominators, sampling assumptions, missing values and interpretation of summaries.",
    "numerical_methods": "Numerical methods: review conditioning, finite precision, stability, limiting behavior and approximation error.",
    "ml_data_science": "ML and data science: review dataset separation, label semantics, evaluation metrics and information leakage.",
    "distributed_systems_reliability": "Distributed systems and reliability: review identity, ordering, retries, recovery and duplicate operations.",
    "algorithms": "Algorithms: review invariants, boundary cases, complexity, termination and correctness of state transitions.",
    "data_integrity": "Data integrity: review consistency, mutation, conservation, validation and atomic changes to records.",
    "api_protocol_engineering": "API and protocol engineering: review framing, partial inputs, interface contracts, state and error semantics.",
    "performance_concurrency": "Performance and concurrency: review interleavings, atomicity, stale state, contention and progress conditions.",
    "general_software_engineering": "Senior software engineering: review requirements, correctness, edge cases, failure modes, maintainability and verification strategy.",
}
DOMAIN_ROLES = {
    "numerical": ["numerical_methods", "algorithms"],
    "statistics": ["statistics", "data_integrity"],
    "defensive_parser": ["security", "api_protocol_engineering"],
    "queue_idempotency": ["distributed_systems_reliability", "data_integrity"],
    "ml_evaluation": ["ml_data_science", "statistics"],
    "concurrency": ["performance_concurrency", "distributed_systems_reliability"],
    "ledger_state_invariant": ["algorithms", "data_integrity"],
    "protocol_client": ["api_protocol_engineering", "distributed_systems_reliability"],
}
STAGES = ("REVIEW_1", "REVIEW_2", "CHALLENGE", "DECISION", "BUILD", "REPAIR")
REVIEW_INSTRUCTION = "You are a competent senior software-engineering reviewer. Independently examine requirements, correctness, edge cases, failure modes, maintainability where relevant, and verification strategy. Use only the supplied public evidence. Return actionable guidance."
LIMITS = {"qualification": 30, "calibration": 216, "main": 768}
QUALIFICATION_DOMAINS = {
    "qualification_double": "numerical",
    "qualification_even": "ledger_state_invariant",
    "qualification_length": "statistics",
    "qualification_reverse": "protocol_client",
    "qualification_uppercase": "defensive_parser",
}


def output_schema(stage: str) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError("UNKNOWN_STAGE")
    field = "code" if stage in {"BUILD", "REPAIR"} else "text"
    return {
        "type": "object",
        "properties": {field: {"type": "string", "minLength": 1}},
        "required": [field],
        "additionalProperties": False,
    }


def parse(stage: str, text: str) -> dict[str, str]:
    import json

    if stage not in STAGES:
        raise ValueError("UNKNOWN_STAGE")
    value = json.loads(text)
    field = "code" if stage in {"BUILD", "REPAIR"} else "text"
    if (
        type(value) is not dict
        or set(value) != {field}
        or type(value[field]) is not str
        or not value[field].strip()
    ):
        raise ValueError("SCHEMA_ERROR")
    return {field: value[field]}


def schedule(tasks: list[str], repetitions: int = 8, seed: int = 2026091601) -> dict[str, Any]:
    if len(tasks) != len(set(tasks)) or not tasks or repetitions < 1:
        raise ValueError("INVALID_SCHEDULE_FRAME")
    rng = random.Random(seed)
    blocks = [(t, r) for t in sorted(tasks) for r in range(repetitions)]
    rng.shuffle(blocks)
    rows = []
    for task, rep in blocks:
        arms = ["B", "C"]
        rng.shuffle(arms)
        for position, arm in enumerate(arms):
            rows.append(
                {
                    "task_id": task,
                    "block": rep,
                    "condition": arm,
                    "position": position,
                    "run_id": f"{EXPERIMENT}--{task}--r{rep:02}--{arm}",
                }
            )
    value = {"experiment_id": EXPERIMENT, "seed": seed, "rows": rows}
    return {**value, "sha256": sha(encoded(value))}


def select_tasks(
    catalog: list[dict[str, Any]], records: list[dict[str, Any]], *, allow_mock: bool = False
) -> list[str]:
    if not 8 <= len(catalog) <= 12 or len({t["task_id"] for t in catalog}) != len(catalog):
        raise ValueError("INVALID_CANDIDATE_CATALOG")
    if set(t["family"] for t in catalog) != set(DOMAIN_ROLES):
        raise ValueError("EIGHT_DOMAINS_REQUIRED")
    kinds = {r.get("kind") for r in records}
    if kinds != {"LIVE"} and not (allow_mock is True and kinds == {"MOCK"}):
        raise ValueError("MOCK_OR_UNKNOWN_CALIBRATION_EVIDENCE")
    if any(
        r.get("experiment_id") != EXPERIMENT or r.get("phase") != "calibration" for r in records
    ):
        raise ValueError("FOREIGN_CALIBRATION")
    if any(r["condition"] != "B" for r in records):
        raise ValueError("CALIBRATION_B_ONLY")
    if len({r["run_id"] for r in records}) != len(records):
        raise ValueError("DUPLICATE_OBSERVATION")
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in records:
        groups[row["task_id"]].append(row)
    if set(groups) != {t["task_id"] for t in catalog}:
        raise ValueError("INCOMPLETE_CANDIDATE_SCREEN")
    eligible: dict[str, list[tuple[float, str]]] = defaultdict(list)
    for task in catalog:
        rows = groups[task["task_id"]]
        if len(rows) != 3:
            raise ValueError("EXACTLY_THREE_CALIBRATION_ATTEMPTS")
        values = [r["score"] for r in rows]
        if any(
            type(v) not in (int, float) or not math.isfinite(v) or not 0 <= v <= 1 for v in values
        ):
            raise ValueError("CALIBRATION_EVALUATOR_UNRESOLVED")
        mean = sum(values) / 3
        if 0.25 <= mean <= 0.75:
            eligible[task["family"]].append((abs(mean - 0.5), task["task_id"]))
    if set(eligible) != set(DOMAIN_ROLES):
        raise ValueError("CALIBRATION_INSUFFICIENT")
    return [min(eligible[domain])[1] for domain in sorted(DOMAIN_ROLES)]


def stop_reason(rows: list[dict[str, Any]]) -> str | None:
    # Caller supplies rows in frozen attempt order, never completion-race order.
    if (
        len(rows) >= 2
        and rows[-1]["failure"] in {"STARTUP", "CONFIGURATION"}
        and rows[-1]["failure"] == rows[-2]["failure"]
        and rows[-1].get("failure_detail") == rows[-2].get("failure_detail")
    ):
        return "TWO_IDENTICAL_STARTUP_FAILURES"
    infra = {"STARTUP", "CONFIGURATION", "PROVIDER_ERROR", "TRANSPORT_TIMEOUT"}
    if len(rows) >= 20 and sum(r["failure"] in infra for r in rows) / len(rows) > 0.05:
        return "INFRASTRUCTURE_FAILURE_RATE"
    return None


STAGE_INSTRUCTIONS = {
    "REVIEW_1": REVIEW_INSTRUCTION,
    "REVIEW_2": REVIEW_INSTRUCTION,
    "CHALLENGE": "Identify disagreements, unsupported assumptions, missed edge cases and likely failure modes.",
    "DECISION": "Produce one frozen implementable decision. Resolve the evidence into one plan.",
    "BUILD": "Implement the frozen decision in solution.py. Execute the plan; do not reopen governance.",
    "REPAIR": "Repair once using only the supplied public failure information and frozen decision.",
}
