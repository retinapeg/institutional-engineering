"""Serial, hash-locked, resumable experiment. No retry and no production changes."""

import argparse
import fcntl
import hashlib
import json
import os
import random
import signal
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from benchmarks.analysis import atomic_json
from benchmarks.runner import error_category
from institutional_workbench.runner import Runner

from .analysis import export
from .design import COMMON, CONDITIONS, MODEL, ROLES, SEED, WRAPPERS, candidates, extract, select

ROOT = Path(__file__).parent
REPO = ROOT.parents[1]
EXPERIMENT = "single-task-role-effect-20260915-v1"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read(path: Path) -> Any:
    return json.loads(path.read_text())


def version() -> str:
    return subprocess.check_output(["codex", "--version"], text=True, timeout=5).strip()


def argv() -> list[str]:
    command = [
        "codex",
        "exec",
        "--ignore-user-config",
        "--ignore-rules",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        "--json",
        "--model",
        MODEL,
    ]
    for option in (
        'approval_policy="never"',
        'web_search="disabled"',
        "project_doc_max_bytes=0",
        "suppress_unstable_features_warning=true",
        'model_reasoning_effort="medium"',
        "model_providers.openai.request_max_retries=0",
        "model_providers.openai.stream_max_retries=0",
    ):
        command += ["-c", option]
    for feature in (
        "hooks",
        "plugins",
        "apps",
        "shell_tool",
        "unified_exec",
        "multi_agent",
        "multi_agent_v2",
        "browser_use",
        "in_app_browser",
        "image_generation",
        "view_image",
        "memories",
        "skill_search",
        "sleep_tool",
        "js_repl",
        "tool_suggest",
    ):
        command += ["--disable", feature]
    return command + ["--enable", "skip_host_skill_discovery", "-"]


def schedule(task_ids: list[str], calibration: bool) -> list[dict[str, Any]]:
    rng = random.Random(SEED + int(calibration))
    rows: list[dict[str, Any]] = []
    for block in range(20 if calibration else 250):
        order = task_ids[:] if calibration else list(CONDITIONS)
        rng.shuffle(order)
        for position, item in enumerate(order):
            rows.append(
                dict(
                    call_index=len(rows),
                    block_index=block,
                    condition_order=position,
                    task_id=item if calibration else task_ids[0],
                    condition="baseline" if calibration else item,
                )
            )
    return rows


def prepare(root: Path = ROOT) -> None:
    if (root / "protocol.json").exists():
        verify(root)
        return
    (root / "candidates").mkdir(exist_ok=True)
    for task in candidates():
        atomic_json(root / "candidates" / (task["task_id"] + ".json"), task)
        (root / "candidates" / (task["task_id"] + ".txt")).write_bytes(task["task"].encode())
    atomic_json(
        root / "calibration_schedule.json", schedule([t["task_id"] for t in candidates()], True)
    )
    paths = [
        *root.glob("*.py"),
        root / "PROTOCOL.md",
        root / "calibration_schedule.json",
        *sorted((root / "candidates").glob("*")),
        REPO / "src/institutional_workbench/runner.py",
        REPO / "benchmarks/analysis.py",
        REPO / "benchmarks/runner.py",
    ]
    protocol = dict(
        experiment_id=EXPERIMENT,
        provider="codex",
        requested_model=MODEL,
        runtime_version=version(),
        reasoning_effort="medium",
        temperature="UNAVAILABLE",
        model_seed="UNAVAILABLE",
        context_size="UNAVAILABLE",
        resolved_model="UNAVAILABLE",
        concurrency=1,
        timeout_seconds=90,
        max_calibration_calls=60,
        max_study_calls=1000,
        schedule_rng_seed=SEED,
        wrappers=WRAPPERS,
        common_instruction=COMMON,
        actual_marginal_cost="UNKNOWN",
        task_id=None,
        task_sha256=None,
        selection_rule="20/candidate; valid>=19, correct 7..17 inclusive; minimise abs(correct-13), then lexical task_id; no eligible => BLOCKED",
        input_hashes={
            os.path.relpath(p.resolve(), root.resolve()): sha(p.read_bytes()) for p in paths
        },
    )
    atomic_json(root / "protocol.json", protocol)
    (root / "results.jsonl").touch(exist_ok=False)
    export(root, [])


