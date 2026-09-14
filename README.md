# Institutional Workbench

A personal command-line engineering workbench using local Claude and Codex CLIs.

Intended commands (not implemented yet):

```text
inst dev "implement this feature"
inst hack "build the strongest demo for this hackathon"
```

The delivery loop is bounded: understand → independent expert assessments → one
challenge round → decide → build → test → one QA pass → repair → deliver → stop.
Acceptance criteria are set before building. Tests and observable behaviour
outrank model confidence. Scope stays fixed until the user approves a feature.

At most four relevant specialist perspectives, one builder, one QA pass and two
repair cycles. No dashboard, database, permanent organisation, distributed
workers or recursive agent creation. Python CLI; Claude and Codex only.

## Status

Repository boundary established. CLI implementation has not started. The supplied
product brief ends mid-section at “16. PROVIDER SELECTION — Keep”; the remainder
is needed before finalising provider defaults and implementation acceptance.

## Separate research project

[institutional-ai](https://github.com/retinapeg/institutional-ai) is the preserved
larger research experiment. This repository reuses concepts, not its architecture.

- Verified research MVP on main: `5839bc65e2f041615d3256e9ce38bcd3c091d58a`.
- Frozen unfinished research work on codex/live-workers-v1:
  `7c3cd71ff4b2f00bd206b049d80982bdc58f7187`.
- Research checkpoint tests: 22 passed, one health-response assertion failed;
  live provider work is unfinished and has not been merged into research main.

No code, credentials, local run data or user repositories were copied here.
