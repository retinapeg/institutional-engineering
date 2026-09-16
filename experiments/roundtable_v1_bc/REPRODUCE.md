# Reproduce the blocked offline checkpoint

This checkpoint contains **no live study data and no live adapter**. The expected overall result is **Gate 1 failed, zero model calls**. Unit-test success and mock pipeline completion must not be reported as scientific observations.

## Environment

Recorded host: macOS 26.5 on Apple silicon, Python 3.14.7, uv 0.12.7, Ruff 0.16.7 and mypy 2.3.1. The research package requires Python >=3.11. Actual candidate execution requires macOS `sandbox-exec`; another platform must fail closed until an equivalent boundary is qualified. The CLI binary is Codex 0.154.0 with the full hash recorded in `manifests/cli/runtime.json`.

Run commands from the root of this checkout. Keep this checkout physically separate from concurrent research and product worktrees.

```sh
uv sync --frozen
uv run --frozen python -m experiments.roundtable_v1_bc.verify \
  --output experiments/roundtable_v1_bc/manifests/preflight-reproduction-001
```

Choose a **new output path** for each verification. Existing receipts are not overwritten. Expected command exit is **2**, because the overall gate remains blocked. Read the generated `summary.json`; all implementation checks should pass while the integrity and live-boundary gates remain false. The verifier builds packages under the ignored study `.build` directory and validates copied fixture bytes and scratch exclusions.

The recorded checkpoint used its isolated `.venv/bin/python` directly and pinned lint/type tools through `uvx`. Its exact commands and outputs are in `manifests/preflight-v2/`; the earlier version remains preserved in `manifests/preflight-v1/`. The first archive check failed because scratch data entered local packages. The repaired build is recorded in `manifests/package-fix-v2.json`; `GATE1_PREFLIGHT.json` records the final complete verification after this repair and the additional calibration/replay/manifest guards.

## Real zero-inference CLI loader check

```sh
python3 experiments/roundtable_v1_bc/manifests/cli/reproduce_doctor.py
```

This checks the exact audited binary hash, denies network access and confines writes to a newly created `.scratch-cli/doctor-reproduction-*` directory. It runs metadata diagnostics only. A valid medium-reasoning configuration must produce config.load `ok`; integer-valued reasoning must produce `fail`. Both process exits can be 1 because network health checks are deliberately denied. Inspect the configuration subcheck. The earlier arbitrary-string sentinel was not a type error and is not evidence that configuration loading was skipped.

The doctor check establishes configuration loading, not model serving, retry limits, generation bounds, tool suppression or worker isolation.

## Reproduce the grader vulnerability alone

```sh
uv run --frozen python -m experiments.roundtable_v1_bc.harness integrity-audit \
  --output experiments/roundtable_v1_bc/manifests/grader-reproduction-001.json
```

Expected `qualified: false` and three false passes. The regression tests deliberately reproduce these counterexamples. A future repair must make the malicious candidates fail without narrowing the public task contract or weakening scoring.

## Mock institutional rehearsal

```sh
uv run --frozen python -m experiments.roundtable_v1_bc.harness mock-qualification \
  --output experiments/roundtable_v1_bc/manifests/mock-reproduction-001
```

Expected five completed mock institutions, 30 local stage invocations, 30 schema completions and five forced repairs. The model-call count remains zero. The output directory contains atomic stage reservations, prompts, parsed responses, decision and artifact freezes, visible/hidden diagnostic results and terminal records. Each row is marked `MOCK`; these artifacts cannot qualify the live pipeline or populate the primary analysis.

`qualification`, `calibration` and `main` entry points refuse while any gate is false. Even a manually altered all-green receipt cannot activate a provider: no live adapter is registered in this checkpoint.

## Analysis

`analysis/stats.py` accepts complete terminal records and an independently verified frozen main manifest. It validates IDs, task/protocol/schedule hashes, all paired cells, failure/score consistency and live-versus-mock identity. LIVE requires eight tasks × eight pairs and a committed freeze marker. Synthetic input requires explicit `allow_mock=True` and produces an explicitly synthetic result. No analysis of actual B/C outcomes can run yet because calibration, main selection, freeze and observations do not exist.

## Evidence integrity

`manifests/FILE_HASHES.json` records committed study content at checkpoint preparation. Verify with the standard-library command below; it omits its own self-hash and the evolving delivery checkpoint, which are authenticated by Git.

```sh
python3 - <<'PY'
import hashlib, json
from pathlib import Path
root = Path('experiments/roundtable_v1_bc')
manifest = json.loads((root / 'manifests/FILE_HASHES.json').read_bytes())
for name, digest in manifest['files'].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest, name
print('All recorded study hashes match')
PY
```

Historical source commit IDs and per-file hashes are preserved as provenance. Some source commits were previously local and are intentionally not published as this branch's ancestors. Reproduction uses the copied, hashed bytes in this package, without fetching those commits or reading product worktrees. Existing Pilot 0/failed calibration outputs remain immutable historical evidence.
