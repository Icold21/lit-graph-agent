"""Graph & Knowledge Engineer agent: ontology, wikilinks and Obsidian output."""

from collections import Counter
from typing import Any, Dict, List, Set, Tuple

from ..config import settings
from ..models import ConceptHub, ConceptMention, LiteratureBaseState, Paper
from ..storage.obsidian_vault import ObsidianVaultManager
from ..utils.logging_setup import get_logger
from .bus import AgentBus, BaseTeamAgent
from .concepts import concept_key, dedupe_concepts
from .roles import TEAM_ROLES

logger = get_logger(__name__)


class GraphAgent(BaseTeamAgent):
    """Owns the knowledge graph: concept canonicalization, node weights and vault notes."""

    role = TEAM_ROLES["graph"]

    def __init__(self, vault: ObsidianVaultManager, bus: AgentBus | None = None):
        super().__init__(bus)
        self.vault = vault

    def actions(self) -> Tuple[str, ...]:
        return ("rebuild_graph", "flush", "save_state", "load_state")

    def _handle(self, action: str, **payload: Any) -> Any:
        if action == "rebuild_graph":
            return self.rebuild_graph(payload["state"], list(payload["papers"]))
        if action == "flush":
            return self.flush(payload["state"], activity=payload.get("activity"))
        if action == "save_state":
            self.vault.save_state(payload["state"])
            return True
        if action == "load_state":
            return self.vault.load_state(payload.get("base_id"))
        raise ValueError(f"Unsupported graph action: {action}")

    def rebuild_graph(self, state: LiteratureBaseState, papers: List[Paper]) -> Dict[str, int]:
        """Canonicalize concepts, compute node weights and preserve definitions."""
        if not papers:
            state.concepts.clear()
            return {"papers": 0, "concepts": 0, "edges": len(state.edges)}

        existing_by_key: Dict[str, ConceptHub] = {
            concept_key(hub.name): hub for hub in state.concepts.values() if concept_key(hub.name)
        }

        per_paper: Dict[str, List[Tuple[str, str]]] = {}
        paper_counts: Counter = Counter()
        displays: Dict[str, Counter] = {}

        for paper in papers:
            raw_concepts = paper.extracted_concepts_all or paper.extracted_concepts
            pairs = dedupe_concepts(raw_concepts, limit=settings.max_concepts_per_paper)
            per_paper[paper.id] = pairs
            for key, display in pairs:
                paper_counts[key] += 1
                displays.setdefault(key, Counter())[display] += 1

        min_required = min(max(1, settings.min_concept_papers), len(papers))
        allowed = {key for key, count in paper_counts.items() if count >= min_required}

        display_map: Dict[str, str] = {}
        for key in allowed:
            if key in existing_by_key:
                display_map[key] = existing_by_key[key].name
            else:
                counter = displays[key]
                display_map[key] = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]

        for paper in papers:
            canonical: List[str] = []
            seen: Set[str] = set()
            for key, _ in per_paper[paper.id]:
                if key in allowed and key not in seen:
                    seen.add(key)
                    canonical.append(display_map[key])
            paper.extracted_concepts = canonical[: settings.max_concepts_per_paper]

        scores = [paper.objective_scientific_score for paper in papers]
        max_score, min_score = max(scores), min(scores)
        for paper in papers:
            normalised = (
                (paper.objective_scientific_score - min_score) / (max_score - min_score)
                if max_score > min_score
                else 1.0
            )
            paper.normalized_weight = round(0.2 + (0.8 * normalised), 3)

        concept_papers: Dict[str, List[Paper]] = {key: [] for key in allowed}
        for paper in papers:
            for concept_name in paper.extracted_concepts:
                key = concept_key(concept_name)
                if key in concept_papers:
                    concept_papers[key].append(paper)

        raw_scores = {
            key: sum(paper.objective_scientific_score for paper in members)
            for key, members in concept_papers.items()
        }
        max_raw = max(raw_scores.values()) if raw_scores else 1.0
        min_raw = min(raw_scores.values()) if raw_scores else 0.0

        state.concepts.clear()
        for key in allowed:
            name = display_map[key]
            members = concept_papers.get(key, [])
            raw_score = raw_scores.get(key, 0.0)
            normalised = (raw_score - min_raw) / (max_raw - min_raw) if max_raw > min_raw else 1.0
            hub = ConceptHub(
                name=name,
                aggregated_score=round(raw_score, 2),
                normalized_weight=round(0.2 + (0.8 * normalised), 3),
            )

            old_hub = existing_by_key.get(key)
            if old_hub and old_hub.summary_en.strip():
                hub.summary_en = old_hub.summary_en

            for member in members:
                page_mentions = [
                    mention
                    for mention in member.concept_mentions
                    if concept_key(mention.concept_name) == key
                ]
                if page_mentions:
                    for mention in page_mentions:
                        hub.mentions.append(
                            ConceptMention(
                                concept_name=name,
                                paper_title=member.title,
                                page_number=mention.page_number,
                                context_snippet=mention.context_snippet,
                            )
                        )
                else:
                    hub.mentions.append(ConceptMention(concept_name=name, paper_title=member.title))

            state.concepts[name] = hub

        return {"papers": len(papers), "concepts": len(state.concepts), "edges": len(state.edges)}

    def flush(self, state: LiteratureBaseState, activity: Any = None) -> Dict[str, int]:
        """Write every note, stub, hub file, state file and the agent activity log."""
        self.vault.prepare_names(state)
        for paper in state.papers.values():
            self.vault.write_paper_note(paper, state)
        for hub in state.concepts.values():
            self.vault.write_concept_note(hub, state)
        self.vault.write_external_stubs(state)
        self.vault.write_hub_files(state)
        if activity is not None:
            self.vault.write_agent_activity(activity)
        self.vault.save_state(state)
        return {
            "papers": len(state.papers),
            "concepts": len(state.concepts),
            "edges": len(state.edges),
        }
