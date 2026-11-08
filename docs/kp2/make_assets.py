"""Generate the diagrams used in the KP2 report and slides.

Run from the repository root::

    python docs/kp2/make_assets.py

Outputs:
    docs/kp2/assets/architecture.png
    docs/kp2/assets/roadmap.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

ASSET_DIR = Path(__file__).resolve().parent / "assets"

INK = "#0f172a"
MUTED = "#475569"
BLUE = "#2563eb"
TEAL = "#0d9488"
AMBER = "#d97706"
VIOLET = "#7c3aed"
RED = "#dc2626"
LINE = "#94a3b8"
PANEL = "#f8fafc"
BORDER = "#cbd5e1"


def box(
    ax,
    x,
    y,
    w,
    h,
    title,
    lines,
    color,
    title_size=10.5,
    body_size=8.2,
    body_offset=0.088,
    line_spacing=0.036,
):
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.02",
        linewidth=1.2,
        edgecolor=color,
        facecolor="white",
        zorder=2,
    )
    ax.add_patch(patch)
    ax.add_patch(
        FancyBboxPatch(
            (x, y + h - 0.058),
            w,
            0.058,
            boxstyle="round,pad=0.012,rounding_size=0.02",
            linewidth=0,
            facecolor=color,
            alpha=0.12,
            zorder=3,
        )
    )
    ax.text(x + 0.017, y + h - 0.029, title, fontsize=title_size, fontweight="bold", color=INK, va="center", zorder=4)
    for index, line in enumerate(lines):
        if not line:
            continue
        ax.text(
            x + 0.017,
            y + h - body_offset - index * line_spacing,
            line,
            fontsize=body_size,
            color=MUTED,
            va="top",
            zorder=4,
        )


def arrow(ax, start, end, color=LINE, style="-|>", width=1.4):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle=style,
            mutation_scale=12,
            linewidth=width,
            color=color,
            zorder=1,
        )
    )


def draw_architecture() -> Path:
    fig, ax = plt.subplots(figsize=(13.2, 7.4), dpi=200)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.02, 0.965, "LitGraphAgent — architecture", fontsize=18, fontweight="bold", color=INK)
    ax.text(
        0.02,
        0.925,
        "Five role agents run as nodes of a LangGraph StateGraph; business logic stays inside the agents.",
        fontsize=9.5,
        color=MUTED,
    )

    # Entry point
    box(
        ax,
        0.02,
        0.60,
        0.19,
        0.24,
        "CLI + LeadAIAgent",
        [
            "litgraph --id --topic",
            "--update / --check / --deep",
            "owns: config, lifecycle,",
            "LangGraph compilation",
        ],
        BLUE,
        body_size=7.9,
    )

    # Graph container
    ax.add_patch(
        FancyBboxPatch(
            (0.245, 0.12),
            0.50,
            0.72,
            boxstyle="round,pad=0.012,rounding_size=0.03",
            linewidth=1.4,
            edgecolor=BORDER,
            facecolor=PANEL,
            zorder=0,
        )
    )
    ax.text(
        0.265,
        0.805,
        "LangGraph StateGraph  ·  ResearchState + activity reducer",
        fontsize=10.5,
        fontweight="bold",
        color=INK,
    )
    ax.text(0.265, 0.778, "create / update graphs · conditional edges · MemorySaver per run", fontsize=8, color=MUTED)

    box(
        ax,
        0.265,
        0.52,
        0.215,
        0.22,
        "RetrievalAgent",
        ["plan_request", "choose_engines (LLM)", "finalize_plan", "search · citations · PDF"],
        TEAL,
        title_size=9.5,
        body_size=7.7,
        line_spacing=0.033,
    )
    box(
        ax,
        0.505,
        0.52,
        0.215,
        0.22,
        "PromptAgent",
        ["validate · synthesize", "ground_concepts", "define_concepts", "bibliography · overview"],
        VIOLET,
        title_size=9.5,
        body_size=7.7,
        line_spacing=0.033,
    )
    box(
        ax,
        0.265,
        0.25,
        0.215,
        0.22,
        "GraphAgent",
        ["rebuild_graph", "flush vault", "save _state.json", "concept canonicalization"],
        AMBER,
        title_size=9.5,
        body_size=7.7,
        line_spacing=0.033,
    )
    box(
        ax,
        0.505,
        0.25,
        0.215,
        0.22,
        "EvaluationAgent",
        ["audit vault", "check_state", "links · frontmatter", "duplicates · coverage"],
        RED,
        title_size=9.5,
        body_size=7.7,
        line_spacing=0.033,
    )
    box(
        ax,
        0.265,
        0.135,
        0.455,
        0.09,
        "Hand-off log",
        ["every node appends one event to activity  →  _Agent_Activity.md"],
        BLUE,
        title_size=8.4,
        body_size=7.4,
        body_offset=0.072,
        line_spacing=0.03,
    )

    # Outputs
    box(
        ax,
        0.78,
        0.62,
        0.20,
        0.24,
        "Obsidian vault",
        ["Sources/ + Concepts/", "_Overview_Synthesis.md", "_Bibliography.md", "references.bib"],
        TEAL,
        body_size=7.9,
    )
    box(
        ax,
        0.78,
        0.38,
        0.20,
        0.19,
        "Durable state",
        ["_state.json", "incremental --update", "search_plan provenance"],
        AMBER,
        body_size=7.9,
    )
    box(
        ax,
        0.78,
        0.14,
        0.20,
        0.19,
        "Quality signal",
        ["QA report", "55 tests · CI 3.10–3.13", "SciERC benchmark"],
        RED,
        body_size=7.9,
    )

    # External services
    ax.text(0.02, 0.545, "External APIs", fontsize=9, fontweight="bold", color=INK)
    for index, label in enumerate(["Semantic Scholar", "arXiv", "Open web", "PDF / DOI"]):
        y = 0.46 - index * 0.075
        ax.add_patch(
            FancyBboxPatch(
                (0.02, y),
                0.19,
                0.052,
                boxstyle="round,pad=0.01,rounding_size=0.015",
                linewidth=1,
                edgecolor=BORDER,
                facecolor="white",
            )
        )
        ax.text(0.115, y + 0.026, label, ha="center", va="center", fontsize=8, color=MUTED)

    arrow(ax, (0.21, 0.64), (0.245, 0.64), color=BLUE, width=2)
    arrow(ax, (0.21, 0.48), (0.245, 0.57), color=TEAL, width=1.2, style="<|-|>")
    arrow(ax, (0.745, 0.74), (0.78, 0.74), color=TEAL, width=2)
    arrow(ax, (0.745, 0.475), (0.78, 0.475), color=AMBER, width=2)
    arrow(ax, (0.745, 0.235), (0.78, 0.235), color=RED, width=2)

    output = ASSET_DIR / "architecture.png"
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


def draw_roadmap() -> Path:
    fig, ax = plt.subplots(figsize=(12.4, 3.9), dpi=200)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    milestones = [
        ("6 Oct", "MVP", ["search + filter", "Obsidian notes"], "done"),
        ("5 Nov", "Modular search", ["engine catalog + LLM routing", "first SciERC metrics"], "done"),
        ("25 Nov", "Test & stabilize", ["ranking calibration", "incremental updates"], "partial"),
        ("15 Dec", "Final release", ["final metrics + demo", "docs + report"], "planned"),
    ]
    xs = [0.10, 0.38, 0.66, 0.94]
    ax.plot([0.03, 0.97], [0.52, 0.52], color=BORDER, linewidth=3, zorder=1, solid_capstyle="round")

    colors = {"done": TEAL, "partial": AMBER, "planned": BLUE}
    labels = {"done": "DONE", "partial": "IN PROGRESS", "planned": "PLANNED"}
    for x, (date, title, items, status) in zip(xs, milestones):
        color = colors[status]
        ax.scatter([x], [0.52], s=180, color=color, zorder=3, edgecolor="white", linewidth=2)
        ax.text(x, 0.63, date, ha="center", fontsize=10, fontweight="bold", color=INK)
        ax.text(x, 0.74, title, ha="center", fontsize=11.5, fontweight="bold", color=color)
        ax.text(
            x,
            0.30,
            "\n".join(items),
            ha="center",
            va="top",
            fontsize=8.3,
            color=MUTED,
            linespacing=1.5,
        )
        ax.text(x, 0.09, labels[status], ha="center", fontsize=7.6, color=color, fontweight="bold")

    ax.text(0.02, 0.93, "KP1 roadmap — status on 8 Nov 2026", fontsize=14, fontweight="bold", color=INK)
    fig.tight_layout()
    output = ASSET_DIR / "roadmap.png"
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


def main() -> int:
    print(f"Wrote {draw_architecture()}")
    print(f"Wrote {draw_roadmap()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

