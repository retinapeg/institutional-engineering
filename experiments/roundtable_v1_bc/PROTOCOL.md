# Roundtable v1 — task-adaptive intellectual jurisdictions

**Experiment:** `roundtable-v1-bc-20260916-v1`  
**Status:** offline implementation; Gate 1 failed; no live observations.  
**Authority:** execution handoff preserved in `manifests/user-handoff.txt`. Its conditional authorization remains subject to every scientific and infrastructure gate.

## Question and estimand

Under one fixed model/runtime, institution, information architecture and resource policy, does task-adaptive jurisdiction guidance for two independent reviewers improve executable coding outcomes compared with competent generic reviewers?

The only conditions are **B, generic institution**, and **C, task-adaptive institution**. The primary effect is the equal-task average of each task's mean hidden score in C minus its mean in B. No single-agent arm, mismatched roles, extra model, dynamic model routing or LLM role selector is included.

This is a **budget-controlled** comparison. Realized calls, tokens, repairs, latency and failures must be reported separately. Exact realized compute matching is not assumed.

## Institution and information

1. Reviewer 1 receives the public task/repository and its jurisdiction. It sees no other report.
2. Reviewer 2 independently receives the same public task/repository and its jurisdiction. It sees no other report.
3. Challenger receives both reports and the public snapshot, and identifies disagreements, unsupported assumptions, omissions and likely failures.
4. Decision authority receives both reports, the challenge and public snapshot, and produces one frozen implementation decision.
5. Builder receives the public snapshot and **only that frozen decision**. It implements `solution.py` without reopening governance.
6. Visible behavioral verification runs. Only a visible failure permits one repair call, which receives public feedback, current code and the frozen decision. There is no second repair. Qualification may mechanically force this transition on non-study scenarios.
7. The latest produced artifact is frozen before any hidden grading. A failed repair preserves the builder artifact. Hidden results never reach a model.

Every call uses the same stage schema and correctness instructions across B/C. `prompts/` records those templates; runtime uses the matching constants in `harness/design.py`. Only the two reviewer jurisdiction strings differ. B reviewers receive competent senior engineering responsibilities covering requirements, correctness, edge cases, failure modes, maintainability and verification; C retains those common instructions and receives concise domain responsibilities. The role definitions are task independent, solution free and contain no hidden-test information.

## Fixed roles

`roles.json` defines exactly ten roles. `ROLE_MANIFEST.json` records the definition hash, mappings and mapping hash before any calibration or treatment.

| Domain | Reviewer 1 | Reviewer 2 |
|---|---|---|
| Numerical | numerical_methods | algorithms |
| Statistics | statistics | data_integrity |
| Defensive parser/security | security | api_protocol_engineering |
| Queue/idempotency | distributed_systems_reliability | data_integrity |
| ML evaluation | ml_data_science | statistics |
| Concurrency | performance_concurrency | distributed_systems_reliability |
| State invariants | algorithms | data_integrity |
| Protocol client | api_protocol_engineering | distributed_systems_reliability |

Both B reviewers use `general_software_engineering`. Five separately named synthetic qualification scenarios exercise B and C using the domain assignments recorded in `protocol.json`. Qualification scenarios cannot enter the benchmark catalog.

## Model and resources

Requested model: **gpt-5.6-terra**, Codex CLI **0.154.0**, reasoning **medium**. The installed binary and offline catalog are recorded in `CLI_PREFLIGHT.md` and `manifests/cli/`. The actual served model and account-serving availability are unobserved because no inference has occurred.

The fixed intended live policy is one request per stage, no retries, at most two institutions concurrently, logically sequential stages per institution, 90 seconds per stage and 600 seconds per institution. Prompt capture is bounded at 131,072 bytes; response capture at 1,048,576 bytes. The proposed hard generation ceiling is 8,192 tokens per stage. **Provider-request, retry, generation-token and model-worker isolation enforcement is not yet qualified.** These limits are requirements, not claims about the present CLI adapter. There is no live adapter in this checkpoint.

Do not add the reserved built-in OpenAI provider retry overrides that caused historical bootstrap failures. Zero-inference doctor controls verify real typed configuration loading; they do not verify serving or transport behavior.

