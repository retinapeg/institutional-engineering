"""96 primary calls, optionally 16 Sol calls. Reserved keys are never retried."""

import argparse
import fcntl
import hashlib
import json
import random
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from datetime import datetime
from pathlib import Path
from typing import Any

from institutional_workbench.providers import CliProviders
from institutional_workbench.routing import LENSES
from institutional_workbench.runner import Blocked, Runner

from .analysis import atomic_json, export
from .graders import grade
from .schemas import BenchmarkResponse, Cell, Result, Task

ROOT = Path(__file__).parent
SEED = 20260915


def load_tasks() -> list[Task]:
    tasks = [
        Task.model_validate(row) for row in json.loads((ROOT / "tasks/tasks.json").read_text())
    ]
    if len(tasks) != 8 or len({t.task_id for t in tasks}) != 8:
        raise ValueError("Exactly eight unique tasks required")
    if any(
        sum(t.domain == domain for t in tasks) != 2
        for domain in ("physics", "mathematics", "statistics", "software")
    ):
        raise ValueError("Exactly two tasks per domain required")
    for task in tasks:
        if (
            task.matched_role == task.mismatched_role
            or task.matched_role not in LENSES
            or task.mismatched_role not in LENSES
        ):
            raise ValueError("Distinct known constitutions required")
    return tasks


def matrix(tasks: list[Task], secondary: bool = False) -> list[Cell]:
    cells = [
        Cell.model_validate(
            dict(
                task_id=task.task_id,
                provider=provider,
                model=model,
                condition=condition,
                repeat=repeat,
                sweep="secondary" if secondary else "primary",
            )
        )
        for task in tasks
        for provider, model in (
            [("codex", "gpt-5.6-sol")]
            if secondary
            else [("claude", "sonnet"), ("codex", "gpt-5.6-terra")]
        )
        for condition in (
            ["baseline", "matched"] if secondary else ["baseline", "matched", "mismatched"]
        )
        for repeat in (1, 2)
    ]
    random.Random(SEED + int(secondary)).shuffle(cells)
    return cells


def role_for(task: Task, cell: Cell) -> str:
    return (
        "None"
        if cell.condition == "baseline"
        else task.matched_role
        if cell.condition == "matched"
        else task.mismatched_role
    )


def prompt_for(task: Task, cell: Cell) -> str:
    prompt: dict[str, Any] = {
        "instruction": "Solve the task accurately and concisely. Return the requested answer plus a brief visible method summary, assumptions, confidence and proposed checks. Do not provide hidden chain-of-thought or a step-by-step reasoning transcript. Attempt the actual task seriously regardless of your jurisdiction. Do not use tools. For noncoding tasks, files must be empty.",
        "task": task.task,
    }
    role = role_for(task, cell)
    if role != "None":
        _, jurisdiction, question = LENSES[role]
        prompt["specialist_constitution"] = {
            "role": role,
            "jurisdiction": jurisdiction,
            "focus": question,
            "authority": "Evidence and the task's requirements outrank your lens. Do not invent facts or substitute a different task.",
        }
    if task.fixture:
        prompt["snapshot"] = {"solution.py": (ROOT / "fixtures" / task.fixture).read_text()}
    return json.dumps(prompt)


def fingerprint() -> str:
    paths = sorted([*ROOT.glob("*.py"), *ROOT.glob("tasks/*"), *ROOT.glob("fixtures/*")])
    paths += [
        ROOT.parent / "src/institutional_workbench" / name
        for name in ("providers.py", "runner.py", "routing.py")
    ]
    digest = hashlib.sha256()
    for path in paths:
        if path.is_file():
            digest.update(path.name.encode() + path.read_bytes())
    return digest.hexdigest()


def clean_usage(usage: dict[str, Any]) -> dict[str, Any]:
    # Explicit allowlist: no account/session IDs, paths, prompts or reasoning content.
    counters = {
        "input_tokens",
        "output_tokens",
        "cached_input_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
        "cache_write_input_tokens",
        "reasoning_output_tokens",
        "inputTokens",
        "outputTokens",
        "cacheReadInputTokens",
        "cacheCreationInputTokens",
        "thinkingTokens",
        "costUSD",
        "webSearchRequests",
        "contextWindow",
        "maxOutputTokens",
    }
    result: dict[str, Any] = {
        "usage": {
            key: value
            for key, value in usage.get("usage", {}).items()
            if key in counters and isinstance(value, (int, float))
        }
    }
    result["models"] = {
        model: {
            key: value
            for key, value in values.items()
            if key in counters and isinstance(value, (int, float))
        }
        for model, values in usage.get("models", {}).items()
        if isinstance(values, dict) and model.startswith(("claude-", "gpt-"))
    }
    if isinstance(usage.get("reported_cost_usd"), (int, float)):
        result["reported_cost_usd"] = usage["reported_cost_usd"]
    return result


