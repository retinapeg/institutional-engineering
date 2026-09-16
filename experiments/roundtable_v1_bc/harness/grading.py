"""Offline scoring diagnostics; candidate-reported mutation is not a trusted oracle.

Expected answers remain in the parent, but unrestricted Python can forge the child
observer's report. Live qualification must fail while integrity_audit is unqualified.
"""

from __future__ import annotations

import json
import math
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from .process_boundary import run_python
from .records import sha


class GraderIntegrityError(RuntimeError):
    """A deterministic observation-integrity defect prevents live grading."""


# Candidate controls all its process output. This wrapper observes behavior but
# does not make introspection/nonmutation reporting tamper-proof; preflight tests
# this limitation explicitly and must refuse live use if the probe succeeds.
OBSERVE = """import json,sys
sys.path.insert(0,'.')
from solution import solve
x=json.loads(input())
try: result={'value':solve(x)}
except Exception as e: result={'error':type(e).__name__}
result['input_after']=x
print(json.dumps(result,allow_nan=False))
"""


def matches(actual: Any, expected: Any, relative: float, absolute: float) -> bool:
    if type(expected) is float:
        return (
            type(actual) in (int, float)
            and math.isfinite(actual)
            and math.isclose(actual, expected, rel_tol=relative, abs_tol=absolute)
        )
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            matches(actual[k], v, relative, absolute) for k, v in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            matches(a, b, relative, absolute) for a, b in zip(actual, expected, strict=True)
        )
    return bool(actual == expected)


def grade(
    artifact: bytes, cases: list[dict[str, Any]], weights: dict[str, float]
) -> dict[str, Any]:
    if (
        not cases
        or not weights
        or any(not math.isfinite(v) or v <= 0 for v in weights.values())
        or not math.isclose(sum(weights.values()), 1)
    ):
        raise ValueError("INVALID_REQUIREMENT_WEIGHTS")
    if len({c["id"] for c in cases}) != len(cases) or {c["requirement_id"] for c in cases} != set(
        weights
    ):
        raise ValueError("RUBRIC_CASE_MISMATCH")
    rows = []
    by_requirement: dict[str, list[bool]] = defaultdict(list)
    for case in cases:
        with tempfile.TemporaryDirectory(prefix="roundtable-evaluate-") as tmp:
            work = Path(tmp).resolve()
            (work / "solution.py").write_bytes(artifact)
            result = run_python(work, OBSERVE, json.dumps(case["input"]), seconds=5, writable=False)
        executed = result["exit"] == 0 and result["failure"] is None
        observed: Any = None
        if executed:
            try:
                observed = json.loads(result["stdout"])
            except ValueError:
                executed = False
        expected = {"error": case["error"]} if "error" in case else {"value": case["expected"]}
        passed = False
        if (
            executed
            and isinstance(observed, dict)
            and set(observed) == set(expected) | {"input_after"}
        ):
            value = {k: v for k, v in observed.items() if k != "input_after"}
            passed = matches(value, expected, case.get("rel_tol", 1e-12), case.get("abs_tol", 0.0))
            if case.get("nonmutation"):
                passed = passed and matches(observed["input_after"], case["input"], 0, 0)
        by_requirement[case["requirement_id"]].append(passed)
        rows.append(
            {
                "id": case["id"],
                "requirement_id": case["requirement_id"],
                "passed": passed,
                "executed": executed,
                "process": result,
            }
        )
    # Requirement succeeds only when all of its specified behavior checks succeed.
    scores = {key: float(all(values)) for key, values in by_requirement.items()}
    return {
        "grader_success": True,
        "integrity_qualified": False,
        "artifact_sha256": sha(artifact),
        "score": sum(weights[k] * v for k, v in scores.items()),
        "full_pass": all(c["passed"] for c in rows),
        "requirements": scores,
        "requirement_weights": weights,
        "checks": rows,
    }


def integrity_audit() -> dict[str, Any]:
    """Reproduce three false passes without exposing any oracle to a candidate.

    This is a regression *of the blocker*, not a test declaring the grader safe.
    The synthetic contract returns the first list item without changing the list.
    All attack programs append to their actual argument. Their claimed observation
    conceals that mutation; the stdout attack does not even return from solve.
    """
    cases: list[dict[str, Any]] = [
        {
            "id": "nonmutation_canary",
            "requirement_id": "input_preservation",
            "input": [2],
            "expected": 2,
            "nonmutation": True,
            "rel_tol": 0.0,
            "abs_tol": 0.0,
        }
    ]
    programs = {
        "honest_reference": "def solve(x):\n    return x[0]\n",
        "ordinary_mutation": "def solve(x):\n    x.append(99)\n    return x[0]\n",
        "counterfeit_score_only": (
            "import os\ndef solve(x):\n    print('{\"score\":1}',flush=True)\n    os._exit(0)\n"
        ),
        "json_monkeypatch": (
            "import json\n"
            "encode=json.dumps\n"
            "before=None\n"
            "def forged(value,*args,**kwargs):\n"
            "    if isinstance(value,dict) and 'input_after' in value:\n"
            "        value={**value,'input_after':before}\n"
            "    return encode(value,*args,**kwargs)\n"
            "json.dumps=forged\n"
            "def solve(x):\n"
            "    global before\n"
            "    before=list(x)\n"
            "    x.append(99)\n"
            "    return x[0]\n"
        ),
        "caller_globals": (
            "import inspect\n"
            "def solve(x):\n"
            "    before=list(x)\n"
            "    x.append(99)\n"
            "    inspect.currentframe().f_back.f_globals['x']=before\n"
            "    return x[0]\n"
        ),
        "stdout_then_exit": (
            "import json,os\n"
            "def solve(x):\n"
            "    before=list(x)\n"
            "    x.append(99)\n"
            "    print(json.dumps({'value':x[0],'input_after':before}),flush=True)\n"
            "    os._exit(0)\n"
        ),
    }
    results: dict[str, dict[str, Any]] = {
        name: {"source": code, "result": grade(code.encode(), cases, {"input_preservation": 1.0})}
        for name, code in programs.items()
    }
    attacks = ("json_monkeypatch", "caller_globals", "stdout_then_exit")
    false_passes = [name for name in attacks if results[name]["result"]["score"] == 1.0]
    return {
        "qualified": False,
        "blocker": "CANDIDATE_CAN_FORGE_INPUT_AFTER",
        "false_passes": false_passes,
        "case": cases[0],
        "checks": results,
        "oracle_scope": "Expected value and pass/fail decision remain in the parent process.",
        "observation_scope": "Candidate owns its interpreter, stdout and reported input_after.",
        "required_remedy": (
            "Independently trusted mutation observation or an explicitly qualified execution "
            "contract. Python serializer prebinding, import blacklists and an additional pipe "
            "do not create a security boundary against unrestricted candidate Python."
        ),
    }


def require_qualified() -> None:
    """Fail closed before inference; the current architecture remains unqualified."""
    raise GraderIntegrityError("CANDIDATE_CAN_FORGE_INPUT_AFTER: live grading is not qualified")
