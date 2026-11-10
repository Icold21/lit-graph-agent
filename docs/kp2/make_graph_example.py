"""Largest connected component of the real vault, Kamada-Kawai layout."""

from __future__ import annotations

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import networkx as nx

ROOT = Path(r"D:\PersonalProjects\lit_graph_agent")
VAULT = ROOT / "vaults" / "transformer_circuits"
OUT = ROOT / "docs" / "kp2" / "assets" / "obsidian_graph_example.png"
LINK = re.compile(r"\[\[([^\]\|#]+)")


def meta(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    label = ""
    kind = "source" if path.parent.name == "Sources" else "concept"
    for line in text.splitlines():
        if line.startswith("concept:"):
            label = line.split(":", 1)[1].strip().strip('"')
        elif line.startswith("title:") and not label:
            label = line.split(":", 1)[1].strip().strip('"')
    return label or path.stem, kind


def main() -> None:
    nodes: dict[str, tuple[str, str]] = {}
    for folder in ("Sources", "Concepts"):
        for path in (VAULT / folder).glob("*.md"):
            nodes[path.stem.lower()] = meta(path)
    graph = nx.Graph()
    for folder in ("Sources", "Concepts"):
        for path in (VAULT / folder).glob("*.md"):
            source = path.stem.lower()
            for target in LINK.findall(path.read_text(encoding="utf-8")):
                key = target.strip().replace("\\", "/").split("/")[-1].lower()
                if key in nodes and key != source:
                    graph.add_edge(source, key)
    graph.remove_nodes_from([n for n in graph.nodes if graph.degree(n) == 0])
    component = max(nx.connected_components(graph), key=len)
    graph = graph.subgraph(component).copy()

    pos = nx.kamada_kawai_layout(graph, scale=2.0)
    concepts = [n for n in graph.nodes if nodes[n][1] == "concept"]
    sources = [n for n in graph.nodes if nodes[n][1] == "source"]
    degrees = dict(graph.degree())
    top_concepts = sorted(concepts, key=lambda n: (-degrees[n], nodes[n][0]))[:12]
    top_sources = sorted(sources, key=lambda n: (-degrees[n], nodes[n][0]))[:8]

    fig, ax = plt.subplots(figsize=(15.5, 8.6), dpi=180)
    fig.patch.set_facecolor("#080D18")
    ax.set_facecolor("#080D18")
    nx.draw_networkx_edges(graph, pos, ax=ax, edge_color="#334155", width=0.8, alpha=0.5)
    nx.draw_networkx_nodes(
        graph,
        pos,
        nodelist=concepts,
        ax=ax,
        node_color="#2DD4BF",
        node_size=[120 + 90 * degrees[n] for n in concepts],
        linewidths=0.8,
        edgecolors="#0F172A",
    )
    nx.draw_networkx_nodes(
        graph,
        pos,
        nodelist=sources,
        ax=ax,
        node_color="#60A5FA",
        node_size=[160 + 55 * degrees[n] for n in sources],
        linewidths=0.8,
        edgecolors="#0F172A",
        alpha=0.92,
    )

    for node in top_concepts:
        label = nodes[node][0]
        if len(label) > 30:
            label = label[:28] + "…"
        ax.text(
            pos[node][0],
            pos[node][1] - 0.055,
            label,
            color="#E2E8F0",
            fontsize=8.5,
            ha="center",
            va="top",
            path_effects=[pe.withStroke(linewidth=3, foreground="#080D18")],
        )
    for node in top_sources:
        label = nodes[node][0]
        if len(label) > 24:
            label = label[:22] + "…"
        ax.text(
            pos[node][0],
            pos[node][1] - 0.045,
            label,
            color="#94A3B8",
            fontsize=6.8,
            ha="center",
            va="top",
            path_effects=[pe.withStroke(linewidth=2.5, foreground="#080D18")],
        )

    ax.set_title(
        "vaults/transformer_circuits · graph view · крупнейшая компонента",
        color="#E2E8F0",
        fontsize=14,
        loc="left",
        pad=16,
    )
    ax.text(
        0.99,
        0.01,
        f"● concepts ({len(concepts)})    ● sources ({len(sources)})    узлы: {len(graph)} · связи: {graph.number_of_edges()}",
        transform=ax.transAxes,
        color="#94A3B8",
        fontsize=8.5,
        ha="right",
        va="bottom",
    )
    ax.axis("off")
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)
    print(f"Wrote {OUT} ({len(graph)} nodes, {graph.number_of_edges()} edges)")


if __name__ == "__main__":
    main()
