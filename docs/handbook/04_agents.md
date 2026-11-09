# 4. Подробный разбор агентов

В этом разделе каждый агент описан по одной схеме: зачем он нужен, какие
данные получает, что делает по шагам, что отдаёт, где лежит код и какие у него
ограничения.

## 4.1. LeadAIAgent (`LiteratureAgent`)

**Файл:** `lit_graph/agent/core.py`.
**Роль:** Lead AI Engineer.
**Смысл:** это «продюсер» проекта. Он не ищет статьи и не пишет заметки
вручную; он собирает workflow, запускает его, печатает прогресс и сохраняет
итог.

### Что получает

- `base_id`, `topic`, `requirements`, `citation_format`;
- путь к vault;
- `max_papers`, `deep_scan`;
- объекты `RetrievalAgent`, `PromptAgent`, `EvaluationAgent`;
- LLM-провайдер и поисковый движок.

### Что делает при create

1. Открывает vault и создаёт `GraphAgent`.
2. Создаёт пустой `LiteratureBaseState` с `created_at`/`updated_at`.
3. Формирует начальный `ResearchState`: режим `create`, тема, требования,
   `queries=[topic]`, пустые кандидаты, `seen_ids=[]`.
4. Собирает `LiteratureWorkflow`, компилирует граф с `MemorySaver`.
5. Запускает `graph.stream(...)` и обновляет прогресс-бар по имени узла.
6. Забирает финальное состояние через `graph.get_state(config).values`.
7. Преобразует `final["base"]` обратно в `LiteratureBaseState`.
8. Печатает таблицу выбранных статей: ранг, название, цитирования, score,
   weight.
9. Печатает итоговую панель: vault, число источников, концептов, связей.
10. Показывает QA-отчёт.

### Что делает при update

1. Биндит существующий vault к `GraphAgent`.
2. Обновляет `updated_at`.
3. Формирует `combined_topic = state.topic + directive`.
4. Запускает workflow в режиме `update` с `queries=[directive]`.
5. Считает, сколько статей добавилось.
6. Показывает QA.

Ключевая деталь: Lead не удаляет старые статьи и не перезаписывает
существующие определения. Он добавляет новое, а `GraphAgent` сохраняет
старое.

### Методы

- `initialize_base(...)` — создать базу.
- `update_base(...)` — расширить базу.
- `flush_to_vault(...)` — принудительно записать vault (используется в CLI).
- `team_table()` — таблица ролей для `litgraph --team`.
- `_run_graph(...)` — общая сборка/запуск workflow.
- `_display_plan(...)` — печать выбранного поискового плана.
- `_report_qa()` — краткий отчёт QA в консоль.

### Ограничения

- Lead не валидирует научное качество сам; это делает Prompt/QA.
- Lead не гарантирует, что статей ровно `max_papers`: validation и elbow
  могут выбрать меньше.
- Lead не спасает от плохой модели: если LLM стабильно ошибается, это
  видно в QA и метриках, но автоматически не исправляется.

## 4.2. RetrievalAgent

**Файл:** `lit_graph/agent/retrieval_agent.py`, клиенты в `lit_graph/search/`.
**Роль:** Data / IR Engineer.
**Смысл:** найти кандидатов, не потерять метаданные, не натащить дубликатов и
подготовить данные для валидации и ранжирования.

### Каталог движков

`search/tools.py` описывает движки как данные:

- ключ (`semantic_scholar`, `arxiv`, `web`);
- название и краткое описание;
- сильные и слабые стороны;
- лучшие сценарии.

`catalog()` возвращает список для CLI `--tools`; `catalog_prompt()` — текст
для LLM, чтобы модель выбирала движки не «из головы», а из описаний.

### plan_request

`plan_request(task, requirements, context)` решает, нужен ли LLM для выбора
движков. Если пользователь передал `--engines`, LLM не нужен: план строится
вручную. Если `--no-router`, используется эвристика. Иначе возвращается
`needs_llm=True`, и workflow идёт в `choose_engines`.

### finalize_plan

`finalize_plan(decision, task, requirements, source)` вызывает `SearchRouter`:

1. нормализует ключи движков;
2. отбрасывает неизвестные;
3. ограничивает число primary (`SEARCH_ROUTER_MAX_PRIMARY`);
4. подбирает fallback, если модель его не дала;
5. сохраняет rationale и source.

Если ответ модели невалиден, router строит эвристический план. План
записывается в `base.search_plan` и печатается пользователю.

### search

`search(query, top_k, engines, fallback_engines, min_results)`:

1. ищет в primary-движках;
2. если результатов меньше `min_results`, добавляет fallback;
3. объединяет метаданные;
4. дедуплицирует по DOI/URL/названию;
5. возвращает кандидатов с `source_engine`.

В workflow поиск повторяется до 3 раундов. Если статей мало, LLM генерирует
sub-queries, и цикл `search → validate` повторяется. `seen_ids` не даёт
бесконечно возвращать одних и тех же кандидатов.

