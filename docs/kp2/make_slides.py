"""Build the KP2 slide deck from the report assets.

Run from the repository root::

    python docs/kp2/make_slides.py

Output: docs/kp2/kp2_presentation.pptx
"""

from __future__ import annotations

from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
OUTPUT = HERE / "kp2_presentation.pptx"

INK = RGBColor(0x0F, 0x17, 0x2A)
MUTED = RGBColor(0x47, 0x55, 0x69)
TEAL = RGBColor(0x0D, 0x94, 0x88)
BLUE = RGBColor(0x25, 0x63, 0xEB)
AMBER = RGBColor(0xD9, 0x77, 0x06)
RED = RGBColor(0xDC, 0x26, 0x26)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT = RGBColor(0xF8, 0xFA, 0xFC)
BORDER = RGBColor(0xCB, 0xD5, 0xE1)
PALE_TEAL = RGBColor(0xE6, 0xFF, 0xFB)

FONT = "Segoe UI"
W, H = 13.333, 7.5


def set_text(frame, text, size, color=INK, bold=False, align=PP_ALIGN.LEFT, space_after=6):
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.space_after = Pt(space_after)
    run = paragraph.add_run()
    run.text = text
    run.font.name = FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return frame


def add_textbox(slide, x, y, w, h, text, size, color=INK, bold=False, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    set_text(box.text_frame, text, size, color, bold, align)
    return box


def add_bullets(slide, x, y, w, h, items, size=15, color=MUTED, bullet_color=TEAL):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.space_after = Pt(9)
        paragraph.level = 0
        marker = paragraph.add_run()
        marker.text = "▪  "
        marker.font.name = FONT
        marker.font.size = Pt(size)
        marker.font.color.rgb = bullet_color
        run = paragraph.add_run()
        run.text = item
        run.font.name = FONT
        run.font.size = Pt(size)
        run.font.color.rgb = color
    return box


def header(slide, title, subtitle=None):
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(0.45), Inches(0.08), Inches(0.52))
    bar.fill.solid()
    bar.fill.fore_color.rgb = TEAL
    bar.line.fill.background()
    add_textbox(slide, 0.95, 0.38, 11.8, 0.7, title, 28, INK, True)
    if subtitle:
        add_textbox(slide, 0.95, 1.02, 11.8, 0.4, subtitle, 12, MUTED)


def footer(slide, number):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.7), Inches(7.02), Inches(11.93), Inches(0.01))
    line.fill.solid()
    line.fill.fore_color.rgb = BORDER
    line.line.fill.background()
    add_textbox(slide, 0.7, 7.08, 8.0, 0.3, "LitGraphAgent · КП2 · ноябрь 2026", 9, MUTED)
    add_textbox(slide, 11.3, 7.08, 1.3, 0.3, str(number), 9, MUTED, align=PP_ALIGN.RIGHT)


def add_image(slide, path, x, y, width=None, height=None):
    picture = slide.shapes.add_picture(str(path), Inches(x), Inches(y), width=Inches(width) if width else None,
                                       height=Inches(height) if height else None)
    return picture


def card(slide, x, y, w, h, accent, title, body):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = WHITE
    shape.line.color.rgb = BORDER
    shape.line.width = Pt(1)
    shape.adjustments[0] = 0.08
    strip = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(0.07), Inches(h))
    strip.fill.solid()
    strip.fill.fore_color.rgb = accent
    strip.line.fill.background()
    add_textbox(slide, x + 0.2, y + 0.14, w - 0.3, 0.35, title, 14, INK, True)
    add_textbox(slide, x + 0.2, y + 0.52, w - 0.3, h - 0.6, body, 11, MUTED)


