# Single-task role intervention study

Status: BLOCKED_CALIBRATION_INFRASTRUCTURE. 0/1000 full-study observations.

Calibration: 60 failed local CLI attempts, zero model responses. Unsupported retry-control
configuration caused bootstrap rejection. This is not evidence about model performance.
No task qualified; task.txt and the full 1000-call schedule are intentionally not frozen.
See CALIBRATION_FAILURE.md. A new calibration requires an approved protocol amendment.

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
