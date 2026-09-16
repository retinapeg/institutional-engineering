"""Executable deterministic institution. Live dispatch stays behind separate qualification."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..taskpack import fixtures, public_snapshot
from .budget import reserve_stage
from .design import (
    DOMAIN_ROLES,
    EXPERIMENT,
    LIMITS,
    QUALIFICATION_DOMAINS,
    ROLE_BANK,
    ROOT,
    STAGE_INSTRUCTIONS,
    parse,
)
from .grading import grade
from .records import encoded, identifier, publish, read, sha

Json = dict[str, Any]
Grader = Callable[[bytes, list[Json], dict[str, float]], Json]


class StageFailure(RuntimeError):
    pass


class FakeProvider:
    """Registered local fixture responses. This class performs no model inference."""

    def __init__(self, code: str, repair_code: str | None = None, fail_at: int = 0) -> None:
        self.code = code
        self.repair_code = repair_code or code
        self.fail_at = fail_at
        self.prompts: list[Json] = []

    def __call__(self, prompt: Json) -> Json:
        self.prompts.append(prompt)
        if len(self.prompts) == self.fail_at:
            raise StageFailure("PROVIDER_ERROR")
        stage = prompt["stage"]
        body = (
            {"code": self.repair_code if stage == "REPAIR" else self.code}
            if stage in {"BUILD", "REPAIR"}
            else {"text": "MOCK " + stage}
        )
        return {
            "text": json.dumps(body),
            "resolved_model": None,
            "tokens": None,
            "process_exit": 0,
            "kind": "MOCK",
        }


def validate_roles(family: str, condition: str) -> list[str]:
    if condition not in {"B", "C"}:
        raise ValueError("BC_ONLY")
    return DOMAIN_ROLES[family] if condition == "C" else ["general_software_engineering"] * 2


def evaluator_fingerprint() -> str:
    files = ("grading.py", "process_boundary.py", "records.py")
    return sha(encoded({name: sha((ROOT / "harness" / name).read_bytes()) for name in files}))


def execute_mock(
    data: Path,
    run_id: str,
    task_id: str,
    condition: str,
    provider: FakeProvider,
    phase: str = "qualification",
    force_repair: bool = False,
    grader: Grader = grade,
) -> Json:
    if type(provider) is not FakeProvider:
        raise ValueError("LIVE_PROVIDER_NOT_QUALIFIED")
    if phase not in LIMITS:
        raise ValueError("UNKNOWN_PHASE")
    target = data / "mock" / phase / identifier(run_id)
    if target.exists():
        raise FileExistsError("ATTEMPT_ID_ALREADY_USED")
    fixture = fixtures(task_id)
    snapshot = public_snapshot(task_id)
    if phase == "qualification" and fixture["purpose"] != "qualification_only":
        raise ValueError("QUALIFICATION_TASK_REQUIRED")
    if phase != "qualification" and fixture["purpose"] != "benchmark_candidate":
        raise ValueError("BENCHMARK_TASK_REQUIRED")
    if phase == "calibration" and condition != "B":
        raise ValueError("CALIBRATION_B_ONLY")
    if force_repair and phase != "qualification":
        raise ValueError("FORCED_REPAIR_NONQUALIFICATION")
    family = QUALIFICATION_DOMAINS[task_id] if phase == "qualification" else fixture["family"]
    roles = validate_roles(family, condition)
    start = time.monotonic()
    row: Json = {
        "kind": "MOCK",
        "experiment_id": EXPERIMENT,
        "run_id": run_id,
        "task_id": task_id,
        "condition": condition,
        "phase": phase,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "snapshot_sha256": sha(encoded(snapshot)),
        "fixture_sha256": sha(encoded(fixture)),
        "evaluator_sha256": evaluator_fingerprint(),
        "roles": roles,
        "stages": [],
        "repair_count": 0,
        "model_calls": 0,
        "stage_invocations": 0,
        "institution_completed": False,
        "evaluable": False,
        "score": 0.0,
        "failure": None,
        "artifact_sha256": None,
        "state": "STARTED",
        "resolved_model": None,
        "tokens": None,
    }
    publish(target / "start.json", row)
    code: bytes | None = None
    decision: Json | None = None

    def ask(prompt: Json) -> dict[str, str]:
        if row["stage_invocations"] >= 6:
            raise StageFailure("CALL_BUDGET")
        if time.monotonic() - start >= 600:
            raise StageFailure("RUN_TIMEOUT")
        if len(encoded(prompt)) > 131072:
            raise StageFailure("PROMPT_LIMIT")
        index = row["stage_invocations"]
        try:
            reserve_stage(data, phase, run_id, prompt["stage"])
        except ValueError as exc:
            raise StageFailure(str(exc)) from exc
        row["stage_invocations"] += 1
        entry: Json = {
            "index": index,
            "stage": prompt["stage"],
            "request": prompt,
            "request_sha256": sha(encoded(prompt)),
            "schema_success": False,
            "failure": None,
        }
        publish(target / f"stage-{index}-start.json", entry)
        began = time.monotonic()
        try:
            response = provider(prompt)
            entry["response"] = response
            if time.monotonic() - began > 90:
                raise StageFailure("STAGE_TIMEOUT")
            if len(response["text"].encode()) > 1048576:
                raise StageFailure("RESPONSE_LIMIT")
            parsed = parse(prompt["stage"], response["text"])
            entry["schema_success"] = True
            return parsed
        except (StageFailure, ValueError) as exc:
            entry["failure"] = str(exc) or "SCHEMA_ERROR"
            raise StageFailure(entry["failure"]) from exc
        finally:
            entry["seconds"] = time.monotonic() - began
            row["stages"].append(entry)
            publish(target / f"stage-{index}-terminal.json", entry)

    def visible(artifact: bytes) -> Json:
        cases = [
            {**case, "requirement_id": "visible"} for case in json.loads(snapshot["visible.json"])
        ]
        # Public tests may cover only a subset; this is separate from hidden weights.
        keys = {c["requirement_id"] for c in cases}
        weights = {key: 1 / len(keys) for key in keys}
        return grader(artifact, cases, weights)

    try:
        reports = []
        for i, role in enumerate(roles, 1):
            reports.append(
                ask(
                    {
                        "stage": f"REVIEW_{i}",
                        "instruction": STAGE_INSTRUCTIONS[f"REVIEW_{i}"],
                        "jurisdiction": ROLE_BANK[role],
                        "snapshot": snapshot,
                    }
                )
            )
        challenge = ask(
            {
                "stage": "CHALLENGE",
                "instruction": STAGE_INSTRUCTIONS["CHALLENGE"],
                "snapshot": snapshot,
                "reports": reports,
            }
        )
        decision = ask(
            {
                "stage": "DECISION",
                "instruction": STAGE_INSTRUCTIONS["DECISION"],
                "snapshot": snapshot,
                "reports": reports,
                "challenge": challenge,
            }
        )
        publish(target / "frozen-decision.json", decision)
        code = ask(
            {
                "stage": "BUILD",
                "instruction": STAGE_INSTRUCTIONS["BUILD"],
                "snapshot": snapshot,
                "decision": decision,
            }
        )["code"].encode()
        publish(target / "builder-artifact.json", {"code": code.decode(), "sha256": sha(code)})
        checked = visible(code)
        row["visible_initial"] = checked
        if force_repair or not checked["full_pass"]:
            row["repair_count"] = 1
            feedback = {"mechanical_qualification_trigger": True} if force_repair else checked
            repaired = ask(
                {
                    "stage": "REPAIR",
                    "instruction": STAGE_INSTRUCTIONS["REPAIR"],
                    "snapshot": snapshot,
                    "decision": decision,
                    "code": code.decode(),
                    "visible_feedback": feedback,
                }
            )["code"].encode()
            code = repaired
            publish(target / "repair-artifact.json", {"code": code.decode(), "sha256": sha(code)})
            row["visible_repair"] = visible(code)
        row["institution_completed"] = True
    except StageFailure as exc:
        row["failure"] = str(exc)
    except Exception as exc:
        row["failure"] = "EVALUATOR_ERROR"
        row["evaluator_exception"] = type(exc).__name__ + ": " + str(exc)
    finally:
        # A failed repair does not erase an already produced builder artifact.
        if code is not None:
            frozen = {"code": code.decode(), "sha256": sha(code)}
            publish(target / "frozen-artifact.json", frozen)
            row["artifact_sha256"] = frozen["sha256"]
            try:
                result = grader(code, fixture["hidden"], fixture["requirement_weights"])
                publish(target / "evaluation-000.json", result)
                row.update(evaluable=True, score=result["score"], full_pass=result["full_pass"])
            except Exception as exc:
                row["score"] = None
                row["failure"] = "EVALUATOR_ERROR"
                publish(
                    target / "evaluation-000.json",
                    {
                        "artifact_sha256": frozen["sha256"],
                        "grader_success": False,
                        "error": type(exc).__name__ + ": " + str(exc),
                    },
                )
        row["state"] = (
            "COMPLETED" if row["institution_completed"] and row["failure"] is None else "FAILED"
        )
        row["schema_success"] = row["institution_completed"] and all(
            e["schema_success"] for e in row["stages"]
        )
        row["seconds"] = time.monotonic() - start
        publish(target / "terminal.json", row)
    return row


def replay_evaluator(run: Path) -> Json:
    record = read(run / "terminal.json")
    frozen = read(run / "frozen-artifact.json")
    code = frozen["code"].encode()
    if sha(code) != frozen["sha256"] or frozen["sha256"] != record["artifact_sha256"]:
        raise ValueError("ARTIFACT_CHANGED")
    fixture = fixtures(record["task_id"])
    if (
        sha(encoded(fixture)) != record["fixture_sha256"]
        or evaluator_fingerprint() != record["evaluator_sha256"]
    ):
        raise ValueError("SCORING_CHANGED_REPLAY_REFUSED")
    result = grade(code, fixture["hidden"], fixture["requirement_weights"])
    index = 1
    while (run / f"evaluation-{index:03}.json").exists():
        index += 1
    publish(run / f"evaluation-{index:03}.json", result)
    return result


def require_live_gate(preflight: Json) -> None:
    required = {
        "typed_config_loader",
        "single_request_bound",
        "zero_retries",
        "generation_ceiling",
        "worker_isolation",
        "grader_integrity",
        "deterministic_checks",
    }
    if set(preflight.get("gates", {})) != required or any(
        preflight["gates"][key] is not True for key in required
    ):
        raise RuntimeError("GATE1_PREFLIGHT_FAILED; NO LIVE MODEL CALL DISPATCHED")
    raise RuntimeError("LIVE_ADAPTER_NOT_IMPLEMENTED; NO LIVE MODEL CALL DISPATCHED")