class EvidenceRunner(Runner):
    """Capture only final visible responses; never persist raw CLI event streams."""

    def __init__(self, cancel_file: Path, seconds: float):
        super().__init__(cancel_file, seconds)
        self.visible = ""
        self.diagnostic = ""
        self.usage: dict[str, Any] = {}

    def run(
        self,
        argv: list[str],
        cwd: Path,
        text: str = "",
        timeout: float = 90,
        *,
        require_success: bool = True,
    ) -> tuple[int, str, str]:
        code, out, err = super().run(argv, cwd, text, timeout, require_success=False)
        self.diagnostic = err
        try:
            if argv[0] == "claude":
                envelope = json.loads(out)
                self.visible = envelope.get("result", "")
                self.usage = {
                    "usage": envelope.get("usage", {}),
                    "models": envelope.get("modelUsage", {}),
                    "reported_cost_usd": envelope.get("total_cost_usd"),
                }
            else:
                texts = []
                for line in out.splitlines():
                    event = json.loads(line)
                    item = event.get("item", {})
                    if (
                        event.get("type") == "item.completed"
                        and item.get("type") == "agent_message"
                    ):
                        texts.append(item.get("text", ""))
                    if event.get("type") == "turn.completed":
                        self.usage = {"usage": event.get("usage", {})}
                    if event.get("type") in {"error", "turn.failed"}:
                        self.diagnostic += json.dumps(event)
                self.visible = "\n".join(texts)
        except (ValueError, TypeError):
            pass
        if code and require_success:
            raise Blocked(f"Provider process exited {code}")
        return code, out, err


def error_category(text: str) -> str:
    lowered = text.lower()
    if any(
        word in lowered
        for word in ("rate limit", "rate_limit", "usage limit", "quota", "429", "out of credits")
    ):
        return "RATE_LIMITED"
    if any(
        word in lowered
        for word in ("login expired", "not logged in", "authentication", "unauthorized", "401")
    ):
        return "UNAVAILABLE"
    if "timed out" in lowered or "time budget" in lowered:
        return "TIMEOUT"
    if "malformed" in lowered:
        return "MALFORMED"
    if "cancel" in lowered:
        return "CANCELLED"
    return "PROVIDER_ERROR"


def empty_result(
    task: Task, cell: Cell, run_id: str, category: str, attempted: bool = True
) -> Result:
    now = time.time()
    return Result(
        key=cell.key,
        run_id=run_id,
        task_id=task.task_id,
        domain=task.domain,
        condition=cell.condition,
        role=role_for(task, cell),
        provider=cell.provider,
        model=cell.model,
        repeat=cell.repeat,
        sweep=cell.sweep,
        task_text=task.task,
        difficulty_prior=task.difficulty_prior,
        relative_cost_class="high" if cell.model == "gpt-5.6-sol" else "medium",
        started_at=now,
        ended_at=now,
        error_category=category,
        model_call_attempted=attempted,
    )


