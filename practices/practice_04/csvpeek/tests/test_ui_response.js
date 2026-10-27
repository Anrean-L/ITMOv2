const { test } = require('node:test');
const assert = require('node:assert/strict');
const { validResult } = require('../src/csvpeek/web/app');

test('result validation rejects wrong counts, types and missing values', () => {
  assert.ok(validResult({ row_count: 1, column_count: 1, columns: [{ name: 'a', missing_count: 1 }] }));
  for (const value of [null, {}, { row_count: -1, column_count: 0, columns: [] }, { row_count: 0, column_count: 2, columns: [] }, { row_count: 0, column_count: 1, columns: [{ name: 'a', missing_count: 1 }] }, { row_count: 0, column_count: 1, columns: [{ name: 4, missing_count: 0 }] }]) assert.ok(!validResult(value));
});
