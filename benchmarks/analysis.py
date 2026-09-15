"""Descriptive summaries only: no significance claims or production weight updates."""

import csv
import itertools
import json
import re
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from .schemas import Result


def atomic_json(path: Path, value: Any) -> None:
    import os

    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def aggregate(rows: list[Result]) -> dict[str, Any]:
    return {
        "n": len(rows),
        "mean_score": mean(r.objective_score for r in rows) if rows else None,
        "mean_score_schema_valid_only": mean(r.objective_score for r in rows if r.schema_success)
        if any(r.schema_success for r in rows)
        else None,
        "mean_latency_seconds": mean(r.latency_seconds for r in rows if r.model_call_attempted)
        if any(r.model_call_attempted for r in rows)
        else 0,
        "input_tokens_reported": sum(r.input_tokens or 0 for r in rows),
        "output_tokens_reported": sum(r.output_tokens or 0 for r in rows),
        "token_observations": sum(r.input_tokens is not None for r in rows),
        "protocol_failures": sum(not r.call_success for r in rows),
        "objective_passes": sum(r.success for r in rows),
    }


def grouped(rows: list[Result], field: str) -> dict[str, Any]:
    groups: dict[str, list[Result]] = defaultdict(list)
    for row in rows:
        groups[str(getattr(row, field))].append(row)
    return {key: aggregate(values) for key, values in sorted(groups.items())}


def summary(rows: list[Result]) -> dict[str, Any]:
    primary = [r for r in rows if r.sweep == "primary"]
    pairs = {(r.task_id, r.model, r.condition, r.repeat): r for r in primary}
    differences: dict[str, list[float]] = {"matched": [], "mismatched": []}
    per_task: dict[str, list[float]] = defaultdict(list)
    for row in primary:
        base = pairs.get((row.task_id, row.model, "baseline", row.repeat))
        if base and row.condition in differences:
            delta = row.objective_score - base.objective_score
            differences[row.condition].append(delta)
            if row.condition == "matched":
                per_task[row.task_id].append(delta)
    model_pairs = {(r.task_id, r.condition, r.repeat, r.model): r for r in primary}
    disagreement: list[dict[str, Any]] = []
    for row in primary:
        if row.model != "sonnet":
            continue
        peer = model_pairs.get((row.task_id, row.condition, row.repeat, "gpt-5.6-terra"))
        if peer:
            disagreement.append(
                {
                    "task_id": row.task_id,
                    "condition": row.condition,
                    "repeat": row.repeat,
                    "sonnet_minus_terra": row.objective_score - peer.objective_score,
                }
            )

    def similarity(a: Result, b: Result) -> float:
        left = set(re.findall(r"[a-z]+", a.response_text.lower()))
        right = set(re.findall(r"[a-z]+", b.response_text.lower()))
        return len(left & right) / len(left | right) if left | right else 0

    consistency = []
    for task, model in sorted({(r.task_id, r.model) for r in primary}):
        matched = [pairs.get((task, model, "matched", rep)) for rep in (1, 2)]
        baselines = [pairs.get((task, model, "baseline", rep)) for rep in (1, 2)]
        if all(r and r.schema_success for r in [*matched, *baselines]):
            m = [r for r in matched if r]
            b = [r for r in baselines if r]
            within = similarity(m[0], m[1])
            cross = mean(similarity(x, y) for x, y in itertools.product(m, b))
            consistency.append(
                {
                    "task_id": task,
                    "model": model,
                    "within_matched_jaccard": within,
                    "matched_to_baseline_jaccard": cross,
                    "difference": within - cross,
                }
            )
    return {
        "interpretation": "Exploratory descriptive evidence, not significance or causal generalisation. Protocol failures score zero; valid-only scores are also shown. Conditions are paired by task/model/repeat, not identical stochastic seeds.",
        "total_calls": sum(r.model_call_attempted for r in rows),
        "successful_calls": sum(r.call_success for r in rows),
        "failed_calls": sum(r.model_call_attempted and not r.call_success for r in rows),
        "unavailable_without_call": sum(not r.model_call_attempted for r in rows),
        "failure_rate": sum(r.model_call_attempted and not r.call_success for r in rows)
        / max(1, sum(r.model_call_attempted for r in rows)),
        "objective_passes": sum(r.success for r in rows),
        "total_rows": len(rows),
        "wall_seconds": round(
            max((r.ended_at for r in rows), default=0)
            - min((r.started_at for r in rows), default=0),
            2,
        ),
        "primary": {
            "overall": aggregate(primary),
            "by_model": grouped(primary, "model"),
            "by_condition": grouped(primary, "condition"),
            "by_domain": grouped(primary, "domain"),
            "by_role": grouped(primary, "role"),
        },
        "secondary": aggregate([r for r in rows if r.sweep == "secondary"]),
        "matched_minus_baseline": mean(differences["matched"]) if differences["matched"] else None,
        "mismatched_minus_baseline": mean(differences["mismatched"])
        if differences["mismatched"]
        else None,
        "matched_pair_count": len(differences["matched"]),
        "mismatched_pair_count": len(differences["mismatched"]),
        "model_effect_sonnet_minus_terra": mean(d["sonnet_minus_terra"] for d in disagreement)
        if disagreement
        else None,
        "task_matched_effects": sorted(
            [
                {"task_id": task, "difference": mean(values), "n": len(values)}
                for task, values in per_task.items()
            ],
            key=lambda d: d["difference"],
            reverse=True,
        ),
        "strong_model_disagreements": [
            d for d in disagreement if abs(d["sonnet_minus_terra"]) >= 0.25
        ],
        "lexical_role_consistency": consistency,
        "lexical_warning": "Token-set Jaccard is only a lexical proxy, not an embedding or proof of changed reasoning. Full responses support later analysis.",
        "actual_marginal_cost": "UNKNOWN",
        "repairs": 0,
        "production_router_modified": False,
    }


