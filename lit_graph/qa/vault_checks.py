"""Automated quality checks for generated vaults and literature state."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

from ..models import LiteratureBaseState

LINK_PATTERN = re.compile(r"\[\[([^\]\|#]+)")
FRONTMATTER_DELIMITER = "---"

REQUIRED_KEYS: Dict[str, Set[str]] = {
    "literature_note": {"title", "type"},
    "concept_hub": {"concept", "type"},
    "external_reference": {"title", "type"},
    "synthesis_hub": {"topic", "type"},
    "master_bibliography": {"citation_format", "type"},
    "agent_activity": {"type"},
}


@dataclass
class QAIssue:
    severity: str
    code: str
    message: str
    path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QAReport:
    issues: List[QAIssue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def errors(self) -> List[QAIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> List[QAIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def add(self, severity: str, code: str, message: str, path: str = "") -> None:
        self.issues.append(QAIssue(severity=severity, code=code, message=message, path=path))

    def merge(self, other: "QAReport") -> None:
        self.issues.extend(other.issues)
        for key, value in other.stats.items():
            self.stats[key] = self.stats.get(key, 0) + value

    def summary(self) -> str:
        stat_line = ", ".join(f"{key}={value}" for key, value in sorted(self.stats.items()))
        return (
            f"{len(self.errors)} errors, {len(self.warnings)} warnings"
            + (f" ({stat_line})" if stat_line else "")
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary(),
            "stats": self.stats,
            "issues": [issue.to_dict() for issue in self.issues],
        }


def _parse_frontmatter(text: str) -> Dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return {}
    data: Dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == FRONTMATTER_DELIMITER:
            break
        if ":" not in line or line.startswith((" ", "\t")):
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _resolve_link(target: str, vault_path: Path, stem_to_path: Dict[str, str]) -> Optional[str]:
    cleaned = target.strip().replace("\\", "/")
    if cleaned.lower().endswith(".md"):
        cleaned = cleaned[:-3]
    if "/" in cleaned:
        candidate = vault_path / f"{cleaned}.md"
        return candidate.as_posix() if candidate.exists() else None
    return stem_to_path.get(cleaned)


def run_vault_checks(vault_path: str | Path) -> QAReport:
    """Validate Obsidian connectivity, frontmatter and hub formats."""
    vault = Path(vault_path)
    report = QAReport()
    if not vault.exists():
        report.add("error", "vault_missing", f"Vault directory does not exist: {vault}")
        return report

    markdown_files = [
        path
        for path in vault.rglob("*.md")
        if ".obsidian" not in path.parts and ".trash" not in path.parts
    ]
    if not markdown_files:
        report.add("warning", "vault_empty", "Vault contains no Markdown notes")
        return report

    stem_counts: Dict[str, int] = {}
    for path in markdown_files:
        stem_counts[path.stem] = stem_counts.get(path.stem, 0) + 1
    for stem, count in stem_counts.items():
        if count > 1:
            report.add("warning", "duplicate_stem", f"Duplicate note name {stem!r} ({count} files)")

    stem_to_path: Dict[str, str] = {}
    for path in markdown_files:
        stem_to_path.setdefault(path.stem, path.as_posix())
    inbound: Dict[str, int] = {path.as_posix(): 0 for path in markdown_files}
    outbound: Dict[str, int] = {path.as_posix(): 0 for path in markdown_files}
    unresolved: List[tuple[str, str]] = []
    type_counts: Dict[str, int] = {}

    for path in markdown_files:
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            report.add("error", "unreadable_note", f"Cannot read note: {exc}", path.as_posix())
            continue

        frontmatter = _parse_frontmatter(text)
        note_type = frontmatter.get("type")
        plain_export = path.name == "Formatted_Bibliography.md"
        if plain_export:
            pass
        elif not frontmatter:
            report.add("warning", "missing_frontmatter", "Note has no YAML frontmatter", path.as_posix())
        elif note_type:
            type_counts[note_type] = type_counts.get(note_type, 0) + 1
            missing = REQUIRED_KEYS.get(note_type, set()) - set(frontmatter)
            # ``type`` itself is always present, keep the check focused on the rest.
            missing.discard("type")
            for key in sorted(missing):
                report.add(
                    "warning",
                    "missing_frontmatter_key",
                    f"Frontmatter missing key {key!r}",
                    path.as_posix(),
                )
            if note_type not in REQUIRED_KEYS:
                report.add("warning", "unknown_note_type", f"Unknown note type {note_type!r}", path.as_posix())
        else:
            report.add("warning", "missing_type", "Frontmatter has no 'type' key", path.as_posix())

        links = LINK_PATTERN.findall(text)
        outbound[path.as_posix()] = len(links)
        for target in links:
            resolved = _resolve_link(target, vault, stem_to_path)
            if resolved is None:
                unresolved.append((path.as_posix(), target))
                continue
            inbound[resolved] = inbound.get(resolved, 0) + 1

    for source, target in unresolved:
        report.add(
            "warning",
            "unresolved_link",
            f"Unresolved wikilink [[{target}]]",
            source,
        )

    orphans = [
        path
        for path in markdown_files
        if path.parent.name in {"Sources", "Concepts"}
        and inbound.get(path.as_posix(), 0) == 0
        and outbound.get(path.as_posix(), 0) == 0
    ]
    for path in orphans:
        report.add("info", "orphan_note", "Note has no inbound or outbound links", path.as_posix())

    bibliography = vault / "_Bibliography.md"
    if bibliography.exists():
        bibliography_text = bibliography.read_text(encoding="utf-8", errors="ignore")
        if "No references available" in bibliography_text:
            report.add("warning", "empty_bibliography", "Bibliography contains no references")

    report.stats = {
        "notes": len(markdown_files),
        "sources": type_counts.get("literature_note", 0),
        "concepts": type_counts.get("concept_hub", 0),
        "external_refs": type_counts.get("external_reference", 0),
        "links": sum(outbound.values()),
        "unresolved_links": len(unresolved),
        "orphans": len(orphans),
    }
    return report


def run_state_checks(state: LiteratureBaseState) -> QAReport:
    """Validate the scientific state and graph invariants before/after a run."""
    report = QAReport()
    if not state.papers:
        report.add("warning", "no_papers", "Literature base contains no papers")
        return report

    concept_names = {name.lower() for name in state.concepts}
    external_titles: Set[str] = set()
    for paper in state.papers.values():
        external_titles.update(title.lower() for title in paper.referenced_paper_titles)
        external_titles.update(title.lower() for title in paper.citing_paper_titles)

        if not paper.summary_en.strip():
            report.add("warning", "missing_summary", f"Paper has no summary: {paper.title}")
        if not paper.formatted_citation.strip():
            report.add("warning", "missing_citation", f"Paper has no formatted citation: {paper.title}")
        if not paper.extracted_concepts:
            report.add("info", "no_concepts", f"Paper has no concepts: {paper.title}")
        for concept in paper.extracted_concepts:
            if concept.lower() not in concept_names:
                report.add(
                    "error",
                    "orphan_concept_link",
                    f"Paper links to missing concept hub {concept!r}: {paper.title}",
                )

    for hub in state.concepts.values():
        if not hub.summary_en.strip():
            report.add("warning", "missing_concept_definition", f"Concept has no definition: {hub.name}")
        if not hub.mentions:
            report.add("info", "concept_without_mentions", f"Concept has no linked papers: {hub.name}")

    if not state.bibliography_en.strip():
        report.add("warning", "empty_bibliography_state", "Master bibliography is empty")
    if not state.overall_summary_en.strip():
        report.add("warning", "empty_overview", "Master overview is empty")

    seen_edges: Set[tuple[str, str, str]] = set()
    known_titles = {paper.title.lower() for paper in state.papers.values()}
    for edge in state.edges:
        key = (edge.source_title.lower(), edge.target_title.lower(), edge.relation_type)
        if key in seen_edges:
            report.add(
                "warning",
                "duplicate_edge",
                f"Duplicate edge {edge.source_title!r} -> {edge.target_title!r}",
            )
        seen_edges.add(key)
        if edge.source_title.lower() not in known_titles:
            report.add("warning", "unknown_edge_source", f"Edge source is not in vault: {edge.source_title!r}")
        if (
            edge.target_title.lower() not in known_titles
            and edge.target_title.lower() not in external_titles
        ):
            report.add("warning", "unknown_edge_target", f"Edge target is not in vault: {edge.target_title!r}")

    report.stats = {
        "papers": len(state.papers),
        "concepts": len(state.concepts),
        "edges": len(state.edges),
        "duplicate_edges": len(state.edges) - len(seen_edges),
    }
    return report


def merge_reports(reports: Iterable[QAReport]) -> QAReport:
    merged = QAReport()
    for report in reports:
        merged.merge(report)
    return merged
