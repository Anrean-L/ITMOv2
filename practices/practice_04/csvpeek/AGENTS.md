# Project instructions

This repository contains `csvpeek`, a small Python CLI for inspecting CSV files.

## Project rules

- Use Python 3.12+.
- Prefer the Python standard library unless an external dependency is clearly justified.
- Keep the implementation small and readable.
- Put application code under `src/csvpeek/`.
- Put tests under `tests/`.
- Keep CLI output deterministic so it can be tested.
- Do not silently ignore malformed input.
- Preserve existing behaviour unless the task explicitly asks to change it.

## Agent workflow

For feature work on CSV analysis, use the `csv-feature-workflow` skill.

Before implementing behaviour that depends on CSV structure, use the `inspect_csv` tool from the `csv-inspector` MCP server on the relevant example file.

Use `apply_patch` for changes to source code and tests so that the repository's automatic verification hook runs after edits.

The automatic verification result is part of the task feedback. If it reports a failure, investigate and fix the failure before considering the task complete.

Before finishing a task, run:

```bash
./scripts/check.sh
```

Do not claim that a change works unless the checks pass.
