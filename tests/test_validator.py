from lit_graph.agent.validator import LiteratureValidator


def test_validator_stages(mock_llm, sample_paper):
    validator = LiteratureValidator(mock_llm)

    # Fast consolidated candidate check
    is_valid = validator.validate_candidate(
        sample_paper,
        topic="Mechanistic Interpretability",
        requirements="Published after 2021"
    )

    assert is_valid is True
    assert sample_paper.topic_relevance_score == 8.5
    assert sample_paper.requirements_met is True