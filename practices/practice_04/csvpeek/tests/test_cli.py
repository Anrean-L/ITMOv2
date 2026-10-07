import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, "-m", "csvpeek", *map(str, args)],
            env={**os.environ, "PYTHONPATH": str(ROOT / "src")},
            capture_output=True,
            text=True,
            check=False,
        )

    def inspect(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_bytes(content.encode("utf-8"))
            return self.run_cli(path)

    def assert_failure(self, result, message):
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn(message, result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_people(self):
        result = self.run_cli(ROOT / "examples" / "people.csv")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(
            result.stdout,
            "Rows: 4\nColumns: name, age, score\nMissing values:\n"
            "  name: 0\n  age: 1\n  score: 0\n",
        )

    def test_only_empty_fields_are_missing(self):
        result = self.inspect('z,a\n,\n"", \n0,NA\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Rows: 3\nColumns: z, a\nMissing values:\n  z: 2\n  a: 1\n",
        )

    def test_header_only(self):
        result = self.inspect("name,age\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Rows: 0\nColumns: name, age\nMissing values:\n  name: 0\n  age: 0\n",
        )

    def test_quoted_fields_and_multiline_records(self):
        result = self.inspect('name,note\r\n"Zoë, A","first\r\nsecond"\r\n')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Rows: 1\nColumns: name, note\nMissing values:\n  name: 0\n  note: 0\n",
        )

    def test_duplicate_columns_are_counted_separately(self):
        result = self.inspect("x,x\n,1\n")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout,
            "Rows: 1\nColumns: x, x\nMissing values:\n  x: 1\n  x: 0\n",
        )

    def test_missing_header(self):
        for content, message in [("", "empty"), ("\n", "no columns")]:
            with self.subTest(content=content):
                self.assert_failure(self.inspect(content), message)

    def test_wrong_field_counts(self):
        for row, count in [("Alice", 1), ("Alice,20,extra", 3), ("", 0)]:
            with self.subTest(row=row):
                self.assert_failure(
                    self.inspect(f"name,age\nBob,30\n{row}\n"),
                    f"record 3: expected 2 fields, got {count}",
                )

    def test_invalid_quoting(self):
        for row in ['"unterminated', '"closed"extra']:
            with self.subTest(row=row):
                self.assert_failure(self.inspect(f"name\n{row}\n"), "error:")

    def test_invalid_encoding(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.csv"
            path.write_bytes(b"name\n\xff\n")
            self.assert_failure(self.run_cli(path), "decode")

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "missing.csv"
            self.assert_failure(self.run_cli(path), str(path))

    def test_path_is_required(self):
        self.assert_failure(self.run_cli(), "required")


if __name__ == "__main__":
    unittest.main()
