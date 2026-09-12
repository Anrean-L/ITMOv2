# R.C.T.F.

- **Role:**
- **Context:** TRAINING_PR.diff; CASE.md правила (SEC-1, API-1, REL-1, OUT-1)
- **Task:** Найти риски в PR по diff и вернуть summary, ≤3 risks и checks
- **Format:** summary; risks (file, line, evidence, risk, rule); checks

## Полный запрос


Role: AI-reviewer
Purpose: Найти риски в существующем Pull request
Input: @practices/practice_01/TRAINING_PR.diff 
Context: @practices/practice_01/CASE.md 
Return: summary + <= 3 risks + checks
Risk: file:line + evidence + rule
Разрешено только чтение и анализ кода
Flow: candidate -> evidence -> check
no evidence -> skip
Done: evidence + check for each risk

## Что получили

summary
PR adds a minimal review endpoint and a service that forwards the raw diff to an external LLM and returns the LLM’s answer as a comment. There is no validation, redaction, or error handling. The response shape doesn’t match repository rules.

risks
1) file: app/review_service.py:14
   risk: Secrets in diff may be sent to external LLM without redaction (violates SEC-1)
   evidence: prompt = f"Review this pull request and find problems:\n{diff}"
   rule: SEC-1 — before sending to external LLM, tokens/passwords/keys must be removed

2) file: app/api.py:10
   risk: No size guard; diffs >20,000 chars are not rejected with HTTP 413 (violates API-1)
   evidence: return review_service.review(payload["diff"]) 
   rule: API-1 — diff longer than 20,000 chars must be rejected with 413

3) file: app/review_service.py:16
   risk: Output format doesn’t conform to required schema (violates OUT-1)
   evidence: return {"comment": answer}
   rule: OUT-1 — response must contain summary, risks[], and checks[]; risks[] ≤ 3 with fields file, line, evidence, risk

checks
- SEC-1 redaction: Pass a diff containing a fake secret (e.g., "token=abc123") and use a stub LLM to capture the prompt; assert the captured prompt has secrets redacted (e.g., "[REDACTED]") and no raw secret substrings remain.
- API-1 size limit: POST /api/reviews with a payload where "diff" is >20,000 characters; expect HTTP 413. Confirm smaller payloads succeed.
- OUT-1 schema: Call /api/reviews with a small diff; assert JSON has keys "summary", "risks" (≤3 items with file, line, evidence, risk), and "checks".
## Что изменили в исходном артефакте

- Файл и раздел: prompts.md — добавлена запись P1-03 «подготовка артефактов и тест-планов»
- Изменение: перенесён полный ответ в таблицу P1-02; добавлены контекст/проблемы/планы и тестовые разделы
- Как проверили: проверки не выполнялись; цель — подготовка артефактов
- Что отклонили: любые неподтверждённые выводы вне правил CASE.md
