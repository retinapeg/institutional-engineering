"""Frozen tasks, role interventions, extraction and baseline-only selection."""

import itertools
import re
from typing import Any

CONDITIONS = ("baseline", "generic", "matched", "mismatched")
MODEL = "gpt-5.6-terra"
SEED = 2026091501
COMMON = (
    "Solve the following task using only the supplied information. Do not use tools, "
    "external data or other files. Attempt the actual mathematical task seriously. "
    "Return FINAL_ANSWER: <integer>. You may include a brief visible method summary "
    "of at most 120 words, but do not provide private reasoning or a step-by-step "
    "thought transcript. The final answer must be a single unambiguous integer.\n"
)
WRAPPERS = {
    "baseline": "",
    "generic": (
        "Act as a rigorous generic expert without a domain identity. Inspect assumptions, "
        "solve carefully, check the result against all constraints and obey the output protocol.\n"
    ),
    "matched": (
        "Act as a Mathematician. Your jurisdiction is formal structure, invariants, "
        "combinatorial optimisation, symmetry, bounds and counterexamples. Identify the "
        "feasible set, distinguish local from global optima and verify all constraints. "
        "Evidence and the stated task outrank your lens. Obey the output protocol.\n"
    ),
    "mismatched": (
        "Act as a Product Engineer. Your jurisdiction is user objectives, visible value, "
        "friction, scope discipline and usable deliverables. Identify the requested outcome, "
        "avoid unnecessary features and verify the deliverable meets the stated requirements. "
        "Evidence and the stated task outrank your lens. Obey the output protocol.\n"
    ),
}
ROLES = dict(zip(CONDITIONS, ("None", "Generic Expert", "Mathematician", "Product Engineer")))


def candidates() -> list[dict[str, Any]]:
    weights = [9, 14, 11, 8, 16, 10, 13, 7, 15, 12, 6, 17]
    edges = [
        (1, 2),
        (1, 5),
        (1, 9),
        (2, 3),
        (2, 7),
        (3, 4),
        (3, 10),
        (4, 5),
        (4, 8),
        (5, 6),
        (5, 11),
        (6, 7),
        (6, 10),
        (7, 8),
        (7, 12),
        (8, 9),
        (9, 10),
        (9, 12),
        (10, 11),
        (11, 12),
        (2, 11),
    ]
    items = [
        (7, 4, 19),
        (5, 7, 18),
        (9, 3, 23),
        (4, 6, 17),
        (6, 5, 20),
        (3, 8, 16),
        (8, 2, 21),
        (5, 4, 15),
        (2, 5, 12),
        (7, 6, 24),
        (4, 3, 14),
        (6, 7, 22),
    ]
    costs = [
        [17, 9, 24, 14, 21, 12],
        [13, 22, 8, 19, 11, 25],
        [20, 15, 18, 7, 23, 10],
        [11, 24, 13, 22, 8, 16],
        [26, 12, 9, 17, 15, 20],
        [8, 19, 21, 13, 16, 11],
    ]
    rows: list[dict[str, Any]] = [
        dict(
            task_id="independent_set",
            kind="independent_set",
            weights=weights,
            edges=edges,
            task="Find the maximum total weight of an independent vertex set in the following undirected graph. An independent set contains no two endpoints of any listed edge. Vertices are numbered 1 through 12. Empty selection is allowed. Weights by vertex: "
            + str(weights)
            + ". Edges: "
            + str(edges)
            + ". Return only the maximum total weight as the final integer, not the vertex set.\n",
        ),
        dict(
            task_id="two_resource_knapsack",
            kind="knapsack",
            items=items,
            task="Choose a subset of twelve indivisible items, each usable at most once, to maximise total value. Each tuple below is (weight, volume, value), with items numbered in list order: "
            + str(items)
            + ". Total weight must be at most 26 and total volume at most 25. Choose exactly five items. Items 2 and 10 cannot both be chosen. If item 6 is chosen, item 9 must also be chosen. Return the maximum total value as the final integer.\n",
        ),
        dict(
            task_id="constrained_assignment",
            kind="assignment",
            costs=costs,
            task="Assign six workers numbered 1 through 6 bijectively to six jobs numbered 1 through 6, minimising total cost. Matrix rows are workers, columns jobs: "
            + str(costs)
            + ". Worker 1 cannot take job 2. Worker 4 cannot take job 5. Exactly two workers must receive their same-numbered job. Workers 2 and 5 must receive jobs of opposite parity. Return the minimum total cost as the final integer.\n",
        ),
    ]
    for row in rows:
        row.update(
            ground_truth=solve(row),
            difficulty_prior="medium-high",
            matched_role="Mathematician",
            mismatched_role="Product Engineer",
            verification_method="exhaustive finite enumeration; exact integer equality",
        )
    return rows


