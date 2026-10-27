const { test } = require('node:test');
const assert = require('node:assert/strict');
const { setup, response } = require('./ui_harness');

test('late response is ignored after selection changes, even for same name', async () => {
  let resolve;
  const app = setup(() => new Promise(done => { resolve = done; }));
  app.select({ name: 'same.csv' }); const first = app.elements.analyze.trigger('click');
  assert.equal(app.elements.analyze.disabled, true);
  app.select({ name: 'same.csv' });
  resolve(response(200, { row_count: 1, column_count: 0, columns: [] })); await first;
  assert.equal(app.elements.result.hidden, true);
  assert.equal(app.elements.analyze.disabled, false);
  assert.match(app.elements.status.textContent, /Файл выбран/);
  app.select(null); assert.equal(app.elements['file-name'].textContent, 'same.csv');
});

test('retry after failure sends another request', async () => {
  let count = 0;
  const app = setup(async () => ++count === 1 ? response(500, null) : response(200, { row_count: 0, column_count: 1, columns: [{ name: 'a', missing_count: 0 }] }));
  app.select({ name: 'a.csv' }); await app.elements.analyze.trigger('click');
  assert.equal(app.elements.error.hidden, false);
  await app.elements.analyze.trigger('click'); assert.equal(count, 2); assert.equal(app.elements.result.hidden, false);
});
