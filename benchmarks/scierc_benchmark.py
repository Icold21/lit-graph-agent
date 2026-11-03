"""Evaluate LitGraphAgent concept extraction on the SciERC benchmark.

SciERC is a standard benchmark for scientific knowledge-graph construction
(Luan et al., EMNLP 2018): 500 annotated abstracts with scientific entities
(Task, Method, Metric, Material, Generic, OtherScientificTerm), relations and
coreference clusters.

This harness focuses on the part of the pipeline that builds graph *nodes* and
paper--concept *edges*: it runs ``PromptAgent.synthesize_paper`` on each abstract
and compares the extracted concepts with the gold entity mentions.  Typed
relation extraction is intentionally not scored because LitGraphAgent does not
predict SciERC relations.

Usage (from the repository root)::

    python benchmarks/scierc_benchmark.py \
        --data-dir C:/path/to/sciERC/raw_data \
        --limit 20 \
        --model qwen3.5:4b \
        --output benchmarks/results/scierc.json
"""

from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

ENTITY_LINE = re.compile(r"^T\d+\t(?P<type>[A-Za-z_-]+)\s+(?P<start>\d+)\s+(?P<end>\d+)\t(?P<text>.+)$")
WORD_RE = re.compile(r"[a-z0-9]+")
ARTICLES = {"a", "an", "the"}


# --------------------------------------------------------------------------- io
@dataclass
class GoldPaper:
    paper_id: str
    abstract: str
    entities: List[Tuple[str, str]] = field(default_factory=list)  # (type, text)

    @property
    def texts(self) -> List[str]:
        return [text for _, text in self.entities]


def parse_ann(path: Path) -> List[Tuple[str, str]]:
    """Parse brat-style entity annotations from a SciERC .ann file."""
    entities: List[Tuple[str, str]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        match = ENTITY_LINE.match(raw_line.strip())
        if not match:
            continue
        entities.append((match.group("type"), match.group("text").strip()))
    return entities


def load_scierc(data_dir: Path, limit: int, seed: int) -> List[GoldPaper]:
    ann_files = sorted(data_dir.glob("*.ann"))
    if not ann_files:
        raise SystemExit(f"No .ann files found in {data_dir}")

    rng = random.Random(seed)
    if limit and limit < len(ann_files):
        ann_files = rng.sample(ann_files, limit)
        ann_files.sort(key=lambda item: item.name)

    papers: List[GoldPaper] = []
    for ann in ann_files:
        text_path = ann.with_suffix(".txt")
        if not text_path.exists():
            continue
        papers.append(
            GoldPaper(
                paper_id=ann.stem,
                abstract=text_path.read_text(encoding="utf-8").strip(),
                entities=parse_ann(ann),
            )
        )
    return papers


# ---------------------------------------------------------------- normalisation
def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = text.replace("'s", " ")
    text = re.sub(r"[-_/]", " ", text)
    tokens = WORD_RE.findall(text)
    while tokens and tokens[0] in ARTICLES:
        tokens.pop(0)
    # A very small, deterministic singulariser; keeps the metric reproducible.
    normalised: List[str] = []
    for token in tokens:
        if len(token) > 3 and token.endswith("ies"):
            token = token[:-3] + "y"
        elif len(token) > 3 and token.endswith("ses"):
            token = token[:-2]
        elif len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
            token = token[:-1]
        normalised.append(token)
    return " ".join(normalised)


def relaxed_match(gold: str, predicted: str) -> bool:
    """Token-level Jaccard match, tolerant to short modifiers and acronyms."""
    gold_tokens = set(normalize(gold).split())
    pred_tokens = set(normalize(predicted).split())
    if not gold_tokens or not pred_tokens:
        return False
    overlap = gold_tokens & pred_tokens
    if not overlap:
        return False
    union = gold_tokens | pred_tokens
    return len(overlap) / len(union) >= 0.5


def unique_texts(items: Iterable[str]) -> List[str]:
    """Collapse duplicate mentions that normalise to the same string."""
    seen: Set[str] = set()
    result: List[str] = []
    for item in items:
        key = normalize(item)
        if key and key not in seen:
            seen.add(key)
            result.append(item)
    return result


def match_sets(
    gold: Sequence[str],
    predicted: Sequence[str],
    *,
    relaxed: bool = False,
) -> Tuple[int, List[str], List[str], List[str], List[str]]:
    """Greedy one-to-one matching used for micro precision/recall."""
    if relaxed:
        predicted_norm = [(item, normalize(item)) for item in predicted]
        matched_pred: Set[int] = set()
        matched_gold: Set[str] = set()
        pairs: List[Tuple[str, str]] = []

        # Prefer exact normalised matches so a longer gold phrase cannot steal a
        # prediction from an exact hit during the greedy relaxed pass.
        for gold_item in gold:
            if gold_item in matched_gold:
                continue
            gold_key = normalize(gold_item)
            for index, (_, pred_key) in enumerate(predicted_norm):
                if index in matched_pred or pred_key != gold_key:
                    continue
                matched_pred.add(index)
                matched_gold.add(gold_item)
                pairs.append((gold_item, predicted[index]))
                break

        for gold_item in sorted(gold, key=len, reverse=True):
            if gold_item in matched_gold:
                continue
            for index, (pred_item, _) in enumerate(predicted_norm):
                if index in matched_pred:
                    continue
                if relaxed_match(gold_item, pred_item):
                    matched_pred.add(index)
                    matched_gold.add(gold_item)
                    pairs.append((gold_item, pred_item))
                    break
        tp = len(pairs)
        unmatched_gold = [item for item in gold if item not in matched_gold]
        unmatched_pred = [item for index, item in enumerate(predicted) if index not in matched_pred]
        return tp, unmatched_gold, unmatched_pred, [pair[0] for pair in pairs], [pair[1] for pair in pairs]

    gold_norm = {normalize(item) for item in gold}
    pred_norm = {normalize(item) for item in predicted}
    tp = len(gold_norm & pred_norm)
    unmatched_gold = sorted(gold_norm - pred_norm)
    unmatched_pred = sorted(pred_norm - gold_norm)
    return tp, unmatched_gold, unmatched_pred, sorted(gold_norm & pred_norm), sorted(gold_norm & pred_norm)


def prf(tp: int, predicted: int, gold: int) -> Dict[str, float]:
    precision = tp / predicted if predicted else 0.0
    recall = tp / gold if gold else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "tp": tp,
        "predicted": predicted,
        "gold": gold,
    }


