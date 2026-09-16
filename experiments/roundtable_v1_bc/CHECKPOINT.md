# Final checkpoint — Roundtable v1 B/C

**STUDY_COMPLETE: NO**

**Outcome:** the offline protocol, task pack, mock controller, analysis and audit receipts are implemented and pushed. Live execution stopped at Gate 1 because grader observation integrity fails and four model-runtime safeguards remain unqualified. No scientific model calls or B/C observations were produced.

## Repository state

| Field | Value |
|---|---|
| Source repository | `retinapeg/institutional-engineering` |
| Starting audited local commit | `ff9353017492153706c875bab1464509e2ddb941` |
| Starting and reverified remote main | `02aa0af04d790b3b362a39a1476793bc813ee40d` |
| New publication branch base | `02aa0af04d790b3b362a39a1476793bc813ee40d` |
| Ending implementation/evidence commit | `16d73f5453c99aad3bbde268c625ebb4e136e984` |
| Branch | `roundtable-v1-bc-20260916-execution` |
| Worktree | `/Users/leonardaarons-ditson/Documents/ChatGPT/AI ENGINEERING RESEARCH 2/roundtable-v1-bc-20260916` |
| Push state | Implementation/evidence commit pushed and exact remote SHA verified. This checkpoint is a separate documentation follow-up on the same branch. |
| Dirty state after implementation commit | Clean; this final checkpoint is the only subsequent file addition. |
| Changed paths | `experiments/roundtable_v1_bc/` plus narrow `.scratch-cli`/`.build` exclusions in research `pyproject.toml` |
| Product repository touched | **NO** |
| Main merged or historical history rewritten | **NO** |

The exact final delivery revision is the Git commit containing this checkpoint; resolve it with `git log -1 --format=%H -- experiments/roundtable_v1_bc/CHECKPOINT.md`. Its full SHA and verified remote state are supplied in the final delivery message. This avoids putting a self-referential commit hash inside its own commit.

The remote repository is public. To keep publication scoped, this branch derives from existing public main while copying only compatible, hashed research primitives and task bytes. The initial `roundtable-v1-bc-20260916` branch at the newer audited local commit remains preserved. Three pre-existing unpublished research commits were not published as this branch's ancestors.

Six research worktrees were detected and preserved. The older `AI ENGINEERING RESEARCH/institutional-engineering` checkout has a modified README and untracked research work and is treated as belonging to another session. The complete inventory, branch heads and observed dirty states are in `manifests/preservation-audit.json`. That audit confirms **1,056 source files with zero byte mismatches**. Pilot 0 and the failed 60-call calibration remain historical evidence and were not resumed.

## Protocol status

B/C-only protocol implemented offline. One requested model/runtime, `gpt-5.6-terra` through Codex CLI 0.154.0 with medium reasoning. Only two independent reviewer jurisdiction blocks vary; challenger, authority, builder, schemas and public evidence remain common. The builder receives the frozen decision rather than the full debate. No role selector, additional model or treatment arm was added.

Twelve candidate tasks span eight domains; five separate scenarios are reserved for qualification. The role bank and domain mapping are hashed. Main task selection and the main schedule remain absent because calibration has not occurred. The protocol is not a completed pre-main freeze.

## Gate and phase status

| Phase | Status |
|---|---|
| Real zero-inference typed configuration loading | PASS |
| Offline implementation checks | PASS |
| Adversarial grader observation integrity | FAIL — three false passes reproduced |
| One provider request per stage and aggregate counting | UNQUALIFIED |
| Zero implicit transport retries | UNQUALIFIED |
| Hard generation-token ceiling | UNQUALIFIED |
| Complete Codex worker tool/hidden-file isolation | UNQUALIFIED |
| **Gate 1 overall** | **FAILED** |
| Live qualification | NOT STARTED; cannot claim 30/30 |
| B-only calibration | NOT STARTED; no task difficulty estimates |
| Main study | NOT STARTED; no selected eight-task manifest or actual main schedule |
| Empirical analysis/report/manuscript | NOT GENERATED; no results exist |

Account-serving availability and the resolved served model remain unobserved. The installed catalog entry and configuration-loader success are metadata evidence only. The live adapter remains deliberately unimplemented while its required boundary cannot be qualified.

## Exact scientific counts

| Phase | Planned institutions | Attempted | Completed | Evaluable | Failed observations | Model calls | Repairs |
|---|---:|---:|---:|---:|---:|---:|---:|
| Qualification | 5 | 0 | 0 | 0 | 0 | 0 / 30 max | 0 |
| Calibration | 36 | 0 | 0 | 0 | 0 | 0 / 216 max | 0 |
| Main, conditional | 128 (64 B, 64 C) | 0 | 0 | 0 | 0 | 0 / 768 max | 0 |

