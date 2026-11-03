from pathlib import Path

from benchmarks.scierc_benchmark import (
    GoldPaper,
    match_sets,
    normalize,
    parse_ann,
    relaxed_match,
    score,
)


def test_normalize_collapses_case_articles_and_plurals():
    assert normalize("The Graph Neural Networks (GNNs)") == "graph neural network gnn"


def test_relaxed_match_tolerates_modifiers():
    assert relaxed_match(
        "word sense disambiguation",
        "word sense disambiguation (WSD) systems",
    )
    assert not relaxed_match("Auditory Nerve", "phase locking in the auditory nerve (AN)")
    assert not relaxed_match("accuracy", "domain adaptation")


def test_match_sets_counts_exact_overlap():
    tp, missing, extra, _, _ = match_sets(
        ["accuracy", "sense priors"],
        ["Sense Priors", "domain adaptation"],
    )
    assert tp == 1
    assert missing == ["accuracy"]
    assert extra == ["domain adaptation"]


def test_relaxed_match_prefers_exact_hits():
    tp, missing, extra, _, _ = match_sets(
        ["Named Entity task", "statistical profile"],
        ["Named Entity task"],
        relaxed=True,
    )
    assert tp == 1
    assert "Named Entity task" not in missing
    assert extra == []


def test_parse_ann_reads_entity_mentions(tmp_path: Path):
    ann = tmp_path / "paper.ann"
    ann.write_text(
        "T1\tMethod 0 10\tword sense\n"
        "T2\tMetric 11 20\taccuracy\n"
        "R1\tUSED-FOR Arg1:T1 Arg2:T2\n",
        encoding="utf-8",
    )
    assert parse_ann(ann) == [("Method", "word sense"), ("Metric", "accuracy")]


def test_score_deduplicates_repeated_gold_mentions():
    papers = [
        GoldPaper(
            paper_id="p1",
            abstract="text",
            entities=[("OtherScientificTerm", "features"), ("OtherScientificTerm", "Features")],
        )
    ]
    summary = score(papers, {"p1": ["features"]})

    assert summary["concepts_all_exact"]["gold"] == 1
    assert summary["concepts_all_exact"]["recall"] == 1.0


def test_score_reports_concept_and_edge_metrics():
    papers = [
        GoldPaper(
            paper_id="p1",
            abstract="text",
            entities=[("Method", "word sense disambiguation"), ("Metric", "accuracy")],
        )
    ]
    summary = score(papers, {"p1": ["word sense disambiguation", "accuracy", "noise"]})

    assert summary["concepts_all_exact"]["tp"] == 2
    assert summary["concepts_all_exact"]["precision"] == round(2 / 3, 4)
    assert summary["concepts_all_exact"]["recall"] == 1.0
    assert summary["edges_all_exact"]["f1"] == summary["concepts_all_exact"]["f1"]
