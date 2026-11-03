"""Concept name canonicalization helpers.

LLM-extracted concept names are notoriously inconsistent ("Transformers" vs
"Transformer", "GNNs" vs "Graph Neural Networks (GNNs)").  The knowledge graph
merges them by a normalized key while keeping a human readable display name.
"""

import re
from collections import Counter
from typing import Iterable

# Acronym -> canonical phrase. Both singular and plural forms are accepted.
ABBREVIATIONS: dict[str, str] = {
    "gnn": "graph neural network",
    "gnns": "graph neural network",
    "llm": "large language model",
    "llms": "large language model",
    "sae": "sparse autoencoder",
    "saes": "sparse autoencoder",
    "vit": "vision transformer",
    "vits": "vision transformer",
    "nn": "neural network",
    "nns": "neural network",
    "rlhf": "reinforcement learning from human feedback",
    "ih": "induction head",
    "ihs": "induction head",
    "mlp": "multilayer perceptron",
    "mlps": "multilayer perceptron",
    "cnn": "convolutional neural network",
    "cnns": "convolutional neural network",
    "rnn": "recurrent neural network",
    "rnns": "recurrent neural network",
    "nlp": "natural language processing",
    "cot": "chain of thought",
}

# Words that should not be singularized / lower-cased by the title-caser.
_LOWERCASE_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with", "via"}
_PRESERVE_CASE = {
    "nnterp",
    "nnsight",
    "transformerlens",
    "huggingface",
    "pytorch",
    "tensorflow",
    "openai",
    "arxiv",
    "github",
    "duckduckgo",
}
_UNCOUNTABLE = {
    "analysis",
    "basis",
    "data",
    "dynamics",
    "ethics",
    "mathematics",
    "media",
    "physics",
    "series",
    "species",
    "statistics",
}
_PARENTHETICAL = re.compile(r"^(?P<base>.+?)\s*[\(\[]\s*(?P<abbr>[^\)\]]{1,25})\s*[\)\]]\s*$")
_HYPHEN_SPLIT = re.compile(r"([-/])")


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def _strip_edges(text: str) -> str:
    return text.strip(" \t\r\n.,:;!?`'\"«»“”")


def _singularize_word(word: str) -> str:
    lower = word.lower()
    if lower in _UNCOUNTABLE:
        return word
    if lower.endswith("ies") and len(lower) > 4:
        return word[:-3] + "y"
    if lower.endswith(("ches", "shes", "sses", "xes", "zes")):
        return word[:-2]
    if lower.endswith("s") and not lower.endswith(("ss", "us", "is")) and len(lower) > 3:
        return word[:-1]
    return word


def _singularize_phrase(phrase: str) -> str:
    words = phrase.split()
    if not words:
        return phrase
    words[-1] = _singularize_word(words[-1])
    return " ".join(words)


def _strip_parenthetical(name: str) -> str:
    match = _PARENTHETICAL.match(name)
    if not match:
        return name
    base = _normalize_whitespace(match.group("base"))
    abbr = _normalize_whitespace(match.group("abbr"))
    # Keep the descriptive part unless the "base" is just the acronym itself.
    if len(base) >= len(abbr) and base.lower() not in ABBREVIATIONS:
        return base
    return abbr


def concept_key(name: str) -> str:
    """Stable comparison key: lowercase, abbreviation-free, singularized."""
    cleaned = _strip_edges(_normalize_whitespace(name))
    if not cleaned:
        return ""
    cleaned = _strip_parenthetical(cleaned)
    lowered = cleaned.lower()
    if lowered in ABBREVIATIONS:
        lowered = ABBREVIATIONS[lowered]
    return _singularize_phrase(lowered)


def _smart_title(text: str) -> str:
    """Title-case a concept while preserving acronyms and mixed-case tokens."""
    parts = _HYPHEN_SPLIT.split(text)
    output: list[str] = []
    for part in parts:
        if part in {"-", "/"}:
            output.append(part)
            continue
        words = part.split()
        rendered = []
        for index, word in enumerate(words):
            if not word:
                continue
            if word.lower() in _PRESERVE_CASE:
                rendered.append(word.lower())
            elif word.isupper() and len(word) > 1:
                rendered.append(word)
            elif any(char.isupper() for char in word[1:]):
                rendered.append(word)
            elif index > 0 and word.lower() in _LOWERCASE_WORDS:
                rendered.append(word.lower())
            else:
                rendered.append(word[:1].upper() + word[1:].lower() if word.islower() else word)
        output.append(" ".join(rendered))
    return "".join(output)


def display_name(name: str) -> str:
    """Human readable name used for notes, links and hub titles."""
    cleaned = _strip_edges(_normalize_whitespace(name))
    if not cleaned:
        return "Untitled Concept"
    cleaned = _strip_parenthetical(cleaned)
    lowered = cleaned.lower()
    if lowered in ABBREVIATIONS:
        cleaned = ABBREVIATIONS[lowered]
    return _smart_title(cleaned)


def canonicalize_concept(name: str) -> str:
    """Public alias for the canonical display name of a concept."""
    return display_name(name)


def choose_display_names(names: Iterable[str]) -> dict[str, str]:
    """Map ``concept_key`` to the most frequent display variant."""
    counters: dict[str, Counter] = {}
    for name in names:
        key = concept_key(name)
        if not key:
            continue
        counters.setdefault(key, Counter())[display_name(name)] += 1
    chosen: dict[str, str] = {}
    for key, counter in counters.items():
        # Most frequent variant wins; ties are broken alphabetically for determinism.
        chosen[key] = sorted(counter.items(), key=lambda item: (-item[1], item[0]))[0][0]
    return chosen


def dedupe_concepts(names: Iterable[str], limit: int | None = None) -> list[tuple[str, str]]:
    """Return ``(key, display)`` pairs in first-seen order."""
    result: list[tuple[str, str]] = []
    seen: set[str] = set()
    for name in names:
        if not isinstance(name, str):
            continue
        key = concept_key(name)
        if not key or key in seen:
            continue
        seen.add(key)
        result.append((key, display_name(name)))
        if limit is not None and len(result) >= limit:
            break
    return result
