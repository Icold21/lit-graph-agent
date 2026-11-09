# 9. Запуск, код и команда

## 9.1. Установка

```bash
git clone https://github.com/Icold21/LitGraphAgent.git
cd LitGraphAgent
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

`pypdf` входит в основные зависимости: он нужен для `--deep`.

## 9.2. Настройка `.env`

Создайте `.env` в корне. Пример для локальной Ollama:

```bash
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen3.5:4b

DEFAULT_VAULTS_DIR=./vaults
MAX_PAPERS_PER_RUN=5
MIN_PAPERS_PER_RUN=2
MAX_SEARCH_CANDIDATES=15
CANDIDATE_EVAL_LIMIT=8
CITATION_EXPANSION_LIMIT=2
ENABLE_ELBOW_CUTOFF=true

SEARCH_ROUTER_ENABLED=true
SEARCH_ROUTER_MAX_PRIMARY=2
SEARCH_FALLBACK_MIN_RESULTS=5

MIN_CONCEPT_PAPERS=2
MAX_CONCEPTS_PER_PAPER=8
CONCEPT_BATCH_SIZE=12
BIBLIOGRAPHY_BATCH_SIZE=20

CACHE_ENABLED=true
CACHE_TTL_HOURS=168
```

Для облачной модели:

```bash
LLM_API_KEY=sk-...
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat
```

Не коммитьте `.env` с реальным ключом. В репозитории есть `.env.example`.

## 9.3. Проверка окружения

```bash
litgraph --version
litgraph --team
litgraph --tools
```

`--team` показывает пять ролей и владельцев. `--tools` показывает каталог
поисковых движков, из которого выбирает модель.

## 9.4. Основные команды

### Создать базу

```bash
litgraph \
  --id "transformer_circuits" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --requirements "Peer-reviewed or high-impact preprints published after 2021" \
  --format "APA 7th" \
  --max-papers 5
```

### Обновить базу

```bash
litgraph \
  --id "transformer_circuits" \
  --update "Sparse Autoencoders and Superposition in Language Models" \
  --max-papers 3
```

### Deep-режим

```bash
litgraph --id "transformer_circuits" --update "Induction heads" --deep
```

### Список, проверка, удаление

```bash
litgraph --list
litgraph --check --id "transformer_circuits"
litgraph --delete --id "transformer_circuits"
```

### Переопределить движки

```bash
litgraph --id "transformer_circuits" --update "Induction heads" --engines arxiv,web
litgraph --id "transformer_circuits" --update "Induction heads" --no-router
```

### Отключить кэш или elbow

```bash
litgraph --id "transformer_circuits" --update "..." --no-cache
litgraph --id "transformer_circuits" --update "..." --no-elbow
```

### Логи

```bash
litgraph --verbose ...
```

## 9.5. Тесты и линтер

```bash
pytest -q
ruff check lit_graph tests benchmarks
```

Ожидаемо: 55 passed, ruff без ошибок.

## 9.6. Бенчмарк

```bash
# 1. Скачать SciERC
curl -L -o sciERC_raw.tar.gz \
  https://nlp.cs.washington.edu/sciIE/data/sciERC_raw.tar.gz
tar -xzf sciERC_raw.tar.gz

# 2. Запустить
python benchmarks/scierc_benchmark.py \
  --data-dir ./raw_data \
  --limit 20 \
  --seed 42 \
  --model qwen3.5:4b \
  --base-url http://localhost:11434/v1 \
  --output benchmarks/results/scierc_qwen3.5-4b-prompt8.json \
  --checkpoint benchmarks/results/scierc_qwen3.5-4b-prompt8.jsonl

# 3. Построить график
python benchmarks/plot_results.py \
  benchmarks/results/scierc_qwen3.5-4b-prompt8.json \
  --output docs/kp2/assets/metrics_qwen3.5-4b-prompt8.png
