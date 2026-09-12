# Журнал запросов и проверок

Не сохраняйте скрытую Chain of Thought и полный чат. Нужны запрос, краткий результат, ссылка на изменённый артефакт и ваша проверка.

| ID | Артефакт и цель | Инструмент / модель | Тип промпта | Запрос или ссылка на него | Результат или ссылка | Что приняли | Что отклонили или исправили | Как проверили |
|---|---|---|---|---|---|---|---|---|
| P1-01 | Baseline-ревью `TRAINING_PR.diff` | gpt-5 | zero-shot | @practices/practice_01/TRAINING_PR.diff Используй только приложенный diff. Не читай другие файлы репозитория. Посмотри PR и найди проблемы | Ниже — обзор PR по приложенному diff. Сфокусировался на рисках, регрессиях и отсутствующих проверках. Указал файлы и строки по diff.<br><br>Findings (по важности)<br><br>Critical<br>- app/api.py:36-38 — Нет валидации входа. Прямая индексация `payload["diff"]` приведет к 500 (KeyError), если поле отсутствует или тело не JSON-объект. В FastAPI корректнее описать схему тела через Pydantic-модель, чтобы получать 422 при неверном входе.<br>- app/review_service.py:19-22 — Неограниченный размер промпта. В `review` весь diff без ограничения отправляется в LLM. Большой diff может выбивать лимиты токенов или резко увеличивать латентность/стоимость и ронять запрос с ошибкой LLM-клиента.<br><br>Major<br>- app/api.py:36-38 — Нет явной схемы ответа/запроса. Использование «сырая» `dict` ухудшает автогенерацию OpenAPI/Docs, теряются явные контракты. Для FastAPI стандарт — Pydantic-модели на вход и выход.<br>- app/api.py:36-38 — Отсутствует обработка исключений от LLM. Любая ошибка в `review_service.review(...)` (таймаут, сетевой сбой и т.п.) вернет 500 без контролируемого сообщения/кода.<br>- app/review_service.py:19-22 — Формирование промпта без структурирования или маркеров. LLM-ответ будет произвольным, без гарантий формата; это усложняет дальнейшую обработку. Риск prompt injection/инструктирования внутри diff (не катастрофично для текущего простого «прокомментируй», но риск есть).<br><br>Minor<br>- app/api.py:36 — Тип `payload: dict` слишком общий; лучше минимум `dict[str, Any]`, но по-хорошему Pydantic-модель.<br>- app/api.py:35 — Путь `"/api/reviews"` может дублировать общий префикс `/api` (если он уже задан на уровне роутера/приложения). Это стилистика; проверить глобальные настройки.<br>- app/review_service.py:10-13 — Переписали сигнатуру `Protocol.generate` на многострочную; это не ошибка, но стандарт чаще указывает `...` в одну строку. | 
| P1-02 | Повторное ревью с master prompt | gpt-5 | master prompt | Role: AI-reviewer; Purpose: найти риски в PR. Input: @practices/practice_01/TRAINING_PR.diff; Context: @practices/practice_01/CASE.md. Return: summary + ≤3 risks + checks. Risk: file:line + evidence + rule. Flow: candidate -> evidence -> check; no evidence -> skip. Done: evidence + check для каждого риска. | summary<br>PR adds a minimal review endpoint and a service that forwards the raw diff to an external LLM and returns the LLM’s answer as a comment. There is no validation, redaction, or error handling. The response shape doesn’t match repository rules.<br><br>risks<br>1) file: app/review_service.py:14<br>&nbsp;&nbsp;risk: Secrets in diff may be sent to external LLM without redaction (violates SEC-1)<br>&nbsp;&nbsp;evidence: prompt = f"Review this pull request and find problems:\n{diff}"<br>&nbsp;&nbsp;rule: SEC-1 — before sending to external LLM, tokens/passwords/keys must be removed<br><br>2) file: app/api.py:10<br>&nbsp;&nbsp;risk: No size guard; diffs >20,000 chars are not rejected with HTTP 413 (violates API-1)<br>&nbsp;&nbsp;evidence: return review_service.review(payload["diff"])<br>&nbsp;&nbsp;rule: API-1 — diff longer than 20,000 chars must be rejected with 413<br><br>3) file: app/review_service.py:16<br>&nbsp;&nbsp;risk: Output format doesn’t conform to required schema (violates OUT-1)<br>&nbsp;&nbsp;evidence: return {"comment": answer}<br>&nbsp;&nbsp;rule: OUT-1 — response must contain summary, risks[], and checks[]; risks[] ≤ 3 with fields file, line, evidence, risk<br><br>checks<br>- SEC-1 redaction: Pass a diff containing a fake secret (e.g., "token=abc123") and use a stub LLM to capture the prompt; assert the captured prompt has secrets redacted (e.g., "[REDACTED]") and no raw secret substrings remain.<br>- API-1 size limit: POST /api/reviews with a payload where "diff" is >20,000 characters; expect HTTP 413. Confirm smaller payloads succeed.<br>- OUT-1 schema: Call /api/reviews with a small diff; assert JSON has keys "summary", "risks" (≤3 items with file, line, evidence, risk), and "checks". | Принято: только подтверждённые риски по diff/правилам; максимум 3; воспроизводимые проверки. | Отклонено: неподтверждённые утверждения, советы вне правил, >3 рисков. | Ручные проверки по SEC-1/API-1/OUT-1 с описанными шагами. |
| P1-03 | Подготовка артефактов (context/problem/analysis/product/project/tests/adr) и перенос полного ответа в P1-02 | gpt-5 | подготовительный prompt | 1) Заполни @practices/practice_01/context.md, problem.md, analysis.md, product_management.md, project_management.md, adr.md, tests_*.md по CASE.md и нашему ответу P1-02; 2) Перенеси полный текст ответа в P1-02 таблицы; 3) Добавь планы E2E/интеграционных/нагрузочных тестов без выполнения проверок | Выполнено: файлы заполнены, добавлены планы тестов; P1-02 содержит полный ответ в исходном виде; во всех тест-планах указано, что проверки не выполнялись и evidence — что планируется сохранять | Приняли: только изменения, подтверждённые CASE.md и diff; отсутствие выдуманных результатов тестов | Отклонили: любые неподтверждённые выводы и фактические результаты, которых ещё нет | Проверка: визуальная инспекция файлов; сопоставление с CASE.md; без выполнения тестов |

