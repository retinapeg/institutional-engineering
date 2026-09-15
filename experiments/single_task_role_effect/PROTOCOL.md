# Preregistration: single-task role effect, v1

This document, the candidate tasks, graders, extraction rule, code and calibration schedule
must be committed before calibration. Selected task and full schedule must be committed
before the first full-study call. No grader or criterion changes after inspecting outputs.

## Question and controls

Does mathematical intellectual jurisdiction improve correctness beyond generic rigor or
an irrelevant but serious Product Engineer constitution? One model only: Codex gpt-5.6-terra,
medium effort. Four conditions: baseline (no role), generic expert, Mathematician, Product
Engineer. Exact wrappers are in design.py and protocol.json. All common instructions and
underlying task bytes are identical across study calls. Only the wrapper varies. Each call
is a fresh ephemeral context; no peers, tools, files, web, skills or previous answers.
Only visible final output is retained, never hidden reasoning events.

## Candidate selection, BEFORE inference

Three fixed finite optimisation candidates: weighted independent set (12 vertices),
two-resource constrained knapsack (12 items), constrained assignment (6 by 6).
Ground truths use exhaustive enumeration, independently checked in deterministic tests.
Data and precise constraints are generated into candidates/*.json and *.txt before calls.

Exactly 20 baseline calls per candidate, at most 60 total. Interleave one of each candidate
per calibration block in seeded random order. No role-conditioned calibration calls.
All runtime failures count against the fixed denominator 20. Eligible: at least 19/20
parseable responses AND 7–17/20 end-to-end correct (inclusive). Choose the eligible candidate
closest to 13/20 correct; ties break by lexical task_id, not judgment about model outputs.
No eligible candidate => BLOCK full study. Do not mutate tasks, add candidates, relax the
rule or repeat calibration. A new protocol would require explicit approval.
Calibration data are never included in full-study estimates. Calibration rate is noisy and
selected, not a guaranteed baseline rate. All 60 terminal observations are required to select.

## Output and scoring

Request FINAL_ANSWER: <integer>, optional <=120-word visible summary. Final integer only
is sufficient. Predefined extractor ignores backticks/bold Markdown, allows grouped thousands,
case variation, final punctuation and repeated identical labelled answers. Conflicting or
malformed FINAL_ANSWER labels are protocol failures. Without this label, accept a bare final
integer or final 'Answer: N' / 'The answer is N' line. Other prose is not manually reinterpreted.
Protocol validity means unambiguous extraction; substantive correctness is exact equality to
the external frozen integer oracle. Runtime success is separate. No subjective judge or repair.

## Freeze and schedule

Copy selected candidate task bytes verbatim to task.txt; SHA256 in protocol.json and
task_sha256.txt. Assert hash before every call. Generate all 250 blocks, each containing
the four conditions once, with seed 2026091501 and independently shuffled within-block order.
Save schedule.json and its SHA256 in protocol.json before full inference. Zero-based block,
call and condition-order indices. No reordering on resume. Any task/code/wrapper/schedule
hash change blocks execution. Random schedule seed is NOT a model sampling seed.

## Runtime, budget and recovery

1000 full calls maximum, 60 calibration maximum; serial concurrency 1 throughout. Ninety-second
per-call timeout, 1 MiB stdout/stderr cap, two-second terminate/kill grace via the frozen bounded
runner. One invocation per cell. Request CLI retry counts zero where supported; opaque
provider-internal behaviour cannot be independently guaranteed. No model substitution.
Record exact CLI version; mismatch blocks study, rather than silently changing it mid-run.
Temperature, model sampling seed, resolved server model and context size are UNAVAILABLE
when not exposed. Record tokens where exposed, but actual marginal monetary cost UNKNOWN.
No purchases, quota resets, new accounts, altered settings or additional providers.

Durable reservation BEFORE each call, then atomic terminal observation and immediate JSONL
refresh. Interrupted reservation becomes an INTERRUPTED observation; never reissue it.
Unique key: experiment_id/block/condition (calibration uses candidate instead of condition).
Single-process file lock. Preserve all failures. Rate limit/auth failures stop the batch safely;
explicit later resume skips the failed cell. A local cancel file/SIGINT/SIGTERM stops safely.
Partial blocks stay in descriptive marginal estimates and are excluded from paired contrasts.

## Analysis, fixed before outcomes

A. End-to-end: correct completed observations / all terminal observations, including runtime,
protocol and interrupted failures. Until complete, report both observed and planned counts;
unattempted calls are missing, not failures.
B. Substantive: correct / successfully parsed, runtime-successful responses.
Wilson 95% intervals for both. Report protocol success separately from correctness.
Contrasts: matched-baseline, generic-baseline, mismatched-baseline, matched-generic,
matched-mismatched. Paired complete-block bootstrap, 10000 draws, seed 872341, percentile
2.5%/97.5% intervals; preserve four-condition block pairing and report complete block count.
For conditional contrasts, recompute parsed denominators within each resample; skip draws
with zero required denominator and report valid draw count. Fewer than two complete blocks:
no bootstrap interval. No manual probability normalization or p-value-only claims.
Unadjusted exploratory intervals, no multiplicity/significance claim. Degenerate empirical
bootstrap intervals do not establish certainty. Temporal dependence across blocks and opaque
provider updates may narrow intervals unjustifiably; report that limitation.

## Interpretation limits

One task, one model, selected difficulty; not broad scientific evidence or router training.
The central controls are matched-versus-generic and matched-versus-mismatched. Any generic
instruction gain is not specialist specificity. Wrappers differ in length and details as well
as identity, so this tests these complete interventions, not a purified role-label-only effect.
Pilot 0 remains untouched. No product routing, architecture or production behaviour changes.
