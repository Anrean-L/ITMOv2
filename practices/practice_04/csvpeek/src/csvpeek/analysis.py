"""Independent, bounded CSV analysis for the local service."""

import csv
import io

FILE_LIMIT = 10 * 1024 * 1024
FIELD_LIMIT = 128 * 1024
COLUMN_LIMIT = 1000
ROW_LIMIT = 100000


class AnalysisError(Exception):
    def __init__(self, code, message, details=None, status=422):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}
        self.status = status


def limit_error(kind, limit, unit):
    return AnalysisError('limit_exceeded', 'Analysis limit exceeded',
                         {'kind': kind, 'limit': limit, 'unit': unit}, 413)


def analyze(data):
    if len(data) > FILE_LIMIT:
        raise limit_error('file_bytes', FILE_LIMIT, 'bytes')
    try:
        with io.TextIOWrapper(io.BytesIO(data), encoding='utf-8', newline='') as file:
            reader = csv.reader(file, strict=True)
            columns = next(reader, None)
            if columns is None or not columns:
                raise AnalysisError('empty_csv', 'CSV file or header is empty')
            if len(columns) > COLUMN_LIMIT:
                raise limit_error('columns', COLUMN_LIMIT, 'columns')
            _check_fields(columns)
            missing = [0] * len(columns)
            row_count = 0
            for record, row in enumerate(reader, 2):
                row_count += 1
                if row_count > ROW_LIMIT:
                    raise limit_error('rows', ROW_LIMIT, 'rows')
                if len(row) != len(columns):
                    raise AnalysisError('invalid_structure', 'Wrong number of fields',
                                        {'record': record, 'expected_fields': len(columns),
                                         'actual_fields': len(row)})
                _check_fields(row)
                for index, value in enumerate(row):
                    missing[index] += value == ''
    except UnicodeDecodeError as exc:
        raise AnalysisError('invalid_encoding', 'CSV must be UTF-8') from exc
    except csv.Error as exc:
        if str(exc).startswith('field larger than field limit'):
            raise limit_error('field_bytes', FIELD_LIMIT, 'bytes') from exc
        raise AnalysisError('invalid_structure', 'Invalid CSV structure') from exc
    return {'row_count': row_count, 'column_count': len(columns),
            'columns': [{'name': name, 'missing_count': count}
                        for name, count in zip(columns, missing)]}


def _check_fields(row):
    if any(len(value.encode('utf-8')) > FIELD_LIMIT for value in row):
        raise limit_error('field_bytes', FIELD_LIMIT, 'bytes')
