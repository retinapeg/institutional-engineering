# Codex CLI preflight

**Typed configuration loading: PASS. Complete live-runtime qualification: NOT PASSED.**
This audit made zero provider model calls. It changed no global configuration and
never used either forbidden built-in provider retry override.

## Frozen local runtime evidence

- CLI: `codex-cli 0.154.0`, macOS ARM64.
- Binary SHA-256: `4f85982624b3898c8991cb80c0981b2aa71070e3537046c9a95950318a95afcc`.
- Requested model: `gpt-5.6-terra`; requested reasoning: `medium`.
- The actual binary's bundled model catalog lists this model, with medium as its
  default reasoning effort and a 272,000-token CLI context window.
- The resolved served model and account-serving availability remain **unobserved**.
  Catalog membership is local availability evidence, not a successful inference call.

`manifests/cli/runtime.json` preserves the binary path, hash, version and only the
relevant bundled model entry. API model documentation does not establish the CLI's
effective context policy. [Official model documentation](https://developers.openai.com/api/docs/models/gpt-5.6-terra)

## Qualified zero-inference loader check

The actual `codex doctor --json` command loaded the requested configuration while
macOS denied network access and denied filesystem writes outside an owned scratch
directory. The diagnostic's configuration scope includes invocation configuration
and managed policy.

| Control | `checks["config.load"].status` | Summary |
|---|---|---|
| `model_reasoning_effort="medium"` | `ok` | `config loaded` |
| `model_reasoning_effort=17` | `fail` | `config could not be loaded` |

Both processes exited 1 because deliberately blocked network health checks failed.
The configuration gate must inspect the **configuration subcheck**, not the overall
doctor exit status. These network failures are induced containment evidence, not
provider-reliability observations.

### Correction to the initial negative control

The generated schema from this binary defines reasoning effort as any **nonempty
string**. Therefore the earlier `"invalid-reasoning-sentinel"` string was
schema-valid. Its acceptance by doctor, the feature listing or the bundled catalog
does not prove those commands bypass typed configuration. The integer control is
outside the actual schema and fails as required. Supported semantic values are
separately checked against the bundled model catalog. The minimal generated schema
excerpt and full-source hash are in `manifests/cli/schema-excerpt.json`.

Other investigated routes were insufficient: strict configuration mode is not
supported for `features` or `debug`; metadata-only app-server startup failed under
containment before initialization; a deliberately malformed output schema is
rejected before the relevant configuration check. None produced inference.

## Remaining hard gates

The actual CLI supports fixed model configuration, JSON events, output schemas,
ephemeral sessions and user-configuration/rule exclusion flags. Those controls do
not establish the following properties:

1. **Exactly one provider model request per stage**, with enforceable aggregate
   request budgets of 30 qualification, 216 calibration and 768 main requests.
2. **Zero implicit retries.** Disabling `unbounded_connection_retries` does not
   establish that finite transport or stream retries are disabled.
3. **A hard model-generated output-token ceiling.** No supported per-request
   `max_output_tokens` or one-turn limit was found in the inspected CLI help and
   configuration schema. Tool-output limits are a different quantity; the
   experimental rollout-budget setting is not qualified for this purpose.
4. **Complete model-visible tool suppression and hidden-file isolation.** Read-only
   filesystem permissions prevent writes but do not establish confidentiality.
5. **Account-serving availability and resolved model provenance.** These have not
   been tested by inference.

The complete deterministic/live gate must remain closed until the independent
runtime and isolation requirements pass. A passing loader subcheck is insufficient
to authorize qualification. [Official configuration schema](https://developers.openai.com/codex/config-schema.json)

## Reproduce the loader check

From this repository's isolated worktree:

```sh
python3 experiments/roundtable_v1_bc/manifests/cli/reproduce_doctor.py
```

The standalone standard-library script requires macOS and the recorded binary
hash. It runs only doctor metadata diagnostics, blocks network access before
launch, permits CLI filesystem writes only under its fresh scratch directory,
terminates an owned process on timeout, and exports a small safe configuration
summary. It never sends a model prompt or starts a model turn. Both observations
and their hashes remain available in the printed receipt directory.

The exported reproduction script itself was executed successfully: configuration
loader passed; complete live preflight remained false. Its output-filter self-check,
lint, formatting and strict type checks are recorded in the export index.

```sh
python3 experiments/roundtable_v1_bc/manifests/cli/reproduce_doctor.py --self-test
```

## Publication review

The exported receipts contain only selected runtime/catalog facts, relevant flags,
configuration-check outcomes and provenance hashes. They exclude credentials,
authentication state, whole configuration files, full model catalogs, diagnostic
logs, unrelated repository paths and complete generated schemas. Exact owned
worktree and runtime paths are retained where required to reproduce the invocation.
The complete private scratch directory is **not** part of this export.

`manifests/cli/export-index.json` lists the exported files and SHA-256 hashes.
