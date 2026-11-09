"""Build the KP2 deck in the visual language of the KP1 presentation.

The KP1 deck used a light paper background, very large black headings, pale
rounded cards with thin borders and small colour accents.  This script recreates
that language for the KP2 content and adds two Tony Stark meme inserts.

Run from the repository root::

    python docs/kp2/make_slides_kp1_style.py

Output: docs/kp2/kp2_presentation_kp1_style.pptx
"""

from __future__ import annotations

import random
from pathlib import Path

from PIL import Image, ImageDraw
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

HERE = Path(__file__).resolve().parent
ASSETS = HERE / "assets"
OUTPUT = HERE / "kp2_presentation_kp1_style.pptx"
BACKGROUND = ASSETS / "kp1_paper_background.png"

W, H = 13.333, 7.5

INK = RGBColor(0x0B, 0x0F, 0x19)
MUTED = RGBColor(0x4B, 0x55, 0x63)
SOFT = RGBColor(0x6B, 0x72, 0x80)
PAPER = RGBColor(0xF6, 0xF6, 0xF4)
CARD = RGBColor(0xFF, 0xFF, 0xFF)
CARD_ALT = RGBColor(0xF3, 0xF4, 0xF6)
BORDER = RGBColor(0xD1, 0xD5, 0xDB)
SHADOW = RGBColor(0xE9, 0xEA, 0xEC)
TEAL = RGBColor(0x0D, 0x94, 0x88)
GREEN = RGBColor(0x05, 0x96, 0x69)
PURPLE = RGBColor(0x7C, 0x3A, 0xED)
BLUE = RGBColor(0x25, 0x63, 0xEB)
AMBER = RGBColor(0xD9, 0x77, 0x06)
RED = RGBColor(0xDC, 0x26, 0x26)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE_TEAL = RGBColor(0xE6, 0xFA, 0xF5)
PALE_BLUE = RGBColor(0xE8, 0xEF, 0xFF)
PALE_PURPLE = RGBColor(0xF1, 0xEA, 0xFF)
PALE_AMBER = RGBColor(0xFF, 0xF4, 0xE5)
PALE_RED = RGBColor(0xFE, 0xE9, 0xE9)

FONT = "Segoe UI"
FONT_BOLD = "Segoe UI Semibold"

# The deck uses only three type sizes: heading, body and small label.
SIZE_HEADING = 40
SIZE_BODY = 18
SIZE_SMALL = 14


def snap(size: float) -> int:
    if size >= 24:
        return SIZE_HEADING
    if size >= 12:
        return SIZE_BODY
    return SIZE_SMALL


# ---------------------------------------------------------------------------
# primitives
# ---------------------------------------------------------------------------


def make_background() -> Path:
    """Create a very subtle paper / dot texture used behind every slide."""
    if BACKGROUND.exists():
        return BACKGROUND
    width, height = 2400, 1350
    image = Image.new("RGB", (width, height), (0xF6, 0xF6, 0xF4))
    draw = ImageDraw.Draw(image)
    rng = random.Random(42)
    for y in range(0, height, 22):
        for x in range(0, width, 22):
            if rng.random() < 0.55:
                tone = 0xE9 + rng.randint(0, 5)
                draw.point((x, y), fill=(tone, tone, tone - 1))
    for _ in range(1400):
        x = rng.randrange(width)
        y = rng.randrange(height)
        tone = 0xEE + rng.randint(0, 5)
        draw.point((x, y), fill=(tone, tone, tone - 1))
    image.save(BACKGROUND)
    return BACKGROUND


def add_background(slide) -> None:
    slide.shapes.add_picture(str(make_background()), 0, 0, width=Inches(W), height=Inches(H))


