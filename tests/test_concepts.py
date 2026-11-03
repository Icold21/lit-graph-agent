from lit_graph.agent.concepts import (
    canonicalize_concept,
    choose_display_names,
    concept_key,
    dedupe_concepts,
)


def test_plural_and_case_are_merged():
    assert concept_key("Transformers") == concept_key("transformer")
    assert concept_key("Attention Heads") == concept_key("attention head")


def test_parenthetical_acronyms_are_resolved():
    assert concept_key("Graph Neural Networks (GNNs)") == concept_key("GNNs")
    assert concept_key("GNNs") == concept_key("graph neural network")
    assert concept_key("Large Language Models (LLMs)") == concept_key("LLM")
    assert canonicalize_concept("GNNs") == "Graph Neural Network"


def test_display_name_is_readable():
    assert canonicalize_concept("attention heads") == "Attention Heads"
    assert canonicalize_concept("self-attention mechanism") == "Self-Attention Mechanism"
    assert canonicalize_concept("nnterp") == "nnterp"
    assert canonicalize_concept("") == "Untitled Concept"


def test_dedupe_keeps_first_seen_order_and_limit():
    pairs = dedupe_concepts(["Transformers", "Transformer", "Induction Heads", "induction head"], limit=2)
    assert [key for key, _ in pairs] == ["transformer", "induction head"]
    assert len(pairs) == 2


def test_choose_display_names_prefers_frequent_variant():
    chosen = choose_display_names(["attention heads", "Attention Heads", "attention head"])
    assert chosen["attention head"] == "Attention Heads"