def export(output: Path, rows: list[Result]) -> dict[str, Any]:
    import os

    temporary = output / "responses.jsonl.tmp"
    with temporary.open("w") as handle:
        for row in rows:
            value = row.model_dump()
            value.update(
                score=row.objective_score,
                latency=row.latency_seconds,
                tokens={"input": row.input_tokens, "output": row.output_tokens},
                specialist_role=row.role,
            )
            handle.write(json.dumps(value, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, output / "responses.jsonl")
    columns = [
        "key",
        "task_id",
        "domain",
        "condition",
        "role",
        "model",
        "provider",
        "repeat",
        "sweep",
        "call_success",
        "success",
        "objective_score",
        "tests_passed",
        "tests_total",
        "latency_seconds",
        "input_tokens",
        "output_tokens",
        "schema_success",
        "error_category",
        "relative_cost_class",
        "actual_marginal_cost",
        "repairs",
        "model_call_attempted",
        "response_text",
    ]
    with (output / "results.csv.tmp").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(row.model_dump() for row in rows)
    os.replace(output / "results.csv.tmp", output / "results.csv")
    report = summary(rows)
    atomic_json(output / "summary.json", report)
    priors = []
    for model, domain in sorted({(r.model, r.domain) for r in rows}):
        group = [r for r in rows if r.model == model and r.domain == domain]
        values = aggregate(group)
        priors.append(
            {
                "model": model,
                "domain": domain,
                "observed_score": values["mean_score"],
                "observed_latency": values["mean_latency_seconds"],
                "sample_count": len(group),
                "suggested_direction": "Insufficient evidence; retain current priors. Compare on a larger held-out task set before any upgrade/downgrade.",
            }
        )
    atomic_json(output / "router_prior_suggestions.json", priors)
    lines = [
        "# Exploratory institutional engineering benchmark",
        "",
        report["interpretation"],
        "",
        f"Calls: {report['total_calls']}; schema-valid: {report['successful_calls']}; failed: {report['failed_calls']}; unavailable without invocation: {report['unavailable_without_call']}.",
        f"Objective full passes: {report['objective_passes']}; failure rate: {report['failure_rate']:.1%}; wall seconds: {report['wall_seconds']}.",
        "",
        f"Primary matched − baseline: {report['matched_minus_baseline']}",
        f"Primary mismatched − baseline: {report['mismatched_minus_baseline']}",
        f"Primary Sonnet − Terra: {report['model_effect_sonnet_minus_terra']}",
        "",
    ]
    for grouping in ("by_model", "by_condition", "by_domain"):
        lines += [
            f"## Primary {grouping}",
            "",
            "| Group | n | Mean score | Mean seconds | Input / output tokens reported |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
        for name, values in report["primary"][grouping].items():
            lines.append(
                f"| {name} | {values['n']} | {values['mean_score']:.4f} | {values['mean_latency_seconds']:.2f} | {values['input_tokens_reported']} / {values['output_tokens_reported']} |"
            )
        lines += [""]
    lines += [
        "## Task effects (matched minus baseline)",
        "",
        *[
            f"- {d['task_id']}: {d['difference']:+.4f}, n={d['n']} paired observations."
            for d in report["task_matched_effects"]
        ],
        "",
        "## Strong model score disagreements (absolute delta >= 0.25)",
        "",
        json.dumps(report["strong_model_disagreements"], indent=2),
        "",
        "## Boundaries",
        "",
        "Eight synthetic tasks, two repetitions; no significance claims. All graders frozen before inference. No repair attempts. Role, model and task effects are not interchangeable. Lexical similarity is not latent reasoning. Secondary Sol tasks are selected, not an unbiased comparison with the whole primary suite. Provider aliases and auxiliary models may change; available metadata is retained. Actual marginal monetary spend UNKNOWN. Routing weights untouched.",
    ]
    (output / "SUMMARY.md").write_text("\n".join(lines) + "\n")
    return report