def solve(task: dict[str, Any]) -> int:
    if task["kind"] == "assignment":
        return int(
            min(
                sum(task["costs"][i][j - 1] for i, j in enumerate(p))
                for p in itertools.permutations(range(1, 7))
                if p[0] != 2
                and p[3] != 5
                and sum(i == j for i, j in enumerate(p, 1)) == 2
                and p[1] % 2 != p[4] % 2
            )
        )
    values: list[int] = []
    for mask in range(1 << 12):
        chosen = {i + 1 for i in range(12) if mask & (1 << i)}
        if task["kind"] == "independent_set":
            if not any(a in chosen and b in chosen for a, b in task["edges"]):
                values.append(sum(task["weights"][i - 1] for i in chosen))
        elif len(chosen) == 5 and not {2, 10} <= chosen and (6 not in chosen or 9 in chosen):
            totals = [sum(task["items"][i - 1][j] for i in chosen) for j in range(3)]
            if totals[0] <= 26 and totals[1] <= 25:
                values.append(totals[2])
    return max(values)


def extract(text: str) -> int | None:
    """Accept harmless Markdown/prose; reject conflicting labels or ambiguous fallback."""
    clean = text.replace("**", "").replace("`", "").strip()
    number = r"([+-]?(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+))"
    matches = re.findall(r"(?im)^\s*FINAL[_ ]ANSWER\s*:\s*" + number + r"[.!]?\s*$", clean)
    label_count = len(re.findall(r"(?im)^\s*FINAL[_ ]ANSWER\s*:", clean))
    if label_count:
        if len(matches) != label_count:
            return None
        answers = {int(value.replace(",", "")) for value in matches}
        return answers.pop() if len(answers) == 1 else None
    # A bare integer or unambiguous final 'Answer: N' line is substantive evidence too.
    last = clean.splitlines()[-1] if clean else ""
    match = re.fullmatch(
        r"\s*(?:(?:the )?answer\s*(?:is|:)\s*)?" + number + r"[.!]?\s*", last, re.I
    )
    return int(match[1].replace(",", "")) if match else None


def select(rows: list[dict[str, Any]]) -> tuple[str | None, list[dict[str, Any]]]:
    scores = []
    for task in candidates():
        group = [r for r in rows if r["task_id"] == task["task_id"]]
        if len(group) != 20:
            raise ValueError("All 20 observations for each of three candidates are required")
        valid = sum(bool(r["protocol_valid"]) for r in group)
        successes = sum(
            bool(r["substantive_correct"]) and not r["error_type_if_any"] for r in group
        )
        scores.append(
            dict(
                task_id=task["task_id"],
                n=20,
                protocol_valid=valid,
                baseline_rate=successes / 20,
                eligible=valid >= 19 and 7 <= successes <= 17,
                distance=abs(successes - 13),
            )
        )
    eligible = sorted(
        (s for s in scores if s["eligible"]), key=lambda s: (s["distance"], s["task_id"])
    )
    return (str(eligible[0]["task_id"]) if eligible else None), scores