def set_text(
    frame,
    text: str,
    size: float,
    color: RGBColor = INK,
    bold: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    font: str = FONT,
    line_spacing: float | None = None,
    space_after: float = 0,
) -> None:
    frame.clear()
    frame.word_wrap = True
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.space_after = Pt(space_after)
    if line_spacing:
        paragraph.line_spacing = line_spacing
    run = paragraph.add_run()
    run.text = text
    run.font.name = font
    run.font.size = Pt(snap(size))
    run.font.bold = bold
    run.font.color.rgb = color


def textbox(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    text: str,
    size: float,
    color: RGBColor = INK,
    bold: bool = False,
    align: PP_ALIGN = PP_ALIGN.LEFT,
    font: str = FONT,
    line_spacing: float | None = None,
    anchor: MSO_ANCHOR = MSO_ANCHOR.TOP,
):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    box.text_frame.vertical_anchor = anchor
    box.text_frame.margin_left = 0
    box.text_frame.margin_right = 0
    box.text_frame.margin_top = 0
    box.text_frame.margin_bottom = 0
    set_text(box.text_frame, text, size, color, bold, align, font, line_spacing)
    return box


def no_shadow(shape) -> None:
    """Remove the theme shape style so LibreOffice/PowerPoint add no shadow."""
    try:
        shape.shadow.inherit = False
    except Exception:
        pass
    try:
        from pptx.oxml.ns import qn

        style = shape._element.find(qn("p:style"))
        if style is not None:
            shape._element.remove(style)
    except Exception:
        pass


def shadow_card(
    slide,
    x: float,
    y: float,
    w: float,
    h: float,
    fill: RGBColor = CARD,
    line: RGBColor = BORDER,
    radius: float = 0.10,
    shadow: bool = True,
):
    if shadow:
        back = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x + 0.025), Inches(y + 0.032), Inches(w), Inches(h)
        )
        back.fill.solid()
        back.fill.fore_color.rgb = SHADOW
        back.line.fill.background()
        back.adjustments[0] = radius
        no_shadow(back)
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.color.rgb = line
    shape.line.width = Pt(0.9)
    shape.adjustments[0] = radius
    no_shadow(shape)
    return shape


def accent_strip(slide, x: float, y: float, w: float, h: float, color: RGBColor):
    strip = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    strip.fill.solid()
    strip.fill.fore_color.rgb = color
    strip.line.fill.background()
    strip.adjustments[0] = 0.35
    no_shadow(strip)
    return strip


def pill(slide, x: float, y: float, w: float, h: float, text: str, fill: RGBColor, color: RGBColor, size: float = 10):
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    shape.line.fill.background()
    shape.adjustments[0] = 0.25
    no_shadow(shape)
    frame = shape.text_frame
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    set_text(frame, text, size, color, True, PP_ALIGN.CENTER)
    return shape


def section(slide, label: str, color: RGBColor = TEAL):
    textbox(slide, 0.75, 0.42, 9.5, 0.3, label.upper(), 10.5, color, True, font=FONT_BOLD)


def heading(slide, title: str, size: float = 38, y: float = 0.74, w: float = 11.9):
    textbox(slide, 0.75, y, w, 1.2, title, size, INK, True, line_spacing=0.95)


def footer(slide, number: int, label: str = "LitGraphAgent · КП2 · ноябрь 2026"):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.75), Inches(6.96), Inches(11.83), Inches(0.012))
    line.fill.solid()
    line.fill.fore_color.rgb = BORDER
    line.line.fill.background()
    no_shadow(line)
    textbox(slide, 0.75, 7.04, 8.0, 0.25, label, 8.5, SOFT)
    textbox(slide, 11.7, 7.04, 0.9, 0.25, f"{number:02d}", 8.5, SOFT, align=PP_ALIGN.RIGHT)


def notes(slide, text: str) -> None:
    slide.notes_slide.notes_text_frame.text = text


def image_asset(name: str) -> Path | None:
    matches = sorted(ASSETS.glob(f"{name}.*"))
    for path in matches:
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
            return path
    return None


