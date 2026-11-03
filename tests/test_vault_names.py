import json

from lit_graph.models import LiteratureBaseState, Paper
from lit_graph.qa.vault_checks import run_vault_checks
from lit_graph.storage.obsidian_vault import ObsidianVaultManager


def _paper(**overrides) -> Paper:
    base = {
        "id": "p1",
        "title": "Short Paper",
        "authors": ["Alice Smith", "Bob Jones"],
        "year": 2024,
        "venue": "NeurIPS",
        "abstract": "First line\nSecond line",
        "formatted_citation": "Smith, A. (2024). Short Paper.",
    }
    base.update(overrides)
    return Paper(**base)


def test_long_titles_get_deterministic_hashed_name(tmp_path):
    title = "A very long paper title " * 8
    first = ObsidianVaultManager(tmp_path / "one")
    second = ObsidianVaultManager(tmp_path / "two")
    name = first.paper_note_name(title)
    assert len(name) <= 80
    assert name == second.paper_note_name(title)
    assert first.paper_note_name(title) == name


def test_sanitized_name_collisions_are_disambiguated(tmp_path):
    vault = ObsidianVaultManager(tmp_path)
    first = vault.paper_note_name("A/B")
    second = vault.paper_note_name("A B")
    assert first == "A B"
    assert second != first
    assert second.startswith("A B ")


def test_note_frontmatter_is_valid_and_blockquote_is_multiline(tmp_path):
    vault = ObsidianVaultManager(tmp_path)
    paper = _paper()
    vault.write_paper_note(paper)
    content = (tmp_path / "Sources" / "Short Paper.md").read_text(encoding="utf-8")
    assert 'authors: ["Alice Smith", "Bob Jones"]' in content
    assert "> First line" in content
    assert "> Second line" in content
    assert 'title: "Short Paper"' in content


def test_external_references_do_not_create_dangling_links(tmp_path):
    vault = ObsidianVaultManager(tmp_path)
    paper = _paper(referenced_paper_titles=["External Reference Work"])
    state = LiteratureBaseState(
        base_id="b",
        topic="Topic",
        requirements="None",
        citation_format="APA 7th",
        papers={paper.id: paper},
        bibliography_en="Smith, A. (2024). Short Paper.",
    )
    vault.prepare_names(state)
    vault.write_paper_note(paper, state)
    vault.write_external_stubs(state)
    assert (tmp_path / "Sources" / "External Reference Work.md").exists()

    report = run_vault_checks(tmp_path)
    assert not [issue for issue in report.issues if issue.code == "unresolved_link"]


def test_existing_obsidian_graph_settings_are_preserved(tmp_path):
    ObsidianVaultManager(tmp_path)
    graph_path = tmp_path / ".obsidian" / "graph.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["nodeSizeMultiplier"] = 3.5
    graph["customUserSetting"] = 42
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    ObsidianVaultManager(tmp_path)
    merged = json.loads(graph_path.read_text(encoding="utf-8"))
    assert merged["nodeSizeMultiplier"] == 3.5
    assert merged["customUserSetting"] == 42
    assert any(group["query"] == "path:Concepts" for group in merged["colorGroups"])
