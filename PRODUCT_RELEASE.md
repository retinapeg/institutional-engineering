# Product release verification — 2026-09-15

Product: https://github.com/retinapeg/institutional-workbench
Frozen commit: f04071b7129b6a2f19185915d0be3242e1d74341
Annotated tag: v0.2.0 (tag object 2994803b954ba30a408bcd77a7f909510237567e).
No product behaviour changes. Main, v0.1.0 and historical branches preserved.

28 deterministic tests, Ruff lint/format, strict mypy (7 files), package build passed.
One live engineering validation: synthetic route('/health') returns (200, {'status':'ok'}).
Independent assessments, one challenge, decision, Sonnet build, host tests, Terra QA,
delivery. Seven CLI invocations, 135.3 seconds, zero repairs, two unittest tests passed.
Only app.py and new tests/test_health.py changed; existing tests/test_app.py unchanged.
Host test execution independently repeated and passed. No user repository was used.

Existing presentation limitation: model-authored limitations say tests were not run by
that model; coordinator host evidence confirms they were run. Product left unchanged.
Requested models Sonnet and gpt-5.6-terra were explicitly pinned for this check.
Claude can use internal auxiliary models; Codex resolved server model is not exposed.
This is a tiny integration smoke, not broad reliability evidence. Prior hackathon smoke
is recorded in the historical V02_VERIFICATION.md, not rerun in this release.

Verified install: `uv tool install --force git+https://github.com/retinapeg/institutional-workbench@v0.2.0`.
Global inst now resolves to that commit, not the old editable checkout. Package metadata
remains 0.2.0.dev0 because the exact source commit was preserved. CLI help exposes
engineering/hackathon/economy, with dev/hack aliases. Requires clean target Git repository.

All subsequent work occurs in the separate institutional-engineering repository.
