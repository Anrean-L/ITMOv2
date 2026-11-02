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

Run the local API separately (the CLI remains unchanged):

```bash
PYTHONPATH=src python -m csvpeek.server --port 8000
```

The server listens only on `127.0.0.1`. Once the UI resources are available,
open `http://127.0.0.1:8000/`. For API details and file limits, see the
[UI/backend contract](specs/ui-backend-contract.md). Run the optional benchmark with
`PYTHONPATH=src python tests/benchmark_cache.py`.

The uploaded CSV is limited to 10 MiB; the entire multipart request is separately
limited to 16 MiB to bound per-request memory. An oversized request receives
`400 invalid_request`; an oversized CSV receives `413 limit_exceeded` with
`file_bytes`. The request limit includes multipart framing and must be taken into
account when integrating clients.
