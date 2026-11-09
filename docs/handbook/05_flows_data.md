# 5. Сквозные сценарии и данные

## 5.1. Сценарий create: из темы в vault

Пользователь запускает:

```bash
litgraph \
  --id "transformer_circuits" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --requirements "Peer-reviewed or high-impact preprints published after 2021" \
  --format "APA 7th" \
  --max-papers 5
```

Что происходит по шагам:

1. **CLI** проверяет аргументы, создаёт/открывает vault, загружает настройки.
2. **Lead** создаёт пустое состояние и запускает LangGraph.
3. **plan_request** решает, нужен ли LLM для выбора движков.
4. **choose_engines** просит модель выбрать primary/fallback из каталога.
5. **finalize_plan** валидирует план и сохраняет `search_plan`.
6. **search** ищет кандидатов, дедуплицирует, помечает `source_engine`.
7. **validate** проверяет тему и требования; кандидаты без прохода
   отбрасываются.
8. Если статей мало, **suggest_queries** генерирует подзапросы и цикл
   повторяется (до 3 раундов).
9. **rank_select** сортирует по наукометрическому скору и применяет elbow
   cutoff.
10. Для каждой выбранной статьи:
    - **expand_citations** добавляет references/citations;
    - **synthesize** извлекает summary/findings/methodology/limitations/
      concepts;
    - в `--deep` — **fetch_pages** и **ground_concepts**;
    - **commit_paper** добавляет статью в `base`.
11. **rebuild_graph** канонизирует концепты и строит рёбра.
12. **define_concepts** пишет определения концептов.
13. **bibliography** собирает цитаты.
14. **link_network** строит типизированные связи.
15. **overview** пишет общий обзор.
16. **flush** записывает vault.
17. **audit** проверяет ссылки, frontmatter, дубли, сирот, целостность.

В конце пользователь видит таблицу выбранных статей и QA-отчёт.

## 5.2. Сценарий update: продолжить базу

```bash
litgraph \
  --id "transformer_circuits" \
  --update "Sparse Autoencoders and Superposition in Language Models" \
  --max-papers 2
```

Отличия от create:

- Lead загружает `_state.json` и передаёт существующую базу в workflow;
- `queries=[directive]`, а тема = исходная тема + директива;
- после validation сразу идёт ingestion, без повторного rank_select;
- новые статьи добавляются к старым;
- существующие определения концептов не перезаписываются;
- в конце `save_state` и `audit`.

Это позволяет расширять базу неделями, не теряя предыдущую работу.

## 5.3. Сценарий deep: PDF и grounding

```bash
litgraph --id "transformer_circuits" --update "Induction heads" --deep
```

В deep-режиме после синтеза:

1. `fetch_pages` скачивает open-access PDF;
2. `ground_concepts` ищет упоминания концептов по страницам;
3. в `ConceptMention` появляются `page_number` и `context_snippet`;
4. в концепт-хабе появляются ссылки вида «источник, страница, цитата».

Если PDF недоступен, статья всё равно обрабатывается по абстракту. Deep не
является обязательным для работы.

## 5.4. Сценарий check, list, delete

```bash
litgraph --list
litgraph --check --id "transformer_circuits"
litgraph --delete --id "transformer_circuits"
```

- `--list` показывает существующие базы.
- `--check` запускает QA и печатает issues.
- `--delete` удаляет базу (осторожно: это необратимо).

## 5.5. Модель данных

Основные модели лежат в `lit_graph/models.py`.

### Paper

`Paper` — статья. Ключевые поля:

- идентификация: `id`, `title`, `authors`, `year`, `venue`, `doi_or_url`,
  `pdf_url`, `source_engine`;
- наукометрия: `citation_count`, `influential_citation_count`,
  `citation_velocity`, `influential_ratio`, `objective_scientific_score`,
  `normalized_weight`, `is_elbow_selected`;
- валидация: `topic_relevance_score`, `topic_relevance_reason`,
  `requirements_met`, `requirements_reason`, `scientific_value_score`;
- синтез: `summary_en`, `key_findings_en`, `methodology_en`,
  `limitations_en`, `extracted_concepts`, `extracted_concepts_all`,
  `concept_mentions`;
- связи: `referenced_paper_titles`, `citing_paper_titles`,
  `related_paper_titles`;
- библиография: `formatted_citation`.

`extracted_concepts` — усечённый список до `MAX_CONCEPTS_PER_PAPER`;
`extracted_concepts_all` — полный, чтобы повторная каноникализация не теряла
идеи.

### ConceptHub

`ConceptHub` — концепт:

