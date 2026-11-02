import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))

from csvpeek.analysis import AnalysisError, analyze


class AnalysisTests(unittest.TestCase):
    def test_duplicates_and_missing(self):
        result = analyze(b'x,x\n,1\n')
        self.assertEqual(result, {'row_count': 1, 'column_count': 2, 'columns': [
            {'name': 'x', 'missing_count': 1}, {'name': 'x', 'missing_count': 0}]})

    def test_invalid_width(self):
        with self.assertRaises(AnalysisError) as caught:
            analyze(b'a,b\n1\n')
        self.assertEqual(caught.exception.details['record'], 2)

    def test_field_byte_limit(self):
        with self.assertRaises(AnalysisError) as caught:
            analyze(b'a\n' + ('é' * 65537).encode())
        self.assertEqual(caught.exception.code, 'limit_exceeded')

    def test_cases_and_boundaries(self):
        self.assertEqual(analyze(b'""\n')['columns'][0]['name'], '')
        self.assertEqual(analyze(b'\xef\xbb\xbfa\n')['columns'][0]['name'], '\ufeffa')
        self.assertEqual(analyze(b'a,b\r\n"x\r\ny",\r\n')['row_count'], 1)
        self.assertEqual(analyze(b'a\n' + b'x' * 131072)['row_count'], 1)
        self.assertEqual(analyze(b','.join([b'x'] * 1000))['column_count'], 1000)
        self.assertEqual(analyze(b'a\n' + b'x\n' * 100000)['row_count'], 100000)
        cases = [(b'', 'empty_csv'), (b'\n', 'empty_csv'),
                 (b'a\n\xff', 'invalid_encoding'), (b'a\n"unterminated', 'invalid_structure'),
                 (b'a\n' + b'x' * 131073, 'limit_exceeded'),
                 (b','.join([b'x'] * 1001), 'limit_exceeded'),
                 (b'a\n' + b'x\n' * 100001, 'limit_exceeded')]
        for value, code in cases:
            with self.subTest(code=code), self.assertRaises(AnalysisError) as caught:
                analyze(value)
            self.assertEqual(caught.exception.code, code)

    def test_example_and_empty_semantics(self):
        data = (Path(__file__).resolve().parents[1] / 'examples' / 'people.csv').read_bytes()
        result = analyze(data)
        self.assertEqual(result['row_count'], 4)
        self.assertEqual([c['name'] for c in result['columns']], ['name', 'age', 'score'])
        self.assertEqual([c['missing_count'] for c in result['columns']], [0, 1, 0])
        result = analyze(b'z,a\n,\n"", \n0,NA\n')
        self.assertEqual([c['missing_count'] for c in result['columns']], [2, 1])
        result = analyze(b'one,two\n')
        self.assertEqual(result['row_count'], 0)
        self.assertEqual([c['missing_count'] for c in result['columns']], [0, 0])

    def test_quoted_and_multibyte_field_limit(self):
        for value in (('é' * 65536).encode(), b'"' + b'""' * 131072 + b'"'):
            self.assertEqual(analyze(b'a\n' + value)['row_count'], 1)
        with self.assertRaises(AnalysisError) as caught:
            analyze(b'a\n"' + b'""' * 131073 + b'"')
        self.assertEqual(caught.exception.details, {'kind': 'field_bytes', 'limit': 131072, 'unit': 'bytes'})
