# LLM-слой: промпты, валидация и синтез

Документ описывает, как LitGraphAgent работает с моделью: какие промпты
существуют, как проверяется ответ и где включаются детерминированные
fallback-и. Общая схема — [ARCHITECTURE.md](ARCHITECTURE.md).

## 1. Единая точка промптов

Все промпты собраны в `lit_graph/llm/prompts.py`. Агенты не собирают длинные
строки у себя — они вызывают функцию вида
`paper_synthesis_prompt(...)` и передают результат провайдеру.

Системные роли заданы отдельными константами (`SYSTEM_REVIEWER`,
`SYSTEM_SYNTHESIZER`, `SYSTEM_ENCYCLOPEDIST` и т.д.), чтобы стиль ответа и
требование «только JSON» не дублировались в каждом вызове.

## 2. Провайдеры

`lit_graph/llm/base.py` задаёт интерфейс, `providers.py` — реализации.
Поддерживаются DeepSeek, OpenAI, Groq, OpenRouter, Ollama, vLLM и любой
OpenAI-совместимый endpoint. Переключение — через `.env`:

```bash
LLM_API_KEY=...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

Провайдер отвечает за таймауты, повторы и опциональный кэш ответов по хэшу
промпта (`LLM_CACHE_ENABLED`).

## 3. Основные операции

| Операция | Промпт | Результат |
| --- | --- | --- |
| Выбор движков | `engine_selection_prompt` | `primary` / `fallback` / обоснование |
| Валидация кандидата | `validation_prompt` | релевантность теме и требованиям |
| Синтез статьи | `paper_synthesis_prompt` | summary, findings, methodology, limitations, concepts |
| Определения концептов | `concept_definitions_prompt` | определения батчем |
| Grounding по PDF | `concept_grounding_prompt` | концепт + страница + фрагмент |
| Библиография | `bibliography_prompt` | форматированные цитаты батчем |
| Связи | `relations_prompt` | типизированные рёбра |
| Обзор | `review_prompt`, `merge_reviews_prompt` | master literature review |

## 4. Устойчивость к ответу модели

Локальные модели 3–4B часто добавляют markdown-обёртку, reasoning-блоки или
незакрытый JSON. Слой использует:

- извлечение первого валидного JSON-объекта из ответа;
- повторный запрос при ошибке разбора;
- батчинг, чтобы ответ не обрезался по лимиту токенов;
- детерминированные fallback-и: если модель не вернула поле, используется
  разумное значение по умолчанию вместо падения.

## 5. Валидация

`PromptAgent` объединяет проверку темы и требований в один вызов. Это
уменьшает число запросов и снимает рассинхронизацию между двумя отдельными
проверками. Результат сохраняется в `Paper`:

- `topic_relevance_score`, `topic_relevance_reason`;
- `requirements_met`, `requirements_reason`;
- `scientific_value_score`.

Кандидат, не прошедший порог, не попадает в итоговую выборку, но причина
остаётся в состоянии для отладки.

## 6. Синтез и концепты

`paper_synthesis_prompt` возвращает структуру, а не свободный текст. Это
позволяет:

- писать атомарную заметку без повторного парсинга;
- передавать концепты в каноникализацию;
- отдельно хранить `extracted_concepts` и `extracted_concepts_all`, чтобы
  повторная каноникализация при `--update` не теряла отфильтрованные идеи.

## 7. Проверка

```bash
pytest tests/test_synthesizer.py tests/test_validator.py tests/test_providers.py -q
```

Тесты покрывают JSON-парсинг, fallback-и, батчинг и поведение при ошибках
провайдера.