def meme(slide, path: Path | None, x: float, y: float, w: float, h: float) -> None:
    """Place a framed meme without any caption or speech bubble."""
    shadow_card(slide, x - 0.08, y - 0.08, w + 0.16, h + 0.16, fill=CARD, line=BORDER, radius=0.06)
    if path:
        pic = slide.shapes.add_picture(str(path), Inches(x), Inches(y), Inches(w), Inches(h))
        pic.line.color.rgb = WHITE
        pic.line.width = Pt(2.5)
    else:
        shadow_card(slide, x, y, w, h, fill=CARD_ALT, line=BORDER, radius=0.04)
        textbox(slide, x + 0.2, y + h / 2 - 0.2, w - 0.4, 0.4, "мем загружается…", 12, SOFT, align=PP_ALIGN.CENTER)


def check_card(slide, x: float, y: float, w: float, h: float, title: str, body: str, accent: RGBColor):
    shadow_card(slide, x, y, w, h, fill=CARD, line=BORDER, radius=0.12)
    circle = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 0.18), Inches(y + 0.18), Inches(0.34), Inches(0.34))
    circle.fill.solid()
    circle.fill.fore_color.rgb = accent
    circle.line.fill.background()
    no_shadow(circle)
    frame = circle.text_frame
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0
    frame.vertical_anchor = MSO_ANCHOR.MIDDLE
    set_text(frame, "✓", 14, WHITE, True, PP_ALIGN.CENTER)
    textbox(slide, x + 0.64, y + 0.15, w - 0.8, 0.28, title, 12.5, INK, True)
    textbox(slide, x + 0.64, y + 0.47, w - 0.8, h - 0.55, body, 9.5, MUTED, line_spacing=1.05)


def stat_card(slide, x: float, y: float, w: float, h: float, value: str, label: str, accent: RGBColor, pale: RGBColor):
    shadow_card(slide, x, y, w, h, fill=pale, line=accent, radius=0.12)
    textbox(slide, x + 0.18, y + 0.12, w - 0.36, 0.55, value, 30, accent, True, font=FONT_BOLD)
    textbox(slide, x + 0.18, y + 0.68, w - 0.36, 0.3, label, 9.5, MUTED, True)


def bullet_list(slide, x: float, y: float, w: float, h: float, items: list[str], size: float = 12, color: RGBColor = MUTED, marker: str = "•", marker_color: RGBColor = TEAL):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    frame = box.text_frame
    frame.clear()
    frame.word_wrap = True
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0
    for index, item in enumerate(items):
        paragraph = frame.paragraphs[0] if index == 0 else frame.add_paragraph()
        paragraph.space_after = Pt(7)
        run = paragraph.add_run()
        run.text = f"{marker}  "
        run.font.name = FONT
        run.font.size = Pt(snap(size))
        run.font.bold = True
        run.font.color.rgb = marker_color
        run = paragraph.add_run()
        run.text = item
        run.font.name = FONT
        run.font.size = Pt(snap(size))
        run.font.color.rgb = color
    return box


# ---------------------------------------------------------------------------
# slides
# ---------------------------------------------------------------------------


