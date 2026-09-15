# Institutional Engineering — open research

Does intellectual reasoning jurisdiction, independently of model capability, produce
measurable, reproducible changes in visible behaviour and task performance?
Role specificity is **not established**.

- [Institutional Workbench](https://github.com/retinapeg/institutional-workbench): installable engineering/hackathon/economy tool.
- [Institutional Engineering](https://github.com/retinapeg/institutional-engineering): this research project, not the product.

Research repository split from retinapeg/institutional-workbench benchmark commit
2400aa4e35bb908f272afb0baca10d588590be43.
Git ancestry and MIT attribution are retained. No changes return to the product.

## Pilot 0 — Protocol and Ceiling Effects

The original eight-task, 96-call experiment is preserved unchanged in `benchmarks/`.
Matched conditioning appeared better under strict scoring, but mismatched conditioning
also improved. Protocol reliability strongly confounded comparisons; schema-valid
responses were near ceiling. Specialist-specific benefit was NOT established.
Read `benchmarks/results/INTERPRETATION.md`, including failures and grading limitations.

The small `src/institutional_workbench/` compatibility snapshot is frozen solely for
Pilot 0 adapters, roles and fingerprint reproducibility. It exposes no `inst` command.
Historical verification notes are provenance, not this repository's product offering.

## Next study

`experiments/single_task_role_effect/`: one fixed mathematical task, one model
(gpt-5.6-terra), four role interventions, randomized blocks. Baseline-only calibration
selects a non-ceiling task using a rule committed before inference. Results pending.
See [REPRODUCE.md](REPRODUCE.md) and `paper/main.tex`. No UI, routing changes or extra models.

**Current study status: blocked at calibration.** Sixty local CLI bootstrap failures,
zero model responses, no task selected and no full-study calls. This is a harness failure,
not a model-performance result. See
[the failure report](experiments/single_task_role_effect/CALIBRATION_FAILURE.md).
Do not restart this batch or silently amend the protocol.
