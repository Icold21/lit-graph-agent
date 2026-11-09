# 10. Глоссарий, FAQ и приложение

## 10.1. Глоссарий

**LLM** — большая языковая модель; вероятностный генератор текста.

**Промпт** — инструкция модели: роль, данные, правила, формат ответа.

**Токен** — единица текста для модели.

**Контекст** — весь текст, который модель видит в одном запросе.

**Температура** — параметр случайности генерации.

**JSON** — текстовый формат структурированных данных.

**Ollama** — локальный сервер моделей с OpenAI-совместимым API.

**Провайдер LLM** — сервис/сервер, к которому обращается проект.

**Агент** — компонент с ограниченной ролью.

**Оркестрация** — управление порядком вызовов агентов.

**LangGraph** — библиотека для графа workflow.

**State** — данные, передаваемые между узлами.

**Reducer** — функция объединения старого и нового значения поля.

**Checkpoint** — сохранённая точка состояния.

**Knowledge graph** — граф знаний: узлы-сущности и рёбра-отношения.

**Узел** — вершина графа.

**Ребро** — связь между узлами.

**Триплет** — тройка «голова, отношение, хвост».

**Онтология** — допустимые типы узлов и рёбер.

**Каноникализация** — приведение разных написаний к одному виду.

**Vault** — папка Obsidian с Markdown-заметками.

**Markdown** — простой текстовый формат разметки.

**Frontmatter** — YAML-блок метаданных в начале заметки.

**Wikilink** — ссылка `[[Заметка]]` внутри vault.

**Stub** — лёгкая заметка-заглушка для внешней ссылки.

**Coverage** — доля gold-сущностей/связей, попавших в граф.

**Orphan** — узел без ссылок.

**Unresolved link** — ссылка, не находящая目标.

**Retrieval** — поиск кандидатов.

**Дедупликация** — удаление одинаковых статей.

**Ранжирование** — сортировка по полезности.

**Elbow cutoff** — отсечение低-impact хвоста по «локтю».

**Fallback** — запасной движок/вариант.

**Sub-query** — уточняющий подзапрос.

**Precision** — доля правильного среди найденного.

**Recall** — доля найденного среди правильного.

**F1** — гармоническое среднее precision и recall.

**Exact** — точное совпадение после нормализации.

**Relaxed** — совпадение по Jaccard ≥ 0.5.

**Micro** — агрегирование TP/FP/FN по всем примерам.

**Macro** — среднее метрик по примерам.

**MRR** — среднее обратных рангов.

**Hits@k** — доля запросов с правильным ответом в top-k.

**nDCG** — метрика ранжирования с градацией релевантности.

**MAP** — среднее Average Precision.

**Triple F1** — F1 по тройкам графа.

**QA** — проверка качества.

**CI** — автоматический запуск тестов и линтера.

**pytest** — фреймворк тестов.

**ruff** — линтер Python.

**SciERC** — бенчмарк scientific knowledge-graph construction.

**SOTA** — state of the art, лучший известный результат.

## 10.2. FAQ

### Это заменяет ChatGPT?

Нет. LitGraphAgent не чат, а конвейер с фиксированными шагами. LLM здесь —
исполнитель операций, а не свободный собеседник.

### Почему не просто отправить тему в ChatGPT?

Потому что нужен воспроизводимый граф, ссылки, библиография, состояние и
проверки. Чат не даёт структуру, не сохраняет `_state.json` и не проверяет
целостность vault.

### Почему локальная модель?

Локальная модель не отправляет тексты в облако, дешевле в эксплуатации и
работает без интернета (после загрузки). Минус — качество и скорость.

### Почему qwen3.5:4b, а не qwen3.5:3b?

Модели `qwen3.5:3b` нет в реестре Ollama (`pull model manifest: file does not
exist`). Поэтому используется 4B. 3B-сравнение сделано на `qwen2.5:3b`.

### Почему exact F1 такой низкий?

Потому что система возвращает канонические концепты, а gold — сырые спаны.
`word sense disambiguation (WSD) systems` и `word sense disambiguation` — это
одно и то же по смыслу, но не по строке. Relaxed и content-only показывают
более честную картину.

### Почему не считается relation F1?

Пайплайн не предсказывает типы отношений SciERC. Считать relation F1 было бы
фикцией. Это ограничение честно зафиксировано.

### Почему 20 абстрактов?

Это regression sample, а не лидерборд. 20 хватает, чтобы ловить регрессии, но
не для статистической значимости. До КП3 планируется 100 абстрактов и 3 seed.

### Почему prompt v2 медленнее?

Он просит 6–8 концептов вместо 3 примеров, поэтому модель генерирует больше
текста. Время выросло с ~31 до ~59 минут на 20 абстрактов. Это trade-off
качества и скорости.

### Можно ли использовать другую модель?

