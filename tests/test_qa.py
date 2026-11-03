from lit_graph.models import ConceptHub, GraphEdge, LiteratureBaseState, Paper
from lit_graph.qa.vault_checks import run_state_checks, run_vault_checks
from lit_graph.storage.obsidian_vault import ObsidianVaultManager


def _paper() -> Paper:
    return Paper(
        id="p1",
        title="Paper One",
        authors=["Alice Smith"],
        year=2024,
        abstract="Abstract",
        summary_en="Summary",
        formatted_citation="Smith, A. (2024). Paper One.",
        extracted_concepts=["Transformers"],
    )


def _state(**overrides) -> LiteratureBaseState:
    paper = _paper()
    state = LiteratureBaseState(
        base_id="qa",
        topic="Topic",
        requirements="None",
        citation_format="APA 7th",
        papers={paper.id: paper},
        bibliography_en="Smith, A. (2024). Paper One.",
        overall_summary_en="Overview",
    )
    state.concepts = {}
    for key, value in overrides.items():
        setattr(state, key, value)
    return state


def test_unresolved_links_are_reported(tmp_path):
    vault = ObsidianVaultManager(tmp_path)
    (tmp_path / "Sources" / "Broken.md").write_text(
        "---\ntitle: Broken\ntype: literature_note\n---\n[[Sources/Missing|Missing]]\n",
        encoding="utf-8",
    )
    report = run_vault_checks(tmp_path)
    assert any(issue.code == "unresolved_link" for issue in report.issues)
    assert vault is not None


def test_orphan_concept_link_is_an_error():
    state = _state()
    report = run_state_checks(state)
    assert any(issue.code == "orphan_concept_link" and issue.severity == "error" for issue in report.issues)


def test_duplicate_edges_are_reported():
    state = _state()
    paper = state.papers["p1"]
    state.concepts = {"Transformers": ConceptHub(name="Transformers")}
    state.add_edge(GraphEdge(source_title=paper.title, target_title="External", relation_type="cites"))
    state.edges.append(GraphEdge(source_title=paper.title, target_title="External", relation_type="cites"))

    report = run_state_checks(state)
    assert any(issue.code == "duplicate_edge" for issue in report.issues)
