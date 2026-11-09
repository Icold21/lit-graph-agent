# 7. QA, тесты и бенчмарк

## 7.1. Зачем отдельный QA-агент

LLM и внешние API ошибаются. Если писать vault без проверки, можно получить:

- `[[ссылки]]`, которые никуда не ведут;
- заметки без обязательного frontmatter;
- дубликаты имён;
- статьи, которые ссылаются на концепты, которых нет;
- пустую библиографию;
- «сиротские» заметки, до которых нельзя дойти по ссылкам.

QA-агент не мутирует данные. Он читает vault и состояние, собирает issues с
severity и отдаёт отчёт. Это позволяет использовать `litgraph --check` в CI и
на демонстрации.

## 7.2. Проверки vault

`qa/vault_checks.py` проходит по всем `.md` вне `.obsidian` и `.trash`:

- **vault_missing** — папки нет;
- **vault_empty** — нет Markdown-файлов;
- **duplicate_stem** — одинаковые имена заметок;
- **missing_frontmatter** — нет YAML-блока;
- **missing_frontmatter_key** — не хватает обязательного ключа;
- **unknown_note_type** — неизвестный `type`;
- **unresolved_link** — `[[ссылка]]` не находит цель;
- **orphan_note** — заметка без входящих/исходящих ссылок;
- **empty_bibliography** — в библиографии нет ссылок.

Обязательные ключи по типам:

| Тип | Ключи |
| --- | --- |
| `literature_note` | `title`, `type` |
| `concept_hub` | `concept`, `type` |
| `external_reference` | `title`, `type` |
| `synthesis_hub` | `topic`, `type` |
| `master_bibliography` | `citation_format`, `type` |
| `agent_activity` | `type` |

Статистика отчёта: `notes`, `sources`, `concepts`, `external_refs`, `links`,
`unresolved_links`, `orphans`.

## 7.3. Проверки состояния

`run_state_checks(state)` проверяет данные, а не файлы:

- **no_papers** — база пустая;
- **missing_summary** — нет summary;
- **missing_citation** — нет formatted citation;
- **no_concepts** — статья без концептов;
- **orphan_concept_link** — статья ссылается на отсутствующий hub;
- **missing_concept_definition** — у концепта нет определения;
- **concept_without_mentions** — концепт без статей;
- **empty_bibliography_state** — пустая библиография;
- **empty_overview** — пустой обзор;
- **duplicate_edge** — дубликат ребра;
- **unknown_edge_source** / **unknown_edge_target** — ребро ссылается на
  неизвестную статью.

Severity:

- `error` — критично;
- `warning` — подозрительно, но база может работать;
- `info` — диагностика.

`EvaluationAgent.audit` объединяет vault + state отчёты и логирует summary.

## 7.4. Тесты и CI

В проекте 55 тестов. Они покрывают:

- pipeline и агентов;
- персистентность `_state.json`;
- каноникализацию концептов;
- имена заметок;
- QA;
- батчинг;
- провайдеры и JSON-санитайзер;
- поисковый роутер;
- ранжирование;
- бенчмарк.

Команды:

```bash
pytest -q
ruff check lit_graph tests benchmarks
```

CI:

- GitHub Actions;
- Python 3.10, 3.11, 3.12, 3.13;
- `ruff` валит сборку при ошибках;
- `pytest` на push/PR.

CI не делает реальных сетевых вызовов и не запускает локальную LLM: E2E
проверяется локально, а CI ловит регрессии структуры и логики.

## 7.5. SciERC: что это

SciERC (Luan et al., EMNLP 2018) — стандартный бенчмарк для scientific
knowledge-graph construction. В нём 500 абстрактов научных статей с
аннотациями:

- сущности 6 типов: Task, Method, Metric, Material, Generic,
  OtherScientificTerm;
- типизированные отношения;
- coreference-кластеры.

Это не «граф вообще», а именно извлечение научных сущностей и связей из
текста. Поэтому SciERC релевантен LitGraphAgent, который тоже строит граф из
научных статей.

## 7.6. Что именно измеряет наш harness

`benchmarks/scierc_benchmark.py`:

1. загружает `.txt` + `.ann` из SciERC;
2. выбирает `limit` абстрактов с `seed`;
3. для каждого вызывает production `PromptAgent.synthesize_paper`;
4. сравнивает `extracted_concepts` с gold-упоминаниями;
5. считает concept P/R/F1 и paper→concept edges;
6. сохраняет JSON + JSONL checkpoint;
7. умеет resume после прерывания;
8. пишет failures, не роняя весь прогон.

Что **не** измеряется:

- типизированные отношения SciERC;
- coreference;
- span boundaries;
- relation extraction.

Причина: пайплайн не предсказывает типы отношений SciERC. Считать relation
F1 было бы фикцией. Это ограничение явно указано в README и отчёте.

## 7.7. Exact, relaxed и content-only

**Exact** — нормализованное равенство строк:

- lowercase;
- singularization;
- удаление пунктуации;
- удаление артиклей.

**Relaxed** — token Jaccard ≥ 0.5. Допускает модификаторы и сокращения:
`word sense disambiguation (WSD) systems` и `word sense disambiguation`
считаются совпадением.

