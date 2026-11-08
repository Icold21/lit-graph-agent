# Материалы КП2

Пакет промежуточной аттестации LitGraphAgent.

| Файл | Назначение |
| --- | --- |
| [KP2_REPORT.md](KP2_REPORT.md) | Полный отчёт по девяти пунктам КП2 |
| [KP2_SLIDES.md](KP2_SLIDES.md) | Структура презентации и текст выступления на 2 минуты |
| [kp2_presentation.pptx](kp2_presentation.pptx) | Готовая презентация, 7 слайдов с заметками докладчика |
| [DEMO.md](DEMO.md) | Сценарий демонстрации прототипа и чек-лист скриншотов |
| [CONTRIBUTIONS.md](CONTRIBUTIONS.md) | Зоны ответственности и доказательная база вклада |
| [assets/architecture.png](assets/architecture.png) | Диаграмма архитектуры |
| [assets/roadmap.png](assets/roadmap.png) | Дорожная карта со статусами |
| [assets/metrics_qwen3.5-4b.png](assets/metrics_qwen3.5-4b.png) | График метрик SciERC (`qwen3.5:4b`) |
| [assets/metrics_qwen2.5-3b.png](assets/metrics_qwen2.5-3b.png) | График метрик SciERC (`qwen2.5:3b`) |
| [docs/ARCHITECTURE.md](../ARCHITECTURE.md) | Подробное описание архитектуры для КП3 |

## Быстрая проверка

```bash
pytest -q
ruff check lit_graph tests benchmarks
python benchmarks/plot_results.py benchmarks/results/scierc_qwen3.5-4b.json
```

## Пересборка материалов

```bash
python docs/kp2/make_assets.py    # диаграммы
python docs/kp2/make_slides.py    # PPTX
```

Диаграммы и слайды генерируются из кода, поэтому их можно обновить после
изменения метрик или архитектуры.
