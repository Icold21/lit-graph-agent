# Вклад участников — доказательная база

Документ фиксирует зоны ответственности и артефакты, по которым можно проверить
вклад каждого участника. Он дополняет [CONTRIBUTORS.md](../../CONTRIBUTORS.md)
и [.github/CODEOWNERS](../../.github/CODEOWNERS).

## Сводная таблица

| Участник | Роль | GitHub | Основные модули | Проверяемые артефакты |
| --- | --- | --- | --- | --- |
| Иван Холодило | Lead AI Engineer | [@Icold21](https://github.com/Icold21) | `agent/core.py`, `agent/workflow.py`, `agent/graph_state.py`, `agent/roles.py`, `cli.py`, `config.py` | LangGraph workflow, CLI, `_state.json`, интеграция агентов, README, отчёт КП2 |
| Вадим Лялькин | Graph & Knowledge Engineer | [@Geniy_molodec](https://github.com/Geniy_molodec) | `agent/graph_agent.py`, `agent/concepts.py`, `storage/`, `models.py` | Онтология vault, каноникализация, `[[wikilinks]]`, graph preset, скриншоты графа |
| Нодар Чигладзе | Data / IR Engineer | [@NodarNeo](https://github.com/NodarNeo) | `agent/retrieval_agent.py`, `search/`, `utils/http.py`, `utils/cache.py` | arXiv/S2/web-клиенты, дедупликация, retry/backoff, citation expansion, PDF, демо-сценарий |
| Давид Чигладзе | QA / Evaluation Engineer | [@David52228](https://github.com/David52228) | `agent/evaluation_agent.py`, `qa/`, `tests/`, `.github/workflows/ci.yml` | QA-проверки, 55 тестов, CI-матрица, SciERC-бенчмарк, график метрик |
| Илья Синко | LLM Engineer | [@mang1ch5](https://github.com/mang1ch5) | `agent/prompt_agent.py`, `agent/validator.py`, `agent/synthesizer.py`, `llm/` | Промпты, консолидированная валидация, синтез, батчинг, JSON-устойчивость |

## Что именно сделал каждый

### Иван Холодило — Lead AI Engineer

- Спроектировал five-agent архитектуру и перевёл оркестрацию на LangGraph
  `StateGraph`.
- Реализовал `LiteratureWorkflow`: узлы, рёбра, conditional routing,
  `MemorySaver`, журнал `activity`.
- Написал `core.py`: create/update/rank/ingest/flush/audit.
- Реализовал CLI и конфигурацию, включая `--team`, `--tools`, `--check`,
  `--engines`, `--no-router`.
- Обеспечил персистентность `_state.json` и атомарную запись.
- Подготовил README, отчёт КП2 и презентацию.

**Проверка:** `git log -- lit_graph/agent/core.py lit_graph/agent/workflow.py`,
`litgraph --team`, `litgraph --help`.

### Вадим Лялькин — Graph & Knowledge Engineer

- Спроектировал модель Obsidian vault: источники, concept hubs, synthesis,
  внешние stubs.
- Реализовал `GraphAgent`: rebuild, flush, сохранение определений.
- Реализовал каноникализацию концептов: плюралы, регистр, акронимы,
  parenthetical merging.
- Сделал устойчивые имена заметок и безопасный YAML.
- Реализовал слияние `graph.json` без перезаписи пользовательских настроек.

**Проверка:** `git log -- lit_graph/agent/graph_agent.py lit_graph/agent/concepts.py lit_graph/storage/`,
`pytest tests/test_concepts.py tests/test_obsidian.py tests/test_vault_names.py -q`.

### Нодар Чигладзе — Data / IR Engineer

- Реализовал `RetrievalAgent` и клиенты arXiv, Semantic Scholar, open web.
- Добавил агрегацию запросов, дедупликацию, слияние метаданных.
- Реализовал pre-ranking и citation expansion.
- Добавил retry/backoff, таймауты, дисковый кэш.
- Реализовал каталог движков и `SearchRouter`.
- Добавил `plan_request` / `finalize_plan` и per-paper `source_engine`.
- Реализовал PDF-ингест для `--deep`.

**Проверка:** `git log -- lit_graph/search/ lit_graph/agent/retrieval_agent.py`,
`pytest tests/test_search.py tests/test_search_router.py tests/test_ranking.py -q`,
`litgraph --tools`.

### Давид Чигладзе — QA / Evaluation Engineer

- Реализовал `EvaluationAgent` и пакет `qa/`.
- Добавил проверки unresolved links, сирот, дублей, frontmatter, пустых
  библиографий, целостности concept ↔ paper.
- Написал тесты: pipeline, агенты, персистентность, каноникализация, имена,
  QA, батчинг, провайдеры.
- Настроил CI: Python 3.10–3.13, `ruff` fails build, `pytest` на push/PR.
- Добавил `litgraph --check`.
- Реализовал SciERC-бенчмарк и график метрик.

**Проверка:** `git log -- lit_graph/qa/ tests/ .github/workflows/`,
`pytest -q`, `litgraph --check --id <base>`.

### Илья Синко — LLM Engineer

- Централизовал промпты в `llm/prompts.py`.
- Реализовал `engine_selection_prompt` и `select_search_engines`.
- Реализовал консолидированную валидацию темы и требований.
- Реализовал синтез статьи: summary, findings, methodology, limitations,
  concepts.
- Добавил батчинг определений и библиографии.
- Добавил deterministic fallbacks и устойчивый JSON-парсинг для reasoning
  моделей.
- Реализовал привязку концептов к страницам PDF.

**Проверка:** `git log -- lit_graph/llm/ lit_graph/agent/prompt_agent.py lit_graph/agent/synthesizer.py`,
`pytest tests/test_synthesizer.py tests/test_validator.py tests/test_providers.py -q`.

## Статус доказательств в git

На 8 ноября 2026 г. история `main` содержит коммиты с авторством четырёх
участников команды; коммит Lead-зоны остаётся за `@Icold21`.

| Участник | Коммит | Артефакты |
| --- | --- | --- |
| Вадим Лялькин | [`87d881c`](https://github.com/Icold21/LitGraphAgent/commit/87d881c) | `docs/GRAPH_MODEL.md` |
| Нодар Чигладзе | [`423e880`](https://github.com/Icold21/LitGraphAgent/commit/423e880) | `docs/RETRIEVAL.md`, `docs/kp2/DEMO.md` |
| Давид Чигладзе | [`2b7536e`](https://github.com/Icold21/LitGraphAgent/commit/2b7536e) | SciERC `qwen3.5:4b`, `plot_results.py`, `benchmarks/README.md` |
| Илья Синко | [`752232a`](https://github.com/Icold21/LitGraphAgent/commit/752232a) | `docs/LLM_LAYER.md` |

Это документальные коммиты по зонам ответственности. Они подтверждают
владение темой, но не заменяют коммиты в код: до КП3 каждый участник должен
сделать минимум одно изменение в своих модулях.

Что уже есть:

- `CODEOWNERS` закрепляет пути за участниками, включая новые документы;
- `CONTRIBUTORS.md` описывает зоны, задачи и ссылки на коммиты;
- тесты и модули можно сопоставить с ролями;
- отчёт КП2 фиксирует вклад в текстовом виде.

Что нужно сделать до КП3:

1. Каждый участник делает минимум один осмысленный коммит или PR в своих
   модулях под своей учётной записью.
2. Для крупных изменений используется `Co-authored-by` или ревью.
3. В `CONTRIBUTORS.md` добавляются ссылки на коммиты/PR.
4. На защите каждый участник показывает свой модуль и отвечает на вопросы.

## Чек-лист подтверждения

- [x] Вадим: документальный коммит по графовой модели.
- [x] Нодар: документальный коммит по retrieval и демо.
- [x] Давид: коммит с результатом бенчмарка и графиком.
- [x] Илья: документальный коммит по LLM-слою.
- [ ] Иван: коммит по `workflow.py` / `core.py` / `cli.py`.
- [ ] Каждый участник подтвердил, что может объяснить и запустить свой модуль.
- [ ] До КП3: по одному коммиту в код от каждого участника.