```

Бенчмарк умеет resume: если прервать, повторный запуск продолжит с
checkpoint. Failures записываются в JSON, а не роняют весь прогон.

## 9.7. Типичные проблемы

### `pull model manifest: file does not exist`

Модели нет в реестре Ollama. Например, `qwen3.5:3b` не существует; есть
`qwen3.5:4b`. Проверьте `ollama list`.

### Модель очень медленная

Локальная 4B на слабом GPU может давать 1–2 токена/с. Это нормально для
ноутбука. Увеличьте `--timeout`, закройте другие GPU-процессы, уменьшите
`--limit` для теста.

### Таймауты

Поднимите `--timeout` и `--retries`. Для больших баз используйте checkpoint.

### JSON-ошибки

Санитайзер восстанавливает большинство случаев, но если модель стабильно
ломает JSON, попробуйте другую модель или уменьшите батч.

### Нет PDF в deep-режиме

Не все статьи open-access. Deep-режим деградирует: статья обрабатывается по
абстракту, grounding пропускается.

### Битые ссылки в Obsidian

Запустите `litgraph --check --id ...`. QA покажет unresolved links, orphans и
frontmatter issues.

### Кириллица в PowerShell

Если вывод Python ломается, задайте:

```powershell
$env:PYTHONIOENCODING='utf-8'
```

## 9.8. Карта кода

| Файл | Зачем |
| --- | --- |
| `lit_graph/agent/core.py` | Lead, жизненный цикл, CLI-интеграция |
| `lit_graph/agent/workflow.py` | LangGraph, узлы, рёбра, activity |
| `lit_graph/agent/graph_state.py` | `ResearchState`, events, reducer |
| `lit_graph/agent/roles.py` | Роли и владельцы |
| `lit_graph/agent/retrieval_agent.py` | Поиск, citations, PDF |
| `lit_graph/search/` | Клиенты, каталог, router, ranking, PDF |
| `lit_graph/agent/prompt_agent.py` | LLM-операции |
| `lit_graph/agent/validator.py` | Валидация кандидатов |
| `lit_graph/agent/synthesizer.py` | Синтез, определения, библиография, обзор |
| `lit_graph/llm/prompts.py` | Все промпты |
| `lit_graph/llm/providers.py` | Провайдеры LLM |
| `lit_graph/agent/graph_agent.py` | Онтология, rebuild, flush |
| `lit_graph/agent/concepts.py` | Каноникализация |
| `lit_graph/storage/obsidian_vault.py` | Запись заметок, state |
| `lit_graph/storage/base_manager.py` | Жизненный цикл баз |
| `lit_graph/agent/evaluation_agent.py` | QA-агент |
| `lit_graph/qa/vault_checks.py` | Проверки |
| `lit_graph/models.py` | Модели данных |
| `lit_graph/cli.py` | CLI |
| `lit_graph/config.py` | Настройки |
| `tests/` | 55 тестов |
| `benchmarks/` | SciERC harness и результаты |

## 9.9. Как добавить нового агента

1. Добавить роль в `agent/roles.py`.
2. Написать сервис-класс с обычными методами.
3. Инстанцировать в `agent/core.py`.
4. Добавить узлы и рёбра в `agent/workflow.py`.
5. Добавить тест.
6. Обновить `CONTRIBUTORS.md`, `docs/AGENT_TEAM.md`, `README.md`,
   `.github/CODEOWNERS`.

Инварианты: агент не пишет данные другого агента напрямую; все промпты — в
`llm/prompts.py`; все записи vault — через `GraphAgent`; QA не мутирует
состояние.

## 9.10. Как добавить поисковый движок

1. Описать движок в `search/tools.py`.
2. Добавить клиент в `search/`.
3. Подключить в `search/engine.py`.
4. Добавить в каталог и тесты.
5. Проверить `litgraph --tools`.

Не добавляйте ветвление «если движок X» внутрь агента: каталог должен
оставаться данными.

## 9.11. Как изменить промпт

1. Найти функцию в `llm/prompts.py`.
2. Изменить текст, сохранив требование JSON.
3. Проверить, что `synthesizer.py`/`validator.py` действительно используют
   эту функцию (раньше был дубликат inline-промпта).
4. Прогнать `pytest` и бенчмарк на 5–10 абстрактах.
5. Обновить метрики и документацию.

## 9.12. Команда и роли

| Участник | Роль | Зона |
| --- | --- | --- |
| Иван Холодило | Lead AI Engineer | Архитектура, LangGraph, CLI, состояние |
| Вадим Лялькин | Graph & Knowledge Engineer | Онтология, `[[wikilinks]]`, Obsidian |
| Нодар Чигладзе | Data / IR Engineer | arXiv, Semantic Scholar, web, ranking, PDF |
| Давид Чигладзе | QA / Evaluation Engineer | QA, тесты, CI, бенчмарк |
| Илья Синко | LLM Engineer | Промпты, валидация, синтез |

Подробнее: `CONTRIBUTORS.md`, `docs/kp2/CONTRIBUTIONS.md`,
`.github/CODEOWNERS`.

## 9.13. Дорожная карта

| Дата | Этап | Статус |
| --- | --- | --- |
| 6 октября | MVP: поиск, фильтрация, заметки | Выполнено |
| 5 ноября | Модульный поиск и первые метрики | Выполнено |
| 25 ноября | Тесты, стабилизация, калибровка | Частично |
| 15 декабря | Финальный релиз, демо, документация | В работе |

До финала:

- 100 абстрактов, 3 seed, 2–3 модели;
- triple-level F1, если появятся типы отношений;
- precision@k/nDCG для поиска;
- coverage, orphan rate, unresolved link rate;
- p95 latency и стоимость прогона;
- демо и скриншоты.

## 9.14. Риски

| Риск | Причина | План |
| --- | --- | --- |
| Узкая оценка | 20 абстрактов, один seed | Расширить выборку |
| Нет relation F1 | Пайплайн не предсказывает типы | Либо добавить типы, либо честно не считать |
| Локальная модель медленная | 4B на слабом GPU | Таймауты, батчинг, меньший `--limit` |
| Внешние API недоступны | Сеть/лимиты | Retry, cache, fallback |
| Каноникализация ошибается | Эвристики | QA, ручная проверка, тесты |
| Вклад участников | История git | Коммиты по зонам, подтверждение |

## 9.15. Что считать успехом

Не «модель выдала красивый граф», а:

- база воспроизводится;
- QA не находит критичных ошибок;
- метрики стабильны на нескольких seed;
- пользователь может открыть vault и найти нужное;
- каждый агент можно объяснить и протестировать отдельно.
