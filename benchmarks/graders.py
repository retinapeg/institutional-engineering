import json
import math
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from .schemas import BenchmarkResponse, Grade, Task

# Inputs/expected results are frozen before inference, never model-authored.
CODE_CASES: dict[str, list[dict[str, Any]]] = {
    "software_escaped_fields": [
        {"name": "empty", "input": "", "expected": [""]},
        {"name": "single", "input": "abc", "expected": ["abc"]},
        {"name": "split", "input": "a,b,c", "expected": ["a", "b", "c"]},
        {"name": "empty_fields", "input": ",a,,", "expected": ["", "a", "", ""]},
        {"name": "escaped_comma", "input": r"a\,b,c", "expected": ["a,b", "c"]},
        {"name": "escaped_slash", "input": r"a\\,b", "expected": ["a\\", "b"]},
        {"name": "combined", "input": r"\,\\\,,", "expected": [",\\,", ""]},
        {"name": "invalid_escape", "input": r"a\qb", "error": "ValueError"},
        {"name": "dangling", "input": "a\\", "error": "ValueError"},
        {"name": "slash_only", "input": "\\", "error": "ValueError"},
        {"name": "spaces", "input": " a , b ", "expected": [" a ", " b "]},
        {"name": "unicode", "input": "α,β\\,γ", "expected": ["α", "β,γ"]},
    ],
    "software_merge_intervals": [
        {"name": "empty", "input": [], "expected": []},
        {"name": "single_fresh", "input": [[1, 3]], "expected": [[1, 3]]},
        {"name": "unsorted", "input": [[8, 9], [1, 3], [2, 6]], "expected": [[1, 6], [8, 9]]},
        {"name": "touching", "input": [[1, 2], [2, 3]], "expected": [[1, 3]]},
        {"name": "containment", "input": [[1, 10], [2, 3], [4, 6]], "expected": [[1, 10]]},
        {"name": "duplicate", "input": [[1, 3], [1, 3]], "expected": [[1, 3]]},
        {"name": "points", "input": [[2, 2], [1, 1]], "expected": [[1, 1], [2, 2]]},
        {"name": "negative", "input": [[-5, -2], [-3, 1]], "expected": [[-5, 1]]},
        {"name": "bridge", "input": [[1, 2], [4, 5], [2, 4]], "expected": [[1, 5]]},
        {"name": "reversed", "input": [[3, 1]], "error": "ValueError"},
        {"name": "reversed_later", "input": [[0, 10], [8, 3]], "error": "ValueError"},
    ],
}


def equal(actual: Any, expected: Any, *, tiny: bool = False) -> bool:
    if isinstance(expected, bool):
        return actual is expected
    if isinstance(expected, (int, float)):
        return (
            isinstance(actual, (int, float))
            and not isinstance(actual, bool)
            and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-24 if tiny else 1e-10)
        )
    return type(actual) is type(expected) and actual == expected


def grade(task: Task, response: BenchmarkResponse) -> Grade:
    if task.fixture:
        cases = CODE_CASES[task.task_id]
        if len(response.files) != 1:
            return Grade(
                score=0,
                tests_passed=0,
                tests_total=len(cases),
                details=[{"error": "Exactly one solution.py required"}],
            )
        payload = {
            "code": response.files[0].content,
            "function": task.ground_truth_or_acceptance["function"],
            "cases": cases,
        }
        try:
            with tempfile.TemporaryDirectory(prefix="inst-benchmark-grade-") as tmp:
                execution = subprocess.run(
                    [sys.executable, "-I", str(Path(__file__).with_name("code_worker.py"))],
                    input=json.dumps(payload),
                    text=True,
                    capture_output=True,
                    cwd=tmp,
                    timeout=8,
                )
            if execution.returncode:
                raise ValueError(f"Restricted worker exited {execution.returncode}")
            output = json.loads(execution.stdout)
            if "error" in output:
                raise ValueError(output["error"])
            details = output["details"]
            passed = sum(item["passed"] for item in details)
            return Grade(
                score=passed / len(cases),
                tests_passed=passed,
                tests_total=len(cases),
                details=details,
            )
        except (ValueError, subprocess.TimeoutExpired) as exc:
            return Grade(
                score=0, tests_passed=0, tests_total=len(cases), details=[{"error": str(exc)}]
            )
    details = []
    for key, expected in task.ground_truth_or_acceptance.items():
        actual: Any = response.answer.get(key)
        if isinstance(expected, dict):
            for field, value in expected.items():
                item = actual.get(field) if isinstance(actual, dict) else None
                details.append(
                    {
                        "check": f"{key}.{field}",
                        "passed": equal(item, value),
                        "actual": item,
                        "expected": value,
                    }
                )
        else:
            if key == "valid_pipeline_ids" and isinstance(actual, list):
                actual = (
                    sorted(cast(list[str], actual))
                    if all(isinstance(v, str) for v in actual)
                    else actual
                )
            details.append(
                {
                    "check": key,
                    "passed": equal(actual, expected, tiny=task.task_id == "math_cancellation"),
                    "actual": actual,
                    "expected": expected,
                }
            )
    passed = sum(bool(item["passed"]) for item in details)
    return Grade(
        score=passed / len(details), tests_passed=passed, tests_total=len(details), details=details
    )