Main planned stage calls are 640 before optional repairs. No live schedule has been instantiated. Scientific attempted/completed/evaluable/failure/call/repair counts are all exactly zero; missing actual usage and latency are **not observed**, not fabricated zeros.

Separately, the final retained mock rehearsal (`manifests/preflight-v2/mock-pipeline/`) has five planned/attempted/completed/evaluable institutions, zero institution failures, 30 local stage invocations, 30 schema completions, five forced repairs and **zero model calls**. The earlier v1 archive preserves another such rehearsal: the two retained archives total ten mock institutions, 60 local invocations and ten mock repairs. Additional temporary unit-test fixtures are test execution, not observations. None of these satisfy live qualification or enter calibration/primary analysis.

## What failed and what was fixed

The hidden oracle is kept outside the candidate process, but candidate Python can forge the observation of input preservation. Serializer monkeypatching, caller-frame substitution and forged stdout each concealed an actual mutation and received a false full score. The exact adversarial code and process receipts are preserved. Prebinding serialization or blacklisting Python imports does not resolve this trust boundary.

The final real CLI doctor test distinguished valid settings from a genuinely invalid type while denying network access. Earlier app-server probes failed during startup under containment; a malformed-output-schema probe failed before typed loading. The initial arbitrary-string reasoning sentinel was not invalid under the actual schema; that interpretation was corrected explicitly. Reserved built-in OpenAI retry overrides were never used. These diagnostic failures were not model calls or scientific observations.

A local package check initially discovered diagnostic scratch files in built archives. Narrow research-package exclusions fixed this. Original receipts remain immutable; the final complete verification confirms the fix. Calibration now rejects mock/unknown evidence by default. Evaluator replay checks fixture and evaluator hashes as well as artifact identity. Task-manifest hashes are checked directly.

## Tests and reproducibility

- **31 new unit/integration tests passed**, including nine synthetic analysis tests and five adversarial/process-boundary tests.
- **27 historical mock regression tests passed** in temporary output directories.
- **17 references** pass public and hidden diagnostic checks; **44 defective controls** fail their targeted requirements.
- Ruff 0.16.7 lint and formatting checks pass.
- mypy 2.3.1 strict checks pass across 17 new implementation/test files.
- Source distribution and wheel build; **87 task/catalog/evaluator files** retain exact bytes; diagnostic scratch and local build products are excluded.
- Independent final review findings were fixed and covered by the complete v2 verification.
- All three live entry points were explicitly exercised and refused with `NO LIVE MODEL CALL DISPATCHED`.

The final command/outputs and machine summary are in `manifests/preflight-v2/` and `GATE1_PREFLIGHT.json`. See `REPRODUCE.md` for fresh-directory verification, metadata-only CLI checks, the grader counterexample and mock rehearsal. The expected overall reproduction exit is 2 while these scientific/infrastructure gates remain false. Markdown uses deliberate two-space hard line breaks in some protocol headings; Git's generic trailing-whitespace check reports those, while code lint/format checks pass.

## Files and hashes

| Artifact | SHA-256 |
|---|---|
| `protocol.json` | `4f8e391abe74b37d70a23bcc4dd476780a649c02f2ec5297bd6b4e556b2e1a7a` |
| `TASK_MANIFEST.json` | `413c50b43565ad7ddbe7d5597b0bcdf1e1a8f6193d6592937ae6ef115f39e845` |
| `ROLE_MANIFEST.json` | `475dcdd1119436f25163e127dcbbf1a8159e0b3001aea4e8e55c7d1e122bb868` |
| `GATE1_PREFLIGHT.json` | `04e5fc8889e63e3f835f6dbc564d16ae3c230f9b426826908850c0531725297e` |
| `manifests/FILE_HASHES.json` | `b98aabca55ac9b9299f0f9fc5a441826b4d7ececee4a2d3845c39135e4f5f983` |

`manifests/FILE_HASHES.json` contains 411 study-file hashes and the research build configuration hash. Its self-hash and this delivery checkpoint are excluded from that manifest and authenticated by Git. The source-preservation and CLI-export manifests provide additional provenance.

## Scientific interpretation boundary

There is no estimated B/C effect, p-value, confidence interval or empirical novelty claim. The generated task/reference checks and mock results establish implementation behavior only. Historical calibration failures are not evidence about model quality. A future completed experiment may support only the narrow fixed-model, benchmark, topology and budget-policy jurisdiction comparison; nonsignificance cannot establish equivalence.

## Next single action

**Qualify a grader observation boundary that rejects all three preserved spoofing candidates while preserving the stated Python task contract.** Keep the current failed audit intact. If the remedy changes task semantics or scoring, create a new protocol version. After that, the remaining CLI request/retry/token/worker safeguards still need qualification before any live call. The existing authorization already permits qualification once every hard gate genuinely passes; no routine approval is needed.
