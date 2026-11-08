# Демонстрация LitGraphAgent

Сценарий рассчитан на 3–5 минут и покрывает путь «тема → vault → граф →
обновление → проверка». Все команды выполняются из корня репозитория.

## 1. Подготовка (до записи)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

В `.env`:

```bash
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b
DEFAULT_VAULTS_DIR=./vaults
MAX_PAPERS_PER_RUN=5
MIN_CONCEPTS_PER_PAPER=2
```

Проверка окружения:

```bash
litgraph --version
litgraph --team
litgraph --tools
```

Ожидаемо: таблица пяти ролей и каталог из трёх движков
(`semantic_scholar`, `arxiv`, `web`).

## 2. Создание базы

```bash
litgraph \
  --id "kp2_demo" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --requirements "Peer-reviewed or high-impact preprints published after 2021" \
  --format "APA 7th" \
  --max-papers 5
```

Что показывать по ходу вывода:

1. `search_plan` — какие движки выбрала модель и почему.
2. Раунды поиска и fallback, если результатов мало.
3. Валидацию кандидатов по теме и требованиям.
4. Ранжирование и elbow cutoff.
5. Синтез статей и определений концептов.
6. Запись vault и QA-отчёт.

## 3. Что получилось

```bash
litgraph --list
```

Структура vault:

```text
vaults/kp2_demo/
├── Formatted_Bibliography.md
├── _Bibliography.md
├── _Overview_Synthesis.md
├── _Agent_Activity.md
├── _state.json
├── references.bib
├── Sources/
└── Concepts/
```

Показать:

- `Sources/` — атомарные заметки с frontmatter, summary, citation;
- `Concepts/` — concept hubs с определениями и обратными ссылками;
- `_Agent_Activity.md` — журнал hand-off: какой агент что сделал;
- `_state.json` — `search_plan`, `papers`, `concepts`, `edges`;
- `references.bib` — BibTeX.

## 4. Граф в Obsidian

1. Открыть `vaults/kp2_demo` как vault.
2. `Ctrl/Cmd + G` — graph view.
3. Показать кластеры: источники, концепты, синтез.
4. Открыть concept hub и перейти по `[[wikilink]]` к источнику.
5. Показать, что нет unresolved links (QA это проверяет).

## 5. Инкрементальное обновление

```bash
litgraph \
  --id "kp2_demo" \
  --update "Sparse Autoencoders and Superposition in Language Models" \
  --max-papers 2
```

Показать:

- новые источники добавились;
- старые определения концептов не перезаписаны;
- `_state.json` вырос, но сохранил прежние записи;
- `_Agent_Activity.md` содержит новый блок.

## 6. QA-проверка

```bash
litgraph --check --id "kp2_demo"
```

Ожидаемо: отчёт без errors; warnings перечислены с путями и кодами.

## 7. Воспроизводимость метрик

```bash
pytest -q
python benchmarks/plot_results.py benchmarks/results/scierc_qwen3.5-4b.json
```

Показать: 55 passed, PNG с метриками.

## Чек-лист скриншотов для КП3

- [ ] `litgraph --team` — таблица ролей.
- [ ] `litgraph --tools` — каталог движков.
- [ ] Вывод create с `search_plan`.
- [ ] Структура vault в файловом менеджере.
- [ ] Graph view в Obsidian.
- [ ] Concept hub с обратными ссылками.
- [ ] `_Agent_Activity.md`.
- [ ] `litgraph --check` без errors.
- [ ] `pytest -q` — 55 passed.
- [ ] График SciERC.

## Если нет сети или LLM

Полный E2E-прогон требует внешних API и локальной модели. Для записи без сети
использовать mock-провайдер из тестов:

```bash
pytest tests/test_agents.py -q
pytest tests/test_search_router.py -q
```

Эти тесты воспроизводят маршрутизацию, выбор движков, сохранение состояния и
сборку vault без реальных запросов. Для записи демонстрации лучше использовать
реальный прогон, а mock-тесты показывать как доказательство воспроизводимости.
