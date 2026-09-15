# Single-task role intervention study

Status: PENDING_OR_PARTIAL. 0/1000 terminal observations.

No role-specific conclusion is asserted from pending or preliminary data.

| Condition | End-to-end successes/n | Estimate | Parsed successes/n | Estimate |
|---|---:|---:|---:|---:|
| baseline | 0/0 | None | 0/0 | None |
| generic | 0/0 | None | 0/0 | None |
| matched | 0/0 | None | 0/0 | None |
| mismatched | 0/0 | None | 0/0 | None |

Wilson 95% intervals and paired block-bootstrap risk differences are in summary.json.
Central contrasts: matched − generic and matched − mismatched, not matched − baseline alone.

- Exploratory single-task study; no across-task generalisation.
- Wilson intervals assume independent repetitions; temporal dependence can understate uncertainty.
- Bootstrap preserves within-block pairing but treats different blocks as independent.
- Conditional estimates can be selected by protocol success; report end-to-end too.
- Unadjusted descriptive intervals, no p-value-based significance claims.
- Calibration-selected rate is noisy; full-study baseline is a fresh estimate.
- Wrappers differ in length/content; generic control does not isolate every prompt feature.
- CLI/server sampling, internal retries and server model revisions may be opaque.