# --------------------------------------------------------------------- scoring
def score(papers: List[GoldPaper], predictions: Dict[str, List[str]]) -> Dict[str, Any]:
    totals: Dict[str, Counter] = {
        "concepts_all_exact": Counter(),
        "concepts_all_relaxed": Counter(),
        "concepts_content_exact": Counter(),
        "concepts_content_relaxed": Counter(),
        "edges_all_exact": Counter(),
        "edges_all_relaxed": Counter(),
    }
    per_paper: List[Dict[str, Any]] = []

    for paper in papers:
        gold_all = unique_texts(paper.texts)
        gold_content = unique_texts(
            [text for kind, text in paper.entities if kind.lower() != "generic"]
        )
        predicted = predictions.get(paper.paper_id, [])

        row: Dict[str, Any] = {
            "paper_id": paper.paper_id,
            "gold_entities": len(gold_all),
            "gold_content_entities": len(gold_content),
            "predicted_concepts": len(predicted),
            "predicted": predicted,
            "gold": gold_all,
        }

        for label, gold_items, is_edge in (
            ("concepts_all", gold_all, False),
            ("concepts_content", gold_content, False),
        ):
            for mode, relaxed in (("exact", False), ("relaxed", True)):
                tp, missing, extra, matched_gold, matched_pred = match_sets(
                    gold_items, predicted, relaxed=relaxed
                )
                totals[f"{label}_{mode}"].update(
                    tp=tp, predicted=len(predicted), gold=len(gold_items)
                )
                row[f"{label}_{mode}"] = {
                    "tp": tp,
                    "missing": missing[:10],
                    "extra": extra[:10],
                }

        for mode, relaxed in (("exact", False), ("relaxed", True)):
            tp, missing, extra, _, _ = match_sets(gold_all, predicted, relaxed=relaxed)
            totals[f"edges_all_{mode}"].update(tp=tp, predicted=len(predicted), gold=len(gold_all))

        per_paper.append(row)

    summary: Dict[str, Any] = {}
    for key, counter in totals.items():
        summary[key] = prf(counter["tp"], counter["predicted"], counter["gold"])

    summary["papers"] = len(papers)
    summary["avg_gold_entities"] = round(
        sum(len(unique_texts(paper.texts)) for paper in papers) / len(papers), 2
    ) if papers else 0.0
    summary["avg_predicted_concepts"] = round(
        sum(len(predictions.get(paper.paper_id, [])) for paper in papers) / len(papers), 2
    ) if papers else 0.0
    summary["entity_type_distribution"] = dict(
        Counter(kind for paper in papers for kind, _ in paper.entities).most_common()
    )
    summary["per_paper"] = per_paper
    return summary


