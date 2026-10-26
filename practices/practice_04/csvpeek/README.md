# csvpeek

A small CSV inspection CLI using only the Python standard library (Python 3.12+).

Run from the repository root:

```bash
PYTHONPATH=src python -m csvpeek examples/people.csv
```

```text
Rows: 4
Columns: name, age, score
Missing values:
  name: 0
  age: 1
  score: 0
```

Input is UTF-8 CSV with the first record as the header. Only empty fields count
as missing; whitespace and strings such as `NA` are values. Column order is
preserved. Empty files, headers without columns, invalid CSV quoting, and records
with the wrong number of fields produce an error and a nonzero exit status.

Run checks:

```bash
./scripts/check.sh
```