def add_table(slide, x, y, w, h, rows, col_widths=None, font_size=11, header_color=TEAL):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(h))
    table = shape.table
    if col_widths:
        for index, width in enumerate(col_widths):
            table.columns[index].width = Inches(width)
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            cell = table.cell(row_index, col_index)
            cell.text = str(value)
            cell.margin_left = Inches(0.08)
            cell.margin_right = Inches(0.08)
            cell.margin_top = Inches(0.04)
            cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.alignment = PP_ALIGN.LEFT if col_index == 0 else PP_ALIGN.CENTER
            for run in paragraph.runs:
                run.font.name = FONT
                run.font.size = Pt(font_size)
                run.font.bold = row_index == 0
                run.font.color.rgb = WHITE if row_index == 0 else INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = header_color if row_index == 0 else (WHITE if row_index % 2 else LIGHT)
    return table


def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def build() -> Path:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    # 1. Title
    slide = prs.slides.add_slide(blank)
    background = slide.background.fill
    background.solid()
    background.fore_color.rgb = INK
    band = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(5.55), Inches(W), Inches(1.95))
    band.fill.solid()
    band.fill.fore_color.rgb = RGBColor(0x11, 0x1C, 0x33)
    band.line.fill.background()
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.9), Inches(1.55), Inches(0.1), Inches(2.25))
    accent.fill.solid()
    accent.fill.fore_color.rgb = TEAL
    accent.line.fill.background()
    add_textbox(slide, 1.2, 1.45, 10.5, 0.9, "LitGraphAgent", 54, WHITE, True)
    add_textbox(
        slide,
        1.2,
        2.45,
        10.0,
        1.3,
        "Автономный агент для сбора, наукометрической фильтрации\nи построения графов литературы в Obsidian",
        20,
        RGBColor(0xCB, 0xD5, 0xE1),
    )
    add_textbox(slide, 1.2, 5.75, 6.5, 0.4, "Команда AI-RIldium", 14, WHITE, True)
    add_textbox(slide, 1.2, 6.15, 10.5, 0.4, "github.com/Icold21/LitGraphAgent", 13, RGBColor(0x5E, 0xEA, 0xD4))
    add_textbox(slide, 10.3, 6.15, 2.3, 0.4, "КП2 · ноябрь 2026", 12, RGBColor(0x94, 0xA3, 0xB8), align=PP_ALIGN.RIGHT)
    notes(
        slide,
        "0:00–0:15. LitGraphAgent превращает тему и требования в готовый Obsidian-граф "
        "литературы: источники, концепты, связи и библиографию. Репозиторий открыт, лицензия MIT.",
    )

    # 2. Roadmap
    slide = prs.slides.add_slide(blank)
    header(slide, "Дорожная карта: план и статус", "Два этапа закрыты, третий в работе, финальный релиз — 15 декабря")
    add_image(slide, ASSETS / "roadmap.png", 0.75, 2.05, width=11.85)
    add_textbox(
        slide,
        0.75,
        6.25,
        11.85,
        0.5,
        "Отклонений, меняющих цель проекта, нет: менялись способ оркестрации и честность оценки.",
        12,
        MUTED,
    )
    footer(slide, 2)
    notes(
        slide,
        "0:15–0:35. По дорожной карте КП1 закрыты MVP и модульный поиск. Первые метрики получены. "
        "Сейчас идёт стабилизация, финальный релиз — к 15 декабря.",
    )

    # 3. Architecture
    slide = prs.slides.add_slide(blank)
    header(slide, "Архитектура: пять агентов на LangGraph", "Бизнес-логика — в агентах, граф отвечает за маршрутизацию и журнал hand-off")
    add_image(slide, ASSETS / "architecture.png", 1.55, 1.55, height=5.15)
    add_textbox(
        slide,
        0.75,
        6.8,
        11.85,
        0.25,
        "ResearchState · activity reducer · MemorySaver на запуск · _state.json как durable-хранилище",
        11,
        MUTED,
        align=PP_ALIGN.CENTER,
    )
    footer(slide, 3)
    notes(
        slide,
        "0:35–0:55. Пять ролей: Lead компилирует граф, Retrieval отвечает за источники, Prompt — за LLM, "
        "Graph пишет vault, QA проверяет. LangGraph только маршрутизирует шаги и ведёт журнал.",
    )

    # 4. What works
    slide = prs.slides.add_slide(blank)
    header(slide, "Что уже работает", "Прототип проходит путь от темы до проверенного vault")
    cards = [
        (TEAL, "CLI и жизненный цикл", "create · update · check\nlist · delete · --team · --tools"),
        (BLUE, "Поиск", "Semantic Scholar · arXiv · open web\nfallback · sub-queries · PDF в --deep"),
        (AMBER, "Выбор движков", "LLM читает каталог\nSearchRouter валидирует план"),
        (RED, "Граф", "источники · concept hubs\n[[wikilinks]] · typed edges · stubs"),
        (TEAL, "Обновления", "_state.json · атомарная запись\nсуществующие определения сохраняются"),
        (BLUE, "QA", "ссылки · frontmatter · дубли\nцелостность concept ↔ paper"),
    ]
    for index, (accent, title, body) in enumerate(cards):
        col = index % 3
        row = index // 3
        card(slide, 0.75 + col * 3.98, 1.65 + row * 1.95, 3.78, 1.7, accent, title, body)
    add_textbox(
        slide,
        0.75,
        5.8,
        11.85,
        0.4,
        "Все компоненты запускаются из одного CLI; полный сценарий — в docs/kp2/DEMO.md.",
        11,
        MUTED,
    )
    footer(slide, 4)
    notes(
        slide,
        "0:55–1:15. Прототип работает целиком: CLI создаёт и обновляет базу, три движка выбираются "
        "моделью, PDF подтягиваются в deep-режиме, на выходе — заметки, хабы, ссылки и библиография.",
    )

    # 5. Metrics
    slide = prs.slides.add_slide(blank)
    header(slide, "Качество: первые метрики", "SciERC · 20 абстрактов · qwen3.5:4b · seed=42 · 0 падений")
    add_image(slide, ASSETS / "metrics_qwen3.5-4b-prompt8.png", 0.55, 1.55, width=7.35)
    add_table(
        slide,
        8.05,
        1.7,
        4.55,
        2.05,
        [
            ["Сигнал", "F1"],
            ["Концепты, exact", "0.422"],
            ["Концепты, relaxed", "0.583"],
            ["Content, relaxed", "0.629"],
        ],
        col_widths=[3.15, 1.4],
        font_size=11,
    )
    add_textbox(slide, 8.05, 4.0, 4.55, 0.5, "Инфраструктура качества", 13, INK, True)
    add_bullets(
        slide,
        8.05,
        4.4,
        4.55,
        2.2,
        [
            "55 тестов, ruff без ошибок",
            "CI: Python 3.10–3.13",
            "0 падений из 20 абстрактов",
            "3b и 4b: 0.345 / 0.422 exact",
        ],
        size=11.5,
    )
    add_textbox(
        slide,
        0.7,
        6.35,
        7.2,
        0.55,
        "Exact — нормализованное равенство; relaxed — token Jaccard ≥ 0.5.\n"
        "Опорные: пустое — 0; qwen2.5:3b — 0.345/0.464; oracle — 1.0; SciERC SOTA — 73.4 (др. задача).",
        9,
        MUTED,
    )
    footer(slide, 5)
    notes(
        slide,
        "1:15–1:40. SciERC: 20 абстрактов, две локальные модели, ноль падений. На 4B с промптом v2 F1 концептов 0.422 exact "
        "и 0.583 relaxed; без Generic-сущностей relaxed F1 0.629. Плюс 55 тестов и CI на четырёх версиях Python.",
    )

    # 6. Changes and risks
    slide = prs.slides.add_slide(blank)
    header(slide, "Изменения плана и риски", "Что поменяли, почему и как это влияет на цель")
    left = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.75), Inches(1.55), Inches(5.8), Inches(3.15))
    left.fill.solid()
    left.fill.fore_color.rgb = LIGHT
    left.line.color.rgb = BORDER
    add_textbox(slide, 1.0, 1.72, 5.3, 0.4, "Изменения", 17, TEAL, True)
    add_bullets(
        slide,
        1.0,
        2.2,
        5.25,
        2.4,
        [
            "LangGraph вместо самописной шины: явные узлы и журнал",
            "LLM выбирает поисковые движки из каталога",
            "Бенчмарк сужен до концептов, без фиктивного relation F1",
            "Добавлены checkpoint/resume и запись failures",
        ],
        size=12,
    )
    right = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.8), Inches(1.55), Inches(5.8), Inches(3.15))
    right.fill.solid()
    right.fill.fore_color.rgb = LIGHT
    right.line.color.rgb = BORDER
    add_textbox(slide, 7.05, 1.72, 5.3, 0.4, "Риски и план до 15 декабря", 17, AMBER, True)
    add_bullets(
        slide,
        7.05,
        2.2,
        5.25,
        2.4,
        [
            "20 абстрактов на модель, 1 seed → 100 абстрактов, 3 seed",
            "Нет end-to-end метрики поиска → precision@k и nDCG",
            "Нет покрытия → pytest --cov и порог",
            "Нет демо → запись, скриншоты, E2E smoke-тест",
            "Вклад в git → коммиты каждого участника",
        ],
        size=12,
        bullet_color=AMBER,
    )
    add_textbox(
        slide,
        0.75,
        5.05,
        11.85,
        0.55,
        "Итог: цель проекта не меняется — локальный граф смысловых концептов "
        "и автоматическая библиография.",
        12,
        INK,
    )
    footer(slide, 6)
    notes(
        slide,
        "1:40–1:55. Главное изменение — LangGraph и LLM-выбор движков. Главный риск — узкая оценка: "
        "только концепты, 20 абстрактов на модель, один seed. До финала расширяем выборку и добавляем end-to-end метрики.",
    )

    # 7. Team and self-assessment
    slide = prs.slides.add_slide(blank)
    header(slide, "Команда и самооценка", "Зоны ответственности закреплены в CODEOWNERS и CONTRIBUTORS")
    add_table(
        slide,
        0.75,
        1.55,
        7.7,
        3.35,
        [
            ["Участник", "Зона"],
            ["Иван Холодило", "Архитектура, LangGraph, CLI, состояние"],
            ["Вадим Лялькин", "Онтология графа, wikilinks, Obsidian"],
            ["Нодар Чигладзе", "arXiv / S2 / web, ранжирование, PDF"],
            ["Давид Чигладзе", "QA, тесты, CI, бенчмарк"],
            ["Илья Синко", "Промпты, валидация, синтез"],
        ],
        col_widths=[2.55, 5.15],
        font_size=10.5,
    )
    panel = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(8.75), Inches(1.55), Inches(3.85), Inches(3.35))
    panel.fill.solid()
    panel.fill.fore_color.rgb = PALE_TEAL
    panel.line.color.rgb = TEAL
    add_textbox(slide, 9.0, 1.72, 3.4, 0.4, "Готовность к КП2", 14, TEAL, True)
    add_textbox(slide, 9.0, 2.12, 3.4, 0.8, "8 / 10", 38, INK, True)
    add_textbox(
        slide,
        9.0,
        2.95,
        3.4,
        1.75,
        "Ядро и инфраструктура качества готовы.\n\n"
        "Глубина оценки и доказательства вклада — основные задачи до КП3.",
        11,
        MUTED,
    )
    add_textbox(
        slide,
        0.75,
        5.25,
        11.85,
        0.9,
        "Главный результат КП2: переход от идеи и MVP к воспроизводимой системе "
        "с архитектурой, тестами, бенчмарком и планом до финальной защиты.",
        13,
        INK,
    )
    footer(slide, 7)
    notes(
        slide,
        "1:55–2:00. Готовность к КП2 — 8 из 10. Ядро и инфраструктура качества готовы, "
        "основные усилия до декабря — глубина оценки и доказательства вклада каждого.",
    )

    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(f"Wrote {build()}")
