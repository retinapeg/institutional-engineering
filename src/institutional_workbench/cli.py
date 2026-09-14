import argparse
import fcntl
import json
import signal
import subprocess
import time
from pathlib import Path

from .orchestrator import Workbench
from .providers import CliProviders
from .runner import Blocked, Runner


def main() -> int:
    parser = argparse.ArgumentParser(description="Decide, build, test, deliver, stop.")
    parser.add_argument("command", choices=["dev", "hack", "status", "cancel"])
    parser.add_argument("task", nargs="?")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--builder", choices=["claude", "codex"], default="claude")
    parser.add_argument("--reviewer", choices=["claude", "codex"], default="codex")
    parser.add_argument("--claude-model", default="sonnet")
    parser.add_argument("--codex-model", default="gpt-5.6-terra")
    parser.add_argument(
        "--quick", action="store_true", help="Routine task: builder only, no expert roundtable"
    )
    parser.add_argument(
        "--test",
        action="append",
        help="Approved acceptance command; repeat for lint/build/demo checks",
    )
    parser.add_argument("--minutes", type=float, default=15)
    args = parser.parse_args()
    if not 0 < args.minutes <= 60:
        parser.error("--minutes must be between 0 and 60")
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=args.repo,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        repo = Path(result.stdout.strip()).resolve()
        root = repo / ".institutional-workbench"
        root.mkdir(exist_ok=True)
        active = root / "active.json"
        if args.command in {"status", "cancel"}:
            if not active.exists():
                raise Blocked("No previous run in this repository")
            state_path = Path(json.loads(active.read_text())["run_dir"]) / "run.json"
            state = (
                json.loads(state_path.read_text())
                if state_path.exists()
                else {"status": "STARTING"}
            )
            if args.command == "cancel":
                if state["status"] in {"DELIVERED", "BLOCKED"}:
                    print("Run has already stopped.")
                else:
                    (state_path.parent / "cancel").touch()
                    print(
                        "Cancellation requested; the child process will stop and isolated work is retained."
                    )
            else:
                print(json.dumps(state, indent=2))
            return 0
        if not args.task or not args.task.strip():
            parser.error("dev/hack require a task")
        with (root / "run.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise Blocked(
                    "Another workbench run is active; use inst status or inst cancel"
                ) from exc
            run_dir = root / time.strftime("%Y%m%d-%H%M%S")
            run_dir.mkdir(exist_ok=False)
            active.write_text(json.dumps({"run_dir": str(run_dir)}))
            runner = Runner(run_dir / "cancel", args.minutes * 60)
            signal.signal(signal.SIGINT, lambda *_: runner.cancel_file.touch())
            signal.signal(signal.SIGTERM, lambda *_: runner.cancel_file.touch())
            providers = CliProviders(runner, args.claude_model, args.codex_model)
            state = Workbench(
                repo,
                run_dir,
                runner,
                providers,
                mode=args.command,
                objective=args.task,
                builder=args.builder,
                reviewer=args.reviewer,
                quick=args.quick,
                tests=args.test,
            ).run()
            print("\n" + state["status"])
            if state["status"] == "DELIVERED":
                print("What changed: " + state["deliverable"])
                print(
                    "Tests: "
                    + "; ".join(" ".join(t["command"]) + " — passed" for t in state["tests"])
                )
                print("Run: " + state["run_command"])
                print("Files changed: " + ", ".join(state["files_changed"]))
                print("Known limitations: " + ("; ".join(state["limitations"]) or "None reported"))
                if args.command == "hack":
                    print("Pitch: " + " → ".join(state["pitch_outline"]))
                    print("Fallback: " + state["fallback"])
            else:
                print("Concrete blocker: " + state["current_blocker"])
                print("Best next action: resolve that blocker, then run the command again.")
            print("Evidence: " + str(run_dir))
            return 0 if state["status"] == "DELIVERED" else 1
    except (Blocked, OSError, subprocess.SubprocessError) as exc:
        print(f"BLOCKED\n{exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
