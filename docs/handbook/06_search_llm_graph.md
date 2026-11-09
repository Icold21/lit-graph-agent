# 6. Как устроены поиск, LLM и граф

Этот раздел — «начинка» трёх самых важных подсистем. Здесь меньше слов о роли
агентов и больше о том, как именно принимаются решения.

## 6.1. Поиск и выбор движков

### Каталог как данные

В `search/tools.py` каждый движок описан структурой:

- `key` — `semantic_scholar`, `arxiv`, `web`;
- `name` — человекочитаемое имя;
- `description` — что это;
- `strengths` — чем хорош;
- `weaknesses` — где ошибается;
- `best_for` — типовые задачи.

Модель получает этот каталог текстом и возвращает JSON:

```json
{
  "primary": ["arxiv", "semantic_scholar"],
  "fallback": ["web"],
  "reason": "Fresh preprints plus citation metadata; web only as a fallback."
}
```

### SearchRouter

`search/router.py` не доверяет ответу модели напрямую:

1. проверяет, что ключи известны;
2. нормализует регистр и пробелы;
3. убирает дубликаты;
4. ограничивает primary;
5. гарантирует непустой fallback;
6. сохраняет `source` (`llm`, `manual`, `heuristic`).

Если модель вернула мусор, router строит эвристику. Если пользователь передал
`--engines`, LLM вообще не вызывается. Если `--no-router`, используется
эвристика.

### Почему не «опросить всё»

Опросить все движки сразу — дорого и шумно. Модель выбирает 1–2 primary и
fallback, исходя из темы. Например, для свежих preprint-ов лучше arXiv, для
цитатной наукометрии — Semantic Scholar, для узких веб-источников — web.

### Дедупликация

Кандидаты приходят из разных источников. `merge_metadata` и дедупликация:

- сравнивают DOI;
- сравнивают URL;
- сравнивают нормализованное название;
- сохраняют более полные метаданные;
- не затирают непустые поля пустыми.

### Ранжирование

`compute_scientific_metrics(paper)` считает:

```text
age = max(1, current_year - year)
velocity = citation_count / age
influential_ratio = (influential_citations + 1) / (citations + 1)
log_volume = log10(citations + 1)
score = min(velocity, 100) * 0.40
      + log_volume * 4.0
      + influential_ratio * 10.0 * 0.25
```

Смысл компонентов:

- **velocity** — свежесть и скорость набора цитирований;
- **log_volume** — общий объём цитирований, сжатый логарифмом, чтобы
  мега-цитируемые работы не доминировали;
- **influential_ratio** — доля влиятельных цитирований.

Веса (40/35/25 в комментарии, но в коде log-компонент масштабирован на 4.0)
эвристические. Они не откалиброваны на размеченном наборе; это честно
зафиксировано в отчёте.

### Elbow cutoff

`find_elbow_cutoff(scores, min_k, max_k)`:

1. сортирует scores по убыванию;
2. считает drops между соседними;
3. считает curvature = drops[i] - drops[i+1];
4. выбирает максимальную положительную кривизну;
5. ограничивает результат `min_k..max_k`.

Идея: в голове списка scores падают медленно, затем резко, затем хвост
выравнивается. «Локоть» — граница головы. Это не строгая статистика, а
эвристика для отсечения низкоимпактного хвоста.

### Кэш и retry

`utils/http.py`:

- таймауты;
- retry с backoff на 429/5xx;
- единый User-Agent.

`utils/cache.py`:

- дисковый кэш поисков и цитирований;
- TTL;
- отключение через `--no-cache`.

Кэш важен для воспроизводимости и скорости: повторный запуск не дёргает API
заново.

### PDF

`search/pdf_extractor.py`:

- проверяет размер;
- извлекает текст постранично;
- ограничивает объём;
- возвращает `{page: text}`.

В deep-режиме текст страниц идёт в grounding-промпт. Если PDF нет, deep
деградирует, но не ломает запуск.

## 6.2. LLM-слой

### Провайдеры

`llm/base.py` — интерфейс `generate`/`generate_json`.
`llm/providers.py` — OpenAI-совместимый клиент. Он работает с любым
endpoint, который поддерживает `/chat/completions`.

Профили:

