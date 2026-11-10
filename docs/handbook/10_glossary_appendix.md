# 10. Глоссарий, FAQ и приложение

## 10.1. Глоссарий

Глоссарий удобно держать таблицей: термин и краткое объяснение. Если термин
уже разбирался в предыдущих разделах, здесь даётся сжатая формулировка для
быстрого возврата.

| Термин | Что это значит |
| --- | --- |
| LLM | Большая языковая модель; вероятностный генератор текста |
| Промпт | Инструкция модели: роль, данные, правила, формат ответа |
| Токен | Единица текста для модели: слово, часть слова или знак |
| Контекст | Весь текст, который модель видит в одном запросе |
| Температура | Параметр случайности генерации |
| JSON | Текстовый формат структурированных данных |
| Ollama | Локальный сервер моделей с OpenAI-совместимым API |
| Провайдер LLM | Сервис или сервер, к которому обращается проект |
| Агент | Компонент с ограниченной ролью |
| Оркестрация | Управление порядком вызовов агентов |
| LangGraph | Библиотека для описания workflow как графа |
| State | Данные, передаваемые между узлами |
| Reducer | Функция объединения старого и нового значения поля |
| Checkpoint | Сохранённая точка состояния |
| Граф знаний | Узлы-сущности и рёбра-отношения |
| Узел | Вершина графа |
| Ребро | Связь между узлами |
| Триплет | Тройка «голова, отношение, хвост» |
| Онтология | Допустимые типы узлов и рёбер |
| Каноникализация | Приведение разных написаний к одному виду |
| Vault | Папка Obsidian с Markdown-заметками |
| Markdown | Простой текстовый формат разметки |
| Frontmatter | YAML-блок метаданных в начале заметки |
| Wikilink | Ссылка `[[Заметка]]` внутри vault |
| Stub | Лёгкая заметка-заглушка для внешней ссылки |
| Coverage | Доля gold-сущностей или связей, попавших в граф |
| Orphan | Узел без ссылок |
| Unresolved link | Ссылка, не находящая цель |
| Retrieval | Поиск кандидатов |
| Дедупликация | Удаление одинаковых статей |
| Ранжирование | Сортировка по полезности |
| Elbow cutoff | Отсечение низкоимпактного хвоста по «локтю» |
| Fallback | Запасной движок или вариант |
| Sub-query | Уточняющий подзапрос |
| Precision | Доля правильного среди найденного |
| Recall | Доля найденного среди правильного |
| F1 | Гармоническое среднее precision и recall |
| Exact | Точное совпадение после нормализации |
| Relaxed | Совпадение по Jaccard ≥ 0.5 |
| Micro | Агрегирование TP/FP/FN по всем примерам |
| Macro | Среднее метрик по примерам |
| MRR | Среднее обратных рангов |
| Hits@k | Доля запросов с правильным ответом в top-k |
| nDCG | Метрика ранжирования с градацией релевантности |
| MAP | Среднее Average Precision |
| Triple F1 | F1 по тройкам графа |
| QA | Проверка качества |
| CI | Автоматический запуск тестов и линтера |
| pytest | Фреймворк тестов Python |
| ruff | Линтер Python |
| SciERC | Бенчмарк scientific knowledge-graph construction |
| SOTA | State of the art, лучший известный результат |

## 10.2. FAQ

**Это заменяет ChatGPT?** Нет. LitGraphAgent — не чат, а конвейер с
фиксированными шагами. LLM здесь исполнитель операций, а не свободный
собеседник.

**Почему не просто отправить тему в ChatGPT?** Потому что нужен
воспроизводимый граф, ссылки, библиография, состояние и проверки. Чат не даёт
структуру, не сохраняет `_state.json` и не проверяет целостность vault.

**Почему локальная модель?** Локальная модель не отправляет тексты в облако,
дешевле в эксплуатации и работает без интернета после загрузки. Минус —
качество и скорость.

**Почему qwen3.5:4b, а не qwen3.5:3b?** Модели `qwen3.5:3b` нет в реестре
Ollama; попытка скачать её даёт `pull model manifest: file does not exist`.
Поэтому используется 4B, а для сравнения — `qwen2.5:3b`.

**Почему exact F1 такой низкий?** Потому что система возвращает канонические
концепты, а gold — сырые спаны. `word sense disambiguation (WSD) systems` и
`word sense disambiguation` — одно и то же по смыслу, но не по строке.
Relaxed и content-only показывают более честную картину.

