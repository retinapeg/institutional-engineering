# Observed results and interpretation boundaries

## Completion and verification

Protocol/code commit before inference: `e53fbfa65a847db1284ac90b93e92aef68215f67`.
Frozen fingerprint: `119af9ab89a24ddee3e323132757e59f4ffe20ded2b4c0d60350d8785100e8f5`.
The code, task texts, constitutions and graders did not change during the sweep.

- 96 unique completed observations:48 Sonnet,48 Terra;32 per condition.
- Eight tasks, three conditions, two repetitions. No repeated keys, retries or repairs.
- 63 schema-valid responses;58 full objective passes.
- 33 protocol failures:13 TIMEOUT,4 PROVIDER_ERROR,16 MALFORMED.
- Wall time:3931.14 seconds (65 minutes31 seconds), within the three-hour night budget.
- Sol secondary sweep skipped:34.375% primary protocol failure rate exceeds the <20% gate.
- 96 record files,96 JSONL rows and96 parsed CSV rows agree exactly.
- Every one of the63 schema-valid responses was independently regraded with the
  unchanged graders after live inference stopped; all stored scores reproduced.
- Harness plus regression suite:42 tests pass (14 new,28 unchanged); lint/format,
  strict typing of15 source files, and package build pass.
- Raw-data scan found no credential/account/session identifiers. Provider metadata
  is numeric-allowlisted; raw stderr and reasoning streams were not saved.

## Primary observed effects

Scores range0..1; failed protocol cells score0 under the predeclared rule.

| Condition | n | Mean score | Schema-valid | Full objective passes |
| --- | ---: | ---: | ---: | ---: |
| Baseline | 32 | 0.587500 | 20 | 18 |
| Matched | 32 | 0.714844 | 23 | 22 |
| Mismatched | 32 | 0.617188 | 20 | 18 |

Matched minus baseline:+0.127344 (12.73 percentage points).
Mismatched minus baseline:+0.029688 (2.97 points):no overall observed mismatch penalty.
These are paired by task/model/repeat, not identical stochastic seeds.

Largest matched gains were the two software tasks, both+0.50 across four paired
observations each. The largest matched decline was the oscillator task,-0.25.
Most of these differences reflect strict output-contract/completion outcomes,
not a demonstrated change in underlying scientific competence.

| CLI stack | n | Schema-valid | Full objective passes | Mean score, all calls | Mean observed seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| Codex gpt-5.6-terra | 48 | 48 | 44 | 0.969792 | 12.91 |
| Claude sonnet | 48 | 15 | 14 | 0.309896 | 72.84 |

Terra's statistical tasks scored1.0 on all12 observations, regardless of role.
All12 Sonnet mathematics observations failed at the protocol/process layer.
That is NOT evidence that Sonnet cannot do the mathematics. Valid-only averages
are0.969792 for Terra and0.991667 for Sonnet, but their different surviving task
mixes make this an unfair intrinsic-quality comparison. Both exhibit ceiling
effects on many successfully returned answers.

The32 large cross-model score gaps in summary.json are performance-outcome gaps,
mostly driven by missing/invalid Sonnet results, not32 substantive intellectual
disagreements. No statistical significance or general superiority is claimed.

## Important error distinctions

- 14 of16 malformed outputs were wrapped in Markdown fences. The other two
  exceeded the1800-character concise_method_summary limit. They were retained
  as visible text but were not normalised/retried/regraded into primary successes.
- Four provider errors were recorded as PermissionError near the per-call limit.
  A read-only process check during the run found only the active benchmark CLI,
  not leaked prior benchmark CLI processes. Their precise cause was not repaired
  or inferred; these remain process failures, not wrong domain answers.
- Both Terra mismatched oscillator repeats supplied the correct coefficient -0.6
  as `invariant_cross_coefficient_a`, instead of the frozen key
  `invariant_cross_coefficient`. Each scored0.875. The task's juxtaposition of the
  key and symbol a was ambiguous: this penalty must not be called a physics error.