def slide_title(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)

    pill(slide, 0.75, 0.48, 4.25, 0.38, "2 · КОНТРОЛЬНАЯ ТОЧКА", PALE_TEAL, TEAL, 10.5)
    textbox(slide, 0.75, 1.10, 7.2, 0.9, "LitGraphAgent", 56, INK, True, font=FONT_BOLD)
    textbox(
        slide,
        0.78,
        2.42,
        6.8,
        1.25,
        "Автономный агент для сбора, наукометрической\nфильтрации и построения графов литературы\nв Obsidian",
        17,
        INK,
        line_spacing=1.12,
    )

    tags = [
        ("Python 3.10+", TEAL, PALE_TEAL),
        ("MIT License", SOFT, CARD_ALT),
        ("Obsidian Native", PURPLE, PALE_PURPLE),
        ("arXiv & Semantic Scholar", BLUE, PALE_BLUE),
    ]
    x = 0.78
    y = 3.75
    for text, color, pale in tags:
        width = 0.52 + len(text) * 0.112
        if x + width > 7.2:
            x = 0.78
            y += 0.46
        pill(slide, x, y, width, 0.36, text, pale, color, 14)
        x += width + 0.10

    shadow_card(slide, 0.78, 4.88, 6.35, 0.52, fill=CARD, line=BORDER, radius=0.16)
    textbox(slide, 1.0, 4.99, 5.9, 0.3, "github.com/Icold21/lit-graph-agent", 13, INK, True)

    textbox(slide, 0.78, 6.55, 7.0, 0.3, "Команда AI-RIldium · КП2 · ноябрь 2026", 10.5, SOFT, True)
    textbox(slide, 0.78, 6.95, 7.0, 0.25, "2 минуты доклада · 1 минута вопросов", 8.5, SOFT)

    meme(
        slide,
        image_asset("tony_hologram"),
        7.90,
        1.25,
        4.90,
        3.06,
    )
    notes(
        slide,
        "0:00–0:10. LitGraphAgent превращает тему и требования в готовый Obsidian-граф "
        "литературы: источники, концепты, связи и библиографию.",
    )
    return slide


def slide_context(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)
    section(slide, "Зачем это нужно")
    heading(slide, "Информационный шум\nпобеждает ручной анализ", 38)

    cards = [
        ("Тысячи препринтов", "Каждый день выходят новые статьи. Просмотреть всё вручную невозможно.", TEAL, PALE_TEAL),
        ("LLM выдумывают", "Базовые модели галлюцинируют источники и факты. Нужна проверка и provenance.", PURPLE, PALE_PURPLE),
        ("Рутина съедает время", "Связи между статьями и библиография собираются часами.", AMBER, PALE_AMBER),
    ]
    for index, (title, body, accent, pale) in enumerate(cards):
        x = 0.75 + index * 4.05
        shadow_card(slide, x, 2.55, 3.82, 1.52, fill=CARD, line=BORDER, radius=0.12)
        accent_strip(slide, x + 0.18, 2.75, 0.08, 0.34, accent)
        textbox(slide, x + 0.38, 2.72, 3.2, 0.3, title, 15, INK, True)
        textbox(slide, x + 0.38, 3.10, 3.2, 0.8, body, 10.5, MUTED, line_spacing=1.1)

    shadow_card(slide, 0.75, 4.42, 11.83, 1.15, fill=PALE_BLUE, line=BLUE, radius=0.10)
    textbox(slide, 1.0, 4.60, 11.3, 0.35, "LitGraphAgent", 14, BLUE, True)
    textbox(
        slide,
        1.0,
        4.94,
        11.3,
        0.4,
        "тема → проверенные источники → граф концептов → готовая библиография",
        14,
        INK,
        True,
    )
    textbox(slide, 0.78, 5.88, 11.6, 0.4, "Не поисковик и не замена эксперту: автоматизация сбора, отбора и оформления.", 10.5, SOFT)
    footer(slide, 2)
    notes(slide, "0:10–0:25. Проблема — информационный шум, галлюцинации LLM и рутина с библиографией. Решение — локальный граф концептов.")
    return slide


