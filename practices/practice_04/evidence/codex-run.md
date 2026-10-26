# Запуск codex для выполнения проекта

## Prompt

```text
Use the csv-feature-workflow skill.

Implement the initial version of csvpeek.

It should provide a small command-line interface that accepts a CSV file path
and prints:
- the number of data rows;
- the column names;
- the number of missing values for each column.

Use examples/people.csv as the example input.

Add tests for the behaviour.
Keep the implementation minimal.
```

## Результат

```text
Implemented a minimal standard-library CLI with row counts, column names, missing-value counts, and clear input errors.

Run:

PYTHONPATH=src python -m csvpeek examples/people.csv

Added README usage and 11 tests. ./scripts/check.sh passes.

Also corrected the verification hook paths. Manual hook verification passes; this session still uses the previously loaded hook command.
```

### Использование skill

```text
I’ll use the csv-feature-workflow skill, inspect examples/people.csv,
then implement the CLI and tests and run the required checks.

• Explored
  └ Read SKILL.md (csv-feature-workflow skill)
```

### Использование MCP

```text
I’ll inspect `examples/people.csv` using the `csv-inspector` MCP tool.
• Called csv-inspector.inspect_csv
  └     ]
      ]
    }
```

### Намеренно неудачное использование MCP

prompt:

```text
Use the csv-inspector MCP tool inspect\_csv to inspect examples/does-not-exist.csv.  
Call the MCP tool directly. Do not use shell commands or Python.  
Do not create the file.  
```

```text
I’ll call `csv-inspector.inspect_csv` for `examples/does-not-exist.csv`.
• Failed csv-inspector.inspect_csv
  └ Error executing tool inspect_csv
Called `csv-inspector.inspect_csv` for `examples/does-not-exist.csv`. The tool returned: `Error executing tool inspect_csv`.

No file was created.
```

### Влияние hook

```text
• Blocked by hook
  └ python3: can't open file '/home/rina/code/ITMOv2/.codex/hooks/run_checks.py': [Errno 2] No such file or directory
```
