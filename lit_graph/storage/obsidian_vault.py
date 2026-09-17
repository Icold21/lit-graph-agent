import re
import shutil
from pathlib import Path
from ..models import Paper, LiteratureBaseState, ConceptHub

GRAPH_PRESET_JSON_PATH = Path(__file__).parent / "graph_preset.json"


class ObsidianVaultManager:
    """Manages Obsidian Vault notes with continuous graph weights, concept hubs, and grounded citations."""

    def __init__(self, vault_path: str | Path):
        self.vault_path = Path(vault_path)
        self.sources_dir = self.vault_path / "Sources"
        self.concepts_dir = self.vault_path / "Concepts"
        self.obsidian_config_dir = self.vault_path / ".obsidian"
        self._init_dirs()
        self._init_obsidian_graph_config()

    def _init_dirs(self):
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.concepts_dir.mkdir(parents=True, exist_ok=True)
        self.obsidian_config_dir.mkdir(parents=True, exist_ok=True)

    def _init_obsidian_graph_config(self):
        target_graph_file = self.obsidian_config_dir / "graph.json"
        if GRAPH_PRESET_JSON_PATH.exists():
            try:
                shutil.copyfile(GRAPH_PRESET_JSON_PATH, target_graph_file)
            except Exception:
                pass

    def clean_name(self, text: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", text).strip()[:80]

    def write_paper_note(self, paper: Paper):
        filename = f"{self.clean_name(paper.title)}.md"
        filepath = self.sources_dir / filename

        # Guaranteed exact wikilinks matching concept files
        concepts = [f"[[Concepts/{self.clean_name(c)}|{c}]]" for c in paper.extracted_concepts]
        related = [f"[[Sources/{self.clean_name(r)}|{r}]]" for r in paper.related_paper_titles]
        citations = [f"[[Sources/{self.clean_name(cit)}|{cit}]]" for cit in paper.citing_paper_titles]
        references = [f"[[Sources/{self.clean_name(ref)}|{ref}]]" for ref in paper.referenced_paper_titles]

        safe_title = paper.title.replace('"', "'")
        safe_venue = (paper.venue or "N/A").replace('"', "'")

        lines = [
            "---",
            f'id: "{paper.id}"',
            f'title: "{safe_title}"',
            f"authors: {paper.authors}",
            f"year: {paper.year or 'N/A'}",
            f'venue: "{safe_venue}"',
            f'url: "{paper.doi_or_url or ""}"',
            f"citation_count: {paper.citation_count}",
            f"citation_velocity: {paper.citation_velocity}",
            f"objective_score: {paper.objective_scientific_score}",
            f"node_weight: {paper.normalized_weight}",
            "type: literature_note",
            "---",
            "",
            f"# {paper.title}",
            "",
            f"> 📊 **Scientometric Score:** `{paper.objective_scientific_score}` | **Continuous Weight:** `{paper.normalized_weight}`",
            "",
            "## 📌 Formatted Citation",
            f"> {paper.formatted_citation}",
            "",
            "## 🧠 Executive Summary (English)",
            paper.summary_en or "N/A",
            "",
            "## 🔍 Key Findings & Contributions",
        ]
        for kf in paper.key_findings_en:
            lines.append(f"- {kf}")

        lines.extend([
            "",
            "## ⚙️ Methodology & Limitations",
            f"**Methodology:** {paper.methodology_en or 'N/A'}",
            "",
            f"**Limitations:** {paper.limitations_en or 'N/A'}",
            "",
            "## 🌐 Knowledge Graph Connections",
            f"**Concepts:** {', '.join(concepts) if concepts else 'None'}",
            "",
            f"**Related Literature:** {', '.join(related) if related else 'None'}",
            "",
            f"**References (Outward):** {', '.join(references) if references else 'None'}",
            "",
            f"**Citations (Inward):** {', '.join(citations) if citations else 'None'}",
            "",
            "## 📄 Abstract",
            f"> {paper.abstract}",
            ""
        ])

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def write_concept_note(self, hub: ConceptHub, state: LiteratureBaseState):
        filename = f"{self.clean_name(hub.name)}.md"
        filepath = self.concepts_dir / filename
        safe_name = hub.name.replace('"', "'")

        mention_lines = []
        for p in state.papers.values():
            if any(c.lower() == hub.name.lower() for c in p.extracted_concepts):
                mentions = [m for m in p.concept_mentions if m.concept_name.lower() == hub.name.lower()]
                if mentions:
                    for m in mentions:
                        page_str = f"p. {m.page_number}" if m.page_number else "full text"
                        quote_str = f' — *"{m.context_snippet}"*' if m.context_snippet else ""
                        mention_lines.append(f"- [[Sources/{self.clean_name(p.title)}|{p.title}]] (**{page_str}**){quote_str}")
                else:
                    mention_lines.append(f"- [[Sources/{self.clean_name(p.title)}|{p.title}]] ({p.year or 'N/A'})")

        lines = [
            "---",
            f'concept: "{safe_name}"',
            f"aggregated_score: {hub.aggregated_score}",
            f"node_weight: {hub.normalized_weight}",
            "type: concept_hub",
            "---",
            f"# Concept: {hub.name}",
            "",
            f"> 🌐 **Aggregated Score:** `{hub.aggregated_score}` | **Continuous Weight:** `{hub.normalized_weight}`",
            "",
            "## 📖 Concept Definition & Consensus",
            hub.summary_en or "Synthesized concept hub across literature sources.",
            "",
            "## 📍 Grounded Citations & Page References:",
            "\n".join(mention_lines) if mention_lines else "- No direct source mentions recorded."
        ]

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def write_hub_files(self, state: LiteratureBaseState):
        safe_topic = state.topic.replace('"', "'")
        safe_format = state.citation_format.replace('"', "'")

        # 1. Overview Synthesis
        overview_path = self.vault_path / "_Overview_Synthesis.md"
        overview_lines = [
            "---",
            f'topic: "{safe_topic}"',
            f"total_sources: {len(state.papers)}",
            f"total_concepts: {len(state.concepts)}",
            f'last_updated: "{state.updated_at}"',
            "type: synthesis_hub",
            "---",
            f"# Master Synthesis: {state.topic}",
            "",
            "## 🎯 Research Requirements",
            f"> {state.requirements}",
            "",
            "## 📑 Executive Literature Review",
            state.overall_summary_en,
            "",
            "## 🗺️ Knowledge Base Index",
        ]
        for p in sorted(state.papers.values(), key=lambda x: x.objective_scientific_score, reverse=True):
            overview_lines.append(
                f"- [[Sources/{self.clean_name(p.title)}|{p.title}]] ({p.year or 'N/A'}) — "
                f"*Weight: {p.normalized_weight}* | *Score: {p.objective_scientific_score}*"
            )

        with open(overview_path, "w", encoding="utf-8") as f:
            f.write("\n".join(overview_lines))

        # 2. Interactive Obsidian Bibliography
        interactive_bib_path = self.vault_path / "_Bibliography.md"
        bib_lines = [
            "---",
            f'citation_format: "{safe_format}"',
            f"total_entries: {len(state.papers)}",
            "type: master_bibliography",
            "---",
            f"# Master Bibliography ({state.citation_format})",
            "",
            "> 💡 **Tip:** A pure copy-paste ready version without markdown is saved in `Formatted_Bibliography.md`.",
            "",
            "## 📚 References List",
            state.bibliography_en,
            "",
            "## 🔗 Vault Source Links",
        ]
        for p in state.papers.values():
            bib_lines.append(f"- [[Sources/{self.clean_name(p.title)}|{p.title}]]")

        with open(interactive_bib_path, "w", encoding="utf-8") as f:
            f.write("\n".join(bib_lines))

        # 3. Clean Standalone Export File
        export_bib_path = self.vault_path / "Formatted_Bibliography.md"
        clean_lines = [
            f"# References ({state.citation_format})",
            f"**Topic:** {state.topic}",
            f"**Total Sources:** {len(state.papers)}",
            "",
            "---",
            "",
            state.bibliography_en,
            ""
        ]
        with open(export_bib_path, "w", encoding="utf-8") as f:
            f.write("\n".join(clean_lines))

        if "bibtex" in state.citation_format.lower():
            bibtex_file = self.vault_path / "references.bib"
            with open(bibtex_file, "w", encoding="utf-8") as f:
                f.write(state.bibliography_en + "\n")