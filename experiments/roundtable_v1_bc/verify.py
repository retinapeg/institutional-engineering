"""Reproduce the offline checkpoint and retain fresh, non-overwriting receipts."""

from __future__ import annotations

import argparse
import os
import platform
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

from .harness.design import DOMAIN_ROLES, ROLE_BANK, ROOT, STAGE_INSTRUCTIONS, STAGES, output_schema
from .harness.grading import integrity_audit
from .harness.process_boundary import negative_access_check
from .harness.records import encoded, publish, read, sha
from .taskpack import catalog, fixtures, public_snapshot

REPO = ROOT.parents[1]


def run(output: Path) -> dict[str, Any]:
    output = output.resolve()
    if output.exists():
        raise FileExistsError("Use a new output directory; preserve earlier checks")
    output.mkdir(parents=True)
    source_paths = [
        ROOT / "harness",
        ROOT / "analysis",
        ROOT / "tests",
        ROOT / "taskpack.py",
        ROOT / "test_taskpack.py",
        ROOT / "verify.py",
    ]
    paths = [str(p.relative_to(REPO)) for p in source_paths]
    commands = {
        "unit_integration": [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "experiments/roundtable_v1_bc",
            "-t",
            ".",
            "-v",
        ],
        "historical_regression_mocks": [
            sys.executable,
            "-m",
            "unittest",
            "discover",
            "-s",
            "tests",
            "-q",
        ],
        "lint": ["uvx", "--from", "ruff==0.16.7", "ruff", "check", *paths],
        "format": ["uvx", "--from", "ruff==0.16.7", "ruff", "format", "--check", *paths],
        "strict_types": ["uvx", "--from", "mypy==2.3.1", "mypy", "--strict", *paths],
        "build": ["uv", "build", "--out-dir", str(ROOT / ".build" / output.name)],
        "mock_pipeline": [
            sys.executable,
            "-m",
            "experiments.roundtable_v1_bc.harness",
            "mock-qualification",
            "--output",
            str(output / "mock-pipeline"),
        ],
    }
    checks = {}
    env = {**os.environ, "PYTHONPATH": str(REPO / "src") + os.pathsep + str(REPO)}
    for name, argv in commands.items():
        print("CHECK", name, flush=True)
        process = subprocess.run(
            argv, cwd=REPO, env=env, capture_output=True, timeout=240, check=False
        )
        receipt = {
            "argv": argv,
            "exit": process.returncode,
            "stdout": process.stdout.decode(errors="replace"),
            "stderr": process.stderr.decode(errors="replace"),
        }
        publish(output / (name + ".json"), receipt)
        checks[name] = {"passed": process.returncode == 0, "receipt_sha256": sha(encoded(receipt))}
    wheels = sorted((ROOT / ".build" / output.name).glob("*.whl"))
    packaged = False
    if len(wheels) == 1:
        with zipfile.ZipFile(wheels[0]) as wheel:
            names = set(wheel.namelist())
            expected = [
                p
                for p in ROOT.rglob("*")
                if p.is_file()
                and (
                    "tasks" in p.relative_to(ROOT).parts or "evaluator" in p.relative_to(ROOT).parts
                )
                and "__pycache__" not in p.parts
            ]
            packaged = all(
                str(p.relative_to(REPO)) in names
                and wheel.read(str(p.relative_to(REPO))) == p.read_bytes()
                for p in expected
            )
            packaged = packaged and "experiments/roundtable_v1_bc/harness/core.py" in names
            packaged = packaged and not any(
                ".scratch-cli/" in n or "domain_jurisdiction_v2/" in n for n in names
            )
    checks["packaged_fixture_bytes"] = {"passed": packaged}
    role_manifest = read(ROOT / "ROLE_MANIFEST.json")
    consistency = (
        read(ROOT / "roles.json") == ROLE_BANK and role_manifest["domain_roles"] == DOMAIN_ROLES
    )
    consistency = (
        consistency
        and role_manifest["definitions_sha256"] == sha(encoded(ROLE_BANK))
        and role_manifest["domain_roles_sha256"] == sha(encoded(DOMAIN_ROLES))
    )
    for stage in STAGES:
        consistency = consistency and read(ROOT / "prompts" / f"{stage.lower()}.json") == {
            "stage": stage,
            "instruction": STAGE_INSTRUCTIONS[stage],
            "schema": output_schema(stage),
        }
    checks["manifest_consistency"] = {"passed": consistency}
    manifest = read(ROOT / "TASK_MANIFEST.json")
    listed = manifest["candidates"]
    task_ok = {row["task_id"] for row in listed} == {row["task_id"] for row in catalog()}
    task_ok = task_ok and len(listed) == len(catalog())
    for row in listed:
        fixture = fixtures(row["task_id"])
        task_ok = task_ok and row["public_sha256"] == sha(encoded(public_snapshot(row["task_id"])))
        task_ok = task_ok and row["fixture_sha256"] == sha(encoded(fixture))
        task_ok = (
            task_ok
            and row["requirements"] == fixture["requirement_weights"]
            and row["domain"] == fixture["family"]
        )
    checks["task_manifest_hashes"] = {"passed": task_ok}
    integrity = integrity_audit()
    publish(output / "grader-integrity.json", integrity)
    containment = negative_access_check()
    publish(output / "candidate-containment.json", containment)
    deterministic = all(check["passed"] for check in checks.values())
    # Metadata-only controls are reproduced separately by the retained CLI script.
    doctor = read(ROOT / "manifests/cli/doctor-valid.json")
    invalid = read(ROOT / "manifests/cli/doctor-invalid-type.json")
    loader = (
        doctor["configuration_load"]["status"] == "ok"
        and invalid["configuration_load"]["status"] == "fail"
    )
    gates = {
        "typed_config_loader": loader,
        "single_request_bound": False,
        "zero_retries": False,
        "generation_ceiling": False,
        "worker_isolation": False,
        "grader_integrity": integrity["qualified"],
        "deterministic_checks": deterministic,
    }
    result = {
        "study_complete": False,
        "gate1_passed": all(gates.values()),
        "status": "BLOCKED",
        "gates": gates,
        "checks": checks,
        "model_calls": 0,
        "scientific_attempts": 0,
        "environment": {"python": sys.version, "platform": platform.platform()},
        "protocol_sha256": sha((ROOT / "protocol.json").read_bytes()),
        "scope": "Offline and mock checks only; reproduced grader counterexamples keep Gate1 failed.",
    }
    publish(output / "summary.json", result)
    print("GATE1", result["gate1_passed"], "MODEL_CALLS", 0, flush=True)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.output)
    raise SystemExit(0 if result["gate1_passed"] else 2)


if __name__ == "__main__":
    main()