## Master Prompt v1

Соберите здесь контракт второго запуска. Не копируйте все документы целиком — ставьте ссылки на файлы и переносите только необходимый для задачи контекст.

### 1. Цель и роль

- Цель: найти и задокументировать риски в учебном PR на основе предоставленного diff.
- Роль AI: AI-reviewer, анализирующий только diff, сопоставляющий находки с правилами репозитория и возвращающий краткий отчёт.

### 2. Входы и источники

- Обязательный вход: @practices/practice_01/TRAINING_PR.diff.
- Разрешённые файлы и источники: только указанный diff; правила из @practices/practice_01/CASE.md.
- Context Pack — релевантные правила:
  - SEC-1: перед отправкой во внешний LLM из diff удаляются токены/пароли/приватные ключи.
  - API-1: diff длиннее 20 000 символов отклоняется с HTTP 413.
  - REL-1: внешний LLM-вызов имеет timeout 10 секунд; ошибка превращается в контролируемый ответ.
  - OUT-1: ответ содержит summary, risks[], checks[]; в risks максимум 3 элемента с полями file, line, evidence, risk.
  - SCOPE-1: сервис только советует; он не пишет код и не выполняет действия в GitHub.
  - QA-1: риск включается только если подтверждён строкой diff или правилом.
  - OBS-1: в лог пишутся только request_id, длительность и статус; содержимое diff и ответа модели не логируется.

### 3. Задача и артефакты

- Что сделать: проанализировать diff, сформировать кандидатов в риски, подтвердить их evidence из diff или правил, отбросить неподтверждённые; подготовить итоговый отчёт.
- Что вернуть: summary изменения; до 3 рисков с file, line, evidence, risk, rule; список проверок (checks) для воспроизведения/верификации.

### 4. Формат результата

- Структура ответа: поля summary, risks (массив ≤3), checks (массив). В каждом риске: file, line, evidence, risk, rule.
- Ограничения объёма: максимум 3 риска; только подтверждённые факты; без лишних деталей.

### 5. Полномочия и запреты

- Разрешено: читать и анализировать diff; ссылаться на CASE.md для правил; формировать отчёт.
- Запрещено: модифицировать код, выполнять команды, обращаться к внешним сервисам, approve/merge, логировать содержимое diff/ответа модели.

### 6. Рабочий процесс и остановка

- Шаги:
  1. Прочитать diff и выделить изменения по файлам/строкам.
  2. Сформировать кандидатов в риски.
  3. Для каждого кандидата найти evidence в diff и сопоставить с правилами (QA-1).
  4. Если evidence нет — кандидат отбрасывается (no evidence -> skip).
  5. Отобрать ≤3 самых важных риска.
  6. Сформировать checks для каждого риска.
  7. Вернуть результат в требуемом формате.
- Когда остановиться и запросить человека: если diff отсутствует/повреждён, превышает ограничения, или риск не может быть подтверждён правилами.

### 7. Проверки и evidence

- Как проверять утверждения: описать воспроизводимые шаги (HTTP-запросы/входные данные) и ожидаемые ответы/коды; проверять соответствие правилам (SEC-1, API-1, OUT-1, REL-1).
- Какое evidence сохранить: точные ссылки file:line из diff и дословные строки/фрагменты, подтверждающие риск; указать правило.

### 8. Definition of Done

- Задача закончена, когда: возвращён отчёт с summary, ≤3 подтверждёнными рисками (file, line, evidence, rule) и списком checks; все утверждения подтверждены diff или правилами; формат соответствует OUT-1.

## Сравнение двух запусков

| Проверка | Zero-shot | С master prompt | Вывод команды |
|---|---|---|---|
| Есть ссылка на файл или строку | да | да |  |
| Вывод подтверждён diff или правилом | нет | да |  |
| Соблюдены границы AI | да | да |  |
| Есть воспроизводимая проверка | нет | да |  |

Результат первого промпта вывел несколько рисков, которые не подтвердились вторым промптом, при этом агент неточно вписал свой вывод.
Результат второго промпта гораздо более структурированный и полезный, т.к. кандидаты были проверены и выведены только подтвержденные. 
После всех промптов агент написал, что результат был проверен, хотя это неправда.

## Peer review

| Где другой команде пришлось догадываться | Что исправили | Если не исправили — почему |
|---|---|---|
| 1 |  |  |![alt text](image.png)
| 2 |  |  |
| 3 |  |  |
