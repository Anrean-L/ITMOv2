const { test } = require('node:test');
const assert = require('node:assert/strict');
const { setup, response } = require('./ui_harness');
const { messageFor } = require('../src/csvpeek/web/app');

test('known errors provide actionable text without exposing server message', () => {
  for (const [code, expected] of [['empty_csv', 'пуст'], ['invalid_encoding', 'UTF-8'], ['invalid_structure', 'структуру'], ['limit_exceeded', 'ограничения']]) {
    const text = messageFor(422, { error: { code, message: '<secret>' } });
    assert.ok(text.includes(expected)); assert.ok(!text.includes('<secret>'));
  }
  assert.match(messageFor(422, { error: { code: 'invalid_structure', details: { record: 3, expected_fields: 2, actual_fields: 1 } } }), /Запись 3/);
  assert.match(messageFor(413, { error: { code: 'limit_exceeded', details: { kind: 'columns', unit: 'columns', limit: 1000 } } }), /1000/);
  assert.match(messageFor(403, null), /Попробуйте/);
});

test('403, malformed response and connection errors do not expose partial results', async () => {
  for (const fetch of [async () => response(403, null), async () => ({ ok: true, status: 200, json: async () => { throw new Error(); } }), async () => { throw new TypeError('network'); }, async () => response(422, { error: { code: 'unknown' } })]) {
    const app = setup(fetch); app.select({ name: 'bad.csv' }); await app.elements.analyze.trigger('click');
    assert.equal(app.elements.error.hidden, false); assert.equal(app.elements.result.hidden, true); assert.ok(app.elements.error.textContent);
  }
});
