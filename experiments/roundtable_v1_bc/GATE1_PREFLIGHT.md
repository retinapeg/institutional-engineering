# Gate 1 preflight — FAILED, no live calls

**STUDY_COMPLETE: NO**  
**Live qualification, calibration and main study: NOT STARTED.**

The implementation checks pass after a narrow package exclusion fix. Gate 1 still fails because candidate-generated observations can be forged, and the model-request/retry/token/worker boundary remains unqualified. Passing unit tests that reproduce a vulnerability does not clear that vulnerability.

## Gate table

| Required gate | Result | Evidence |
|---|---|---|
| Real CLI typed configuration loading, zero inference | PASS | `manifests/cli/doctor-valid.json` versus `doctor-invalid-type.json`: config.load `ok` versus `fail`, network denied. Both overall exits are 1 due to denied network health checks. |
| One model request per stage; aggregate request accounting | UNQUALIFIED | CLI capabilities audit; mock reservations prove local accounting only. |
| Zero implicit transport retries | UNQUALIFIED | No verified supported mechanism; reserved built-in provider overrides were not used. |
| Hard generation-token ceiling | UNQUALIFIED | Response-byte limits and token metadata do not prove a generation limit. |
| Complete model-worker tool and hidden-file isolation | UNQUALIFIED | Candidate sandbox probes pass, but this does not qualify Codex worker tools or filesystem visibility. |
| Adversarial grader observation integrity | FAIL | Three false passes in `manifests/preflight-v1/grader-integrity.json`. |
| Offline implementation checks | PASS | 31 new tests, 27 historical mock regression tests, lint, formatting, strict types, reference/defect checks and repaired package validation. |

`GATE1_PREFLIGHT.json` is the machine-readable summary copied from the final `manifests/preflight-v2/summary.json`. `manifests/preflight-v1/summary.json` preserves the original failed archive check. `manifests/package-fix-v2.json` records its repair. The complete v2 check also verifies calibration evidence-kind rejection, replay scoring identity and task-manifest hashes. Earlier raw receipts were not overwritten.

## What the tests establish

- **31 new tests passed**, including exact paired scheduling, jurisdiction-only substitution, strong generic reviewers, reviewer independence, builder decision-only handoff, visible-only one-repair transition, artifact preservation after failed repair, evaluator replay against the same hash, immutable attempt IDs, failure thresholds, durable concurrent mock reservations and provenance-checked synthetic analysis.
- **27 historical regression tests passed**, with model invocations mocked and temporary outputs. These are not resumed historical experiments.
- All **17 reference programs** pass public and hidden diagnostic evaluation; all **44 annotated defective controls** fail their targeted requirement.
- The analysis uses 100,000 paired swaps and 19,999 hierarchical bootstrap draws with distinct fixed seeds; nine synthetic analysis tests validate identity, pairing, effects, uncertainty and missing usage handling.
- Ruff 0.16.7 lint/format and mypy 2.3.1 strict checks pass across **17 new implementation/test files**. Frozen copied public task bytes were not reformatted. The separately exported CLI script also passed its own checks.
- The rebuilt wheel and source distribution exclude `.scratch-cli` and `.build`, preserve **87 task/catalog/evaluator files** byte-for-byte, and retain the implementation package. The only change outside the new study directory is the narrow exclusion list in research `pyproject.toml`.
- The macOS candidate boundary denies hidden/prior/credential/researcher file reads, symlink escape, network and fork. Wall-time and output caps are exercised. This does not enforce a hard resident-memory cap or metadata secrecy.

## Reproducible grader blocker

The diagnostic case requires returning the first list element without mutating the list. The ordinary mutating control correctly scores zero. Three malicious variants mutate the input and still score one:

1. Monkeypatch JSON serialization to hide the mutation.
2. Replace the observer's `x` through caller-frame globals.
3. Emit a forged observation and exit without returning normally.

Expected values stay in the trusted parent. The untrusted child controls the reported `input_after`, so keeping the oracle secret is insufficient. Prebinding a serializer, adding an import blacklist or filtering AST nodes is not a sound repair for unrestricted Python. `require_qualified()` and all live entry points refuse dispatch.

**Next engineering requirement:** provide an externally trusted observation boundary that can verify the public Python contract, then rerun these exact counterexamples. A contract-changing restriction requires a new protocol version; it cannot silently narrow the benchmark.

## Counts

| Phase | Planned institutions | Attempted | Completed | Evaluable artifacts | Failures | Model calls | Repair calls |
|---|---:|---:|---:|---:|---:|---:|---:|
| Live qualification | 5 | 0 | 0 | 0 | 0 | 0 / 30 max | 0 |
| Live calibration | 36 | 0 | 0 | 0 | 0 | 0 / 216 max | 0 |
| Main, conditional on eight qualifying domains | 128 | 0 | 0 | 0 | 0 | 0 / 768 max | 0 |

A **separate mock rehearsal** completed five institutions and 30 local stage invocations, including five forced repairs and 30 schema completions. The v1 and v2 verification receipts each retain a separate such mock rehearsal (60 local stage invocations in those two archives combined). Neither run used inference. The final rehearsal used **zero model calls** and does not satisfy live qualification. Diagnostic failures and adversarial counterexamples are preflight findings, not failed scientific observations.

## Preservation and publication scope

`manifests/preservation-audit.json` verifies **1,056/1,056 source files unchanged** in the audited preserved research snapshot. Six research worktrees were observed; the older dirty checkout and all existing branches were preserved. Product repositories and global Codex/Claude configuration were not modified.

The public checkpoint is based on existing public main `02aa0af04d790b3b362a39a1476793bc813ee40d`. The branch `roundtable-v1-bc-20260916-execution` publishes only this derivative and its build exclusions. The initial branch at the newer local source remains intact, so unpublished historical studies are not pulled into this publication.