### merge_metadata

`merge_metadata(existing, incoming)` аккуратно сливает записи: не затирает
непустые поля пустыми, дополняет отсутствующие. Это важно, потому что arXiv
может дать abstract, а Semantic Scholar — citation counts.

### expand_citations

`expand_citations(paper_id, limit)` получает references и citations. В
workflow они превращаются в рёбра `cites` и сохраняются в `Paper`:

- `referenced_paper_titles`;
- `citing_paper_titles`.

Внешние работы, которых нет в базе, позже получат stub-заметки.

### fetch_pages

`fetch_pages(doi_or_url, pdf_url)` скачивает open-access PDF, извлекает текст
постранично и возвращает `{page: text}`. Используется только в `--deep`.
Если PDF нет или он защищён, deep-режим деградирует: grounding пропускается,
статья всё равно попадает в базу.

### Кэш и retry

`utils/http.py` и `utils/cache.py` дают:

- таймауты;
- retry/backoff для 429/5xx;
- дисковый кэш поисков и цитирований;
- TTL (`CACHE_TTL_HOURS`);
- отключение через `--no-cache`.

### Ограничения

- Качество зависит от внешних API; при их недоступности база будет меньше.
- Open web шумный; его спасает валидация и ранжирование.
- Citation counts могут быть неполными или устаревшими.
- Дедупликация по названию может склеить разные работы с одинаковым названием;
  поэтому DOI/URL имеют приоритет.

## 4.3. PromptAgent и LLM-слой

**Файлы:** `lit_graph/agent/prompt_agent.py`, `validator.py`,
`synthesizer.py`, `lit_graph/llm/`.
**Роль:** LLM Engineer.
**Смысл:** превратить «сырой» текст статьи в структурированные данные и
определения, устойчиво к плохому JSON и ограничениям локальной модели.

### Провайдеры

`llm/base.py` задаёт интерфейс, `providers.py` — реализацию для
OpenAI-совместимых API. Поддерживаются DeepSeek, OpenAI, Groq, OpenRouter,
Ollama, vLLM. Переключение — через `.env`:

```bash
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen3.5:4b
```

Провайдер отвечает за таймауты, повторы, температуру и опциональный кэш
ответов по хэшу промпта.

### Валидация

`LiteratureValidator.validate_candidate(paper, topic, requirements)` делает
один консолидированный LLM-проход:

- тема релевантна?
- требования выполнены?
- какова научная ценность?

Результат пишется в `Paper`:

- `topic_relevance_score`, `topic_relevance_reason`;
- `requirements_met`, `requirements_reason`;
- `scientific_value_score`.

Кандидат, не прошедший порог, не попадает в выборку, но причина остаётся в
логах/состоянии для отладки.

### Синтез статьи

`LiteratureSynthesizer.synthesize_paper_content(paper)` вызывает
`paper_synthesis_prompt` и заполняет:

- `summary_en` — executive summary;
- `key_findings_en` — ключевые находки;
- `methodology_en` — методология;
- `limitations_en` — ограничения;
- `extracted_concepts` — концепты (до `MAX_CONCEPTS_PER_PAPER`);
- `extracted_concepts_all` — все концепты до усечения, чтобы повторная
  каноникализация при `--update` не теряла идеи.

Промпт v2 просит 6–8 конкретных концептов, явно упомянутых в абстракте. Это
дало заметный прирост F1 на SciERC (см. раздел 7).

### JSON-устойчивость

`_sanitize_and_parse_json`:

