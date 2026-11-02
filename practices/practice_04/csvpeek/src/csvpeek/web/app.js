(() => {
  'use strict';
  const validNumber = n => Number.isSafeInteger(n) && n >= 0;
  function validResult(value) {
    return value && validNumber(value.row_count) && validNumber(value.column_count) &&
      Array.isArray(value.columns) && value.columns.length === value.column_count &&
      value.columns.every(column => column && typeof column.name === 'string' &&
        validNumber(column.missing_count) && column.missing_count <= value.row_count);
  }
  function messageFor(status, payload) {
    if (status === 403) return 'Не удалось выполнить анализ. Попробуйте ещё раз.';
    const error = payload && payload.error;
    const details = error && error.details && typeof error.details === 'object' ? error.details : {};
    switch (error && error.code) {
      case 'empty_csv': return 'Файл пуст или в заголовке нет столбцов. Выберите исправленный файл.';
      case 'invalid_encoding': return 'Не удалось прочитать файл. Сохраните его в кодировке UTF-8 и выберите снова.';
      case 'invalid_structure': {
        const numbers = ['record', 'expected_fields', 'actual_fields'];
        const more = numbers.every(k => validNumber(details[k])) && details.record >= 1
          ? ` Запись ${details.record}: ожидалось ${details.expected_fields} полей, получено ${details.actual_fields}.` : '';
        return 'Не удалось прочитать структуру CSV. Проверьте кавычки и число полей.' + more + ' Выберите исправленный файл.';
      }
      case 'limit_exceeded': {
        const kinds = { file_bytes: ['размер файла', 'bytes'], columns: ['число столбцов', 'columns'], rows: ['число записей', 'rows'], field_bytes: ['размер поля', 'bytes'] };
        const kind = kinds[details.kind];
        const limit = kind && details.unit === kind[1] && validNumber(details.limit)
          ? ` Предел: ${kind[0]} — ${details.limit} ${details.unit === 'bytes' ? 'байт' : details.unit === 'columns' ? 'столбцов' : 'записей'}.` : '';
        return 'Файл превышает ограничения анализа.' + limit + ' Уменьшите файл и выберите его снова.';
      }
      case 'invalid_request': case 'unsupported_media_type': return 'Не удалось отправить файл на анализ. Попробуйте ещё раз.';
      default: return status === 413 ? 'Файл превышает допустимый размер. Уменьшите файл и выберите его снова.' : 'Не удалось выполнить анализ. Попробуйте ещё раз.';
    }
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = { validResult, messageFor };
  if (typeof document === 'undefined') return;

  const file = document.getElementById('file');
  const fileLabel = document.getElementById('file-label');
  const fileName = document.getElementById('file-name');
  const analyze = document.getElementById('analyze');
  const status = document.getElementById('status');
  const error = document.getElementById('error');
  const result = document.getElementById('result');
  const resultFile = document.getElementById('result-file');
  const rows = document.getElementById('rows');
  const columns = document.getElementById('columns');
  const list = document.getElementById('column-list');
  let selected = null, attempt = 0, loading = false;

  function reset() {
    result.hidden = true;
    error.hidden = true;
    error.textContent = '';
    resultFile.textContent = '';
    list.replaceChildren();
  }
  file.addEventListener('change', () => {
    const chosen = file.files && file.files[0];
    if (!chosen) return;
    selected = chosen;
    file.value = '';
    attempt++;
    loading = false;
    reset();
    fileName.textContent = chosen.name;
    fileLabel.textContent = 'Выбрать другой файл';
    analyze.disabled = false;
    status.textContent = 'Файл выбран. Нажмите «Анализировать».';
  });
  function showResult(data) {
    rows.textContent = String(data.row_count);
    columns.textContent = String(data.column_count);
    resultFile.textContent = selected.name;
    list.replaceChildren();
    data.columns.forEach((column, index) => {
      const row = document.createElement('li'); row.className = 'column-row';
      const name = document.createElement('div'); name.className = 'column-name';
      const position = document.createElement('span'); position.className = 'column-position'; position.textContent = `${index + 1}.`;
      name.append(position, document.createTextNode(column.name === '' ? 'Без имени' : column.name));
      if (index === 0 && column.name.startsWith('\ufeff')) {
        const bom = document.createElement('span'); bom.textContent = ' (BOM)'; name.append(bom);
      }
      if (data.row_count > 0 && column.missing_count === data.row_count) {
        const note = document.createElement('span'); note.className = 'column-note'; note.textContent = 'Все значения пусты'; name.append(note);
      }
      const count = document.createElement('span'); count.className = 'column-count'; count.textContent = `${column.missing_count} пропусков`;
      row.append(name, count); list.append(row);
    });
    result.hidden = false;
    status.textContent = data.row_count === 0 ? 'Анализ завершён. В файле нет строк данных.' : 'Анализ завершён.';
  }
  analyze.addEventListener('click', async () => {
    if (!selected || loading) return;
    const current = ++attempt;
    loading = true; analyze.disabled = true; reset();
    status.textContent = 'Анализируем файл…';
    try {
      const form = new FormData(); form.append('file', selected);
      const response = await fetch('/api/analysis', { method: 'POST', headers: { 'X-Csvpeek-Request': '1' }, body: form });
      let payload = null;
      try { payload = await response.json(); } catch (_) { /* The server may return a non-JSON error. */ }
      if (current !== attempt) return;
      if (!response.ok) throw new Error(messageFor(response.status, payload));
      if (!validResult(payload)) throw new Error('Не удалось выполнить анализ. Попробуйте ещё раз.');
      showResult(payload);
    } catch (err) {
      if (current !== attempt) return;
      status.textContent = '';
      error.textContent = err instanceof TypeError ? 'Не удалось связаться с сервисом анализа. Проверьте соединение и попробуйте ещё раз.' : (err.message || 'Не удалось выполнить анализ. Попробуйте ещё раз.');
      error.hidden = false;
    } finally {
      if (current === attempt) { loading = false; analyze.disabled = false; }
    }
  });
})();