def verify(root: Path, full: bool = False, committed: bool = False) -> dict[str, Any]:
    protocol: dict[str, Any] = read(root / "protocol.json")
    if protocol["requested_model"] != MODEL or protocol["concurrency"] != 1:
        raise ValueError("Model/concurrency differs from frozen protocol")
    paths = [root / "protocol.json"]
    for name, expected in protocol["input_hashes"].items():
        path = root / name
        if sha(path.read_bytes()) != expected:
            raise ValueError("Frozen input hash mismatch: " + name)
        paths.append(path)
    if protocol["wrappers"] != WRAPPERS or protocol["common_instruction"] != COMMON:
        raise ValueError("Role wrappers changed")
    if full:
        if not protocol["task_id"]:
            raise ValueError("No calibration-qualified task is frozen")
        for name, key in (("task.txt", "task_sha256"), ("schedule.json", "schedule_sha256")):
            if sha((root / name).read_bytes()) != protocol[key]:
                raise ValueError("Frozen " + name + " changed; experiment BLOCKED")
            paths.append(root / name)
        if (root / "task_sha256.txt").read_text().strip() != protocol["task_sha256"]:
            raise ValueError("Task hash receipt differs")
        if read(root / "schedule.json") != schedule([protocol["task_id"]], False):
            raise ValueError("Schedule differs from preregistered generator")
        paths += [root / "task_sha256.txt", root / "selection.json"]
    if committed:
        for path in paths:
            rel = str(path.resolve().relative_to(REPO))
            stored = subprocess.check_output(
                ["git", "show", "HEAD:" + rel], cwd=REPO, stderr=subprocess.DEVNULL
            )
            if stored != path.read_bytes():
                raise ValueError("Preregistration is uncommitted: " + rel)
    return protocol


def prompt(task: bytes, condition: str) -> str:
    return COMMON + WRAPPERS[condition] + "\n<TASK>\n" + task.decode("utf-8") + "</TASK>\n"


def parse_events(stdout: str, stderr: str, code: int) -> dict[str, Any]:
    texts: list[str] = []
    usage: dict[str, int] = {}
    errors = stderr if code else ""
    completed = False
    tool_attempt = False
    malformed = False
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
            item = event.get("item", {})
            if event.get("type") == "item.completed" and item.get("type") == "agent_message":
                texts.append(str(item["text"]))
            if event.get("type") == "turn.completed":
                completed = True
                usage = {
                    k: v
                    for k, v in event.get("usage", {}).items()
                    if k in {"input_tokens", "output_tokens", "cached_input_tokens"}
                    and isinstance(v, int)
                }
            if event.get("type") in {"error", "turn.failed"} or item.get("type") == "error":
                errors += json.dumps(event)
            if item and item.get("type") not in {
                "agent_message",
                "reasoning",
                "todo_list",
                "error",
            }:
                tool_attempt = True
        except (ValueError, TypeError, KeyError, AttributeError):
            malformed = True
    category = (
        error_category(errors)
        if errors or code
        else "TOOL_ATTEMPT"
        if tool_attempt
        else "MALFORMED_RUNTIME"
        if malformed or not completed or not texts
        else None
    )
    return dict(
        response_text="\n".join(texts),
        input_tokens_if_known=usage.get("input_tokens"),
        output_tokens_if_known=usage.get("output_tokens"),
        cached_input_tokens_if_known=usage.get("cached_input_tokens"),
        error_type_if_any=category,
    )


def invoke(full_prompt: str, root: Path) -> dict[str, Any]:
    started = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="institutional-study-") as directory:
            code, out, err = Runner(root / "cancel", 95).run(
                argv(), Path(directory), full_prompt, timeout=90, require_success=False
            )
        result = parse_events(out, err, code)
    except Exception as exc:
        result = dict(
            response_text="",
            error_type_if_any=error_category(str(exc)),
            input_tokens_if_known=None,
            output_tokens_if_known=None,
            cached_input_tokens_if_known=None,
        )
    result["latency_seconds"] = time.monotonic() - started
    return result


