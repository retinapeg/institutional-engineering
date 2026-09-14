"""One roundtable, one decision, one builder, one QA pass, at most two repairs."""

import hashlib
import json
import os
import shlex
import sys
import time
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel

from .models import BuildTask, Challenge, Decision, ExpertReport, FileChange, QAResult, RepairResult
from .providers import Provider
from .runner import Blocked, Runner

T = TypeVar("T", bound=BaseModel)
POLICIES = {
    "dev": "Ship the smallest correct implementation. Prioritise working behaviour, correctness, reliability and maintainability. No speculative refactoring.",
    "hack": "Optimise the supplied judging rubric, deadline, sponsor stack and visible user value. Rank scoring opportunities. Choose ONE winning demo moment. Verify the demo path. Freeze stable code. Return pitch and fallback; mark missing rubric details UNKNOWN.",
}
REASONING = "Identify objective and constraints. Reduce the problem; look for invariants, symmetry and the highest-leverage change where relevant. Make claims testable. Evidence outranks confidence. Do not imitate or automatically agree with the user. Build a vertical slice and stop."


class Workbench:
    def __init__(
        self,
        repo: Path,
        run_dir: Path,
        runner: Runner,
        provider: Provider,
        *,
        mode: str,
        objective: str,
        builder: str = "claude",
        reviewer: str = "codex",
        quick: bool = False,
        tests: list[str] | None = None,
        experts: list[tuple[str, str, str]] | None = None,
    ):
        self.repo, self.run_dir, self.runner, self.provider = repo, run_dir, runner, provider
        self.mode, self.objective = mode, objective
        self.builder, self.reviewer, self.quick = builder, reviewer, quick
        self.commands = [shlex.split(command) for command in (tests or [])]
        self.experts = experts if experts is not None else self.select_experts()
        if len(self.experts) > 4 or any(not question.strip() for _, _, question in self.experts):
            raise Blocked("At most four specialists, each with a concrete question")
        self.work = run_dir / "workspace"
        self.state: dict[str, Any] = {
            "objective": objective,
            "deliverable": "",
            "acceptance_criteria": [],
            "current_phase": "UNDERSTAND",
            "current_blocker": None,
            "next_build_action": "Inspect repository",
            "calls": 0,
            "max_calls": 16,
            "repairs": 0,
            "mode": mode,
            "status": "RUNNING",
            "started": time.time(),
            "run_dir": str(run_dir),
            "repository": str(repo),
            "experts": [
                {"role": role, "provider": provider, "question": question}
                for role, provider, question in self.experts
            ],
        }
        self.test_results: list[dict[str, Any]] = []
        self.changed: set[str] = set()

    def select_experts(self) -> list[tuple[str, str, str]]:
        if self.quick:
            return []
        roles = [
            (
                "Software Engineer",
                "codex",
                "What is the smallest correct change and its failure test?",
            )
        ]
        if self.mode == "hack":
            roles.append(
                (
                    "Hackathon Strategist",
                    "claude",
                    "Which one demo moment earns the most rubric value within the stated deadline and sponsor stack?",
                )
            )
        else:
            roles.append(
                (
                    "Product Engineer",
                    "claude",
                    "What observable user outcome matters, and what should remain out of scope?",
                )
            )
        return roles

    def save(self) -> None:
        target = self.run_dir / "run.json"
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2) + "\n")
        os.replace(temporary, target)

    def event(self, phase: str, action: str, **details: Any) -> None:
        self.state.update(current_phase=phase, next_build_action=action)
        self.save()
        with (self.run_dir / "events.jsonl").open("a") as output:
            output.write(
                json.dumps({"time": time.time(), "phase": phase, "action": action, **details})
                + "\n"
            )
            output.flush()
        print(f"[{phase}] {action}", flush=True)

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return self.runner.run(["git", *args], cwd or self.repo)[1].strip()

    def dirty(self) -> str:
        return self.git(
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            ".",
            ":!.institutional-workbench",
        )

    def ask(self, phase: str, provider: str, context: dict[str, Any], schema: type[T]) -> T:
        self.runner.check()
        if self.state["calls"] >= self.state["max_calls"]:
            raise Blocked("Model-call cap reached; no further consultation")
        self.state["calls"] += 1
        self.event(phase, f"{context.get('role', schema.__name__)} · {provider}", provider=provider)
        prompt = json.dumps(
            {
                "objective": self.objective,
                "policy": POLICIES[self.mode],
                "reasoning": REASONING,
                **context,
            }
        )
        result = self.provider.ask(provider, prompt, schema)
        (self.run_dir / "reports" / f"{self.state['calls']:02d}-{schema.__name__}.json").write_text(
            result.model_dump_json(indent=2)
        )
        self.event(phase, f"{provider} finished", usage=getattr(self.provider, "last_usage", {}))
        return result

    def snapshot(self, directory: Path) -> dict[str, str]:
        paths = self.git(
            "ls-files", "--cached", "--others", "--exclude-standard", cwd=directory
        ).splitlines()
        snapshot: dict[str, str] = {}
        size = 0
        for name in paths:
            path = directory / name
            if path.is_symlink() or not path.is_file():
                continue
            if any(part.startswith(".") for part in Path(name).parts) or path.suffix in {
                ".pem",
                ".key",
                ".lock",
            }:
                continue
            if path.stat().st_size > 60_000:
                continue
            try:
                content = path.read_text()
            except (UnicodeError, OSError):
                continue
            if "\x00" in content:
                continue
            size += len(content)
            if size > 180_000:
                raise Blocked(
                    "Repository snapshot exceeds 180k characters; use a smaller target repository"
                )
            snapshot[name] = content
        return snapshot

    def test_commands(self) -> None:
        if self.commands:
            return
        python = self.repo / ".venv/bin/python"
        executable = str(python) if python.is_file() else sys.executable
        if (self.work / "tests").is_dir():
            contents = "\n".join(
                path.read_text() for path in (self.work / "tests").glob("test*.py")
            )
            self.commands = (
                [[executable, "-m", "pytest", "-q"]]
                if "pytest" in contents
                else [[executable, "-m", "unittest", "discover", "-s", "tests", "-v"]]
            )
        elif (self.work / "package.json").is_file():
            package = json.loads((self.work / "package.json").read_text())
            if "test" in package.get("scripts", {}):
                self.commands = [["npm", "test"]]
        if not self.commands:
            raise Blocked('No test command detected. Retry with --test "your acceptance command"')

    def test(self) -> bool:
        self.event("5/7 TEST", "Running frozen acceptance commands")
        self.test_results = []
        for command in self.commands:
            code, out, err = self.runner.run(command, self.work, timeout=120, require_success=False)
            result = {"command": command, "exit_code": code, "output": (out + err)[-20000:]}
            self.test_results.append(result)
        (self.run_dir / "output/tests.json").write_text(json.dumps(self.test_results, indent=2))
        return all(
            item["exit_code"] == 0 and "Ran 0 tests" not in item["output"]
            for item in self.test_results
        )

    def apply(self, files: list[FileChange], *, protected: set[str] | None = None) -> None:
        names = [change.path for change in files]
        if len(names) != len(set(names)):
            raise Blocked("Duplicate paths in builder output")
        for change in files:
            path = Path(change.path)
            target = self.work / path
            if (
                path.is_absolute()
                or path.as_posix() != change.path
                or ".." in path.parts
                or not path.parts
                or any(part.startswith(".") for part in path.parts)
                or path.suffix in {".pem", ".key"}
                or target.is_symlink()
                or any(
                    parent.is_symlink() for parent in target.parents if self.work in parent.parents
                )
                or self.work.resolve() not in target.resolve().parents
                or change.path in (protected or set())
            ):
                raise Blocked(f"Refusing protected or escaping file path: {change.path}")
        for change in files:
            target = self.work / change.path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(change.content)
            self.changed.add(change.path)

    def run(self) -> dict[str, Any]:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "reports").mkdir(exist_ok=True)
        (self.run_dir / "output").mkdir(exist_ok=True)
        try:
            self.event("1/7 INSPECT", "Inspecting repository")
            if self.dirty():
                raise Blocked(
                    "Target repository has uncommitted work. Commit or stash it yourself before running; no files changed."
                )
            base = self.git("rev-parse", "HEAD")
            self.state["base_commit"] = base
            self.git("worktree", "add", "--detach", str(self.work), base)
            self.test_commands()
            before = self.snapshot(self.work)
            reports = []
            for role, provider, question in self.experts:
                reports.append(
                    self.ask(
                        "2/7 INDEPENDENT",
                        provider,
                        {"role": role, "jurisdiction": question, "snapshot": before},
                        ExpertReport,
                    ).model_dump()
                )
            # All initial reports exist before any peer report is revealed.
            challenges = []
            for role, provider, question in self.experts:
                challenges.append(
                    self.ask(
                        "2/7 CHALLENGE",
                        provider,
                        {
                            "role": role,
                            "jurisdiction": question,
                            "reports": reports,
                            "instruction": "One flaw/disagreement/missing fact only. No new round.",
                        },
                        Challenge,
                    ).model_dump()
                )
            decision = self.ask(
                "3/7 DECIDE",
                self.builder if self.quick else self.reviewer,
                {
                    "snapshot": before,
                    "reports": reports,
                    "challenges": challenges,
                    "acceptance_commands": self.commands,
                    "instruction": "Freeze deliverable, scope and testable acceptance now. Preserve disagreement. Build next; no more analysis.",
                },
                Decision,
            )
            if (
                challenges
                and any(
                    c["disagreement"].strip().lower() not in {"", "none", "no disagreement"}
                    for c in challenges
                )
                and not decision.disputed
            ):
                raise Blocked("Decision erased specialist disagreement")
            self.state.update(
                deliverable=decision.deliverable,
                acceptance_criteria=decision.acceptance_criteria,
                decision=decision.model_dump(),
            )
            context = {
                "snapshot": before,
                "decision": decision.model_dump(),
                "acceptance_commands": self.commands,
                "instruction": "BUILD NOW. Return complete contents of only changed files, plus relevant tests. No deletions, hidden files, new dependencies or unrelated features. Never weaken existing tests. No prose-only deliverable.",
            }
            build = self.ask("4/7 BUILD", self.builder, context, BuildTask)
            if build.question:
                answer = self.ask(
                    "4/7 FOCUSED HELP",
                    self.reviewer,
                    {
                        "question": build.question,
                        "snapshot": before,
                        "decision": decision.model_dump(),
                    },
                    ExpertReport,
                )
                build = self.ask(
                    "4/7 BUILD", self.builder, {**context, "answer": answer.model_dump()}, BuildTask
                )
                if build.question:
                    raise Blocked("Builder still blocked after its one focused question")
            if not build.files:
                raise Blocked("Builder returned no implementation")
            # Existing tests are coordinator-owned acceptance evidence; builder may add tests.
            protected = {
                name
                for name in before
                if Path(name).name.startswith("test") or "/tests/" in f"/{name}"
            }
            self.apply(build.files, protected=protected)
            passed = self.test()
            qa = self.ask(
                "6/7 RED TEAM",
                self.builder if self.quick else self.reviewer,
                {
                    "decision": decision.model_dump(),
                    "snapshot": self.snapshot(self.work),
                    "diff": self.git("diff", cwd=self.work),
                    "test_results": self.test_results,
                    "instruction": "Review ACTUAL implementation against acceptance. One pass. Only critical/high-value blockers. If critical findings require repairs, supply independent regression test files runnable by the frozen commands. Do not reopen architecture.",
                },
                QAResult,
            )
            if qa.verdict == "BLOCKED":
                raise Blocked("QA blocker: " + "; ".join(qa.critical_findings))
            if not qa.acceptance_met and not qa.regression_tests:
                raise Blocked(
                    "QA could not establish acceptance; no executable regression evidence was supplied"
                )
            if qa.regression_tests:
                if any(not change.path.startswith("tests/test") for change in qa.regression_tests):
                    raise Blocked("QA may add only tests/test* regression files")
                self.apply(qa.regression_tests, protected=set(self.snapshot(self.work)))
                protected.update(change.path for change in qa.regression_tests)
                passed = self.test()
            if qa.critical_findings and not qa.regression_tests:
                raise Blocked(
                    "QA found critical issues without executable regression evidence: "
                    + "; ".join(qa.critical_findings)
                )
            needs_fix = not passed or qa.verdict == "FIX" or not qa.acceptance_met
            for _ in range(2):
                if not needs_fix:
                    break
                self.state["repairs"] += 1
                fix = self.ask(
                    "FIX",
                    self.builder,
                    {
                        "decision": decision.model_dump(),
                        "snapshot": self.snapshot(self.work),
                        "test_results": self.test_results,
                        "qa": qa.model_dump(),
                        "instruction": "Fix only the listed blockers. Existing and QA tests are immutable. Return full changed file contents; no architecture reopening.",
                    },
                    RepairResult,
                )
                self.apply(fix.files, protected=protected)
                build = fix
                passed = self.test()
                needs_fix = not passed or not set(qa.critical_findings) <= set(
                    fix.resolved_findings
                )
            if needs_fix:
                raise Blocked(
                    "Acceptance still fails after two repair cycles. See output/tests.json"
                )
            self.runner.check()
            if self.dirty() or self.git("rev-parse", "HEAD") != base:
                raise Blocked(
                    "Original repository changed during the run; verified result remains in isolated workspace"
                )
            self.git("add", "--intent-to-add", "--", *sorted(self.changed), cwd=self.work)
            if (
                set(self.git("diff", "--name-only", "HEAD", cwd=self.work).splitlines())
                - self.changed
            ):
                raise Blocked(
                    "Acceptance commands changed unrelated tracked files; refusing delivery"
                )
            patch = self.runner.run(["git", "diff", "--binary", "HEAD"], self.work)[1]
            if not patch.strip():
                raise Blocked("No deliverable diff exists")
            patch_path = self.run_dir / "output/delivery.patch"
            patch_path.write_text(patch)
            self.runner.run(["git", "apply", "--check", str(patch_path)], self.repo)
            self.runner.run(["git", "apply", str(patch_path)], self.repo)
            changed = self.git("diff", "--name-only", "HEAD", cwd=self.work).splitlines()
            self.state.update(
                status="DELIVERED",
                files_changed=changed,
                tests=self.test_results,
                run_command=build.run_command,
                limitations=build.limitations + qa.limitations,
                pitch_outline=build.pitch_outline,
                fallback=build.fallback,
                patch_sha256=hashlib.sha256(patch.encode()).hexdigest(),
            )
            self.event("7/7 DELIVERED", build.summary)
        except (Blocked, OSError, ValueError) as exc:
            self.state.update(status="BLOCKED", current_blocker=str(exc))
            self.event("BLOCKED", "Resolve the concrete blocker, then start a fresh bounded run")
        self.state["elapsed_seconds"] = round(time.time() - self.state["started"], 1)
        self.save()
        return self.state
