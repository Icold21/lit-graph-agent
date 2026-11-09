# Материалы КП2

Пакет промежуточной аттестации LitGraphAgent.

| Файл | Назначение |
| --- | --- |
| [KP2_REPORT.md](KP2_REPORT.md) | Полный отчёт по девяти пунктам КП2 |
| [KP2_SLIDES.md](KP2_SLIDES.md) | Структура презентации и текст выступления на 2 минуты |
| [kp2_presentation.pptx](kp2_presentation.pptx) | Готовая презентация, 7 слайдов с заметками докладчика |
| [kp2_presentation_kp1_style.pptx](kp2_presentation_kp1_style.pptx) | Вариант в стиле КП1: 8 слайдов, два мема с Тони Старком без подписей |
| [DEMO.md](DEMO.md) | Сценарий демонстрации прототипа и чек-лист скриншотов |
| [CONTRIBUTIONS.md](CONTRIBUTIONS.md) | Зоны ответственности и доказательная база вклада |
| [assets/architecture.png](assets/architecture.png) | Диаграмма архитектуры |
| [assets/roadmap.png](assets/roadmap.png) | Дорожная карта со статусами |
| [assets/metrics_qwen3.5-4b-prompt8.png](assets/metrics_qwen3.5-4b-prompt8.png) | График метрик SciERC (`qwen3.5:4b`, prompt v2) |
| [assets/metrics_qwen3.5-4b.png](assets/metrics_qwen3.5-4b.png) | График метрик SciERC (`qwen3.5:4b`, prompt v1) |
| [assets/metrics_qwen2.5-3b.png](assets/metrics_qwen2.5-3b.png) | График метрик SciERC (`qwen2.5:3b`) |
| [docs/ARCHITECTURE.md](../ARCHITECTURE.md) | Подробное описание архитектуры для КП3 |

## Быстрая проверка

```bash
pytest -q
ruff check lit_graph tests benchmarks
python benchmarks/plot_results.py benchmarks/results/scierc_qwen3.5-4b-prompt8.json
```

## Пересборка материалов

```bash
python docs/kp2/make_assets.py             # диаграммы
python docs/kp2/make_slides.py             # PPTX в стиле КП2
python docs/kp2/make_slides_kp1_style.py   # PPTX в стиле КП1 с мемами
```

Мемы для варианта в стиле КП1 взяты из открытых шаблонов imgflip и используются
как учебная цитата.

Диаграммы и слайды генерируются из кода, поэтому их можно обновить после
изменения метрик или архитектуры.