## Task pack and scoring

There are twelve candidates across eight domains, with public task, initial `solution.py`, visible cases and executable visible-test script. Public bytes are copied from committed local research `9d4140afc76b4dcbcdb639a588f5d6d1721db2c5` and preserve file hashes. They have no dependency on that checkout at runtime. Hidden rubrics, reference programs and annotated defects are separate evaluator inputs.

The twelve candidates contain 91 hidden cases grouped into 39 meaningful requirements, with 39 targeted defective controls. Five non-study qualification scenarios add ten cases and five defective controls. Diagnostic checks require all 17 references to pass public and hidden cases and every one of the 44 controls to fail its annotated target requirement. These checks have passed; adversarial observation integrity has not.

Within a task, each requirement receives a frozen positive weight summing to one. It earns that weight only when **all** associated cases pass. Hidden cases are not independent experimental observations. Each selected task has equal aggregate weight regardless of case count. Float comparison uses relative tolerance `1e-12` and zero absolute tolerance unless the public specification defines another comparator; requirements and case definitions remain explicit.

The concurrency fixture models deterministic compare-and-swap interleavings, not real threaded scheduling. Candidates are small hand-authored/generated tasks derived from prior research. Ceiling effects are plausible; calibration is permitted to stop the study.

## Hard gates and execution budgets

### Gate 1 — deterministic implementation and infrastructure

Verify actual CLI configuration loading, OS isolation, schemas, serialization, hashing, schedules, public copying, sole jurisdiction substitution, visible verification, hidden isolation, repair transitions, evaluator replay, failure recording and durable budgets. Run unit/integration tests, lint, formatting, strict typing and package/build checks. Commit and push the report.

**Current result: failed.** Candidate-controlled Python can falsify the observer's input-preservation evidence. OS protection of the hidden oracle does not authenticate values emitted from the candidate interpreter. The retained adversarial counterexamples are hard failures, even though the tests correctly reproduce them. Separately, the CLI's request count, zero retries, hard generation ceiling and complete worker isolation remain unqualified.

### Qualification

Only after Gate 1 fully passes: five non-study scenarios × six stages, at most **30 calls**, requiring **30/30** schema/protocol stage completions. A 29/30 batch fails. Preserve a failed batch and stop live execution. Any operational fix requires a new qualification version; no replacement call converts a failure into success. Mock rehearsals have zero model calls and never satisfy this gate.

### B-only calibration

Only after qualification: twelve candidates × three B institutional runs = **36 runs**, at most **216 model calls** including one repair per run. Every attempted failure remains an observation under the frozen failure policy. No unlucky rerun or replacement is permitted.

Eligibility is mean normalized hidden score in **[0.25, 0.75] inclusive**. Three attempts provide a coarse screen, not precise difficulty estimates. Select one candidate per domain, closest mean to 0.50, then lexicographically smallest stable ID. If any domain lacks an eligible task, stop and preserve the screen. Do not relax thresholds or invent replacement tasks.

### Pre-main freeze and main study

Only after eight domains qualify: freeze selected task bytes, evaluator, references, roles/mapping, prompts/schemas, model/runtime, limits, failure policy and analysis. Generate the complete schedule with seed **2026091601**: eight tasks × eight paired repetitions × B/C = **128 institutions**, 64 per condition, 640 scheduled calls and at most **768 calls**. Shuffle task-block order and independently randomize B/C order within each pair. Record the complete schedule hash and commit/push before the first main call.

No `MAIN_SCHEDULE.json` is emitted at this checkpoint because no task has been calibrated or selected. A synthetic schedule in tests is not the main manifest.

Use a fixed maximum of two concurrent institutions across conditions. Define attempt order by schedule position. Evaluate stop conditions in that order, buffering completed observations if necessary; never use completion-race order. Do not launch new work past a stop boundary; retain any already dispatched attempts and their reservations.

Suspend on two consecutive identical startup/configuration failures, or infrastructure/provider failures **greater than 5% after at least 20 attempted runs**. Never stop because of scores or significance. A treatment-relevant fix after suspension requires a new experiment ID. No retry, replacement observation, prompt/role/task/model/timeout/parser tuning is permitted during the main experiment.

