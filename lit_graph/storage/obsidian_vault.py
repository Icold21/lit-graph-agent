import re
from pathlib import Path
from ..models import Paper, LiteratureBaseState


class ObsidianVaultManager:
    """Manages Obsidian Vault notes, graphs, and dedicated clean bibliography files."""

    def __init__(self, vault_path: str | Path):
        self.vault_path = Path(vault_path)
        self.sources_dir = self.vault_path / "Sources"
        self.concepts_dir = self.vault_path / "Concepts"
        self._init_dirs()

    def _init_dirs(self):
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.concepts_dir.mkdir(parents=True, exist_ok=True)

    def clean_name(self, text: str) -> str:
        return re.sub(r'[\\/*?:"<>|]', "", text).strip()[:80]

    def write_paper_note(self, paper: Paper):
        filename = f"{self.clean_name(paper.title)}.md"
        filepath = self.sources_dir / filename

        concepts = [f"[[Concepts/{self.clean_name(c)}|{c}]]" for c in paper.extracted_concepts]
        related = [f"[[Sources/{self.clean_name(r)}|{r}]]" for r in paper.related_paper_titles]
        citations = [f"[[Sources/{self.clean_name(cit)}|{cit}]]" for cit in paper.citing_paper_titles]
        references = [f"[[Sources/{self.clean_name(ref)}|{ref}]]" for ref in paper.referenced_paper_titles]

        lines = [
            "---",
            f"id: \"{paper.id}\"",
            f"title: \"{paper.title.replace('\"', "'")}\"",
            f"authors: {paper.authors}",
            f"year: {paper.year or 'N/A'}",
            f"venue: \"{paper.venue or 'N/A'}\"",
            f"url: \"{paper.doi_or_url or ''}\"",
            f"citation_count: {paper.citation_count}",
            f"citation_velocity: {paper.citation_velocity}",
            f"influential_ratio: {paper.influential_ratio}",
            f"objective_score: {paper.objective_scientific_score}",
            "type: literature_note",
            "---",
            "",
            f"# {paper.title}",
            "",
            "## 📌 Citation",
            f"> {paper.formatted_citation}",
            "",
            "## 📊 Scientometric Profile",
            f"- **Total Citations:** {paper.citation_count}",
            f"- **Citation Velocity:** {paper.citation_velocity} citations/year",
            f"- **Influential Ratio:** {paper.influential_ratio * 100:.1f}%",
            f"- **Composite Scientific Score:** `{paper.objective_scientific_score}`",
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
            f"**Cross-Links:** {', '.join(related) if related else 'None'}",
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

    def write_concept_note(self, concept: str, linked_titles: list[str]):
        filepath = self.concepts_dir / f"{self.clean_name(concept)}.md"
        lines = [
            "---",
            f"concept: \"{concept}\"",
            "type: concept_hub",
            "---",
            f"# Concept: {concept}",
            "",
            "## Linked Sources:",
        ]
        for t in linked_titles:
            lines.append(f"- [[Sources/{self.clean_name(t)}|{t}]]")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    def write_hub_files(self, state: LiteratureBaseState):
        """Generates overview hub, interactive bibliography, and pure formatted export file."""
        
        # 1. Overview Synthesis Note
        overview_path = self.vault_path / "_Overview_Synthesis.md"
        overview_lines = [
            "---",
            f"topic: \"{state.topic}\"",
            f"total_sources: {len(state.papers)}",
            f"last_updated: \"{state.updated_at}\"",
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
                f"*Impact Score: {p.objective_scientific_score}* | *Velocity: {p.citation_velocity}/yr*"
            )

        with open(overview_path, "w", encoding="utf-8") as f:
            f.write("\n".join(overview_lines))

        # 2. Interactive Obsidian Bibliography Note
        interactive_bib_path = self.vault_path / "_Bibliography.md"
        bib_lines = [
            "---",
            f"citation_format: \"{state.citation_format}\"",
            f"total_entries: {len(state.papers)}",
            "type: master_bibliography",
            "---",
            f"# Master Bibliography ({state.citation_format})",
            "",
            "> 💡 **Tip:** A pure, copy-paste ready version without markdown links is saved in `Formatted_Bibliography.md`.",
            "",
            "## 📚 References List",
            state.bibliography_en,
            "",
            "## 🔗 Vault Note Links",
        ]
        for p in state.papers.values():
            bib_lines.append(f"- [[Sources/{self.clean_name(p.title)}|{p.title}]]")

        with open(interactive_bib_path, "w", encoding="utf-8") as f:
            f.write("\n".join(bib_lines))

        # 3. Clean Standalone Export File (No frontmatter, ready to copy into Word/Docs/Thesis)
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

        # 4. Optional BibTeX export file if BibTeX format is chosen
        if "bibtex" in state.citation_format.lower():
            bibtex_file = self.vault_path / "references.bib"
            with open(bibtex_file, "w", encoding="utf-8") as f:
                f.write(state.bibliography_en + "\n")