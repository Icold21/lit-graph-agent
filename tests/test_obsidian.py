from lit_graph.storage.obsidian_vault import ObsidianVaultManager
from lit_graph.models import LiteratureBaseState


def test_obsidian_vault_generation(tmp_path, sample_paper):
    vault = ObsidianVaultManager(tmp_path)
    vault.write_paper_note(sample_paper)

    note_path = tmp_path / "Sources" / f"{vault.clean_name(sample_paper.title)}.md"
    assert note_path.exists()

    content = note_path.read_text(encoding="utf-8")
    assert "type: literature_note" in content
    assert "In-context Learning and Induction Heads" in content
    assert "## 📊 Scientometric Profile" in content

    # Test master files
    state = LiteratureBaseState(
        base_id="test_vault",
        topic="Transformers Research",
        requirements="Strict",
        citation_format="APA 7th",
        papers={sample_paper.id: sample_paper},
        overall_summary_en="Master review summary.",
        bibliography_en="1. Alice Smith (2023). In-context Learning."
    )
    vault.write_hub_files(state)
    assert (tmp_path / "_Overview_Synthesis.md").exists()
    assert (tmp_path / "_Bibliography.md").exists()