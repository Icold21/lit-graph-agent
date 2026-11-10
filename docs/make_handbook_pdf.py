"""Build the full LitGraphAgent handbook (DOCX + PDF) from Markdown sections."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
HANDBOOK = ROOT / "docs" / "handbook"
DOCX = ROOT / "docs" / "LitGraphAgent_Handbook.docx"
PDF = ROOT / "docs" / "LitGraphAgent_Handbook.pdf"

SECTIONS = [
    "01_intro.md",
    "02_basics.md",
    "03_architecture.md",
    "04_agents.md",
    "05_flows_data.md",
    "06_search_llm_graph.md",
    "07_qa_benchmark.md",
    "08_metrics.md",
    "09_run_code_team.md",
    "10_glossary_appendix.md",
]

INK = RGBColor(0x0B, 0x0F, 0x19)
MUTED = RGBColor(0x47, 0x55, 0x69)
TEAL = RGBColor(0x0D, 0x94, 0x88)
BLUE = RGBColor(0x25, 0x63, 0xEB)
PALE = "F3F7F6"
PALE_BLUE = "EEF4FF"
BORDER = "D7DEE8"
FONT = "Calibri"
HEAD_FONT = "Segoe UI"
MONO = "Consolas"


def shade(cell, color: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), color)
    tc_pr.append(shd)


def set_cell_margins(cell, top=60, bottom=60, left=100, right=100) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for tag, value in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        node = tc_mar.find(qn(f"w:{tag}"))
        if node is None:
            node = OxmlElement(f"w:{tag}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def add_page_number(paragraph) -> None:
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run()
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = "PAGE"
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    text = OxmlElement("w:t")
    text.text = "1"
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(text)
    run._r.append(fld_end)
    run.font.name = FONT
    run.font.size = Pt(8.5)
    run.font.color.rgb = MUTED


def add_hyperlink(paragraph, text: str, url: str) -> None:
    part = paragraph.part
    r_id = part.relate_to(url, "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink", is_external=True)
    hyperlink = OxmlElement("w:hyperlink")
    hyperlink.set(qn("r:id"), r_id)
    new_run = OxmlElement("w:r")
    r_pr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "2563EB")
    r_pr.append(color)
    underline = OxmlElement("w:u")
    underline.set(qn("w:val"), "single")
    r_pr.append(underline)
    new_run.append(r_pr)
    t = OxmlElement("w:t")
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)


def add_inline(paragraph, text: str) -> None:
    pattern = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+?`|\[[^\]]+\]\([^)]+\))")
    pos = 0
    for match in pattern.finditer(text):
        if match.start() > pos:
            paragraph.add_run(text[pos : match.start()])
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2].replace("`", ""))
            run.bold = True
        elif token.startswith("`") and token.endswith("`"):
            run = paragraph.add_run(token[1:-1])
            run.font.name = MONO
            run.font.size = Pt(9)
        elif token.startswith("*") and token.endswith("*"):
            run = paragraph.add_run(token[1:-1].replace("`", ""))
            run.italic = True
        elif token.startswith("["):
            label, url = re.match(r"\[([^\]]+)\]\(([^)]+)\)", token).groups()
            add_hyperlink(paragraph, label, url)
        pos = match.end()
    if pos < len(text):
        paragraph.add_run(text[pos:])


def add_heading(doc: Document, text: str, level: int, page_break: bool = False) -> None:
    if page_break:
        doc.add_page_break()
    style = f"Heading {level}"
    paragraph = doc.add_paragraph(style=style)
    add_inline(paragraph, text)
    if level == 1:
        paragraph.paragraph_format.space_before = Pt(0)
        paragraph.paragraph_format.space_after = Pt(10)
    elif level == 2:
        paragraph.paragraph_format.space_before = Pt(14)
        paragraph.paragraph_format.space_after = Pt(6)
    else:
        paragraph.paragraph_format.space_before = Pt(10)
        paragraph.paragraph_format.space_after = Pt(4)
    paragraph.paragraph_format.keep_with_next = True


def add_body(doc: Document, text: str) -> None:
    paragraph = doc.add_paragraph(style="Normal")
    add_inline(paragraph, text)
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(6)
    paragraph.paragraph_format.line_spacing = 1.22


def add_bullets(doc: Document, items: list[str], numbered: bool = False) -> None:
    if numbered:
        for index, item in enumerate(items, 1):
            paragraph = doc.add_paragraph(style="Normal")
            paragraph.paragraph_format.left_indent = Cm(0.75)
            paragraph.paragraph_format.first_line_indent = Cm(-0.55)
            paragraph.paragraph_format.space_after = Pt(2)
            paragraph.paragraph_format.line_spacing = 1.15
            run = paragraph.add_run(f"{index}.  ")
            run.bold = True
            add_inline(paragraph, item)
        return
    for item in items:
        paragraph = doc.add_paragraph(style="Normal")
        paragraph.paragraph_format.left_indent = Cm(0.75)
        paragraph.paragraph_format.first_line_indent = Cm(-0.45)
        paragraph.paragraph_format.space_after = Pt(2)
        paragraph.paragraph_format.line_spacing = 1.15
        marker = paragraph.add_run("•  ")
        marker.bold = True
        marker.font.color.rgb = TEAL
        add_inline(paragraph, item)


def add_code(doc: Document, lines: list[str]) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    cell = table.cell(0, 0)
    shade(cell, "F5F7FA")
    set_cell_margins(cell, top=90, bottom=90, left=120, right=120)
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(0)
    paragraph.paragraph_format.line_spacing = 1.0
    for index, line in enumerate(lines):
        run = paragraph.add_run(line)
        run.font.name = MONO
        run.font.size = Pt(8.5)
        if index < len(lines) - 1:
            run.add_break()
    if len(lines) <= 28:
        tr_pr = table.rows[0]._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_callout(doc: Document, text: str) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = table.cell(0, 0)
    shade(cell, PALE_BLUE)
    set_cell_margins(cell, top=90, bottom=90, left=140, right=140)
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    add_inline(paragraph, text)
    for run in paragraph.runs:
        run.italic = True
        run.font.color.rgb = RGBColor(0x1E, 0x3A, 0x5F)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_table(doc: Document, rows: list[list[str]]) -> None:
    if not rows:
        return
    cols = max(len(row) for row in rows)
    table = doc.add_table(rows=len(rows), cols=cols)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = True
    for row_index, row in enumerate(rows):
        tr_pr = table.rows[row_index]._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)
        if row_index == 0:
            header = OxmlElement("w:tblHeader")
            tr_pr.append(header)
        for col_index in range(cols):
            cell = table.cell(row_index, col_index)
            set_cell_margins(cell)
            value = row[col_index] if col_index < len(row) else ""
            paragraph = cell.paragraphs[0]
            paragraph.paragraph_format.space_after = Pt(0)
            paragraph.paragraph_format.line_spacing = 1.0
            add_inline(paragraph, value)
            for run in paragraph.runs:
                run.font.size = Pt(8.5 if row_index else 9)
                if row_index == 0:
                    run.bold = True
                    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            if row_index == 0:
                shade(cell, "0D9488")
            elif row_index % 2 == 0:
                shade(cell, "F8FAFC")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_image(doc: Document, source: Path, alt: str, base_dir: Path) -> None:
    resolved = (base_dir / source).resolve()
    if not resolved.exists():
        add_body(doc, f"[Изображение не найдено: {source}]")
        return
    from PIL import Image

    with Image.open(resolved) as image:
        width_px, height_px = image.size
    max_width_cm = 15.2
    width_cm = max_width_cm
    if width_px / height_px < 1.2:
        width_cm = min(max_width_cm, 12.5)
    doc.add_picture(str(resolved), width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    if alt:
        caption = doc.add_paragraph()
        caption.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = caption.add_run(alt)
        run.italic = True
        run.font.size = Pt(9)
        run.font.color.rgb = MUTED


def parse_markdown(doc: Document, path: Path, first_h1: bool) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    index = 0
    bullets: list[str] = []
    numbered: list[str] = []
    table_rows: list[list[str]] = []
    code_lines: list[str] = []
    paragraph_lines: list[str] = []
    in_code = False
    seen_h1 = False

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            add_body(doc, " ".join(paragraph_lines))
            paragraph_lines = []

    def flush_bullets() -> None:
        nonlocal bullets, numbered
        flush_paragraph()
        if bullets:
            add_bullets(doc, bullets)
            bullets = []
        if numbered:
            add_bullets(doc, numbered, numbered=True)
            numbered = []

    def flush_table() -> None:
        nonlocal table_rows
        flush_paragraph()
        if table_rows:
            add_table(doc, table_rows)
            table_rows = []

    while index < len(lines):
        raw = lines[index]
        line = raw.rstrip()

        if line.startswith("```"):
            flush_bullets()
            flush_table()
            if in_code:
                add_code(doc, code_lines)
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue

        if in_code:
            code_lines.append(raw)
            index += 1
            continue

        if not line.strip():
            flush_bullets()
            flush_table()
            index += 1
            continue

        if line.startswith("#"):
            flush_bullets()
            flush_table()
            match = re.match(r"^(#{1,4})\s+(.*)$", line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                if level == 1:
                    if seen_h1:
                        page_break = True
                    else:
                        page_break = not first_h1
                    add_heading(doc, text, 1, page_break=page_break)
                    seen_h1 = True
                else:
                    add_heading(doc, text, level)
            index += 1
            continue

        if line.startswith("|"):
            flush_bullets()
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                index += 1
                continue
            table_rows.append(cells)
            index += 1
            continue

        if line.startswith("> "):
            flush_bullets()
            flush_table()
            quote_lines = []
            while index < len(lines) and lines[index].startswith("> "):
                quote_lines.append(lines[index][2:].strip())
                index += 1
            add_callout(doc, " ".join(quote_lines))
            continue

        image_match = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
        if image_match:
            flush_bullets()
            flush_table()
            alt, source = image_match.groups()
            add_image(doc, Path(source), alt, path.parent)
            index += 1
            continue

        if line.startswith("- "):
            flush_table()
            bullets.append(line[2:].strip())
            index += 1
            continue

        if re.match(r"^\d+\.\s+", line):
            flush_table()
            numbered.append(re.sub(r"^\d+\.\s+", "", line).strip())
            index += 1
            continue

        if (bullets or numbered) and raw[:1].isspace() and line.strip():
            if numbered:
                numbered[-1] = f"{numbered[-1]} {line.strip()}"
            else:
                bullets[-1] = f"{bullets[-1]} {line.strip()}"
            index += 1
            continue

        paragraph_lines.append(line.strip())
        index += 1

    flush_bullets()
    flush_table()
    flush_paragraph()
    if in_code:
        add_code(doc, code_lines)


def configure_styles(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = FONT
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = INK
    normal.paragraph_format.line_spacing = 1.22
    normal.paragraph_format.space_after = Pt(6)
    normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)

    for level, size, color, before, after in (
        (1, 21, INK, 0, 10),
        (2, 15.5, TEAL, 14, 6),
        (3, 12.5, RGBColor(0x1F, 0x29, 0x37), 10, 4),
        (4, 11, RGBColor(0x33, 0x41, 0x55), 8, 3),
    ):
        style = doc.styles[f"Heading {level}"]
        style.font.name = HEAD_FONT
        style.font.size = Pt(size)
        style.font.bold = True
        style.font.color.rgb = color
        style.paragraph_format.space_before = Pt(before)
        style.paragraph_format.space_after = Pt(after)
        style.paragraph_format.keep_with_next = True


def add_cover(doc: Document) -> None:
    section = doc.sections[0]
    section.page_width = Cm(21)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.2)
    section.right_margin = Cm(2.2)
    section.different_first_page_header_footer = True

    for _ in range(3):
        doc.add_paragraph()
    label = doc.add_paragraph()
    run = label.add_run("ТЕХНИЧЕСКИЙ ГАЙД")
    run.font.name = HEAD_FONT
    run.font.size = Pt(10)
    run.font.bold = True
    run.font.color.rgb = TEAL

    title = doc.add_paragraph()
    run = title.add_run("LitGraphAgent")
    run.font.name = HEAD_FONT
    run.font.size = Pt(40)
    run.font.bold = True
    run.font.color.rgb = INK

    subtitle = doc.add_paragraph()
    run = subtitle.add_run(
        "Автономный агент для сбора, фильтрации и построения\n"
        "графов литературы в Obsidian"
    )
    run.font.name = HEAD_FONT
    run.font.size = Pt(17)
    run.font.color.rgb = RGBColor(0x33, 0x41, 0x55)

    line = doc.add_paragraph()
    run = line.add_run("─" * 56)
    run.font.color.rgb = TEAL
    run.font.size = Pt(10)

    intro = doc.add_paragraph()
    run = intro.add_run(
        "Полное введение в проект для новых участников, преподавателей и инженеров.\n"
        "Архитектура, пять агентов, логика пайплайна, метрики, запуск и глоссарий."
    )
    run.font.size = Pt(11)
    run.font.color.rgb = MUTED
    intro.paragraph_format.space_after = Pt(24)

    box = doc.add_table(rows=1, cols=1)
    cell = box.cell(0, 0)
    shade(cell, PALE)
    set_cell_margins(cell, top=160, bottom=160, left=200, right=200)
    paragraph = cell.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
    paragraph.paragraph_format.space_after = Pt(0)
    run = paragraph.add_run(
        "Команда AI-RIldium  |  ноябрь 2026\n"
        "github.com/Icold21/LitGraphAgent  |  MIT License"
    )
    run.font.size = Pt(10)
    run.font.color.rgb = INK

    for _ in range(6):
        doc.add_paragraph()
    note = doc.add_paragraph()
    note.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = note.add_run(
        "Документ объясняет не только «что сделано», но и «почему это работает»:\n"
        "от precision и recall до того, как LLM выбирает поисковый движок."
    )
    run.font.size = Pt(9.5)
    run.font.color.rgb = MUTED
    run.italic = True
    doc.add_page_break()


def add_toc(doc: Document) -> None:
    title = doc.add_paragraph()
    run = title.add_run("Содержание")
    run.font.name = HEAD_FONT
    run.font.size = Pt(22)
    run.font.bold = True
    run.font.color.rgb = INK

    for name in SECTIONS:
        in_code = False
        for line in (HANDBOOK / name).read_text(encoding="utf-8").splitlines():
            if line.startswith("```"):
                in_code = not in_code
                continue
            if in_code:
                continue
            if line.startswith("# ") or line.startswith("## "):
                level = 1 if line.startswith("# ") else 2
                text = line.lstrip("#").strip().replace("`", "").replace("**", "")
                paragraph = doc.add_paragraph()
                paragraph.paragraph_format.space_after = Pt(0.5)
                if level == 1:
                    run = paragraph.add_run(text)
                    run.bold = True
                    run.font.size = Pt(10.2)
                    run.font.color.rgb = INK
                else:
                    paragraph.paragraph_format.left_indent = Cm(0.7)
                    run = paragraph.add_run(text)
                    run.font.size = Pt(8.2)
                    run.font.color.rgb = MUTED
    doc.add_page_break()


def add_header_footer(doc: Document) -> None:
    section = doc.sections[0]
    header = section.header
    paragraph = header.paragraphs[0]
    run = paragraph.add_run("LitGraphAgent · технический гайд · ноябрь 2026")
    run.font.name = FONT
    run.font.size = Pt(8)
    run.font.color.rgb = MUTED
    paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT

    footer = section.footer
    add_page_number(footer.paragraphs[0])


def build() -> tuple[Path, Path]:
    doc = Document()
    configure_styles(doc)
    add_cover(doc)
    add_toc(doc)
    add_header_footer(doc)

    first = True
    for name in SECTIONS:
        parse_markdown(doc, HANDBOOK / name, first_h1=first)
        first = False

    doc.core_properties.title = "LitGraphAgent — технический гайд"
    doc.core_properties.author = "AI-RIldium"
    doc.core_properties.subject = "Архитектура, агенты, метрики и запуск LitGraphAgent"
    doc.save(DOCX)

    soffice = Path(r"C:\Program Files\LibreOffice\program\soffice.exe")
    subprocess.run(
        [str(soffice), "--headless", "--convert-to", "pdf", "--outdir", str(ROOT / "docs"), str(DOCX)],
        check=True,
    )
    return DOCX, PDF


if __name__ == "__main__":
    docx_path, pdf_path = build()
    print(f"Wrote {docx_path}")
    print(f"Wrote {pdf_path}")
