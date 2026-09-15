# Institutional Engineering benchmark lab

An exploratory, frozen synthetic experiment. Not a product mode or router update.

## Predeclared protocol

- Eight tasks, two each in physics, mathematics, statistics and software.
- Sonnet and gpt-5.6-terra; baseline/matched/mismatched; two repeats: 96 calls.
- Same task, response schema and concise instruction in every condition; only
  the constitution changes. Mismatched roles still seriously attempt the task.
- No tool use by models, no shared conversation, no previous answers revealed.
- Random cell order with fixed seed20260915, at most2 simultaneous calls. Separate
  adapter/runner instance per call. After two timeout/provider errors, serial.
- No retry or repair. A malformed/failed call is data. Explicit provider
  quota/auth failures circuit-break that provider; remaining cells are recorded
  UNAVAILABLE without new calls. Generic transient failures do not remove a model.
- Primary completion means all96 cells recorded. Secondary eligibility uses
  **protocol failure rate** (not objective score) below20%, plus >30min remaining.
  Lowest mean primary score ranks hardest; ties: greater score spread, high prior,
  task id. Four tasks, Sol baseline/matched, two repeats:16 additional calls.
- Default maximum112 external CLI invocations, absolute cap120, max3hours.
  Budget includes failures; CLI-internal auxiliary inference is separately reported
  where exposed and cannot be counted/controlled as independent workbench calls.
- Night deadline: 2026-09-15T04:16:43Z, three hours from initial preservation.

Task texts, ground truth, role assignments, grading methods and difficulty priors
are in tasks/tasks.json. Full grader criteria are committed before live execution;
models receive the task/specification, never hidden expected values or grader code.
Each scalar/subcheck has equal weight within its task. Tasks have equal weight
when averaged over the balanced primary matrix. A full objective pass means1.0.
Numeric tolerances are predeclared; tiny roots cannot pass as zero. Coding tasks
use frozen input/output/error/nonmutation/nonaliasing checks, not model-written tests.
No subjective judge or embeddings are used.

## Run or resume

From the separate benchmark worktree:

```sh
uv sync --python 3.11
uv run python -m benchmarks.runner
uv run python -m benchmarks.runner --live --deadline 2026-09-15T04:16:43+00:00
```

The first command lists the matrix without inference. The live command owns an
exclusive file lock. manifest.json durably reserves each task/model/condition/repeat
key BEFORE invocation. Completed records are immutable, atomically written and
immediately exported. Restart skips completed keys; orphaned reservations become
INTERRUPTED observations, never automatic repeats. The original deadline/cap
cannot increase on resume. A changed code/task fingerprint refuses mixed-protocol
resume. Touch benchmarks/results/cancel to stop new work and active model children.
No account settings, user repositories, production source or installed CLI change.

## Checks

```sh
uv run python -m unittest discover -s tests -v
uvx ruff check src benchmarks tests
uvx mypy --python-executable .venv/bin/python src benchmarks
```

14 new harness tests exercise loading, matrix/roles, ground-truth correctness,
code graders, restricted-code rejection, cap, concurrency, persistence/resume,
interruption, failure recording, metadata sanitisation and summary generation.
The28 existing tests remain unchanged.

## Safety and interpretation

Code is returned as one structured solution.py and tested in a disposable child.
The accepted language is pure functions with an AST/builtin allowlist; no imports,
reflection, arbitrary method access, file/network APIs or tools. CPU limit3s and
host timeout8s bound grading. macOS rejects memory rlimits on this machine: the
restricted grader is **not a general hostile-code memory sandbox**. Do not feed it
untrusted arbitrary repositories. It is solely for these small synthetic fixtures.

Only visible structured responses are saved. Raw provider streams (including
reasoning events), stderr, session/account identifiers and filesystem paths from
providers are not persisted. Usage uses an explicit numeric allowlist. Claude
auxiliary model names/token/list-cost estimates may be reported. Actual marginal
subscription cost is UNKNOWN. Latency includes CLI/model execution, excludes
post-response grading; provider caches and internal advisors can confound timing.

summary.json separates protocol success from objective passes and separates Sol's
selected secondary subset from the primary model effect. Failed cells score0;
schema-valid-only averages are also supplied. Lexical Jaccard is only a descriptive
role-consistency proxy, not a latent manifold or hidden-reasoning measurement.
Two repeats and eight tasks cannot establish statistical significance. Stable
provider aliases may hide model changes. Correct answers with altered language
do not prove better reasoning. No routing weights are changed from these results.

## Outputs

- results/responses.jsonl: full embedding-ready visible-response corpus, score,
  role/model/task/condition/repeat, latency/tokens and verification evidence.
- results/results.csv: flat analysis table.
- results/summary.json and results/SUMMARY.md: descriptive effects/failures.
- results/router_prior_suggestions.json: conservative suggestions ONLY.
- results/records/: durable one-result-per-key source records.
- results/manifest.json: frozen fingerprint, cap/deadline/reservations/secondary gate.

The product adapters and routing.py are reused read-only. Only this lab and its
tests are added on v0.3-benchmark-lab; nothing is merged.
