# Institutional Workbench

A personal Python CLI that uses Claude and Codex to decide, build, test and deliver
small repository changes. No browser or manual agent coordination.

## Try v0.2 without changing the stable installation

Requires Python 3.11+, Git, uv, and logged-in local Claude and Codex CLIs.
Developed against Claude 2.1.270 and Codex 0.154.0.

Stable main is frozen at `0a6da5dba7dbf44082c02c451ab85e41f0b1ecd6`, tag
`v0.1.0`. This checkout is the **experimental `v0.2-dynamic-routing` branch**.
Do not install it over the global `inst` tool. Use its isolated project environment:

```sh
uv run --project /Users/leonardaarons-ditson/Documents/Codex/institutional-workbench-v0.2 inst engineering "TASK" --repo /absolute/target/repo --explain-routing
```

On another machine, clone the experimental branch separately and replace that
`--project` path with your clone. No merge into main is required.

## Use

Enter a clean Git repository with an initial commit and installed test dependencies:

```sh
uv run --project /path/to/v0.2 inst engineering "Add a health endpoint and test it."
uv run --project /path/to/v0.2 inst hackathon "Three hours. Build X. Rubric: ... Sponsor stack: ..."
uv run --project /path/to/v0.2 inst economy "Rename the API field with exhaustive tests"
uv run --project /path/to/v0.2 inst economy "Run existing tests"
uv run --project /path/to/v0.2 inst dev "Implement X" --builder claude --reviewer codex
uv run --project /path/to/v0.2 inst dev "Implement X" --no-routing
uv run --project /path/to/v0.2 inst status
uv run --project /path/to/v0.2 inst cancel
```

`dev` aliases engineering; `hack` aliases hackathon. The global, stable `inst`
continues using v0.1. `--no-routing` reproduces the original fixed-provider path:
Claude Sonnet builds, Codex Terra decides/reviews, two independent experts.
`--quick` uses one selected provider without a roundtable.

Engineering balances correctness, reliability, time and relative inference cost.
Economy selects the lowest-cost sufficiently capable configured route; routine,
strongly verified work skips the roundtable. Hackathon sets monetary cost weight
to zero and prioritises quality/reliability/speed, with rubric, pitch and fallback
instructions. It still obeys the same deadline and call limits.

Overrides: `--builder claude|codex`, `--reviewer claude|codex`,
`--claude-model MODEL`, `--codex-model MODEL`, `--minutes 20`, `--explain-routing`.
Provider pins constrain the relevant routes. Explicit model identifiers remain
unclassified and are never silently upgraded; failure blocks if escalation would
violate the override. Use `--no-routing` for original same-model repair behaviour.

## Specialists and routing

One compact keyword-based TaskProfile selects 2–4 relevant lenses: Physicist,
Mathematician, Statistician, Data Scientist, Software Engineer, Systems Engineer,
Product Engineer, UX / Human Factors, Security / Reliability and Hackathon
Strategist / Judge. Each receives its jurisdiction and a concrete question.
Roles are distinct from providers/models. Reports remain independent until all
have committed; only one challenge round precedes the frozen decision.

The transparent scoring/registry lives in `routing.py`. Its capability, speed,
reliability and cost ranks are **configured heuristic priors, not benchmarks or
measured success probabilities**. Model access depends on your account; registry
membership is not a successful authentication check.

| Provider | Configured model | Tier |
| --- | --- | --- |
| Claude | haiku | 1 |
| Claude | sonnet | 2 |
| Claude | opus | 3 |
| Codex | gpt-5.6-luna | 1 |
| Codex | gpt-5.6-terra | 2 |
| Codex | gpt-5.6-sol | 3 |
| Codex | gpt-6-astra | 4 |

Tier 0 currently supports only explicit test-only objectives such as `Run existing
tests`: execute frozen tests and stop with no models or edits. Arbitrary renames
are not falsely treated as deterministic. Model/schema/evidence failures may
escalate once to the next populated tier; a failed implementation escalates the
builder locally during the existing repair allowance. No same-tier retry loop,
no project-wide upgrade, no restart of the roundtable. At the top tier or under a
fixed model override, an unresolvable failure stops the run.

Calls stay serial to preserve the proven cancellation/audit path. Provider
diversity is a small preference, not a quota: hackathon may select the same fast
model for every independently prompted specialist. The profiler does not fully
understand language or negation and can misclassify tasks; inspect its explanation.
Having a test command is a verification signal, not proof of exhaustive coverage.

Test commands are frozen before implementation. They are argument lists, not
shell scripts; use a checked-in script for pipes or compound commands.
Without `--test`, the CLI detects Python unittest/pytest under tests/, or npm test.
Install dependencies yourself first. Commands run in the isolated checkout;
the original repository's .venv/bin/python is reused when available.

## Delivery and limits

- Default 15 minutes/run, 90 seconds/model call, 120 seconds/test command.
- Maximum 16 model invocations, four specialists, one challenge round, one QA pass,
  two repair cycles and one focused builder question.
- Fixed control flow prevents another analysis round after the decision.
- Model output is schema-validated. The host writes complete changed text files.
  Models are instructed to use no tools; CLI tool attempts are rejected.
- Builds and tests run in an isolated Git worktree. The original must remain clean
  and at the same commit before a checked patch is applied. No reset, stash, commit,
  merge or push is performed on the target repository.
- Existing tests and independent QA regression files cannot be edited by the builder.
  QA critical findings require executable regression evidence; otherwise the run blocks.
- Success means acceptance commands passed and the bounded QA/repair gate completed.
  It is not proof of arbitrary user intent or production suitability.
- Ctrl+C or inst cancel terminates the current process group. Failed work is retained.
  There is no resume command: resolve the blocker and start a fresh bounded run.

Evidence lives in .institutional-workbench/RUN_ID/: run.json, events.jsonl,
reports/, output/tests.json, output/delivery.patch, and workspace/.
Routed runs also persist `invocations.json`: selected model and role, task profile,
reason and alternatives, escalation, start/end/latency, schema status, available
token usage, and builder test results. `null` means unavailable/not applicable.
Claude's model usage may include auxiliary models outside workbench control.
CLI-reported cost estimates are recorded separately from **unknown actual marginal
subscription spend**. Codex selected model is recorded; resolved server identity
is unavailable where the CLI does not expose it. No prices are invented.
Add .institutional-workbench/ to the target project's .gitignore before committing.
Only intended edits are delivered; generated caches are excluded.

This is a small-repository tool: 180k characters of visible source maximum.
Text files above 60k, binaries, hidden files and key files are skipped. No file
deletion, dependency installation or hidden-file editing. Test commands are
locally trusted code, not a security sandbox. Models see selected repository text.

## Development checks

```sh
uv sync --python 3.11
uv run python -m unittest discover -s tests -v
uvx ruff check src tests
uvx mypy --python-executable .venv/bin/python src
uv build
```

Normal tests mock model responses but use real temporary Git repositories,
test subprocesses, file edits, cancellation and patch delivery.
See VERIFICATION.md for historical v0.1 evidence; V02_VERIFICATION.md records this
branch's separate checks and bounded smoke outcomes.

## Research boundary

The separate [institutional-ai](https://github.com/retinapeg/institutional-ai)
research repository is frozen. Verified MVP main:
`5839bc65e2f041615d3256e9ce38bcd3c091d58a`.
Unfinished research preserved on codex/live-workers-v1:
`7c3cd71ff4b2f00bd206b049d80982bdc58f7187`.
This workbench reuses concepts, not that architecture. See FUTURE.md for deferred work.