def observations(root: Path, calibration: bool) -> list[dict[str, Any]]:
    folder = root / ("calibration_records" if calibration else "records")
    rows = [read(p) for p in sorted(folder.glob("*.json"))]
    keys = [r["key"] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate observation keys")
    return [r for r in rows if r["terminal"]]


def sync_jsonl(root: Path, calibration: bool) -> None:
    name = "calibration_results.jsonl" if calibration else "results.jsonl"
    rows = observations(root, calibration)
    temporary = root / (name + ".tmp")
    with temporary.open("w") as handle:
        for row in rows:
            handle.write(json.dumps(row, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(root / name)


def batch(root: Path, calibration: bool) -> None:
    protocol = verify(root, not calibration, committed=True)
    if version() != protocol["runtime_version"]:
        raise ValueError("CLI version changed; no unrecorded runtime change allowed")
    planned = read(root / ("calibration_schedule.json" if calibration else "schedule.json"))
    if len(planned) != (60 if calibration else 1000):
        raise ValueError("Call cap/schedule mismatch")
    folder = root / ("calibration_records" if calibration else "records")
    folder.mkdir(exist_ok=True)
    for cell in planned:
        # Every call rechecks exact task bytes, wrappers, code, schedule and committed state.
        verify(root, not calibration, committed=True)
        if (root / "cancel").exists():
            break
        key = f"{EXPERIMENT}:{cell['block_index']}:{cell['task_id'] if calibration else cell['condition']}"
        path = folder / f"{cell['call_index']:04d}.json"
        if path.exists():
            previous = read(path)
            if previous["key"] != key:
                raise ValueError("Observation does not match frozen schedule")
            if not previous["terminal"]:
                previous.update(terminal=True, error_type_if_any="INTERRUPTED")
                atomic_json(path, previous)
                sync_jsonl(root, calibration)
            continue
        if version() != protocol["runtime_version"]:
            raise ValueError("CLI version changed during study")
        task_file = (
            root / "candidates" / (cell["task_id"] + ".txt") if calibration else root / "task.txt"
        )
        task = task_file.read_bytes()
        expected = (
            protocol["input_hashes"]["candidates/" + cell["task_id"] + ".txt"]
            if calibration
            else protocol["task_sha256"]
        )
        if sha(task) != expected:
            raise ValueError("Task changed immediately before inference")
        full_prompt = prompt(task, cell["condition"])
        row = dict(
            **cell,
            key=key,
            experiment_id=EXPERIMENT,
            stage="calibration" if calibration else "full",
            task_sha256=sha(task),
        )
        row.update(
            role=ROLES[cell["condition"]],
            provider="codex",
            requested_model=MODEL,
            resolved_model_if_known="UNAVAILABLE",
            runtime_version=protocol["runtime_version"],
            reasoning_effort="medium",
            temperature="UNAVAILABLE",
            model_seed="UNAVAILABLE",
            context_size="UNAVAILABLE",
            concurrency=1,
            full_prompt_sha256=sha(full_prompt.encode()),
            timestamp=datetime.now(timezone.utc).isoformat(),
            terminal=False,
            response_text="",
            extracted_answer=None,
            protocol_valid=False,
            substantive_correct=False,
            latency_seconds=None,
            input_tokens_if_known=None,
            output_tokens_if_known=None,
            cached_input_tokens_if_known=None,
            error_type_if_any=None,
            actual_marginal_cost="UNKNOWN",
            protocol_sha256=sha((root / "protocol.json").read_bytes()),
            code_commit=subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=REPO, text=True
            ).strip(),
        )
        atomic_json(path, row)  # Reservation is durable BEFORE inference; never retry after crash.
        print(
            f"START {row['stage']} {cell['call_index'] + 1}/{len(planned)} {cell['task_id']} {cell['condition']}",
            flush=True,
        )
        result = invoke(full_prompt, root)
        answer = extract(result["response_text"])
        gold = read(root / "candidates" / (cell["task_id"] + ".json"))["ground_truth"]
        row.update(
            result,
            extracted_answer=answer,
            protocol_valid=answer is not None,
            substantive_correct=answer == gold if answer is not None else False,
            terminal=True,
            ended_at=datetime.now(timezone.utc).isoformat(),
        )
        atomic_json(path, row)
        sync_jsonl(root, calibration)
        print(
            f"DONE correct={row['substantive_correct']} parsed={row['protocol_valid']} error={row['error_type_if_any']} seconds={row['latency_seconds']:.1f}",
            flush=True,
        )
        if row["error_type_if_any"] in {"RATE_LIMITED", "UNAVAILABLE", "CANCELLED"}:
            break
    if not calibration:
        export(root, observations(root, False))


def freeze(root: Path) -> None:
    protocol = verify(root)
    if protocol["task_id"]:
        verify(root, True)
        return
    rows = observations(root, True)
    chosen, scores = select(rows)
    atomic_json(
        root / "selection.json",
        dict(
            selected=chosen, calibration=scores, status="SELECTED" if chosen else "NO_ELIGIBLE_TASK"
        ),
    )
    if chosen is None:
        raise ValueError(
            "No candidate meets preregistered calibration rule; full experiment BLOCKED"
        )
    task = (root / "candidates" / (chosen + ".txt")).read_bytes()
    (root / "task.txt").write_bytes(task)
    (root / "task_sha256.txt").write_text(sha(task) + "\n")
    atomic_json(root / "schedule.json", schedule([chosen], False))
    protocol.update(
        task_id=chosen,
        task_sha256=sha(task),
        schedule_sha256=sha((root / "schedule.json").read_bytes()),
    )
    atomic_json(root / "protocol.json", protocol)
    print(json.dumps(dict(task_id=chosen, task_sha256=sha(task), calibration=scores), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "calibrate", "freeze", "run", "analyse"])
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    with (ROOT / "study.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        signal.signal(signal.SIGINT, lambda *_: (ROOT / "cancel").touch())
        signal.signal(signal.SIGTERM, lambda *_: (ROOT / "cancel").touch())
        if args.command == "prepare":
            prepare()
        elif args.command == "freeze":
            freeze(ROOT)
        elif args.command == "analyse":
            export(ROOT, observations(ROOT, False))
        elif not args.live:
            print("No calls made. --live is required for the preregistered batch.")
        else:
            batch(ROOT, args.command == "calibrate")


if __name__ == "__main__":
    main()