def invoke(task: Task, cell: Cell, run_id: str, output: Path, deadline: float) -> Result:
    result = empty_result(task, cell, run_id, "PROVIDER_ERROR")
    runner = EvidenceRunner(output / "cancel", max(0, deadline - time.time()))
    provider = CliProviders(runner)
    response_received: float | None = None
    try:
        response = provider.ask(
            cell.provider, prompt_for(task, cell), BenchmarkResponse, model=cell.model
        )
        response_received = time.time()
        result.response = response
        result.response_text = response.model_dump_json()
        result.schema_success = result.call_success = True
        result.error_category = None
        verification = grade(task, response)
        result.objective_score = verification.score
        result.success = verification.score == 1
        result.tests_passed, result.tests_total = (
            verification.tests_passed,
            verification.tests_total,
        )
        result.verification_details = verification.details
    except Exception as exc:
        result.error_category = (
            "GRADER_ERROR"
            if result.schema_success
            else error_category(str(exc) + runner.diagnostic + runner.visible)
        )
        result.error = (
            f"{type(exc).__name__}: {result.error_category}; raw stderr excluded for privacy"
        )
        result.response_text = runner.visible[:30000]
    result.ended_at = time.time()
    result.latency_seconds = round((response_received or result.ended_at) - result.started_at, 3)
    result.reported_usage_metadata = clean_usage(runner.usage or provider.last_usage)
    counts = result.reported_usage_metadata.get("usage", {})
    if isinstance(counts, dict):
        input_count, output_count = counts.get("input_tokens"), counts.get("output_tokens")
        result.input_tokens = int(input_count) if isinstance(input_count, (int, float)) else None
        result.output_tokens = int(output_count) if isinstance(output_count, (int, float)) else None
    return result


class Store:
    def __init__(self, output: Path, deadline: float, max_calls: int = 112):
        if not 0 <= max_calls <= 120:
            raise ValueError("Absolute cap is 120 calls")
        self.output = output
        (output / "records").mkdir(parents=True, exist_ok=True)
        self.path = output / "manifest.json"
        if self.path.exists():
            self.manifest = json.loads(self.path.read_text())
            if self.manifest["protocol_hash"] != fingerprint():
                raise ValueError(
                    "Frozen experiment code/tasks changed; refusing mixed-protocol resume"
                )
            self.manifest["deadline"] = min(deadline, self.manifest["deadline"])
            self.manifest["max_calls"] = min(max_calls, self.manifest["max_calls"])
        else:
            self.manifest = {
                "run_id": datetime.now().strftime("%Y%m%d-%H%M%S"),
                "created_at": time.time(),
                "deadline": min(deadline, time.time() + 10800),
                "max_calls": max_calls,
                "protocol_hash": fingerprint(),
                "seed": SEED,
                "reservations": {},
                "unavailable_providers": [],
                "status": "READY",
            }
        self.rows: dict[str, Result] = {}
        for path in sorted((output / "records").glob("*.json")):
            row = Result.model_validate_json(path.read_text())
            if path.stem != row.key:
                raise ValueError("Stored result key mismatch")
            self.rows[row.key] = row
        self.save()

    def save(self) -> None:
        atomic_json(self.path, self.manifest)

    def reserve(self, cell: Cell) -> bool:
        if cell.key in self.rows or cell.key in self.manifest["reservations"]:
            return False
        if (
            len(self.manifest["reservations"]) >= self.manifest["max_calls"]
            or time.time() >= self.manifest["deadline"]
            or (self.output / "cancel").exists()
        ):
            return False
        self.manifest["reservations"][cell.key] = cell.model_dump()
        self.save()  # Durable BEFORE external call; crash does not authorise another attempt.
        return True

    def persist(self, result: Result) -> None:
        if result.key in self.rows:
            raise ValueError("Cannot overwrite an existing observation")
        atomic_json(self.output / "records" / f"{result.key}.json", result.model_dump())
        self.rows[result.key] = result
        export(self.output, list(self.rows.values()))

    def interrupted(self, tasks: dict[str, Task]) -> None:
        for key, value in self.manifest["reservations"].items():
            if key not in self.rows:
                cell = Cell.model_validate(value)
                self.persist(
                    empty_result(tasks[cell.task_id], cell, self.manifest["run_id"], "INTERRUPTED")
                )