Да. Любой OpenAI-совместимый endpoint: DeepSeek, OpenAI, Groq, OpenRouter,
vLLM. Достаточно поменять `.env`.

### Можно ли использовать без Obsidian?

Vault — это папка Markdown. Obsidian нужен только для graph view и удобной
навигации. Без него файлы всё равно читаются.

### Что будет, если LLM вернёт плохой JSON?

Санитайзер попробует восстановить, затем retry, затем fallback. Если совсем
плохо — статья может остаться без части полей, а QA покажет warning.

### Что будет, если сеть упала?

Retrieval сделает retry/backoff, затем пропустит кандидата. База может быть
меньше, но запуск не упадёт.

### Как проверить, что база не сломана?

```bash
litgraph --check --id "your_base"
```

QA покажет errors/warnings.

### Где хранится состояние?

В `vaults/<id>/_state.json`. Запись атомарная.

### Можно ли обновлять базу частями?

Да, `--update` для этого и нужен. Старые определения не перезаписываются.

### Почему в графе есть внешние заметки?

Это stubs для цитирований, которых нет в базе. Они нужны, чтобы `[[ссылки]]`
не повисали.

### Как добавить новый движок?

Описать в `search/tools.py`, добавить клиент, подключить в `search/engine.py`,
добавить тест. Не встраивать условие в агента.

### Как добавить нового агента?

Роль, сервис, инстанс в `core.py`, узлы/рёбра в `workflow.py`, тест, docs,
CODEOWNERS.

## 10.3. Приложение A. Пример `_state.json`

```json
{
  "base_id": "transformer_circuits",
  "topic": "Mechanistic Interpretability and Induction Heads",
  "requirements": "Peer-reviewed or high-impact preprints after 2021",
  "citation_format": "APA 7th",
  "overall_summary_en": "The literature converges on...",
  "papers": {
    "2401.00001": {
      "id": "2401.00001",
      "title": "Example Paper",
      "authors": ["A. Author", "B. Author"],
      "year": 2024,
      "venue": "arXiv",
      "doi_or_url": "https://arxiv.org/abs/2401.00001",
      "source_engine": "arxiv",
      "citation_count": 42,
      "influential_citation_count": 7,
      "citation_velocity": 10.5,
      "influential_ratio": 0.186,
      "objective_scientific_score": 13.2,
      "normalized_weight": 0.71,
      "summary_en": "The paper studies...",
      "key_findings_en": ["Finding 1", "Finding 2"],
      "methodology_en": "The authors...",
      "limitations_en": "Small sample...",
      "extracted_concepts": ["Induction Head", "Transformer"],
      "extracted_concepts_all": ["Induction Head", "Transformer", "Attention"],
      "formatted_citation": "Author, A. (2024). Example Paper..."
    }
  },
  "concepts": {
    "Induction Head": {
      "name": "Induction Head",
      "summary_en": "A circuit that...",
      "aggregated_score": 4.2,
      "normalized_weight": 0.83,
      "mentions": [
        {
          "concept_name": "Induction Head",
          "paper_title": "Example Paper",
          "page_number": 3,
          "context_snippet": "We identify an induction head..."
        }
      ]
    }
  },
  "edges": [
    {
      "source_title": "Example Paper",
      "target_title": "Another Paper",
      "relation_type": "cites"
    }
  ],
  "search_plan": {
    "primary": ["arxiv", "semantic_scholar"],
    "fallback": ["web"],
    "reason": "Fresh preprints plus citation metadata.",
    "source": "llm"
  },
  "created_at": "2026-11-09T10:00:00+00:00",
  "updated_at": "2026-11-09T10:05:00+00:00"
}
```

## 10.4. Приложение B. Пример заметки источника

```markdown
---
id: "2401.00001"
title: "Example Paper"
authors: ["A. Author"]
year: 2024
venue: "arXiv"
url: "https://arxiv.org/abs/2401.00001"
source_engine: "arxiv"
citation_count: 42
citation_velocity: 10.5
objective_score: 13.2
node_weight: 0.71
type: literature_note
---

# Example Paper

> 📊 **Scientometric Score:** `13.2` | **Continuous Weight:** `0.71`

## 📌 Formatted Citation

> Author, A. (2024). Example Paper...

## 🧠 Executive Summary (English)

The paper studies...

## 🔍 Key Findings & Contributions

- Finding 1
- Finding 2

## ⚙️ Methodology & Limitations

**Methodology:** The authors...

**Limitations:** Small sample...

## 🌐 Knowledge Graph Connections

**Concepts:** [[Induction Head]], [[Transformer]]

**Related Literature:** None

**References (Outward):** [[Another Paper]]

**Citations (Inward):** None

## 📄 Abstract

> ...
```

## 10.5. Приложение C. Пример концепт-хаба

