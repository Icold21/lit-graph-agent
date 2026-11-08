"""Render SciERC benchmark metrics from a result JSON file.

Usage::

    python benchmarks/plot_results.py benchmarks/results/scierc_qwen2.5-3b.json

The script is intentionally dependency-light (matplotlib only) and writes a PNG
next to the input file, so the chart in the report can always be regenerated
from the committed raw metrics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, Optional, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

METRICS = [
    ("concepts_all_exact", "Concepts\nexact"),
    ("concepts_all_relaxed", "Concepts\nrelaxed"),
    ("concepts_content_exact", "Content\nexact"),
    ("concepts_content_relaxed", "Content\nrelaxed"),
]
COLORS = {"precision": "#2563eb", "recall": "#14b8a6", "f1": "#f59e0b"}


def load_results(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render(results: Dict, output: Path) -> Path:
    labels = [label for key, label in METRICS if key in results]
    keys = [key for key, _ in METRICS if key in results]
    precision = [results[key]["precision"] for key in keys]
    recall = [results[key]["recall"] for key in keys]
    f1 = [results[key]["f1"] for key in keys]

    x = range(len(keys))
    width = 0.26
    fig, ax = plt.subplots(figsize=(9.2, 4.4), dpi=200)

    bars = [
        (precision, "Precision", COLORS["precision"], -width),
        (recall, "Recall", COLORS["recall"], 0.0),
        (f1, "F1", COLORS["f1"], width),
    ]
    for values, label, color, offset in bars:
        positions = [index + offset for index in x]
        containers = ax.bar(positions, values, width, label=label, color=color, zorder=3)
        for rect, value in zip(containers, values):
            ax.annotate(
                f"{value:.2f}",
                xy=(rect.get_x() + rect.get_width() / 2, value),
                xytext=(0, 3),
                textcoords="offset points",
                ha="center",
                va="bottom",
                fontsize=10,
                color="#0f172a",
            )

    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_ylabel("Score", fontsize=12)
    ax.set_title(
        f"SciERC concept extraction — {results.get('model', 'unknown model')}"
        f" ({results.get('papers', '?')} abstracts)",
        fontsize=15,
        fontweight="bold",
        color="#0f172a",
    )
    ax.grid(axis="y", color="#e2e8f0", linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    ax.legend(frameon=False, ncols=3, loc="upper right", fontsize=10.5)
    ax.text(
        0.99,
        -0.18,
        "Exact = normalised string equality; relaxed = token Jaccard >= 0.5. "
        "Typed relations are not scored.",
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=9,
        color="#475569",
    )
    fig.tight_layout()
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return output


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="Path to a SciERC result JSON")
    parser.add_argument("--output", type=Path, default=None, help="Output PNG path")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    results = load_results(args.results)
    output = args.output or args.results.with_suffix(".png")
    written = render(results, output)
    print(f"Wrote {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