def slide_roadmap(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)
    section(slide, "План и статус")
    heading(slide, "Дорожная карта: два этапа закрыты", 36)

    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.85), Inches(3.58), Inches(11.5), Inches(0.035))
    line.fill.solid()
    line.fill.fore_color.rgb = BORDER
    line.line.fill.background()
    no_shadow(line)

    milestones = [
        (1.00, "6 ОКТ", "Базовый MVP", "Поиск, фильтрация,\nObsidian-заметки", GREEN, "готово", True),
        (4.00, "5 НОЯ", "Модульный поиск", "Выбор движка,\nпервые метрики", GREEN, "готово", False),
        (7.00, "25 НОЯ", "Стабилизация", "Тесты, калибровка,\nапдейты", AMBER, "в работе", True),
        (10.00, "15 ДЕК", "Финальный релиз", "Метрики, демо,\nдокументация", BLUE, "по плану", False),
    ]
    for x, date, title, body, accent, status, above in milestones:
        dot = slide.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + 1.05), Inches(3.44), Inches(0.30), Inches(0.30))
        dot.fill.solid()
        dot.fill.fore_color.rgb = accent
        dot.line.color.rgb = WHITE
        dot.line.width = Pt(3)
        no_shadow(dot)
        textbox(slide, x + 0.55, 3.02, 1.4, 0.25, date, 14, accent, True, align=PP_ALIGN.CENTER)
        card_y = 1.40 if above else 3.90
        shadow_card(slide, x, card_y, 2.85, 1.55, fill=CARD, line=BORDER, radius=0.10)
        accent_strip(slide, x + 0.16, card_y + 0.16, 0.07, 0.30, accent)
        textbox(slide, x + 0.34, card_y + 0.12, 2.45, 0.30, title, 18, INK, True)
        textbox(slide, x + 0.34, card_y + 0.52, 2.45, 0.58, body, 18, MUTED, line_spacing=1.05)
        pill(slide, x + 1.38, card_y + 1.08, 1.28, 0.40, status, accent, WHITE, 14)

    textbox(slide, 0.78, 6.18, 11.7, 0.4, "Цель проекта не меняется: локальный граф смысловых концептов и автоматическая библиография.", 10.5, SOFT)
    footer(slide, 3)
    notes(slide, "0:25–0:40. MVP и модульный поиск закрыты. Сейчас идёт стабилизация, финальный релиз — 15 декабря.")
    return slide


def slide_architecture(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)
    section(slide, "Один сквозной пайплайн")
    heading(slide, "Пять агентов, один LangGraph", 36)

    agents = [
        ("Lead", "архитектура,\nCLI, состояние", TEAL, PALE_TEAL),
        ("Retrieval", "arXiv / S2 / web,\nранжирование, PDF", BLUE, PALE_BLUE),
        ("Prompt", "валидация,\nсинтез, концепты", PURPLE, PALE_PURPLE),
        ("Graph", "онтология,\nwikilinks, vault", GREEN, PALE_TEAL),
        ("QA", "ссылки, формат,\nцелостность", AMBER, PALE_AMBER),
    ]
    x = 0.75
    for index, (name, body, accent, pale) in enumerate(agents):
        shadow_card(slide, x, 2.05, 2.18, 1.55, fill=pale, line=accent, radius=0.12)
        textbox(slide, x + 0.18, 2.22, 1.8, 0.35, name, 16, accent, True, font=FONT_BOLD)
        textbox(slide, x + 0.18, 2.64, 1.8, 0.8, body, 9.5, MUTED, line_spacing=1.05)
        if index < 4:
            arrow = slide.shapes.add_shape(
                MSO_SHAPE.RIGHT_ARROW, Inches(x + 2.24), Inches(2.70), Inches(0.22), Inches(0.22)
            )
            arrow.fill.solid()
            arrow.fill.fore_color.rgb = BORDER
            arrow.line.fill.background()
            no_shadow(arrow)
        x += 2.44

    shadow_card(slide, 0.75, 3.95, 11.83, 0.95, fill=CARD, line=BORDER, radius=0.10)
    textbox(slide, 1.0, 4.10, 11.3, 0.3, "LangGraph StateGraph", 12.5, INK, True)
    textbox(
        slide,
        1.0,
        4.42,
        11.3,
        0.3,
        "явные узлы и рёбра · ResearchState · activity reducer · MemorySaver на запуск · _state.json как durable-хранилище",
        9.5,
        MUTED,
    )

    textbox(slide, 0.78, 5.20, 11.7, 0.9, "Бизнес-логика живёт в агентах. Граф только маршрутизирует шаги и ведёт журнал hand-off.", 12, INK, True)
    textbox(slide, 0.78, 6.18, 11.7, 0.45, "Новый агент добавляется ролью, сервисом, узлом и тестом — без переписывания pipeline.", 10.5, SOFT)
    footer(slide, 4)
    notes(slide, "0:40–1:00. Пять ролей на LangGraph. Бизнес-логика в агентах, граф маршрутизирует шаги и ведёт журнал hand-off.")
    return slide


