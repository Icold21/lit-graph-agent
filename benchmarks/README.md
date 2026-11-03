# SciERC benchmark

This folder contains a small, reproducible evaluation of the graph-building part
of LitGraphAgent on [SciERC](https://nlp.cs.washington.edu/sciIE/) — a standard
benchmark for scientific knowledge-graph construction (Luan et al., EMNLP 2018).

## Why SciERC?

`FB15k-237`, `WN18RR` and `OGB` are link-prediction benchmarks over fixed
graphs; they do not measure whether a system can build a graph from papers.
SciERC is the standard entity/relation extraction benchmark for **scientific
knowledge-graph construction**, which is the task LitGraphAgent performs.

## What is measured

SciERC provides 500 abstracts annotated with scientific entities (Task, Method,
Metric, Material, Generic, OtherScientificTerm), typed relations and
coreference clusters. LitGraphAgent is a literature-to-graph pipeline, not a
span tagger or a relation classifier, so the harness scores the parts it
actually produces:

- **concept nodes** — concepts extracted from each abstract compared with the
  gold SciERC entity mentions;
- **paper → concept edges** — the bipartite edges that the vault graph is built
  from.

Two matching modes are reported:

- **exact** — lowercased, singularised, punctuation-free string equality;
- **relaxed** — token Jaccard overlap ≥ 0.5, which tolerates modifiers such as
  `word sense disambiguation (WSD) systems` vs `word sense disambiguation`.

Typed SciERC relations are **not** scored: LitGraphAgent does not predict
SciERC relation types. Reporting a relation F1 would be misleading.

## Reproduce

```bash
# 1. Download the raw annotations (about 3.3 MB)
curl -L -o sciERC_raw.tar.gz https://nlp.cs.washington.edu/sciIE/data/sciERC_raw.tar.gz
tar -xzf sciERC_raw.tar.gz

# 2. Run the benchmark against a local OpenAI-compatible endpoint
python benchmarks/scierc_benchmark.py \
  --data-dir ./raw_data \
  --limit 20 \
  --seed 42 \
  --model qwen2.5:3b \
  --base-url http://localhost:11434/v1 \
  --output benchmarks/results/scierc.json
```

Extraction is checkpointed to a JSONL file next to the output, so an interrupted
run resumes without repeating model calls. Failed abstracts are recorded in the
result's `failures` field instead of aborting the whole benchmark; the default
per-request timeout is 600 s because local reasoning models can be slow. The committed result was produced
with `seed=42`, `limit=20`, and the local `qwen2.5:3b` model through Ollama.

## Results

Committed run: `qwen2.5:3b` via Ollama, 20 abstracts, `seed=42`, no failed
abstracts.

| Signal | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Concept nodes — exact | 0.538 | 0.254 | 0.345 |
| Concept nodes — relaxed | 0.723 | 0.341 | 0.464 |
| Paper → concept edges — relaxed | 0.723 | 0.341 | 0.464 |
| Content entities only — exact | 0.521 | 0.297 | 0.378 |
| Content entities only — relaxed | 0.706 | 0.402 | **0.512** |

The extractor produced 5.95 concepts per abstract against 12.6 unique gold
mentions. The gap is driven by the pipeline's per-paper concept budget and by
normalisation: LitGraphAgent returns canonical concepts rather than copying
annotated spans, so exact match is a lower bound. The paper→concept edge row is
the bipartite projection of the same matches.

Raw result: [`results/scierc_qwen2.5-3b.json`](results/scierc_qwen2.5-3b.json).

## Interpreting the numbers

- The benchmark uses the production `PromptAgent.synthesize_paper` call, so the
  numbers include the pipeline's normal concept selection and JSON parsing.
- Gold items are unique entity mentions per abstract; duplicate mentions are
  collapsed to avoid penalising a concept that is mentioned twice.
- SciERC abstracts are short and cover many AI subfields. A 20-abstract sample
  is enough to catch regressions, not to claim state-of-the-art extraction.
- The pipeline intentionally caps concepts per paper
  (`MAX_CONCEPTS_PER_PAPER`, default 8), so recall is bounded by that budget.
- SciERC raw files contain abstracts only; the paper ID is used as the title
  placeholder in the extraction prompt.
- LLM sampling is not deterministic; the reported numbers are one run with
  `temperature=0.2` (the production setting), not an average over seeds.
