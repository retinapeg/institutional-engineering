# Verification

- Deterministic suite: 14 tests passed. Real Git worktrees, file edits, acceptance
  subprocesses, cancellation, timeout, protected tests and patch delivery; mocked model responses.
- Ruff: passed. Strict mypy: passed for six source files. Wheel and source build: passed.
- Installed locally with `uv tool install --editable .`; `inst --help` works.

## Live health-endpoint smoke

Run `20260914-232252` completed DELIVERED in 213.7 seconds, seven provider calls,
zero repair cycles. Two independent assessments, one challenge each, Codex decision,
Claude build, actual unittest execution, one Codex QA PASS, checked patch delivery.

Changes: `app.py` and new `tests/test_health.py`. Three tests passed: GET /health
returns 200/application-json/ok; unknown paths remain 404; POST /health remains 404.
The original fixture's existing test was preserved. No generated caches were delivered.

The small smoke experiment also exposed adapter startup problems before this successful
run: an unsupported old model selection and a Codex startup warning emitted as an
error item. Four preliminary runs stopped at their first Codex call. Defaults and
warning handling were corrected; these failures are not counted as successful runs.

Codex was explicitly selected as `gpt-5.6-terra`; exec JSONL does not independently
attest the resolved server model. Claude was requested as `sonnet`; its CLI reported
`claude-sonnet-5`, `claude-fable-5-1` and `claude-haiku-4-5-20251001` in modelUsage.
The CLI can use auxiliary models internally. The workbench records this usage and
does not implement its own premium escalation or fallback router.

Runtime providers are real. Mock responses are confined to the normal test suite.
The hack policy is covered by deterministic tests; no separate paid hack run was made.

Builder caveats describe what the model itself could inspect. Host-executed test
results in output/tests.json are the authoritative execution evidence.
