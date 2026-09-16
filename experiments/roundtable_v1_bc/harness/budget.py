"""Durable mock-stage reservations; these are not provider request accounting."""

from __future__ import annotations

import fcntl
from pathlib import Path

from .design import EXPERIMENT, LIMITS, STAGES
from .records import identifier, publish, read


def reserve_stage(data: Path, phase: str, run_id: str, stage: str) -> int:
    if phase not in LIMITS or stage not in STAGES:
        raise ValueError("UNKNOWN_BUDGET")
    identifier(run_id)
    root = data / "mock" / phase / "reservations"
    root.mkdir(parents=True, exist_ok=True)
    # Reservations never roll back after failure or interruption.
    with (root / ".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        entries = [read(p) for p in sorted(root.glob("*.json"))]
        if len(entries) >= LIMITS[phase]:
            raise ValueError("PHASE_CALL_BUDGET")
        own = [entry for entry in entries if entry["run_id"] == run_id]
        if len(own) >= 6:
            raise ValueError("RUN_CALL_BUDGET")
        if stage != STAGES[len(own)]:
            raise ValueError("DUPLICATE_OR_OUT_OF_ORDER_STAGE")
        index = len(entries)
        publish(
            root / f"{index:04}.json",
            {
                "kind": "MOCK",
                "experiment_id": EXPERIMENT,
                "phase": phase,
                "index": index,
                "run_id": run_id,
                "stage": stage,
                "model_calls": 0,
            },
        )
        return index