**Content-only** — gold-сущности без типа Generic. Это отдельный сигнал:
Generic-слова (`system`, `method`, `approach`) часто шумят, и без них
метрика показывает содержательные концепты.

Метрики считаются micro: TP/FP/FN агрегируются по всем абстрактам, затем
считаются P/R/F1. Это стандартно для extraction, но нужно явно указывать.

## 7.8. Результаты на 20 абстрактах

Протокол:

- 20 абстрактов;
- `seed=42`;
- локальные модели через Ollama;
- production-вызов `PromptAgent.synthesize_paper`;
- 0 падений.

| Модель | Сигнал | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: |
| `qwen2.5:3b` | Concepts, exact | 0.538 | 0.254 | 0.345 |
| `qwen2.5:3b` | Concepts, relaxed | 0.723 | 0.341 | 0.464 |
| `qwen2.5:3b` | Content, relaxed | 0.706 | 0.402 | 0.512 |
| `qwen3.5:4b`, prompt v1 | Concepts, exact | 0.556 | 0.254 | 0.349 |
| `qwen3.5:4b`, prompt v1 | Concepts, relaxed | 0.800 | 0.365 | 0.501 |
| `qwen3.5:4b`, prompt v1 | Content, relaxed | 0.774 | 0.426 | 0.549 |
| `qwen3.5:4b`, prompt v2 | Concepts, exact | 0.544 | 0.345 | 0.422 |
| `qwen3.5:4b`, prompt v2 | Concepts, relaxed | 0.750 | 0.476 | 0.583 |
| `qwen3.5:4b`, prompt v2 | Content, relaxed | 0.725 | 0.555 | 0.629 |

![Метрики SciERC для qwen3.5:4b, prompt v2](../kp2/assets/metrics_qwen3.5-4b-prompt8.png)

Среднее число концептов:

- `qwen2.5:3b` — 5.95;
- `qwen3.5:4b` prompt v1 — 5.75;
- `qwen3.5:4b` prompt v2 — 8.0;
- gold — 12.6.

Время:

- `qwen2.5:3b` — 252.7 с;
- `qwen3.5:4b` prompt v1 — 1836.9 с;
- `qwen3.5:4b` prompt v2 — 3571.0 с (~179 с на абстракт).

## 7.9. Что дал prompt v2

Старый промпт не задавал количество концептов и показывал три примера. Модель
выдавала ~5.75 концепта, часто общих.

Новый промпт:

- просит 6–8 концептов;
- требует, чтобы они были явно упомянуты;
- покрывает methods/tasks/metrics/materials/datasets/technical terms;
- запрещает generic и дубликаты;
- ставит `extracted_concepts` первым в JSON.

Прирост:

- exact F1: +0.073;
- relaxed F1: +0.082;
- content relaxed F1: +0.080.

Цена: почти вдвое дольше, потому что модель генерирует больше концептов и
отвечает стабильно длиннее. Для исследовательской базы это приемлемый
trade-off; для интерактивного сценария — нет.

## 7.10. Опорные точки

| Точка | Exact F1 | Relaxed F1 | Content relaxed F1 | Смысл |
| --- | ---: | ---: | ---: | --- |
| Пустое предсказание | 0.000 | 0.000 | 0.000 | нижняя граница |
| `qwen2.5:3b` | 0.345 | 0.464 | 0.512 | меньшая модель |
| `qwen3.5:4b`, prompt v1 | 0.349 | 0.501 | 0.549 | предыдущий промпт |
| `qwen3.5:4b`, prompt v2 | 0.422 | 0.583 | 0.629 | текущий результат |
| Gold oracle | 1.000 | 1.000 | 1.000 | верхняя граница |

Внешний ориентир: SciERC SOTA (SURE, COLING 2025):

- entity F1 73.4;
- relation F1 56.9;
- strict relation F1 44.3.

Это span-level NER/RE, а не извлечение канонических концептов. Прямое
сравнение некорректно: у нас другая постановка и другой матчинг.

## 7.11. Ограничения бенчмарка

- 20 абстрактов — мало для статистической значимости.
- Один seed.
- Одна модель (плюс меньшая 3B для сравнения).
- Оценены только концепты, не отношения.
- Нет end-to-end метрики поиска (precision@k, nDCG).
- Нет оценки качества итогового обзора.
- LLM недетерминирована; один прогон не равен среднему.
- Exact — нижняя граница из-за каноникализации.
- SOTA SciERC — другая задача.

До КП3 имеет смысл:

- 100 абстрактов;
- 3 seed;
- 2–3 модели;
- triple-level F1, если появятся типы отношений;
- coverage, orphan rate, unresolved link rate;
- precision@k/nDCG для поиска;
- p95 latency и cost per run.

## 7.12. Как читать эту таблицу

1. Смотрите на **content relaxed F1** как на основной сигнал качества
   концептов.
2. Смотрите на **exact F1** как на нижнюю границу: каноникализация мешает
   точному совпадению.
3. Сравнивайте только строки с одинаковым протоколом (модель, seed, prompt).
4. Не сравнивайте наш concept F1 с SciERC entity/relation F1 напрямую.
5. Помните, что 20 абстрактов — regression sample, а не лидерборд.
