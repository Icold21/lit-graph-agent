# Метрики для графов знаний и KG-бенчмарков

Справка для отчёта и защиты: какие метрики считаются стандартными, что они
показывают и где легко получить некорректное сравнение. В конце — что из
этого применимо к LitGraphAgent.

## 1. Базовые обозначения

Граф знаний обычно задают как набор троек:

```text
KG = (E, R, T),   T ⊆ E × R × E
```

- `E` — сущности (concepts, papers, авторы, методы);
- `R` — типы отношений (`cites`, `uses`, `part_of`, ...);
- `T` — факты (triples).

Для задач извлечения дополнительно есть текст и gold-разметка спанов.
Для link prediction — train/valid/test-сплиты и множество кандидатов.

## 2. Link prediction / KG completion

Это основной класс бенчмарков для `FB15k-237`, `WN18RR` и `OGB LinkPropPredDataset`.

### 2.1. Постановка

Для тестовой тройки `(h, r, t)` модель оценивает все возможные `t'` (или все
`h'`) и сортирует кандидатов по убыванию score. Истинная сущность получает
ранг `rank_i` (1 — лучший).

### 2.2. MRR

```text
MRR = (1 / |Q|) * Σ 1 / rank_i
```

- диапазон `0..1`, больше — лучше;
- сильно чувствует себя на «лёгких» запросах: одна хорошая догадка даёт
  большой вклад;
- стандарт для `FB15k-237`, `WN18RR`, OGB.

### 2.3. Hits@k

```text
Hits@k = (1 / |Q|) * Σ 1[rank_i <= k]
```

- доля запросов, где истинная сущность попала в top-k;
- обычно report `Hits@1`, `Hits@3`, `Hits@10`;
- для OGB часто `Hits@1`, `Hits@10`, `Hits@100`.

### 2.4. Mean Rank (MR)

```text
MR = (1 / |Q|) * Σ rank_i
```

Ниже — лучше, но метрика чувствительна к выбросам; в современных работах
обычно приводят MRR и Hits@k, а MR — как дополнительный сигнал.

### 2.5. Raw vs filtered

Главная ловушка. В raw-режиме среди кандидатов остаются другие истинные
тройки, и модель «наказывается» за правильный ответ, который просто не
совпал с тестовой тройкой. В filtered-режиме все известные истинные тройки,
кроме текущей, удаляются из кандидатов.

Правило: **всегда указывайте `filtered` или `raw`**. Сравнивать числа из
разных режимов нельзя.

### 2.6. Особенности бенчмарков

| Бенчмарк | Что оценивает | Стандартные метрики | Нюанс |
| --- | --- | --- | --- |
| `FB15k-237` | Link prediction по реальным фактам | Filtered MRR, Hits@1/3/10 | Убраны обратные отношения, чтобы модель не выучивала тривиальные inverse-правила |
| `WN18RR` | Link prediction по WordNet | Filtered MRR, Hits@10 | Специально очищен от inverse leakage; маленький и «лексический» |
| `ogbl-wikikg2` | Link prediction в Wikidata | MRR, Hits@1/10/100 | Официальный OGB-evaluator; свои сплиты ломают сравнимость |
| `ogbl-biokg` | Link prediction в биомедицинском KG | MRR, Hits@1/10/100 | Мульти-реляционный, другой домен |

Ориентиры: сильные модели на `FB15k-237` обычно дают примерно `0.33–0.36`
MRR, на `WN18RR` — примерно `0.45–0.55` MRR. Точные SOTA-числа смотрите в
официальном leaderboard: они меняются.

### 2.7. Что ещё влияет на число

- размер candidate set (все сущности или подвыборка);
- использование inverse relations;
- фильтрация valid/test leakage;
- усреднение по seed;
- tie-breaking при равных score;
- версия сплита.

## 3. Entity and relation extraction

Это класс задач `SciERC`, `ACE`, `CoNLL`, `NYT`, `WebNLG` и т.п.

### 3.1. NER / entity extraction

Стандарт — span-level precision, recall и F1:

```text
P = TP / (TP + FP)
R = TP / (TP + FN)
F1 = 2PR / (P + R)
```

Варианты:

- **strict** — границы спана и тип должны совпасть точно;
- **relaxed / partial** — допускается частичное совпадение границ;
- **micro** — агрегирование по всем упоминаниям;
- **macro** — среднее по типам сущностей (чувствительно к редким типам).

В SciERC типы: `Task`, `Method`, `Metric`, `Material`, `Generic`,
`OtherScientificTerm`. Для сравнения с литературой нужен официальный
scorer, а не самописный матчер.

### 3.2. Relation extraction

- **relation classification F1** — тип отношения для пары сущностей;
- **strict relation F1** — правильны и пара, и тип;
- **relaxed relation F1** — допускается частичное совпадение;
- **overlap-aware** — несколько отношений на одной паре.

Для SciERC стандартно считают entity F1 и relation F1 отдельно; relation F1
обычно заметно ниже. Сильные модели на SciERC дают entity F1 примерно
`60–70`, relation F1 — примерно `40–50`, но точные числа зависят от сплита и
scorer.

### 3.3. Почему нельзя смешивать с concept extraction

LitGraphAgent извлекает **канонические концепты**, а не копирует
аннотированные спаны. Поэтому наш `exact` — это нормализованное равенство
строк, а `relaxed` — Jaccard ≥ 0.5. Это полезная regression-метрика, но она
**не эквивалентна** SciERC NER F1 и тем более не заменяет relation F1.

## 4. KG construction / triple-level evaluation

Когда система строит граф с нуля, оценивают не только узлы, но и факты.

### 4.1. Triple precision / recall / F1

Предсказанная тройка `(h, r, t)` считается правильной, если после
entity linking и каноникализации она совпала с gold-тройкой.

```text
Triple P = correct triples / predicted triples
Triple R = correct triples / gold triples
Triple F1 = 2PR / (P + R)
```

Это самая честная метрика для «граф построен правильно», но она требует
размеченных отношений и сущностей.

### 4.2. Entity linking / canonicalization accuracy

- доля упоминаний, привязанных к правильной сущности;
- доля вариантов (`GNN`, `GNNs`, `Graph Neural Networks`), слитых в один
  концепт;
- ошибки over-merging (разные сущности слиты) и under-merging (одна
  сущность раздроблена).

### 4.3. Graph-level metrics

Не заменяют precision/recall, но полезны для диагностики:

| Метрика | Что показывает |
| --- | --- |
| Node coverage | Доля gold-концептов, попавших в граф |
| Edge coverage | Доля gold-связей, попавших в граф |
| Orphan rate | Доля узлов без рёбер |
| Unresolved link rate | Доля `[[wikilinks]]`, не находящих цель |
| Graph density | `2E / (N(N-1))` для неориентированного графа |
| Connected components | Число компонент связности |
| Clustering coefficient | Локальная кластеризация |
| Schema conformance | Доля троек, удовлетворяющих онтологии |
| Provenance accuracy | Доля рёбер с корректным источником/страницей |

Для Obsidian-vault особенно важны `orphan rate`, `unresolved link rate` и
`schema conformance`: они напрямую влияют на то, можно ли пользоваться базой.

## 5. KGQA и вопрос-ответ по графу

Стандартные метрики:

- **Hits@1 / accuracy** — правильный ответ первый;
- **F1** — токенный F1 для свободного ответа;
- **MRR** — если ответ ранжируется;
- **path recall** — доля вопросов, для которых найден правильный путь;
- **answer coverage** — доля вопросов, на которые система вообще дала ответ.

Для GraphRAG дополнительно смотрят:

- **context precision / recall** — сколько нужных фактов попало в контекст;
- **faithfulness** — ответ опирается на контекст, а не выдуман;
- **citation accuracy** — ссылка ведёт на правильный источник;
- **answer relevance** — ответ по существу вопроса.

## 6. Retrieval-метрики для поиска источников

Если система сначала ищет статьи, полезны:

```text
Precision@k = relevant@k / k
Recall@k = relevant@k / all_relevant
MRR = mean(1 / rank_first_relevant)
nDCG@k = DCG@k / IDCG@k
DCG@k = Σ (2^rel_i - 1) / log2(i + 1)
MAP = mean(average precision)
```

- `nDCG@k` учитывает порядок и градацию релевантности;
- `MAP` — среднее по запросам;
- для LitGraphAgent нужен размеченный набор «тема → релевантные статьи»,
  иначе метрика превращается в самооценку.

## 7. Node / graph property prediction

Для OGB-задач на узлах и рёбрах:

- **ROC-AUC** — бинарная классификация;
- **Average Precision (AP)** — при сильном дисбалансе классов;
- **Accuracy / micro-F1 / macro-F1** — многоклассовая классификация;
- **MRR / Hits@k** — link property prediction.

Важно: OGB требует официальный evaluator и официальный split. Свои сплиты
дают несравнимые числа.

## 8. Статистическая честность

Минимальный набор требований для отчёта:

1. Указать split, seed, число прогонов, версию модели и датасета.
2. Для нескольких seed приводить `mean ± std`, а не лучший прогон.
3. Для link prediction — `filtered` и размер candidate set.
4. Для extraction — strict/relaxed, micro/macro, границы спанов.
5. Не смешивать разные задачи в одной таблице без пометки.
6. Не называть 20 абстрактов «SOTA-сравнением».
7. Фиксировать failures: timeout, parse error, пустой ответ.

## 9. Что стоит добавить LitGraphAgent

Сейчас в README и отчёте есть:

- concept P/R/F1, exact и relaxed;
- paper → concept edges как бипартитная проекция;
- 20 абстрактов, 2 модели, 1 seed, 0 падений.

До КП3 имеет смысл добавить:

| Направление | Метрика | Зачем |
| --- | --- | --- |
| Triple-level | Triple P/R/F1 | Показать, что граф правильный, а не только узлы |
| Canonicalization | Merge accuracy, over/under-merge rate | Проверить `GNNs → Graph Neural Networks` |
| Vault quality | Orphan rate, unresolved link rate, schema conformance | Показать, что Obsidian-база связная |
| Coverage | Node/edge coverage против gold | Понять, сколько графа потеряно |
| Retrieval | nDCG@10, Precision@5, MRR | Оценить отбор источников |
| Provenance | Citation accuracy, page accuracy | Проверить, что ссылки не выдуманы |
| Robustness | Failure rate, p95 latency, cost per run | Показать инженерную зрелость |
| Statistics | mean ± std по 3 seed | Не заявлять результат одного прогона |

### 9.1. Что не стоит делать

- Считать relation F1, если пайплайн не предсказывает типы отношений.
- Сравнивать свой concept F1 с SciERC NER F1 без оговорки о разнице
  постановок.
- Отчитываться по `FB15k-237`/`WN18RR`, если задача — не link prediction.
- Показывать только лучший seed.
- Называть `relaxed`-метрику «точной»: это разные сигналы.

## 10. Короткая шпаргалка

| Задача | Главная метрика | Дополнительно |
| --- | --- | --- |
| KG completion | Filtered MRR | Hits@1/10 |
| NER | Span F1 | micro/macro, strict/relaxed |
| Relation extraction | Relation F1 | strict/relaxed, overlap-aware |
| KG construction | Triple F1 | entity linking, coverage |
| KGQA | Hits@1 / F1 | MRR, path recall |
| Retrieval | nDCG@k | MAP, Precision@k, Recall@k |
| Node classification | Accuracy / F1 | ROC-AUC, AP |
| Vault quality | Orphan/unresolved rate | schema conformance, coverage |

## 11. Полезные ссылки

- SciERC: <https://nlp.cs.washington.edu/sciIE/>
- FB15k-237: <https://paperswithcode.com/dataset/fb15k-237>
- WN18RR: <https://paperswithcode.com/dataset/wn18rr>
- OGB: <https://ogb.stanford.edu/docs/linkprop/>
- OGB evaluator: <https://github.com/snap-stanford/ogb>
- BEIR / retrieval metrics: <https://github.com/beir-cellar/beir>
