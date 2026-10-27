const { test } = require('node:test');
const assert = require('node:assert/strict');
const { setup, response } = require('./ui_harness');

test('request sends the selected file and renders ordered duplicate columns safely', async () => {
  let call;
  const app = setup(async (...args) => { call = args; return response(200, { row_count: 1, column_count: 3, columns: [{ name: 'x', missing_count: 1 }, { name: 'x', missing_count: 0 }, { name: '', missing_count: 0 }] }); });
  const selected = { name: '<img>.csv', size: 8 }; app.select(selected);
  await app.elements.analyze.trigger('click');
  assert.equal(call[0], '/api/analysis');
  assert.equal(call[1].method, 'POST');
  assert.equal(call[1].headers['X-Csvpeek-Request'], '1');
  assert.deepEqual(call[1].body.parts[0], ['file', selected]);
  assert.equal(call[1].body.parts.length, 1);
  assert.equal(app.elements['result-file'].textContent, '<img>.csv');
  assert.equal(app.elements['column-list'].children.length, 3);
  assert.equal(app.elements['column-list'].children[2].children[0].children[1].textContent, 'Без имени');
  assert.equal(app.elements.result.hidden, false);
});

test('header only shows zero and BOM remains represented', async () => {
  const app = setup(async () => response(200, { row_count: 0, column_count: 1, columns: [{ name: '\ufeff', missing_count: 0 }] }));
  app.select({ name: 'bom.csv' }); await app.elements.analyze.trigger('click');
  assert.equal(app.elements.rows.textContent, '0');
  const name = app.elements['column-list'].children[0].children[0];
  assert.equal(name.children[1].textContent, '\ufeff');
  assert.equal(name.children[2].textContent, ' (BOM)');
  assert.equal(name.children.length, 3);
});
