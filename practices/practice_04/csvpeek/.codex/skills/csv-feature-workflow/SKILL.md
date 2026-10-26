---
name: csv-feature-workflow
description: Implement or modify csvpeek CSV-analysis features using the project's CSV inspection MCP tool, tests, and automatic verification workflow.
---

# CSV feature workflow

Use this workflow when implementing or modifying behaviour related to reading, validating, summarizing, or displaying CSV data.

Before editing code, read `references/csv-contract.md`.

## Workflow

1. Identify which example CSV file is relevant to the requested behaviour.
2. Call the `inspect_csv` tool from the `csv-inspector` MCP server on that file before implementing the feature.
3. Use the returned columns, row count, sample rows, and validation information to understand the input.
4. Inspect the existing implementation and tests.
5. Make the smallest change that satisfies the requested behaviour.
6. Add or update tests for the change.
7. Pay attention to the automatic verification result produced after edits. If it fails, diagnose and fix the failure.
8. Run `./scripts/check.sh` before finishing.
9. Briefly report what changed and which checks passed.

Do not infer the structure of an example CSV file when the MCP tool can inspect it directly.