def slide_works(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)
    section(slide, "Прототип")
    heading(slide, "Путь от темы до проверенного vault", 36)

    cards = [
        ("CLI и жизненный цикл", "create · update · check · list · delete · --team · --tools", TEAL),
        ("Поиск", "Semantic Scholar · arXiv · open web · fallback · PDF в --deep", BLUE),
        ("Выбор движков", "LLM читает каталог, SearchRouter валидирует план", PURPLE),
        ("Граф", "источники · concept hubs · [[wikilinks]] · typed edges · stubs", GREEN),
        ("Обновления", "_state.json · атомарная запись · старые определения сохраняются", AMBER),
        ("QA", "ссылки · frontmatter · дубли · целостность concept ↔ paper", RED),
    ]
    for index, (title, body, accent) in enumerate(cards):
        row = index // 2
        col = index % 2
        check_card(slide, 0.75 + col * 6.0, 1.95 + row * 1.34, 5.78, 1.08, title, body, accent)

    shadow_card(slide, 0.75, 6.18, 11.83, 0.50, fill=PALE_BLUE, line=BLUE, radius=0.12)
    textbox(slide, 1.0, 6.29, 11.3, 0.28, "Всё запускается одной командой: litgraph", 11.5, BLUE, True)
    footer(slide, 5)
    notes(slide, "1:00–1:20. Прототип работает целиком: CLI, три источника, выбор движков, граф, обновления и QA.")
    return slide


def slide_metrics(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)
    section(slide, "Первые метрики")
    heading(slide, "SciERC: качество извлечения концептов", 34)

    stats = [
        ("0.422", "exact F1", TEAL, PALE_TEAL),
        ("0.583", "relaxed F1", BLUE, PALE_BLUE),
        ("0.629", "content F1", PURPLE, PALE_PURPLE),
    ]
    for index, (value, label, accent, pale) in enumerate(stats):
        stat_card(slide, 0.75 + index * 2.15, 1.78, 1.95, 1.10, value, label, accent, pale)

    chart = ASSETS / "metrics_qwen3.5-4b-prompt8.png"
    if chart.exists():
        slide.shapes.add_picture(str(chart), Inches(0.62), Inches(2.98), width=Inches(6.70))

    shadow_card(slide, 8.05, 3.10, 4.55, 2.45, fill=CARD, line=BORDER, radius=0.10)
    textbox(slide, 8.28, 3.26, 4.1, 0.3, "Как считали", 12.5, INK, True)
    bullet_list(
        slide,
        8.28,
        3.64,
        4.05,
        1.8,
        [
            "20 абстрактов SciERC, seed=42",
            "qwen3.5:4b и qwen2.5:3b",
            "0 падений",
            "exact — строка, relaxed — Jaccard ≥ 0.5",
        ],
        size=10,
    )
    textbox(slide, 8.05, 5.72, 4.55, 0.55, "Типизированные отношения не оцениваются:\nпайплайн их не предсказывает.", 8.5, SOFT)
    textbox(slide, 0.78, 6.38, 7.0, 0.25, "Это regression sample, не заявка на state-of-the-art.", 8.5, SOFT)
    footer(slide, 6)
    notes(
        slide,
        "1:20–1:40. SciERC, 20 абстрактов, две модели, ноль падений. На 4B с промптом v2 F1 0.422 exact, "
        "0.583 relaxed и 0.629 без Generic-сущностей.",
    )
    return slide