- One matched Sonnet Lorentz answer rounded particle velocity to -0.384615. It was
  at the relative-tolerance boundary and failed the floating-point check, scoring
  0.875. This is a precision-contract artifact, not evidence of a wrong transform.
- One Terra baseline parser used `.join`, contrary to the explicitly allowed
  method list. The restricted-code gate rejected it without executing the tests.
  Its score0 reflects the task/tool-language constraint, not proven algorithmic failure.
- One substantive mathematical mistake did occur: Terra baseline repeat1 selected
  indices[1,3], weight10 for [4,5,4,5,4], rather than indices[0,2,4], weight12.
  Both matched and both mismatched Terra repeats found12. This is an interesting
  small observation, not evidence that only a matched Mathematician lens caused success.

No scoring criteria or stored primary scores were changed after seeing these issues.
Any later normalised/sensitivity analysis must be labelled post-hoc and preserved
separately from the frozen primary scores.

## Behavioural consistency and the 3D corpus

79 observations have nonempty visible response text. The17 timeout/process-failure
rows remain useful metadata but cannot supply an embedding. All96 rows have labels,
scores, latency and available usage. Embed response_text or selected visible method
fields, NOT the role labels, expected answers or grading metadata themselves.

The token-set Jaccard proxy has eight complete task/model groups, all Terra:
within-matched similarity exceeded matched-to-baseline similarity in3/8 groups;
mean difference=-0.02060. This does not show a consistent increase in lexical
within-role similarity. It is not semantic embedding evidence, and missing Sonnet
groups plus two repeats prevent a general conclusion about constitutions.

No embeddings, dimensionality reduction, UI, vector database or learned routing
were added. The corpus supports tomorrow's analysis without inventing a manifold tonight.

## Provider, timing and cost confounds

Local versions at launch:Claude Code2.1.272;Codex CLI0.154.0. Sonnet reported
claude-sonnet-5 plus internal claude-fable-5-1 and claude-haiku-4-5-20251001 usage.
The96-call cap refers to external benchmark CLI invocations; opaque internal
provider inference is not separately scheduled or fully counted by the lab.
No Astra, Opus or Sol was selected/invoked by this experiment.

This compares CLI stacks with their native/default system instructions and the
frozen adapter settings, not neutral standalone base models. Baseline means no
ADDED specialist constitution. Claude safe mode disables local customisations;
Codex ignores user configuration/rules and runs with tools disabled. Existing
provider-internal advisors and differences in effort/defaults remain confounds.

The first calls allowed concurrency2; after two provider/timeout failures the
predeclared fallback used serial calls. Timing is observed CLI wall latency,
excluding post-response grading; timeouts are censored, not completed responses.
No model settings or per-call limits were tuned after observing results.

Usage metadata is available for79 calls. The raw input-token counters are NOT
directly comparable: Claude separates cache reads/creation from fresh input,
whereas Codex reports cached input within its usage breakdown. Preserve and
normalise these provider-specific fields before cross-provider token comparisons.
Timeout/process-failure token consumption is unknown. Reported dollar estimates
are not subscription marginal spend. Actual marginal monetary cost:UNKNOWN.

## Preserved product state

- Main and v0.1.0:`0a6da5dba7dbf44082c02c451ab85e41f0b1ecd6`.
- v0.2-dynamic-routing:`f04071b7129b6a2f19185915d0be3242e1d74341`.
- Product src/, routing.py, pyproject.toml and uv.lock unchanged from v0.2.
- Global inst remains v0.1.0. Only v0.3-benchmark-lab is published; no merge.
- router_prior_suggestions.json contains conservative evidence summaries only.

Bottom line:there is an observed matched-role gain in strict delivery score,
but this small, ceiling-heavy, protocol-confounded experiment does not establish
that matched specialist constitutions generally improve underlying reasoning.