def sweep(store: Store, tasks: dict[str, Task], cells: list[Cell], concurrency: int = 2) -> None:
    if concurrency not in (1, 2):
        raise ValueError("Concurrency must be 1 or 2")
    pending = [c for c in cells if c.key not in store.rows]
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        active: dict[Any, Cell] = {}
        while pending or active:
            if (
                sum(r.error_category in {"PROVIDER_ERROR", "TIMEOUT"} for r in store.rows.values())
                >= 2
            ):
                concurrency = 1  # Conservative fallback; no retry of failed cells.
            while pending and len(active) < concurrency:
                cell = pending.pop(0)
                if cell.provider in store.manifest["unavailable_providers"]:
                    store.persist(
                        empty_result(
                            tasks[cell.task_id],
                            cell,
                            store.manifest["run_id"],
                            "UNAVAILABLE",
                            attempted=False,
                        )
                    )
                    continue
                if not store.reserve(cell):
                    pending.clear()
                    break
                print(
                    f"START {len(store.manifest['reservations'])}/120 {cell.task_id} {cell.model} {cell.condition} r{cell.repeat}",
                    flush=True,
                )
                active[
                    pool.submit(
                        invoke,
                        tasks[cell.task_id],
                        cell,
                        store.manifest["run_id"],
                        store.output,
                        store.manifest["deadline"],
                    )
                ] = cell
            if not active:
                break
            done, _ = wait(active, timeout=1, return_when=FIRST_COMPLETED)
            for future in done:
                cell = active.pop(future)
                result = future.result()
                store.persist(result)
                if result.error_category in {"RATE_LIMITED", "UNAVAILABLE"}:
                    store.manifest["unavailable_providers"] = sorted(
                        set(store.manifest["unavailable_providers"]) | {cell.provider}
                    )
                    store.save()
                print(
                    f"DONE {len(store.rows)} {cell.task_id} {cell.model} {cell.condition} score={result.objective_score:.3f} {result.latency_seconds:.1f}s {result.error_category or 'OK'}",
                    flush=True,
                )


def secondary_tasks(tasks: list[Task], rows: list[Result]) -> list[Task]:
    def difficulty(task: Task) -> tuple[float, float, int, str]:
        scores = [
            r.objective_score for r in rows if r.task_id == task.task_id and r.sweep == "primary"
        ]
        return (
            sum(scores) / max(1, len(scores)),
            -(max(scores) - min(scores)) if scores else 0,
            -int(task.difficulty_prior == "high"),
            task.task_id,
        )

    return sorted(tasks, key=difficulty)[:4]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Explicitly invoke the authorised primary/conditional secondary sweep",
    )
    parser.add_argument("--output", type=Path, default=ROOT / "results")
    parser.add_argument(
        "--deadline", help="ISO UTC deadline; cannot exceed 3 hours from first launch"
    )
    parser.add_argument("--max-calls", type=int, default=112)
    parser.add_argument("--concurrency", type=int, choices=[1, 2], default=2)
    args = parser.parse_args()
    tasks = load_tasks()
    if not args.live:
        print(
            f"Frozen plan: {len(matrix(tasks))} primary cells; <=16 conditional Sol cells. No live calls. Add --live to execute."
        )
        return
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "experiment.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        deadline = (
            datetime.fromisoformat(args.deadline).timestamp()
            if args.deadline
            else time.time() + 10800
        )
        store = Store(args.output, deadline, args.max_calls)
        lookup = {task.task_id: task for task in tasks}
        store.interrupted(lookup)
        store.manifest["status"] = "PRIMARY"
        store.save()
        sweep(store, lookup, matrix(tasks), args.concurrency)
        primary = [r for r in store.rows.values() if r.sweep == "primary"]
        protocol_failures = sum(not r.call_success for r in primary) / max(1, len(primary))
        eligible = (
            len(primary) == 96
            and protocol_failures < 0.2
            and store.manifest["deadline"] - time.time() > 1800
        )
        if "secondary_tasks" not in store.manifest:
            store.manifest["secondary_tasks"] = (
                [t.task_id for t in secondary_tasks(tasks, primary)] if eligible else []
            )
            store.manifest["secondary_gate"] = {
                "primary_rows": len(primary),
                "protocol_failure_rate": protocol_failures,
                "remaining_seconds": store.manifest["deadline"] - time.time(),
                "eligible": eligible,
            }
            store.save()
        selected = [lookup[key] for key in store.manifest["secondary_tasks"]]
        if selected:
            store.manifest["status"] = "SECONDARY"
            store.save()
            sweep(store, lookup, matrix(selected, secondary=True), args.concurrency)
        store.manifest["status"] = (
            "FINISHED"
            if len(primary) == 96
            and all(cell.key in store.rows for cell in matrix(selected, secondary=True))
            else "BUDGET_OR_CANCELLED"
        )
        store.manifest["finished_at"] = time.time()
        store.save()
        report = export(store.output, list(store.rows.values()))
        print(
            json.dumps(
                {
                    key: report[key]
                    for key in (
                        "total_calls",
                        "successful_calls",
                        "failed_calls",
                        "matched_minus_baseline",
                        "mismatched_minus_baseline",
                        "wall_seconds",
                    )
                },
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