# ------------------------------------------------------------------ extraction
def build_agent(model: str, base_url: str, api_key: str, timeout: float, retries: int):
    from lit_graph.agent.prompt_agent import PromptAgent
    from lit_graph.config import settings
    from lit_graph.llm.providers import UniversalLLMProvider

    settings.llm_timeout = timeout
    settings.llm_max_retries = retries
    llm = UniversalLLMProvider(api_key=api_key, model_name=model, base_url=base_url)
    return PromptAgent(llm)


def extract(agent, paper: GoldPaper) -> List[str]:
    from lit_graph.models import Paper

    item = Paper(
        id=paper.paper_id,
        title=paper.paper_id,
        authors=[],
        abstract=paper.abstract,
    )
    agent.synthesize_paper(item)
    return list(item.extracted_concepts)


def load_checkpoint(path: Path) -> Dict[str, List[str]]:
    done: Dict[str, List[str]] = {}
    if not path.exists():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        done[record["paper_id"]] = list(record.get("concepts") or [])
    return done


def append_checkpoint(path: Path, paper_id: str, concepts: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"paper_id": paper_id, "concepts": list(concepts)}, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------ main
def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="Directory with SciERC .txt/.ann files")
    parser.add_argument("--limit", type=int, default=20, help="Number of abstracts to evaluate (0 = all)")
    parser.add_argument("--seed", type=int, default=42, help="Sampling seed for reproducible subsets")
    parser.add_argument("--model", default="qwen3.5:4b", help="OpenAI-compatible model name")
    parser.add_argument("--base-url", default="http://localhost:11434/v1", help="OpenAI-compatible endpoint")
    parser.add_argument("--api-key", default="ollama", help="API key for the endpoint")
    parser.add_argument("--timeout", type=float, default=600.0, help="Per-request timeout in seconds")
    parser.add_argument("--retries", type=int, default=2, help="LLM retries per request")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "benchmarks" / "results" / "scierc.json")
    parser.add_argument("--checkpoint", type=Path, default=None, help="JSONL file for resumable extraction")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    papers = load_scierc(args.data_dir, args.limit, args.seed)
    if not papers:
        raise SystemExit("No papers loaded")

    checkpoint = args.checkpoint or args.output.with_suffix(".jsonl")
    predictions = load_checkpoint(checkpoint)
    agent = build_agent(args.model, args.base_url, args.api_key, args.timeout, args.retries)

    failures: Dict[str, str] = {}
    started = time.perf_counter()
    for index, paper in enumerate(papers, 1):
        if paper.paper_id in predictions:
            print(f"[{index}/{len(papers)}] {paper.paper_id}: cached", flush=True)
            continue
        paper_started = time.perf_counter()
        try:
            concepts = extract(agent, paper)
        except Exception as exc:  # noqa: BLE001 - one bad abstract must not abort the benchmark
            failures[paper.paper_id] = str(exc)[:240]
            concepts = []
            print(f"[{index}/{len(papers)}] {paper.paper_id}: FAILED ({exc})", flush=True)
        predictions[paper.paper_id] = concepts
        append_checkpoint(checkpoint, paper.paper_id, concepts)
        print(
            f"[{index}/{len(papers)}] {paper.paper_id}: {len(concepts)} concepts "
            f"in {time.perf_counter() - paper_started:.1f}s",
            flush=True,
        )

    summary = score(papers, predictions)
    summary.update(
        {
            "benchmark": "SciERC",
            "task": "scientific concept extraction + paper-concept edge construction",
            "model": args.model,
            "base_url": args.base_url,
            "seed": args.seed,
            "limit": args.limit,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.perf_counter() - started, 1),
            "failures": failures,
            "notes": [
                "Gold items are unique SciERC entity mentions per abstract.",
                "Exact matching uses lowercased, singularised, punctuation-free strings.",
                "Relaxed matching uses token Jaccard overlap >= 0.5.",
                "Typed SciERC relations are not scored: the pipeline does not predict them.",
                "SciERC raw files contain abstracts only; the paper ID is used as the title placeholder.",
            ],
        }
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\nSciERC results")
    for key in (
        "concepts_all_exact",
        "concepts_all_relaxed",
        "concepts_content_exact",
        "concepts_content_relaxed",
        "edges_all_exact",
        "edges_all_relaxed",
    ):
        metrics = summary[key]
        print(
            f"  {key:24s} P={metrics['precision']:.3f} "
            f"R={metrics['recall']:.3f} F1={metrics['f1']:.3f}"
        )
    print(f"\nSaved {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
