# CSV behaviour contract

`csvpeek` should treat the first CSV record as the header.

A valid CSV file must contain at least one column.

Rows with fewer or more fields than the header must not be silently accepted as normal rows.

Empty fields are considered missing values.

Output intended for tests should be deterministic.

User-facing failures should explain what input was invalid instead of exposing an internal traceback when possible.
