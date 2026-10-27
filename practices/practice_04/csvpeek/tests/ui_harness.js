const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

class Element {
  constructor() { this.listeners = {}; this.children = []; this.textContent = ''; this.hidden = false; this.disabled = false; this.files = []; this.value = ''; this.attributes = {}; }
  addEventListener(type, callback) { this.listeners[type] = callback; }
  setAttribute(key, value) { this.attributes[key] = value; }
  append(...items) { this.children.push(...items); }
  replaceChildren(...items) { this.children = items; }
  trigger(type) { return this.listeners[type](); }
}

function setup(fetch) {
  const elements = Object.fromEntries(['file', 'file-label', 'file-name', 'analyze', 'status', 'error', 'result', 'result-file', 'rows', 'columns', 'column-list', 'results'].map(id => [id, new Element()]));
  const document = {
    getElementById: id => elements[id], querySelector: () => elements.results,
    createElement: () => new Element(), createTextNode: text => ({ textContent: text }),
  };
  class FormData { constructor() { this.parts = []; } append(...args) { this.parts.push(args); } }
  const script = fs.readFileSync(path.join(__dirname, '../src/csvpeek/web/app.js'), 'utf8');
  vm.runInNewContext(script, { document, FormData, fetch, Error, TypeError, Number });
  return { elements, select: file => { elements.file.files = file ? [file] : []; elements.file.trigger('change'); } };
}
const response = (status, data) => ({ status, ok: status >= 200 && status < 300, json: async () => data });
module.exports = { setup, response };
