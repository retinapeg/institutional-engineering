"""Wilson proportions and block-resampled risk differences; no p-value claims."""

import csv
import json
import math
import random
from pathlib import Path
from statistics import mean
from typing import Any

from benchmarks.analysis import atomic_json

from .design import CONDITIONS


def wilson(successes: int, n: int) -> list[float] | None:
    if n == 0:
        return None
    z = 1.959963984540054
    p = successes / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [max(0.0, centre - half), min(1.0, centre + half)]


def proportion(rows: list[dict[str, Any]], conditional: bool = False) -> dict[str, Any]:
    group = (
        [r for r in rows if r["protocol_valid"] and not r["error_type_if_any"]]
        if conditional
        else rows
    )
    successes = sum(bool(r["substantive_correct"]) and not r["error_type_if_any"] for r in group)
    return dict(
        n=len(group),
        successes=successes,
        p_hat=successes / len(group) if group else None,
        wilson_95=wilson(successes, len(group)),
    )


def comparisons(rows: list[dict[str, Any]], draws: int = 10000) -> dict[str, Any]:
    # Resample whole blocks, preserving the four-condition pairing. Interrupted partial
    # blocks are included in marginal proportions but excluded from paired comparisons.
    blocks: dict[int, dict[str, dict[str, Any]]] = {}
    for row in rows:
        blocks.setdefault(row["block_index"], {})[row["condition"]] = row
    complete = [b for b in blocks.values() if set(b) == set(CONDITIONS)]
    output: dict[str, Any] = {
        "complete_blocks": len(complete),
        "bootstrap_draws": draws,
        "ci_method": "paired whole-block percentile bootstrap; seed 872341; descriptive, unadjusted",
    }
    rng = random.Random(872341)
    pairs = [
        ("matched", "baseline"),
        ("generic", "baseline"),
        ("mismatched", "baseline"),
        ("matched", "generic"),
        ("matched", "mismatched"),
    ]
    samples: dict[str, list[float]] = {}
    estimates: dict[str, float | None] = {}

    def rates(group: list[dict[str, dict[str, Any]]], conditional: bool) -> dict[str, Any]:
        return {c: proportion([b[c] for b in group], conditional)["p_hat"] for c in CONDITIONS}

    for conditional in (False, True):
        label = "parsed" if conditional else "end_to_end"
        actual = rates(complete, conditional)
        for a, b in pairs:
            key = f"{label}:{a}-{b}"
            samples[key] = []
            estimates[key] = (
                actual[a] - actual[b] if actual[a] is not None and actual[b] is not None else None
            )
    if len(complete) >= 2:
        for _ in range(draws):
            sample = rng.choices(complete, k=len(complete))
            for conditional in (False, True):
                label = "parsed" if conditional else "end_to_end"
                ps = rates(sample, conditional)
                for a, b in pairs:
                    if ps[a] is not None and ps[b] is not None:
                        samples[f"{label}:{a}-{b}"].append(ps[a] - ps[b])
    for key, values in samples.items():
        values.sort()
        output[key] = dict(
            risk_difference=estimates[key],
            ci_95=[values[int(0.025 * (len(values) - 1))], values[int(0.975 * (len(values) - 1))]]
            if values
            else None,
            valid_bootstrap_draws=len(values),
        )
    return output


def export(root: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {
        "planned_calls": 1000,
        "completed_calls": len(rows),
        "remaining_calls": 1000 - len(rows),
        "status": "COMPLETE" if len(rows) == 1000 else "PENDING_OR_PARTIAL",
        "runtime_failures": sum(bool(r["error_type_if_any"]) for r in rows),
        "protocol_failures": sum(not r["protocol_valid"] for r in rows),
        "conditions": {
            c: {
                "end_to_end": proportion([r for r in rows if r["condition"] == c]),
                "parsed": proportion([r for r in rows if r["condition"] == c], True),
            }
            for c in CONDITIONS
        },
        "comparisons": comparisons(rows),
        "mean_latency_seconds": mean(
            r["latency_seconds"] for r in rows if r["latency_seconds"] is not None
        )
        if any(r["latency_seconds"] is not None for r in rows)
        else None,
        "actual_marginal_cost": "UNKNOWN",
        "limitations": [
            "Exploratory single-task study; no across-task generalisation.",
            "Wilson intervals assume independent repetitions; temporal dependence can understate uncertainty.",
            "Bootstrap preserves within-block pairing but treats different blocks as independent.",
            "Conditional estimates can be selected by protocol success; report end-to-end too.",
            "Unadjusted descriptive intervals, no p-value-based significance claims.",
            "Calibration-selected rate is noisy; full-study baseline is a fresh estimate.",
            "Wrappers differ in length/content; generic control does not isolate every prompt feature.",
            "CLI/server sampling, internal retries and server model revisions may be opaque.",
        ],
    }
    atomic_json(root / "summary.json", report)
    fields = (
        list(rows[0])
        if rows
        else [
            "experiment_id",
            "call_index",
            "condition",
            "response_text",
            "protocol_valid",
            "substantive_correct",
        ]
    )
    with (root / "results.csv.tmp").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    (root / "results.csv.tmp").replace(root / "results.csv")
    lines = [
        "# Single-task role intervention study",
        "",
        f"Status: {report['status']}. {len(rows)}/1000 terminal observations.",
        "",
        "No role-specific conclusion is asserted from pending or preliminary data.",
        "",
        "| Condition | End-to-end successes/n | Estimate | Parsed successes/n | Estimate |",
        "|---|---:|---:|---:|---:|",
    ]
    for c, values in report["conditions"].items():
        a, b = values["end_to_end"], values["parsed"]
        lines.append(
            f"| {c} | {a['successes']}/{a['n']} | {a['p_hat']} | {b['successes']}/{b['n']} | {b['p_hat']} |"
        )
    lines += [
        "",
        "Wilson 95% intervals and paired block-bootstrap risk differences are in summary.json.",
        "Central contrasts: matched − generic and matched − mismatched, not matched − baseline alone.",
        "",
        *["- " + item for item in report["limitations"]],
    ]
    (root / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    return report


if __name__ == "__main__":
    root = Path(__file__).parent
    rows = (
        [json.loads(line) for line in (root / "results.jsonl").read_text().splitlines()]
        if (root / "results.jsonl").exists()
        else []
    )
    export(root, rows)
