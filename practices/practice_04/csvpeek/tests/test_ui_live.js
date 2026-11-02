const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { setup } = require('./ui_harness');

test('local API and UI agree with CLI for representative CSV files', async () => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'csvpeek-ui-'));
  try {
    const cases = [
      ['people.csv', fs.readFileSync(path.join(__dirname, '../examples/people.csv'), 'utf8')],
      ['duplicate.csv', 'x,x\n,1\n'],
      ['header.csv', 'name,age\n'],
    ];
    for (const [name, content] of cases) {
      const filename = path.join(directory, name);
      fs.writeFileSync(filename, content);
      const cli = execFileSync('python', ['-m', 'csvpeek', filename], { encoding: 'utf8', env: { ...process.env, PYTHONPATH: 'src' } });
      const records = cli.trimEnd().split('\n');
      const fetchLocal = (url, options) => {
        const form = new FormData();
        form.append('file', new Blob([content], { type: 'text/csv' }), name);
        return fetch(`${process.env.CSVPEEK_TEST_URL || 'http://127.0.0.1:8000'}${url}`, { ...options, body: form });
      };
      const app = setup(fetchLocal);
      app.select({ name, size: Buffer.byteLength(content) });
      await app.elements.analyze.trigger('click');
      assert.equal(app.elements.result.hidden, false, app.elements.error.textContent);
      assert.equal(app.elements.rows.textContent, records[0].slice(6));
      const expected = records.slice(3).map(line => Number(line.slice(line.lastIndexOf(': ') + 2)));
      assert.equal(Number(app.elements.columns.textContent), expected.length);
      assert.deepEqual(app.elements['column-list'].children.map(row => Number(row.children[1].textContent.split(' ')[0])), expected);
      assert.deepEqual(app.elements['column-list'].children.map(row => row.children[0].children[1].textContent), records[1].slice(9).split(', '));
    }
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
});