**Почему не считается relation F1?** Пайплайн не предсказывает типы
отношений SciERC. Считать relation F1 было бы фикцией. Это ограничение честно
зафиксировано в отчёте и README.

**Почему 20 абстрактов?** Это regression sample, а не лидерборд. 20 хватает,
чтобы ловить регрессии, но не для статистической значимости. До КП3
планируется 100 абстрактов и 3 seed.

**Почему prompt v2 медленнее?** Он просит 6–8 концептов вместо трёх примеров,
поэтому модель генерирует больше текста. Время выросло с ~31 до ~59 минут на
20 абстрактов. Это trade-off качества и скорости.

**Можно ли использовать другую модель?** Да. Любой OpenAI-совместимый
endpoint: DeepSeek, OpenAI, Groq, OpenRouter, vLLM. Достаточно поменять
`.env`.

**Можно ли использовать без Obsidian?** Vault — это папка Markdown. Obsidian
нужен только для graph view и удобной навигации. Без него файлы всё равно
читаются.

**Что будет, если LLM вернёт плохой JSON?** Санитайзер попробует
восстановить, затем retry, затем fallback. Если совсем плохо, статья может
остаться без части полей, а QA покажет warning.

**Что будет, если сеть упала?** Retrieval сделает retry/backoff, затем
пропустит кандидата. База может быть меньше, но запуск не упадёт.

**Как проверить, что база не сломана?** `litgraph --check --id "your_base"`.
QA покажет errors и warnings.

**Где хранится состояние?** В `vaults/<id>/_state.json`. Запись атомарная.

**Можно ли обновлять базу частями?** Да, `--update` для этого и нужен. Старые
определения не перезаписываются.

**Почему в графе есть внешние заметки?** Это stubs для цитирований, которых
нет в базе. Они нужны, чтобы `[[ссылки]]` не повисали.

**Как добавить новый движок?** Описать в `search/tools.py`, добавить клиент,
подключить в `search/engine.py`, добавить тест. Не встраивать условие в
агента.

**Как добавить нового агента?** Роль, сервис, инстанс в `core.py`,
узлы/рёбра в `workflow.py`, тест, docs, CODEOWNERS.

**Почему в отчёте есть SOTA SciERC, если мы не сравниваемся?** Это внешний
ориентир, чтобы читатель понимал масштаб. Прямое сравнение некорректно: SOTA
считает span NER/RE, а мы — канонические концепты.

**Что делать, если модель не влезает в GPU?** Использовать меньшую модель
или квантизацию, закрыть другие процессы, уменьшить контекст и батч. На
6 ГБ GPU 4B-модель работает, но медленно.

**Почему в проекте так много документов?** Потому что разные читатели хотят
разное: README для быстрого старта, ARCHITECTURE для инженеров, KP2_REPORT
для защиты, KG_METRICS для метрик, этот гайд для полного погружения.

## 10.3. Приложение A. Пример `_state.json`

Этот пример показывает структуру, а не реальную базу. В реальном файле
больше статей, концептов и полей.

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

Заметка источника — это обычный Markdown с frontmatter. В реальном vault
название файла очищено от запрещённых символов и может быть обрезано с
хэшем.

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

Концепт-хаб собирает определение и все упоминания концепта. Если в базе был
deep-режим, у упоминаний есть страницы и цитаты.

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

QA-отчёт показывает summary, статистику и список issues. В реальном отчёте
issues может быть больше; в примере только один warning.

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

Этот промпт используется в `paper_synthesis_prompt`. Он просит 6–8
концептов, требует явной поддержки в абстракте и ставит концепты первыми в
JSON.

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

# список и удаление
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

Главное, что стоит запомнить: LitGraphAgent — это конвейер, а не «магический
ИИ»; LLM — вероятностный компонент, поэтому есть валидация, JSON-санитайзер,
fallback-и и QA; граф знаний держится на каноникализации, ссылках и
дедупликации; `_state.json` — источник правды между запусками; бенчмарк
измеряет только то, что система реально предсказывает; 20 абстрактов — это
regression sample, а не лидерборд.

Если понадобится продолжить проект, начните с `README.md`, затем откройте
`docs/ARCHITECTURE.md` и `docs/kp2/KP2_REPORT.md`, а после — код агентов в
том порядке, в котором они вызываются: Lead → Retrieval → Prompt → Graph → QA.

Контакты и ссылки: репозиторий <https://github.com/Icold21/LitGraphAgent>,
команда AI-RIldium, лицензия MIT, дата сборки гайда — ноябрь 2026. Спасибо,
что дочитали. Дальше — только код, эксперименты и вопросы.