1. убирает `<think>`/`<thought>`-блоки;
2. снимает markdown-обёртку ```json;
3. пытается `json.loads`;
4. если не вышло — ищет самый большой валидный объект/массив в тексте;
5. при пустом результате логирует предупреждение.

Это не «делает модель умнее», но спасает от типичных локальных моделей,
которые добавляют комментарии или обрезают JSON.

### Батчинг

- `CONCEPT_BATCH_SIZE` — сколько концептов определять за один запрос.
- `BIBLIOGRAPHY_BATCH_SIZE` — сколько источников форматировать за раз.

Батчинг нужен, чтобы ответ не обрезался по лимиту токенов. Без него большие
базы получали бы половину пустых определений.

### Определения концептов

`synthesize_all_concept_hubs_batch(state)` берёт концепты без определения и
просит модель написать 2-предложения. Определения сохраняются в
`ConceptHub.summary_en`. При `--update` существующие определения не
перезаписываются.

### Библиография, связи, обзор

- `harmonize_master_bibliography(state)` — единый формат цитат;
- `link_paper_network(state)` — типизированные связи между статьями;
- `build_overall_synthesis(state)` — общий обзор;
- `ground_concepts_to_pages(paper, pages)` — привязка концептов к страницам
  PDF в deep-режиме.

### Ограничения

- Локальные модели 3–4B ограничены: они путают термины и иногда добавляют
  лишние концепты.
- JSON-санитайзер восстанавливает структуру, но не факты.
- Промпт не заменяет эксперта: summary и findings нужно проверять.
- Определения концептов могут быть общими, если в базе мало контекста.

## 4.4. GraphAgent

**Файлы:** `lit_graph/agent/graph_agent.py`, `concepts.py`, `storage/`.
**Роль:** Graph & Knowledge Engineer.
**Смысл:** превратить состояние в связный Obsidian-vault и не потерять
пользовательские данные.

### rebuild_graph

`rebuild_graph(state, papers)`:

1. собирает концепты из статей;
2. канонизирует имена;
3. считает веса и aggregated score;
4. строит `paper → concept` и `concept → paper` связи;
5. сохраняет `state.concepts` и `state.edges`;
6. возвращает статистику: сколько концептов/рёбер.

### Каноникализация

`concepts.py`:

- `concept_key(name)` — ключ сравнения: lowercase, без пунктуации,
  parenthetical, с раскрытием известных акронимов и singularization;
- `display_name(name)` — человекочитаемое имя: smart title case, сохранение
  акронимов и mixed-case;
- `choose_display_names(names)` — выбирает самый частый вариант;
- `dedupe_concepts(names)` — убирает дубли.

Пример: `GNNs` → ключ `graph neural network`, display `Graph Neural Network`.

### Веса

Вес концепта зависит от числа упоминаний и наукометрического веса статей.
Нормализация в 0..1 позволяет использовать размер узла в graph view.
`MIN_CONCEPT_PAPERS` отсекает концепты, которые встретились меньше чем в N
статьях; это шумовой фильтр.

### flush

`flush(state, activity)`:

1. готовит имена файлов;
2. пишет заметки источников;
3. пишет концепт-хабы;
4. пишет внешние stubs;
5. пишет `_Overview_Synthesis.md`, `_Bibliography.md`,
   `Formatted_Bibliography.md`, `references.bib`;
6. пишет `_Agent_Activity.md`;
7. сохраняет `_state.json`.

### Имена и YAML

`ObsidianVaultManager`:

- `clean_name` убирает запрещённые символы;
- `_truncated_stem` обрезает слишком длинные имена и добавляет хэш;
- `_register` разрешает коллизии;
- `_yaml` экранирует значения, чтобы двоеточия и кавычки не ломали
  frontmatter.

### graph.json

Пресет графа Obsidian устанавливается при первом запуске и **сливается** с
пользовательскими настройками, а не перезаписывает их. Это важно: иначе
каждый запуск сбрасывал бы цвета и фильтры пользователя.

### Ограничения

- Каноникализация эвристическая: сложные синонимы могут не слиться.
- Слишком агрессивное слияние может объединить разные сущности.
- Graph view — визуализация, а не доказательство качества; QA проверяет
  ссылки, но не смысл связей.

## 4.5. EvaluationAgent

**Файлы:** `lit_graph/agent/evaluation_agent.py`, `qa/vault_checks.py`.
**Роль:** QA / Evaluation Engineer.
**Смысл:** независимо проверить, что vault и состояние не противоречат друг
другу.

### audit

`audit(state, vault_path)`:

1. `run_vault_checks(vault_path)` — проверки файлов и ссылок;
2. `run_state_checks(state)` — проверки данных;
3. merge отчётов;
4. логирование summary.

### Проверки vault

- `vault_missing` — папки нет;
- `vault_empty` — нет Markdown-файлов;
- `duplicate_stem` — одинаковые имена заметок;
- `missing_frontmatter` — нет YAML-блока;
- `missing_frontmatter_key` — не хватает обязательного ключа;
- `unknown_note_type` — неизвестный `type`;
- `unresolved_link` — `[[ссылка]]` не находит цель;
- `orphan_note` — заметка без входящих/исходящих ссылок;
- `empty_bibliography` — библиография пустая.

### Проверки состояния

- `no_papers` — база пустая;
- `missing_summary` — у статьи нет summary;
- `missing_citation` — нет форматированной цитаты;
- `no_concepts` — статья без концептов;
- `orphan_concept_link` — статья ссылается на концепт, которого нет в state;
- `missing_concept_definition` — у концепта нет определения;
- `concept_without_mentions` — концепт без статей;
- `empty_bibliography_state` — пустая библиография в state;
- `empty_overview` — пустой обзор;
- `duplicate_edge` — дубликат ребра;
- `unknown_edge_source` / `unknown_edge_target` — ребро ссылается на
  неизвестную статью.

### Severity

- `error` — критично, обычно ломает целостность;
- `warning` — подозрительно, но база может работать;
- `info` — заметка для диагностики.

`litgraph --check --id ...` печатает отчёт; в CI можно проверять наличие
errors.

### Ограничения

- QA проверяет структуру и целостность, а не научную истинность.
- Он не может понять, что статья нерелевантна, если LLM её пропустил.
- Он не заменяет бенчмарк качества извлечения.
