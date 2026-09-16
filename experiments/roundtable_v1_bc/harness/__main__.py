"""Offline validation commands; every live command refuses unqualified dispatch."""

from __future__ import annotations

import argparse
from pathlib import Path

from ..taskpack import fixtures, qualification_catalog
from .core import FakeProvider, execute_mock, require_live_gate
from .design import ROOT
from .grading import integrity_audit
from .records import publish, read


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=["mock-qualification", "integrity-audit", "qualification", "calibration", "main"],
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command in {"qualification", "calibration", "main"}:
        preflight = ROOT / "GATE1_PREFLIGHT.json"
        require_live_gate(read(preflight) if preflight.exists() else {})
    if args.output is None:
        parser.error("--output is required for offline receipts")
    output = args.output.resolve()
    if output.exists():
        parser.error("output must be a new path; raw receipts are never overwritten")
    if args.command == "integrity-audit":
        result = integrity_audit()
        publish(output, result)
        print("GRADER_INTEGRITY_QUALIFIED:", result["qualified"])
    if args.command == "mock-qualification":
        rows = []
        for i, task in enumerate(qualification_catalog()):
            fixture = fixtures(task["task_id"])
            rows.append(
                execute_mock(
                    output,
                    f"mock-operational-{i}",
                    task["task_id"],
                    ["B", "C", "B", "C", "C"][i],
                    FakeProvider(fixture["reference"]),
                    force_repair=True,
                )
            )
        result = {
            "kind": "MOCK",
            "not_live_qualification": True,
            "planned_institutions": 5,
            "attempted_institutions": len(rows),
            "completed_institutions": sum(row["institution_completed"] for row in rows),
            "stage_invocations": sum(row["stage_invocations"] for row in rows),
            "schema_completions": sum(
                stage["schema_success"] for row in rows for stage in row["stages"]
            ),
            "model_calls": 0,
            "repair_invocations": sum(row["repair_count"] for row in rows),
        }
        publish(output / "summary.json", result)
        print(result)


if __name__ == "__main__":
    main()
