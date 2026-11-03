import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from ..models import ConceptHub, LiteratureBaseState, Paper
from ..utils.logging_setup import get_logger

logger = get_logger(__name__)

GRAPH_PRESET_JSON_PATH = Path(__file__).parent / "graph_preset.json"
STATE_FILENAME = "_state.json"
MAX_STEM_LENGTH = 80


def _yaml(value: object) -> str:
    """Return a JSON string, which is also a valid YAML scalar."""
    return json.dumps(str(value), ensure_ascii=False)


class ObsidianVaultManager:
    """Manages Obsidian Vault notes with continuous graph weights, concept hubs, and grounded citations."""

    def __init__(self, vault_path: str | Path):
        self.vault_path = Path(vault_path)
        self.sources_dir = self.vault_path / "Sources"
        self.concepts_dir = self.vault_path / "Concepts"
        self.obsidian_config_dir = self.vault_path / ".obsidian"
        self.state_path = self.vault_path / STATE_FILENAME
        self._paper_names: Dict[str, str] = {}
        self._concept_names: Dict[str, str] = {}
        self._used_paper_stems: Dict[str, str] = {}
        self._used_concept_stems: Dict[str, str] = {}
        self._init_dirs()
        self._init_obsidian_graph_config()

    # --------------------------------------------------------------- lifecycle
    def _init_dirs(self) -> None:
        self.sources_dir.mkdir(parents=True, exist_ok=True)
        self.concepts_dir.mkdir(parents=True, exist_ok=True)
        self.obsidian_config_dir.mkdir(parents=True, exist_ok=True)

    def _init_obsidian_graph_config(self) -> None:
        """Install the graph preset without destroying user graph tweaks."""
        target_graph_file = self.obsidian_config_dir / "graph.json"
        if not GRAPH_PRESET_JSON_PATH.exists():
            return

        try:
            preset = json.loads(GRAPH_PRESET_JSON_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Could not read graph preset: %s", exc)
            return

        if not target_graph_file.exists():
            try:
                shutil.copyfile(GRAPH_PRESET_JSON_PATH, target_graph_file)
            except OSError as exc:
                logger.warning("Could not install graph preset: %s", exc)
            return

        try:
            existing = json.loads(target_graph_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            logger.warning("Existing .obsidian/graph.json is invalid; leaving it untouched")
            return

        if not isinstance(existing, dict):
            return

        changed = False
        for key, value in preset.items():
            if key not in existing:
                existing[key] = value
                changed = True

        groups = existing.get("colorGroups")
        if not isinstance(groups, list):
            groups = []
            existing["colorGroups"] = groups
            changed = True
        known_queries = {group.get("query") for group in groups if isinstance(group, dict)}
        for group in preset.get("colorGroups", []):
            if group.get("query") not in known_queries:
                groups.append(group)
                changed = True

        if changed:
            try:
                target_graph_file.write_text(
                    json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8"
                )
            except OSError as exc:
                logger.warning("Could not merge graph preset: %s", exc)

    # ------------------------------------------------------------------- names
    @staticmethod
    def clean_name(text: str) -> str:
        """Filesystem/Obsidian-safe stem (without the truncation hash)."""
        stem = re.sub(r'[\\/*?:"<>|#^\[\]\r\n\t]', " ", str(text))
        stem = re.sub(r"\s+", " ", stem).strip(" .")
        return stem[:MAX_STEM_LENGTH] or "Untitled"

    @staticmethod
    def _truncated_stem(stem: str, original: str) -> str:
        if len(stem) <= MAX_STEM_LENGTH:
            return stem
        digest = hashlib.sha1(original.encode("utf-8")).hexdigest()[:8]
        return f"{stem[: MAX_STEM_LENGTH - 9].rstrip(' .')} {digest}"

    def _register(self, name: str, registry: Dict[str, str], used: Dict[str, str]) -> str:
        key = str(name).strip().lower()
        if key in registry:
            return registry[key]

        stem = self._truncated_stem(self.clean_name(name), str(name))
        candidate = stem
        counter = 2
        while candidate.lower() in used and used[candidate.lower()] != key:
            digest = hashlib.sha1(str(name).encode("utf-8")).hexdigest()[:6]
            candidate = f"{stem[: MAX_STEM_LENGTH - 10].rstrip(' .')} {digest}"
            if candidate.lower() in used and used[candidate.lower()] != key:
                candidate = f"{stem[: MAX_STEM_LENGTH - 4].rstrip(' .')} ({counter})"
                counter += 1

        registry[key] = candidate
        used[candidate.lower()] = key
        return candidate

    def paper_note_name(self, title: str) -> str:
        return self._register(title, self._paper_names, self._used_paper_stems)

    def concept_note_name(self, name: str) -> str:
        return self._register(name, self._concept_names, self._used_concept_stems)

    def prepare_names(self, state: LiteratureBaseState) -> None:
        """Register every title up-front so links are stable within a run."""
        external = self._external_titles(state)
        paper_titles = list(state.papers.keys()) and [paper.title for paper in state.papers.values()]
        for title in sorted(set(paper_titles) | set(external), key=str.lower):
            if str(title).strip():
                self.paper_note_name(title)
        for concept_name in sorted(state.concepts.keys(), key=str.lower):
            self.concept_note_name(concept_name)

    @staticmethod
    def _link_label(title: str) -> str:
        return re.sub(r"[|\]\[\r\n]", " ", str(title)).strip() or "Untitled"

    def _source_link(self, title: str) -> str:
        return f"[[Sources/{self.paper_note_name(title)}|{self._link_label(title)}]]"

    def _concept_link(self, name: str) -> str:
        return f"[[Concepts/{self.concept_note_name(name)}|{self._link_label(name)}]]"

    @staticmethod
    def _external_titles(state: LiteratureBaseState) -> List[str]:
        known = {paper.title.strip().lower() for paper in state.papers.values()}
        external: List[str] = []
        seen: set[str] = set()
        for paper in state.papers.values():
            for title in list(paper.referenced_paper_titles) + list(paper.citing_paper_titles):
                key = str(title).strip().lower()
                if key and key not in known and key not in seen:
                    seen.add(key)
                    external.append(str(title).strip())
        return external

    # ------------------------------------------------------------------ papers
    def write_paper_note(self, paper: Paper, state: Optional[LiteratureBaseState] = None) -> None:
        filename = f"{self.paper_note_name(paper.title)}.md"
        filepath = self.sources_dir / filename

        known_concepts = (
            {concept.lower() for concept in state.concepts} if state else None
        )
        concepts = []
        for concept in paper.extracted_concepts:
            if known_concepts is not None and concept.lower() not in known_concepts:
                continue
            concepts.append(self._concept_link(concept))

        related = [self._source_link(title) for title in paper.related_paper_titles]
        citations = [self._source_link(title) for title in paper.citing_paper_titles]
        references = [self._source_link(title) for title in paper.referenced_paper_titles]

        clean_title = re.sub(r"\s+", " ", paper.title).strip()
        abstract_lines = [
            f"> {line}" for line in (paper.abstract or "N/A").splitlines() if line.strip()
        ] or ["> N/A"]

        lines = [
            "---",
            f"id: {_yaml(paper.id)}",
            f"title: {_yaml(clean_title)}",
            f"authors: {json.dumps(paper.authors, ensure_ascii=False)}",
            f"year: {paper.year if paper.year else 'null'}",
            f"venue: {_yaml(paper.venue or 'N/A')}",
            f"url: {_yaml(paper.doi_or_url or '')}",
            f"pdf_url: {_yaml(paper.pdf_url or '')}",
            f"source_engine: {_yaml(paper.source_engine or 'unknown')}",
            f"citation_count: {paper.citation_count}",
            f"citation_velocity: {paper.citation_velocity}",
            f"objective_score: {paper.objective_scientific_score}",
            f"node_weight: {paper.normalized_weight}",
            "type: literature_note",
            "---",
            "",
            f"# {clean_title}",
            "",
            f"> 📊 **Scientometric Score:** `{paper.objective_scientific_score}` | **Continuous Weight:** `{paper.normalized_weight}`",
            "",
            "## 📌 Formatted Citation",
            f"> {paper.formatted_citation or 'N/A'}",
            "",
            "## 🧠 Executive Summary (English)",
            paper.summary_en or "N/A",
            "",
            "## 🔍 Key Findings & Contributions",
        ]
        if paper.key_findings_en:
            lines.extend(f"- {finding}" for finding in paper.key_findings_en)
        else:
            lines.append("- N/A")

        lines.extend(
            [
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
            ]
        )

        if state is not None:
            relations = self._paper_relations(paper, state)
            if relations:
                lines.extend(["", "## 🕸️ Typed Graph Relations"])
                for relation, titles in relations.items():
                    lines.append(
                        f"- **{relation}** → " + ", ".join(self._source_link(title) for title in titles)
                    )

        lines.extend(["", "## 📄 Abstract", *abstract_lines, ""])

        with open(filepath, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    @staticmethod
    def _paper_relations(paper: Paper, state: LiteratureBaseState) -> Dict[str, List[str]]:
        relations: Dict[str, List[str]] = {}
        paper_key = paper.title.strip().lower()
        for edge in state.edges:
            relation = edge.relation_type or "relates_to"
            if edge.source_title.strip().lower() == paper_key:
                relations.setdefault(relation, []).append(edge.target_title)
            elif edge.target_title.strip().lower() == paper_key:
                relations.setdefault(f"incoming:{relation}", []).append(edge.source_title)

        cleaned: Dict[str, List[str]] = {}
        for relation, titles in relations.items():
            unique = sorted({title for title in titles if title}, key=str.lower)
            if unique:
                cleaned[relation] = unique
        return cleaned

    # ---------------------------------------------------------------- concepts
    def write_concept_note(self, hub: ConceptHub, state: LiteratureBaseState) -> None:
        filename = f"{self.concept_note_name(hub.name)}.md"
        filepath = self.concepts_dir / filename

        mention_lines: List[str] = []
        if hub.mentions:
            for mention in hub.mentions:
                page_str = f"p. {mention.page_number}" if mention.page_number else "full text"
                quote_str = (
                    f' — *"{mention.context_snippet}"*' if mention.context_snippet else ""
                )
                mention_lines.append(
                    f"- {self._source_link(mention.paper_title)} (**{page_str}**){quote_str}"
                )
        else:
            for paper in state.papers.values():
                if any(concept.lower() == hub.name.lower() for concept in paper.extracted_concepts):
                    mention_lines.append(f"- {self._source_link(paper.title)} ({paper.year or 'N/A'})")

        lines = [
            "---",
            f"concept: {_yaml(hub.name)}",
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
            "\n".join(mention_lines) if mention_lines else "- No direct source mentions recorded.",
        ]

        with open(filepath, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    # ------------------------------------------------------------------- stubs
    def write_external_stubs(self, state: LiteratureBaseState) -> None:
        """Create lightweight notes for cited references so wikilinks never dangle."""
        known = {paper.title.strip().lower() for paper in state.papers.values()}
        collected: Dict[str, Dict[str, object]] = {}

        for paper in state.papers.values():
            for title in list(paper.referenced_paper_titles) + list(paper.citing_paper_titles):
                cleaned = str(title).strip()
                key = cleaned.lower()
                if not cleaned or key in known:
                    continue
                entry = collected.setdefault(key, {"title": cleaned, "papers": set()})
                entry["papers"].add(paper.title)

        for entry in collected.values():
            title = str(entry["title"])
            filename = f"{self.paper_note_name(title)}.md"
            filepath = self.sources_dir / filename
            cited_by = sorted(entry["papers"], key=str.lower)
            lines = [
                "---",
                f"title: {_yaml(title)}",
                "type: external_reference",
                "---",
                f"# {title}",
                "",
                "> 📎 **External reference** — appears in the citation network but was not ingested.",
                "",
                "## 🔗 Cited within this vault",
            ]
            lines.extend(f"- {self._source_link(paper_title)}" for paper_title in cited_by)
            lines.append("")
            with open(filepath, "w", encoding="utf-8") as handle:
                handle.write("\n".join(lines))

    # -------------------------------------------------------------------- hubs
    def write_hub_files(self, state: LiteratureBaseState) -> None:
        safe_topic = re.sub(r"\s+", " ", state.topic).strip()

        # 1. Overview Synthesis
        overview_path = self.vault_path / "_Overview_Synthesis.md"
        overview_lines = [
            "---",
            f"topic: {_yaml(safe_topic)}",
            f"total_sources: {len(state.papers)}",
            f"total_concepts: {len(state.concepts)}",
            f"last_updated: {_yaml(state.updated_at)}",
            "type: synthesis_hub",
            "---",
            f"# Master Synthesis: {safe_topic}",
            "",
            "## 🎯 Research Requirements",
            f"> {state.requirements}",
            "",
            "## 📑 Executive Literature Review",
            state.overall_summary_en or "No synthesis generated yet.",
            "",
            "## 🗺️ Knowledge Base Index",
        ]
        for paper in sorted(
            state.papers.values(), key=lambda item: item.objective_scientific_score, reverse=True
        ):
            overview_lines.append(
                f"- {self._source_link(paper.title)} ({paper.year or 'N/A'}) — "
                f"*Weight: {paper.normalized_weight}* | *Score: {paper.objective_scientific_score}*"
            )

        unique_edges = {(edge.source_title, edge.target_title, edge.relation_type) for edge in state.edges}
        if unique_edges:
            overview_lines.extend(["", f"## 🕸️ Citation & Relation Network ({len(unique_edges)} edges)"])
            for source, target, relation in sorted(unique_edges)[:300]:
                overview_lines.append(
                    f"- {self._source_link(source)} —`{relation}`→ {self._source_link(target)}"
                )
            if len(unique_edges) > 300:
                overview_lines.append(f"- … and {len(unique_edges) - 300} more edges")

        with open(overview_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(overview_lines))

        # 2. Interactive Obsidian Bibliography
        interactive_bib_path = self.vault_path / "_Bibliography.md"
        bib_lines = [
            "---",
            f"citation_format: {_yaml(state.citation_format)}",
            f"total_entries: {len(state.papers)}",
            "type: master_bibliography",
            "---",
            f"# Master Bibliography ({state.citation_format})",
            "",
            "> 💡 **Tip:** A pure copy-paste ready version without markdown is saved in `Formatted_Bibliography.md`.",
            "",
            "## 📚 References List",
            state.bibliography_en or "No references available.",
            "",
            "## 🔗 Vault Source Links",
        ]
        for paper in sorted(state.papers.values(), key=lambda item: item.title.lower()):
            bib_lines.append(f"- {self._source_link(paper.title)}")

        with open(interactive_bib_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(bib_lines))

        # 3. Clean Standalone Export File
        export_bib_path = self.vault_path / "Formatted_Bibliography.md"
        clean_lines = [
            f"# References ({state.citation_format})",
            f"**Topic:** {safe_topic}",
            f"**Total Sources:** {len(state.papers)}",
            "",
            "---",
            "",
            state.bibliography_en or "No references available.",
            "",
        ]
        with open(export_bib_path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(clean_lines))

        if "bibtex" in state.citation_format.lower():
            bibtex_file = self.vault_path / "references.bib"
            with open(bibtex_file, "w", encoding="utf-8") as handle:
                handle.write(state.bibliography_en + "\n")

    # ------------------------------------------------------------------- state
    def write_agent_activity(self, activity: object) -> None:
        """Persist the lead/specialist hand-off log as a readable note."""
        messages = []
        for item in activity if isinstance(activity, list) else []:
            if hasattr(item, "sender"):
                messages.append(item)
            elif isinstance(item, dict):
                messages.append(item)
        if not messages:
            return

        lines = [
            "---",
            "type: agent_activity",
            "---",
            "# 🤖 Agent Activity",
            "",
            "| Time | From | To | Action | Status | Duration | Summary |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for message in messages:
            data = message if isinstance(message, dict) else message.__dict__
            summary = str(data.get("summary", "")).replace("|", "\\|")
            lines.append(
                f"| {data.get('timestamp', '')} | `{data.get('sender', '')}` | `{data.get('recipient', '')}` "
                f"| `{data.get('action', '')}` | {data.get('status', '')} "
                f"| {data.get('duration_ms', 0)} ms | {summary} |"
            )
        lines.append("")

        with open(self.vault_path / "_Agent_Activity.md", "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines))

    def save_state(self, state: LiteratureBaseState) -> None:
        """Atomically persist the whole research base next to the notes."""
        self.vault_path.mkdir(parents=True, exist_ok=True)
        temporary = self.state_path.with_suffix(".json.tmp")
        try:
            temporary.write_text(state.model_dump_json(indent=2), encoding="utf-8")
            temporary.replace(self.state_path)
        except OSError as exc:
            logger.error("Could not persist state for %r: %s", state.base_id, exc)
            temporary.unlink(missing_ok=True)

    def load_state(self, base_id: str | None = None) -> Optional[LiteratureBaseState]:
        if not self.state_path.exists():
            return None
        try:
            state = LiteratureBaseState.model_validate_json(
                self.state_path.read_text(encoding="utf-8")
            )
        except (OSError, ValueError) as exc:
            logger.error("Could not read state from %s: %s", self.state_path, exc)
            return None
        if base_id and state.base_id != base_id:
            logger.warning(
                "State in %s belongs to base %r, not %r", self.state_path, state.base_id, base_id
            )
        return state