def slide_reference(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)
    section(slide, "Опорные точки")
    heading(slide, "С чем сравниваем метрики", 36)

    rows = [
        ("Точка сравнения", "Что это", "F1"),
        ("Пустое предсказание", "нижняя граница: концепты не извлекаются", "0.000"),
        ("qwen2.5:3b", "меньшая модель, те же 20 абстрактов и seed", "0.345 / 0.464 / 0.512"),
        ("qwen3.5:4b, prompt v2", "текущая формулировка 6–8 концептов", "0.422 / 0.583 / 0.629"),
        ("SciERC SOTA", "span-level NER/RE, другая постановка", "73.4 / 56.9 / 44.3"),
        ("Gold oracle", "верхняя граница: все gold-упоминания", "1.000"),
    ]
    shape = slide.shapes.add_table(len(rows), 3, Inches(0.75), Inches(1.70), Inches(11.83), Inches(3.55))
    table = shape.table
    widths = [2.55, 6.15, 3.13]
    for index, width in enumerate(widths):
        table.columns[index].width = Inches(width)
    for row_index, row in enumerate(rows):
        for col_index, value in enumerate(row):
            cell = table.cell(row_index, col_index)
            cell.text = value
            cell.margin_left = Inches(0.12)
            cell.margin_right = Inches(0.12)
            cell.margin_top = Inches(0.05)
            cell.margin_bottom = Inches(0.05)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            paragraph = cell.text_frame.paragraphs[0]
            paragraph.alignment = PP_ALIGN.LEFT if col_index < 2 else PP_ALIGN.CENTER
            for run in paragraph.runs:
                run.font.name = FONT
                run.font.size = Pt(18)
                run.font.bold = row_index == 0 or col_index == 0
                run.font.color.rgb = WHITE if row_index == 0 else INK
            cell.fill.solid()
            cell.fill.fore_color.rgb = TEAL if row_index == 0 else (CARD if row_index % 2 else CARD_ALT)
    no_shadow(shape)

    textbox(
        slide,
        0.78,
        5.45,
        11.7,
        0.9,
        "F1: exact / relaxed / content relaxed. Prompt v1: 0.349 / 0.501 / 0.549.\n"
        "SOTA — entity / relation / strict relation F1, проценты. С SOTA напрямую не сравниваем:\n"
        "там другая постановка — span-level NER/RE, а не канонические концепты.",
        14,
        SOFT,
        line_spacing=1.1,
    )
    footer(slide, 7)
    notes(slide, "Опорные точки: пустое предсказание, 3B-baseline, текущая 4B-модель, oracle и внешний SciERC SOTA.")
    return slide


def slide_risks(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)
    section(slide, "Честно о рисках", AMBER)
    heading(slide, "Что может пойти не так", 36, w=7.4)

    shadow_card(slide, 0.75, 1.95, 3.65, 2.75, fill=CARD, line=BORDER, radius=0.10)
    textbox(slide, 1.0, 2.12, 3.1, 0.3, "Ограничения сейчас", 12.5, AMBER, True)
    bullet_list(
        slide,
        1.0,
        2.55,
        3.15,
        2.0,
        [
            "20 абстрактов на модель, один seed",
            "Оценены только концепты",
            "Нет end-to-end метрики поиска",
            "Одна локальная модель за раз",
        ],
        size=10.5,
        marker_color=AMBER,
    )

    shadow_card(slide, 4.55, 1.95, 3.65, 2.75, fill=CARD, line=BORDER, radius=0.10)
    textbox(slide, 4.80, 2.12, 3.1, 0.3, "План до 15 декабря", 12.5, TEAL, True)
    bullet_list(
        slide,
        4.80,
        2.55,
        3.15,
        2.0,
        [
            "100 абстрактов, 3 seed",
            "precision@k и nDCG для поиска",
            "pytest --cov и порог покрытия",
            "E2E smoke-тест, демо и скриншоты",
            "По коммиту в код от каждого",
        ],
        size=10.5,
    )

    meme(
        slide,
        image_asset("tony_confident"),
        8.35,
        1.95,
        4.40,
        3.26,
    )

    textbox(slide, 0.78, 5.05, 7.5, 0.5, "Изменения: LangGraph, LLM-выбор движков, честный бенчмарк.", 14, SOFT)
    footer(slide, 8)
    notes(slide, "1:40–1:55. Главный риск — узкая оценка, а не архитектура. До финала расширяем выборку и добавляем E2E-метрики.")
    return slide


