# Calibration v1 — infrastructure failure, not model performance

Preregistration commit: e2ac1302cc56fd499db2e367a8a4a024c808ef51.
Committed and pushed before the first attempted inference.

2026-09-15 11:15:10–11:15:23 UTC: 60 reserved calibration CLI attempts, 20 per candidate.
All terminal observations have PROVIDER_ERROR and empty response text. Zero model responses,
zero parseable answers, no selected task. Provider-call latency sums to 0.924 seconds; wall
time includes hash/Git checks. No inference success, usage or monetary charge is claimed.
Full experiment: 0/1000 calls. No full-task or full-schedule hash exists because selection failed.

## Root cause and responsibility

The new harness added these two unsupported CLI configuration overrides:

```
model_providers.openai.request_max_retries=0
model_providers.openai.stream_max_retries=0
```

A read-only local configuration probe reproduces the failure without model inference:

```
codex -c 'model_providers.openai.request_max_retries=0' \
  -c 'model_providers.openai.stream_max_retries=0' features list
```

Exit 1: "model_providers contains reserved built-in provider IDs: `openai`.
Built-in providers cannot be overridden."
The same `codex features list` without these overrides exits 0. Runtime: codex-cli 0.154.0.
All study invocations contain the rejected configuration, consistent with immediate bootstrap
failure before model execution. Original per-call stderr was deliberately not retained, so
individual failure messages cannot be retrospectively reconstructed. Do not fabricate them.

This was a harness implementation mistake. Mock tests validated scheduling, persistence and
grading but did not validate these new options against the real CLI configuration loader.
The already-proven product adapter does not contain these options and its separate live
engineering smoke passed. No account setting was modified and no login is required to fix this.

## Scientific handling

All 60 failed reservations/observations remain immutable. No retries or replacements were run.
selection.json mechanically reports 0/20 end-to-end successes and 0/20 valid responses for
every task. These are infrastructure failures, NOT a 0% mathematical-reasoning estimate and
NOT evidence of a floor effect, role effect or task difficulty. Conditional correctness is
undefined. The full study is BLOCKED under the committed selection rule.

The current code/protocol are preserved to reproduce this failure. A future amendment should
remove the two rejected overrides, test configuration loading without inference, and explicitly
acknowledge opaque CLI-internal retry behaviour. It must use a distinct experiment ID/output
location, preserve this batch and obtain approval for a new calibration allocation. No extra
calls or protocol changes are authorized by this report itself.

## Checks and boundaries

27 deterministic tests passed, Ruff lint/format passed, strict mypy passed (18 files), package
build passed before calibration. They are not evidence that unsupported CLI flags work.
Pilot 0 source/graders/data and fingerprint remain byte-identical to the source benchmark.
Product frozen at f04071b7129b6a2f19185915d0be3242e1d74341 / v0.2.0, unchanged afterward.
No background study or follow-up automation is running. No second calibration was started.
