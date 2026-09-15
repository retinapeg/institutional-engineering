# Reproduce

Python 3.11+, uv, and authenticated local Codex CLI for live calls.
Checks require no models:

```sh
uv sync
uv run python -m unittest discover -s tests -q
uvx ruff check src benchmarks experiments tests
uvx mypy --python-executable .venv/bin/python src benchmarks experiments
uv build
```

Pilot 0's `benchmarks/results/` retains all 96 observations and failures.
`uv run python -m benchmarks.runner` displays its historical plan without calls.
Do not rerun or alter published observations. Original code remains in Git history.

New study:

```sh
uv run python -m experiments.single_task_role_effect.study prepare
# Commit protocol, candidates, graders and hashes BEFORE inference.
uv run python -m experiments.single_task_role_effect.study calibrate --live
uv run python -m experiments.single_task_role_effect.study freeze
# Commit selected task and schedule BEFORE full inference.
uv run python -m experiments.single_task_role_effect.study run --live
uv run python -m experiments.single_task_role_effect.study analyse
```

Maximum 60 calibration and 1000 full calls; serial, no retries. Resume the same command:
terminal observations/interrupted reservations are never reissued. A `cancel` file
in the experiment directory stops safely; remove it only to intentionally resume.
Rate/auth failures stop the batch. Investigate before explicit resume.
Frozen hashes and CLI version are checked before calls. No qualifying candidate means
BLOCKED, not an improvised task. Never run simultaneous study processes.

Only visible final text and allowlisted counters are retained. Temperature, model seed,
resolved model and context size are UNAVAILABLE unless reported; marginal cost UNKNOWN.
Opaque CLI/server retries and model updates remain limitations.

Method references: [NIST Wilson intervals](https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm)
and [official Codex non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode).
Neither establishes availability or marginal subscription pricing of the requested model;
those are recorded from the actual local run, not inferred from documentation.
