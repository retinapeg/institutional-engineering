# Exploratory institutional engineering benchmark

Exploratory descriptive evidence, not significance or causal generalisation. Protocol failures score zero; valid-only scores are also shown. Conditions are paired by task/model/repeat, not identical stochastic seeds.

Calls: 96; schema-valid: 63; failed: 33; unavailable without invocation: 0.
Objective full passes: 58; failure rate: 34.4%; wall seconds: 3931.14.

Primary matched − baseline: 0.12734375
Primary mismatched − baseline: 0.0296875
Primary Sonnet − Terra: -0.6598958333333333

## Primary by_model

| Group | n | Mean score | Mean seconds | Input / output tokens reported |
| --- | ---: | ---: | ---: | ---: |
| gpt-5.6-terra | 48 | 0.9698 | 12.91 | 551100 / 24290 |
| sonnet | 48 | 0.3099 | 72.84 | 6068 / 89521 |

## Primary by_condition

| Group | n | Mean score | Mean seconds | Input / output tokens reported |
| --- | ---: | ---: | ---: | ---: |
| baseline | 32 | 0.5875 | 43.61 | 182932 / 31821 |
| matched | 32 | 0.7148 | 41.80 | 184180 / 41161 |
| mismatched | 32 | 0.6172 | 43.22 | 190056 / 40829 |

## Primary by_domain

| Group | n | Mean score | Mean seconds | Input / output tokens reported |
| --- | ---: | ---: | ---: | ---: |
| mathematics | 24 | 0.4917 | 52.31 | 141997 / 13882 |
| physics | 24 | 0.7344 | 39.17 | 138911 / 47841 |
| software | 24 | 0.6250 | 47.76 | 138138 / 20641 |
| statistics | 24 | 0.7083 | 32.26 | 138122 / 31447 |

## Task effects (matched minus baseline)

- software_merge_intervals: +0.5000, n=4 paired observations.
- software_escaped_fields: +0.5000, n=4 paired observations.
- physics_lorentz: +0.2188, n=4 paired observations.
- math_independent_set: +0.0500, n=4 paired observations.
- math_cancellation: +0.0000, n=4 paired observations.
- stats_base_rate: +0.0000, n=4 paired observations.
- stats_leakage: +0.0000, n=4 paired observations.
- physics_symplectic: -0.2500, n=4 paired observations.

## Strong model score disagreements (absolute delta >= 0.25)

[
  {
    "task_id": "math_cancellation",
    "condition": "mismatched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "software_merge_intervals",
    "condition": "baseline",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "software_merge_intervals",
    "condition": "mismatched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_cancellation",
    "condition": "baseline",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "stats_leakage",
    "condition": "mismatched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_cancellation",
    "condition": "matched",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "physics_symplectic",
    "condition": "baseline",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "stats_base_rate",
    "condition": "mismatched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "stats_leakage",
    "condition": "baseline",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "stats_leakage",
    "condition": "mismatched",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_independent_set",
    "condition": "baseline",
    "repeat": 1,
    "sonnet_minus_terra": -0.8
  },
  {
    "task_id": "physics_lorentz",
    "condition": "mismatched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_independent_set",
    "condition": "mismatched",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_independent_set",
    "condition": "matched",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "software_escaped_fields",
    "condition": "matched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "stats_base_rate",
    "condition": "baseline",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "software_merge_intervals",
    "condition": "baseline",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "software_escaped_fields",
    "condition": "baseline",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_cancellation",
    "condition": "mismatched",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "physics_symplectic",
    "condition": "mismatched",
    "repeat": 2,
    "sonnet_minus_terra": -0.875
  },
  {
    "task_id": "software_escaped_fields",
    "condition": "mismatched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_independent_set",
    "condition": "mismatched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_independent_set",
    "condition": "matched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "physics_symplectic",
    "condition": "matched",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "stats_base_rate",
    "condition": "matched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "physics_lorentz",
    "condition": "baseline",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_cancellation",
    "condition": "baseline",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "physics_symplectic",
    "condition": "matched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_independent_set",
    "condition": "baseline",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "stats_leakage",
    "condition": "matched",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "math_cancellation",
    "condition": "matched",
    "repeat": 1,
    "sonnet_minus_terra": -1.0
  },
  {
    "task_id": "software_merge_intervals",
    "condition": "mismatched",
    "repeat": 2,
    "sonnet_minus_terra": -1.0
  }
]

## Boundaries

Eight synthetic tasks, two repetitions; no significance claims. All graders frozen before inference. No repair attempts. Role, model and task effects are not interchangeable. Lexical similarity is not latent reasoning. Secondary Sol tasks are selected, not an unbiased comparison with the whole primary suite. Provider aliases and auxiliary models may change; available metadata is retained. Actual marginal monetary spend UNKNOWN. Routing weights untouched.