## Failure and raw evidence policy

Raw evidence is append-only, atomically published without overwriting prior IDs. A reservation is spent before provider dispatch and is never refunded after failure or interruption. Current reservation tests exercise local mock stages; transport request accounting remains unqualified.

Classify startup/configuration, provider/transport, schema, stage/run timeout, candidate/process and evaluator failures separately. If an attempted institution produces no artifact, its primary end-to-end score is zero. If an artifact exists, grade that frozen artifact even if repair fails. A malfunctioning evaluator produces an unresolved score; replay only the same hash-checked artifact with identical fixture and evaluator hashes with a new immutable evaluation receipt and no model invocation. Never silently convert a replay into an overwritten original terminal record.

A qualified live implementation must retain experiment/task/hash/block/condition/stage/jurisdiction, exact model request and observable resolved identity, timestamps/latency/usage, schema/process outcomes, visible results, repair use, frozen artifact hash, hidden result and failure classification. Planned, attempted, completed, evaluable and failed counts remain distinct. Missing usage is unknown, not zero. Mock records carry `kind: MOCK` and zero model calls.

## Analysis and interpretation

Primary Delta is the equal-task mean of task-specific C minus B score differences. Use **100,000 Monte Carlo draws**, two-sided independent B/C swaps within the actual paired blocks, with seed **2026091602** and the plus-one Monte Carlo correction. Do not shuffle across unrelated tasks.

Secondary uncertainty uses **19,999 hierarchical bootstrap draws**, seed **2026091603**: resample tasks and, within each sampled task, resample complete paired repetition blocks. Preserve B/C pairing. Report the percentile interval, eight task effects, per-condition full-pass and visible-pass rates, schema/institution/failure rates, repairs, calls, observed token coverage and latency. The implemented analysis rejects missing/duplicate cells and mismatched experiment, task, protocol or schedule hashes. It rejects mock evidence unless synthetic validation is explicitly requested.

The practical-effect threshold is **absolute Delta = 0.05**. A p-value greater than .05 does not establish equivalence. A wide interval means inconclusive evidence. Show heterogeneous and negative task effects. Valid-output-only summaries are descriptive post-treatment conditioning and cannot replace the primary end-to-end estimate.

A supported positive claim is limited to improved executable outcomes from task-specific reviewer guidance under this particular model, benchmark, topology and budget policy. A null does not establish equivalence. A negative result may be consistent with overspecialization/anchoring but cannot establish that mechanism. No outcome proves general persona intelligence, changed internal reasoning, routing benefits, organizational superiority, safety, or general superiority over single agents. Eight task families do not represent all coding work. No novelty claim is made for separating role and capability or for decision handoffs.

## Repository independence and historical evidence

SOURCE REPOSITORY: `retinapeg/institutional-engineering`  
SOURCE COMMIT: audited local `ff9353017492153706c875bab1464509e2ddb941`; compatible task source `9d4140afc76b4dcbcdb639a588f5d6d1721db2c5`  
PUBLISHED BASE: `02aa0af04d790b3b362a39a1476793bc813ee40d`  
NEW BRANCH: `roundtable-v1-bc-20260916-execution`  
NEW WORKTREE: `/Users/leonardaarons-ditson/Documents/ChatGPT/AI ENGINEERING RESEARCH 2/roundtable-v1-bc-20260916`  
DIRTY STATE: new branch initially clean; changes are confined to this study directory and the narrow research-package scratch/build exclusions in `pyproject.toml`.  
OTHER ACTIVE WORKTREES DETECTED: presumed concurrent dirty older research checkout at `AI ENGINEERING RESEARCH/institutional-engineering`; all existing research branches and worktrees preserved. Full inventory is in the checkpoint receipts.  
PRODUCT REPOSITORY TOUCHED: **NO**

The public remote initially contained only main. The new publication branch is based on that main revision so it publishes only this study derivative, preserving three unpublished local historical-study commits. The initial new branch at the audited newer source is retained. No main merge, history rewrite, reset or stash is used. Pilot 0 and failed 60-call calibration bytes remain historical evidence; their failures are not model-quality observations. No product source, moving HEAD, uncommitted product file, external engine checkout or global agent configuration is a dependency.