```bash
# Ollama
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen3.5:4b

# DeepSeek
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

### Промпты

`llm/prompts.py` — единая точка. Основные:

| Функция | Назначение |
| --- | --- |
| `engine_selection_prompt` | выбрать primary/fallback |
| `sub_queries_prompt` | сгенерировать подзапросы |
| `validation_prompt` | тема + требования |
| `paper_synthesis_prompt` | summary, findings, methodology, limitations, concepts |
| `concept_definitions_prompt` | определения концептов |
| `concept_grounding_prompt` | привязка к страницам PDF |
| `bibliography_prompt` | форматирование цитат |
| `relations_prompt` | типизированные связи |
| `review_prompt` / `merge_reviews_prompt` | обзор |

Важно: `LiteratureSynthesizer` использует `paper_synthesis_prompt`, поэтому
формулировка живёт в одном месте. Раньше был дубликат inline-промпта; его
убрали, иначе изменения в `prompts.py` не влияли на бенчмарк.

### JSON-санитайзер

Локальные модели часто возвращают:

- `<think>...</think>` перед JSON;
- ```json ... ```;
- комментарии;
- обрезанный JSON.

`_sanitize_and_parse_json`:

1. удаляет reasoning-блоки;
2. снимает code fence;
3. пробует `json.loads`;
4. ищет самый большой валидный объект/массив;
5. возвращает `{}` при полной неудаче и логирует.

Это делает пайплайн устойчивым, но не гарантирует правильность фактов.

### Батчинг

- `CONCEPT_BATCH_SIZE=12` — определения концептов;
- `BIBLIOGRAPHY_BATCH_SIZE=20` — цитаты.

Батчинг уменьшает риск обрезания ответа и позволяет большим базам
обрабатываться частями.

### Промпт v2 для концептов

Старый промпт просил JSON с тремя примерами концептов и не задавал
количество. Модель выдавала в среднем 5.75 концепта, часто общих.

Новый промпт:

- просит 6–8 конкретных концептов;
- требует, чтобы они были явно упомянуты;
- просит methods/tasks/metrics/materials/datasets/technical terms;
- запрещает generic-слова и дубликаты;
- ставит `extracted_concepts` первым в JSON.

Результат на 20 абстрактах:

- average concepts: 5.75 → 8.0;
- exact F1: 0.349 → 0.422;
- relaxed F1: 0.501 → 0.583;
- content relaxed F1: 0.549 → 0.629.

Цена — время: 1836.9 → 3571.0 секунд на 20 абстрактов (~179 с на абстракт).

### Валидация

Один консолидированный вызов проверяет тему и требования. Это дешевле и
меньше рассинхронизирует два отдельных прохода. Результат сохраняется в
`Paper`; кандидат, не прошедший порог, отбрасывается.

### Синтез

`paper_synthesis_prompt` возвращает структуру, а не свободный текст. Это
позволяет:

- писать заметку без повторного парсинга;
- передавать концепты в каноникализацию;
- хранить полный и усечённый список концептов;
- повторно канонизировать при `--update`.

## 6.3. Граф и каноникализация

### Зачем каноникализация

LLM возвращает `Transformer`, `Transformers`, `GNN`, `GNNs`,
`Graph Neural Networks (GNNs)`. Без слияния это четыре разных узла, и граф
теряет смысл.

`concepts.py`:

- `_normalize_whitespace`;
- `_strip_edges`;
- `_singularize_word` с учётом uncountable;
- `_strip_parenthetical` (оставляет описательную часть, если она длиннее
  аббревиатуры);
- `ABBREVIATIONS` (GNN, LLM, SAE, ViT, MLP, CNN, RNN, NLP, CoT);
- `concept_key` — ключ сравнения;
- `display_name` — человекочитаемое имя;
- `choose_display_names` — самый частый вариант;
- `dedupe_concepts` — уникальные пары `(key, display)`.

Пример:

```text
"Graph Neural Networks (GNNs)"
  key:     "graph neural network"
  display: "Graph Neural Network"
```

### Веса

Вес концепта зависит от:

- числа упоминаний;
- веса статей, где он встречается;
- агрегированного score.

Нормализация в 0..1 даёт размер узла в graph view. `MIN_CONCEPT_PAPERS`
отсекает концепты, которые встретились меньше чем в N статьях. Это снижает
шум, но может потерять редкие, но важные термины.

### Запись заметок

`ObsidianVaultManager.write_paper_note`:

- формирует frontmatter;
- добавляет citation, summary, findings, methodology, limitations;
- добавляет связи;
- добавляет typed relations;
- добавляет abstract.

`write_concept_note`:

- frontmatter с `concept`, `aggregated_score`, `node_weight`;
- определение;
- grounded citations с страницами и цитатами.

`write_external_stubs`:

- собирает внешние referenced/citing titles;
- создаёт лёгкие заметки, чтобы ссылки не повисали.

`write_hub_files`:

- `_Overview_Synthesis.md`;
- `_Bibliography.md`;
- `Formatted_Bibliography.md`;
- `references.bib`;
- `_Agent_Activity.md`.

### Безопасность имён и YAML

- `clean_name` убирает `/`, `\`, `:`, `*`, `?`, `"`, `<`, `>`, `|`;
- длинные имена обрезаются с хэшем;
- коллизии разрешаются суффиксом;
- `_yaml` экранирует значения;
- `graph.json` сливается, а не перезаписывается.

### Что может пойти не так

- Слишком агрессивная каноникализация объединит разные сущности.
- Слишком слабая — оставит дубли.
- `MIN_CONCEPT_PAPERS` может удалить редкий, но важный концепт.
- Graph view красив, но не доказывает семантическую правильность связей.

Именно поэтому QA и бенчмарк существуют отдельно от «выглядит красиво».