- `name` — display-имя;
- `summary_en` — определение;
- `aggregated_score` — суммарный вес;
- `normalized_weight` — вес 0..1 для визуализации;
- `mentions` — список `ConceptMention`.

### ConceptMention

`ConceptMention` — упоминание концепта в статье:

- `concept_name`;
- `paper_title`;
- `page_number`;
- `context_snippet`.

### GraphEdge

`GraphEdge` — ребро:

- `source_title`;
- `target_title`;
- `relation_type` (`cites`, `relates_to` и т.д.).

`LiteratureBaseState.add_edge` не добавляет дубликаты.

### LiteratureBaseState

`LiteratureBaseState` — вся база:

- `base_id`, `topic`, `requirements`, `citation_format`;
- `overall_summary_en`;
- `papers: Dict[str, Paper]`;
- `concepts: Dict[str, ConceptHub]`;
- `edges: List[GraphEdge]`;
- `bibliography_en`;
- `search_plan`;
- `created_at`, `updated_at`.

## 5.6. `_state.json`

`_state.json` — JSON-представление `LiteratureBaseState`. Он лежит в корне
vault. Пример (сокращённо):

```json
{
  "base_id": "transformer_circuits",
  "topic": "Mechanistic Interpretability...",
  "requirements": "Peer-reviewed...",
  "citation_format": "APA 7th",
  "papers": {
    "2401.00001": {
      "id": "2401.00001",
      "title": "Example Paper",
      "year": 2024,
      "citation_count": 42,
      "extracted_concepts": ["Induction Head", "Transformer"],
      "source_engine": "arxiv"
    }
  },
  "concepts": {
    "Induction Head": {
      "name": "Induction Head",
      "summary_en": "A circuit that...",
      "mentions": []
    }
  },
  "edges": [],
  "search_plan": {
    "primary": ["arxiv", "semantic_scholar"],
    "fallback": ["web"],
    "source": "llm"
  }
}
```

Запись атомарная: `.json.tmp` → replace. Если процесс упал, старый файл
остаётся целым.

## 5.7. Структура vault

```text
vaults/transformer_circuits/
├── Formatted_Bibliography.md
├── _Bibliography.md
├── _Overview_Synthesis.md
├── _Agent_Activity.md
├── _state.json
├── references.bib
├── Sources/
│   ├── <paper title>.md
│   └── <external reference>.md
└── Concepts/
    └── <concept name>.md
```

### Заметка источника

Frontmatter:

```yaml
id: "2401.00001"
title: "Example Paper"
authors: ["A. Author"]
year: 2024
venue: "arXiv"
source_engine: "arxiv"
citation_count: 42
citation_velocity: 10.5
objective_score: 12.3
node_weight: 0.71
type: literature_note
```

Секции:

- Formatted Citation;
- Executive Summary;
- Key Findings;
- Methodology & Limitations;
- Knowledge Graph Connections;
- Typed Graph Relations (если есть);
- Abstract.

### Концепт-хаб

Frontmatter:

```yaml
concept: "Induction Head"
aggregated_score: 4.2
node_weight: 0.83
type: concept_hub
```

Секции:

- Concept Definition & Consensus;
- Grounded Citations & Page References.

### Внешняя заглушка

```yaml
title: "External Paper"
type: external_reference
```

Секция «Cited within this vault» со ссылками на источники.

### Хаб-файлы

- `_Overview_Synthesis.md` — обзор, индекс, типизированные связи;
- `_Bibliography.md` — интерактивная библиография с `[[links]]`;
- `Formatted_Bibliography.md` — чистый список для копирования;
- `references.bib` — BibTeX;
- `_Agent_Activity.md` — журнал: кто, что, когда, сколько заняло.

## 5.8. Почему vault, а не база данных

Vault выбран по трём причинам:

1. **Прозрачность.** Каждую заметку можно открыть и поправить руками.
2. **Локальность.** Нет облачной зависимости и vendor lock-in.
3. **Obsidian.** Граф, обратные ссылки и поиск уже есть; не нужно писать UI.

Минус — нет транзакций и строгой схемы. Поэтому в проекте есть QA,
детерминированные имена, YAML-экранирование и `_state.json` как источник
правды.

## 5.9. Что происходит при повторном запуске

- `_state.json` загружается;
- существующие статьи не дублируются по `id`;
- существующие концепты переиспользуются;
- определения не перезаписываются, если уже есть;
- новые статьи добавляются;
- граф перестраивается, но пользовательские настройки `graph.json`
  сохраняются;
- QA проверяет итог.

Именно это делает базу «живой», а не одноразовым экспортом.
