from lit_graph.models import Paper
from lit_graph.search.ranking import compute_scientific_metrics, find_elbow_cutoff


def test_compute_scientific_metrics():
    paper = Paper(
        id="test_01",
        title="Attention Is All You Need",
        year=2017,
        citation_count=100000,
        influential_citation_count=15000
    )
    score = compute_scientific_metrics(paper, current_year=2024)
    
    assert paper.citation_velocity > 10000
    assert paper.influential_ratio > 0.1
    assert score > 50.0


def test_elbow_cutoff_detection():
    # Steep drop from top 3 papers to a low-quality flat tail
    scores = [95.0, 88.0, 72.0, 15.0, 12.0, 10.0, 8.0, 7.0]
    cutoff = find_elbow_cutoff(scores, min_k=2, max_k=6)
    
    # The elbow should accurately detect the drop around index 2/3
    assert cutoff == 3