```markdown
---
concept: "Induction Head"
aggregated_score: 4.2
node_weight: 0.83
type: concept_hub
---

# Concept: Induction Head

> 🌐 **Aggregated Score:** `4.2` | **Continuous Weight:** `0.83`

## 📖 Concept Definition & Consensus

A circuit that...

## 📍 Grounded Citations & Page References:

- [[Example Paper]] (**p. 3**) — *"We identify an induction head..."*
```

## 10.6. Приложение D. Пример QA-отчёта

```json
{
  "summary": "0 errors, 2 warnings (notes=42, sources=12, concepts=28, links=96)",
  "stats": {
    "notes": 42,
    "sources": 12,
    "concepts": 28,
    "external_refs": 2,
    "links": 96,
    "unresolved_links": 0,
    "orphans": 2
  },
  "issues": [
    {
      "severity": "warning",
      "code": "orphan_note",
      "message": "Note has no inbound or outbound links",
      "path": "Concepts/Example.md"
    }
  ]
}
```

## 10.7. Приложение E. Промпт v2

```text
Synthesize the following paper strictly in English:
Title: ...
Authors: ...
Year: ...
Venue: ...
Abstract: ...

Concept extraction rules:
- Return 6-8 key scientific concepts that are explicitly mentioned in the abstract.
- Prefer specific methods, tasks, metrics, materials, datasets and technical terms.
- Prefer canonical multi-word names over bare acronyms.
- Avoid generic words such as system, approach, method, algorithm or result.
- Return each concept once.

Return strict JSON with concepts first:
{
  "extracted_concepts": ["Specific concept 1", "Specific concept 2", "Specific concept 3"],
  "summary_en": "Deep single-paragraph executive summary in English",
  "key_findings_en": ["Key finding 1", "Key finding 2", "Key finding 3"],
  "methodology_en": "Methodology summary in English",
  "limitations_en": "Limitations identified in English"
}
```

## 10.8. Приложение F. Шпаргалка команд

```bash
# окружение
litgraph --version
litgraph --team
litgraph --tools

# создать
litgraph --id "base" --topic "..." --requirements "..." --format "APA 7th" --max-papers 5

# обновить
litgraph --id "base" --update "..." --max-papers 3

# deep
litgraph --id "base" --update "..." --deep

# проверить
litgraph --check --id "base"

# список/удаление
litgraph --list
litgraph --delete --id "base"

# тесты
pytest -q
ruff check lit_graph tests benchmarks

# бенчмарк
python benchmarks/scierc_benchmark.py --data-dir ./raw_data --limit 20 --seed 42 --model qwen3.5:4b --output benchmarks/results/run.json
python benchmarks/plot_results.py benchmarks/results/run.json
```

## 10.9. Что читать дальше

- `README.md` — быстрый старт и верхнеуровневые метрики.
- `docs/ARCHITECTURE.md` — архитектура и диаграммы.
- `docs/RETRIEVAL.md` — поиск и ранжирование.
- `docs/LLM_LAYER.md` — промпты и синтез.
- `docs/GRAPH_MODEL.md` — онтология и каноникализация.
- `docs/KG_METRICS.md` — метрики KG-бенчмарков и SOTA-ориентиры.
- `docs/kp2/KP2_REPORT.md` — отчёт КП2.
- `benchmarks/README.md` — протокол SciERC.

## 10.10. Заключение

Если вы дошли до конца, у вас есть полная карта проекта: зачем он нужен, из
каких агентов состоит, как проходит статья от поиска до заметки, что именно
измеряет бенчмарк и где лежит код. Этого достаточно, чтобы включиться в
работу, объяснить систему на защите и не потеряться в первый день.

Главное, что стоит запомнить:

- LitGraphAgent — это конвейер, а не «магический ИИ». Каждый шаг можно
  проверить.
- LLM — вероятностный компонент; поэтому есть валидация, JSON-санитайзер,
  fallback-и и QA.
- Граф знаний держится на каноникализации, ссылках и дедупликации.
- `_state.json` — источник правды между запусками.
- Бенчмарк измеряет только то, что система реально предсказывает; relation F1
  без типов отношений был бы фикцией.
- 20 абстрактов — regression sample, а не лидерборд.

Если понадобится продолжить проект, начните с `README.md`, затем откройте
`docs/ARCHITECTURE.md` и `docs/kp2/KP2_REPORT.md`, а после — код агентов в
том порядке, в котором они вызываются: Lead → Retrieval → Prompt → Graph → QA.

Контакты и ссылки:

- Репозиторий: <https://github.com/Icold21/LitGraphAgent>
- Команда: AI-RIldium
- Лицензия: MIT
- Дата сборки гайда: ноябрь 2026

Спасибо, что дочитали. Дальше — только код, эксперименты и вопросы.

