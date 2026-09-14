# v0.2 experimental verification — 2026-09-15

## Stable version preserved

- Repository: retinapeg/institutional-workbench.
- Main and peeled v0.1.0 tag: `0a6da5dba7dbf44082c02c451ab85e41f0b1ecd6`.
- Original suite rerun before tagging: 14 passed.
- Annotated tag object: `f17388094511a3e67112c9e5b543187701d91f4d`; pushed without overwrite.
- Stable checkout: `/Users/leonardaarons-ditson/Documents/Codex/institutional-workbench`.
- Global editable `inst` remains v0.1.0 pointing at that stable checkout.
- Experiment: separate physical worktree `institutional-workbench-v0.2`, branch
  `v0.2-dynamic-routing`. No merge to main or edits to institutional-ai.

## Scope and deterministic evidence

One routing module adds profiles, role lenses, model registry and transparent
scores beside the existing orchestrator. Seven source modules total, no new runtime
dependencies. No parallel scheduler, UI or provider expansion.

Verification commands:

```sh
uv run python -m unittest discover -s tests -q
uvx ruff check src tests
uvx ruff format --check src tests
uvx mypy --python-executable .venv/bin/python src
uv build
```

28 unique tests pass (14 original + 14 routing tests). Lint, format check, strict
type check and wheel/source-distribution builds pass. Test cases cover domain
selection and irrelevant-role exclusion, cap4, mode differences, role/model
separation, override forwarding, lowest sufficient economy tier, hack cost0,
bounded schema-failure escalation, failed-test builder escalation, deadline
termination, Tier0 bypass, unchanged fixture main/tag, telemetry, initial
independence, legacy provider flow and existing delivery/QA/repair protections.
Mocks validate policy/control flow; they do not establish real model quality.

## Exactly three smoke runs; no further live retries

Disposable fixtures: `/private/tmp/inst-v02-smoke.nebIVU/`.
Each has independent Git history, a greeting function and an immutable baseline
unittest. No user project was used. Building runs were capped at six minutes;
economy at one minute. Existing limits remain 90s per model call, 16 calls per run,
one challenge, one QA pass and at most two repairs.

| Mode | Result | Seconds | Calls | Repairs | Host checks |
| --- | --- | ---: | ---: | ---: | --- |
| Engineering | BLOCKED safely | 144.6 | 6 | 0 | No acceptance execution reached |
| Economy | DELIVERED | 0.1 | 0 | 0 | 1 existing unittest passed |
| Hackathon | DELIVERED | 130.3 | 9 | 0 | 2 unittests passed; demo also executed independently |

### Engineering

Run: `engineering/.institutional-workbench/20260915-001436`.
Objective: add farewell(name), preserve greeting and add a unittest.
Selected models: Codex gpt-5.6-terra tier2 and Claude sonnet tier2.
Independent roles: Software Engineer and Data Scientist. The latter was an
incorrect keyword match on “no other features”; this smoke exposed the issue.
The selector now matches feature engineering/selection instead of generic
“features”, with a regression case. Final selector chooses Software/Product.

Both independent reports, challenge round and decision completed. Claude's build
included edits to protected `tests/test_app.py`. Host protection rejected it;
no source-repository changes were delivered. The final build instruction now
explicitly requires NEW test files rather than merely “never weaken tests”.
That prompt clarification is deterministic-tested but **not live-revalidated**.
This is not a successful engineering delivery.

### Economy

Run: `economy/.institutional-workbench/20260915-001447`.
Objective: exactly `Run existing tests`. Deterministic profile recognised a
read-only verification request, selected no specialists/models, executed the
frozen test command and stopped. This proves Tier0 bypass, not cheap-model
implementation quality. Low-cost model routing is covered by mocks only.

### Hackathon

Run: `hackathon/.institutional-workbench/20260915-001502`.
Synthetic rubric: runnable demo70%, clear presentation30%; greeting plus ASCII
star banner, Python standard library only. Roles: Software Engineer, Hackathon
Strategist / Judge and Product Engineer. All routed to Codex gpt-5.6-sol tier3:
configured quality/speed beat the provider-diversity preference; cost weight0.
Nine calls: three independent, three challenges, decision, build and QA.
Delivered `demo.py` and `tests/test_demo.py`, with a pitch and fallback.

Independent post-delivery checks:

```sh
cd /private/tmp/inst-v02-smoke.nebIVU/hackathon
python3 -m unittest discover -s tests -v
python3 demo.py
git diff -- app.py tests/test_app.py
```

Both tests passed, the demo printed Hello, Ada! and the star banner, and the
protected baseline files had no diff. Some model-authored limitations still say
execution was unverified: those statements describe what the model itself did,
not the host-run evidence. No provider was allowed to execute tools. Host evidence
above is authoritative. The handoff does not yet reconcile those stale caveats.

## Model and cost evidence

- Live selected/working: Claude sonnet, Codex gpt-5.6-terra and gpt-5.6-sol.
- Claude reported resolved sonnet5 plus auxiliary haiku4.5 and fable5.1 usage;
  these internal provider calls are not independently controlled by the router.
- Other registry entries are configuration/catalog-backed, not live-validated
  in this iteration: Claude haiku/opus, Codex luna/astra.
- Routing quality, speed, reliability and relative cost are uncalibrated priors.
- Available token counts and Claude list-cost estimates are retained in
  invocations.json. Cache/advisor breakdowns remain in provider_metadata.
- Actual marginal monetary spend: **UNKNOWN**. No fabricated monetary prices.
- Evidence directories contain full invocation/report/test records locally;
  raw CLI metadata is not uploaded to GitHub.

## Remaining boundaries

Profiles are keyword heuristics, not semantic understanding. Test-command
availability is not a measurement of coverage. Serial specialists save scheduler
complexity but not wall time. Top-tier/explicit-model failures stop instead of
retrying the same failed route. Physics/statistics selection is tested; their
substantive scientific reasoning quality is not benchmarked. Live engineering
delivery remains unproven for this iteration. Stop here; no main merge.