def slide_team(prs, blank):
    slide = prs.slides.add_slide(blank)
    add_background(slide)
    section(slide, "Команда")
    heading(slide, "Кто за что отвечает", 36, w=8.0)

    team = [
        ("Иван Холодило", "@Icold21", "Lead AI Engineer", "архитектура, LangGraph, CLI, состояние", TEAL),
        ("Вадим Лялькин", "@Geniy_molodec", "Graph & Knowledge", "онтология графа, wikilinks, Obsidian", GREEN),
        ("Нодар Чигладзе", "@NodarNeo", "Data / IR Engineer", "arXiv / S2 / web, ранжирование, PDF", BLUE),
        ("Давид Чигладзе", "@David52228", "QA / Evaluation", "QA, тесты, CI, бенчмарк", AMBER),
        ("Илья Синко", "@mang1ch5", "LLM Engineer", "промпты, валидация, синтез", PURPLE),
    ]
    for index, (name, handle, role, zone, accent) in enumerate(team):
        y = 1.62 + index * 0.88
        shadow_card(slide, 0.75, y, 8.45, 0.74, fill=CARD, line=BORDER, radius=0.10)
        accent_strip(slide, 0.80, y + 0.12, 0.08, 0.50, accent)
        textbox(slide, 1.02, y + 0.10, 2.0, 0.26, name, 11.5, INK, True)
        textbox(slide, 1.02, y + 0.38, 2.0, 0.22, handle, 8.5, SOFT)
        textbox(slide, 3.05, y + 0.10, 1.8, 0.5, role, 9.5, INK, True)
        textbox(slide, 4.95, y + 0.10, 4.0, 0.5, zone, 9.2, MUTED)

    shadow_card(slide, 9.55, 1.62, 3.05, 3.95, fill=PALE_TEAL, line=TEAL, radius=0.10)
    textbox(slide, 9.80, 1.80, 2.55, 0.3, "Готовность к КП2", 11.5, TEAL, True)
    textbox(slide, 9.80, 2.18, 2.55, 0.8, "8 / 10", 36, INK, True, font=FONT_BOLD)
    textbox(
        slide,
        9.80,
        3.05,
        2.55,
        2.2,
        "Ядро и инфраструктура качества готовы.\n\n"
        "До КП3: глубина оценки, E2E-метрики и коммиты каждого участника.",
        10,
        MUTED,
        line_spacing=1.1,
    )

    shadow_card(slide, 0.75, 6.05, 11.85, 0.55, fill=CARD, line=BORDER, radius=0.14)
    textbox(slide, 1.0, 6.16, 11.3, 0.3, "github.com/Icold21/lit-graph-agent · MIT License · команда AI-RIldium", 10.5, INK, True, align=PP_ALIGN.CENTER)
    footer(slide, 9)
    notes(slide, "1:55–2:00. Готовность к КП2 — 8 из 10. До декабря — глубина оценки и коммиты каждого участника.")
    return slide


def build() -> Path:
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    slide_title(prs, blank)
    slide_context(prs, blank)
    slide_roadmap(prs, blank)
    slide_architecture(prs, blank)
    slide_works(prs, blank)
    slide_metrics(prs, blank)
    slide_reference(prs, blank)
    slide_risks(prs, blank)
    slide_team(prs, blank)

    prs.save(OUTPUT)
    return OUTPUT


if __name__ == "__main__":
    print(f"Wrote {build()}")
