"""Frozen public task copies and separately held behavioral requirement rubrics."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PUBLIC_FILES = ("task.txt", "solution.py", "visible.json", "visible_tests.py")


def _identifier(task_id: str) -> str:
    if not re.fullmatch(r"[a-z][a-z0-9_]*", task_id):
        raise ValueError("Invalid task ID")
    return task_id


def _catalog(name: str) -> list[dict[str, str]]:
    value: list[dict[str, str]] = json.loads((ROOT / "tasks" / name).read_bytes())
    return value


def catalog() -> list[dict[str, str]]:
    """The twelve benchmark candidates; never includes qualification scenarios."""
    return _catalog("catalog.json")


def qualification_catalog() -> list[dict[str, str]]:
    return _catalog("qualification_catalog.json")


def public_snapshot(task_id: str) -> dict[str, str]:
    directory = ROOT / "tasks" / _identifier(task_id)
    return {name: (directory / name).read_text() for name in PUBLIC_FILES}


def fixtures(task_id: str) -> dict[str, Any]:
    value: dict[str, Any] = json.loads(
        (ROOT / "evaluator" / f"{_identifier(task_id)}.json").read_bytes()
    )
    if value["task_id"] != task_id:
        raise ValueError("Fixture identity mismatch")
    return value
