from lit_graph.search.engine import AcademicSearchEngine


def test_academic_search_pre_ranking():
    engine = AcademicSearchEngine()
    paper_a = {
        "title": "Mechanistic Interpretability Circuits",
        "abstract": "We analyze circuits in large language models.",
        "year": 2024,
        "citation_count": 300,
        "influential_citation_count": 40
    }
    paper_b = {
        "title": "General AI Overview",
        "abstract": "Short overview text.",
        "year": 2017,
        "citation_count": 1,
        "influential_citation_count": 0
    }

    score_a = engine._calculate_pre_rank_heuristic(paper_a, "Mechanistic Interpretability")
    score_b = engine._calculate_pre_rank_heuristic(paper_b, "Mechanistic Interpretability")

    assert score_a > score_b