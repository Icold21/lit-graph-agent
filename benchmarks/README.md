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
  --model qwen3.5:4b \
  --base-url http://localhost:11434/v1 \
  --output benchmarks/results/scierc_qwen3.5-4b.json
```

Extraction is checkpointed to a JSONL file next to the output, so an interrupted
run resumes without repeating model calls. Failed abstracts are recorded in the
result's `failures` field instead of aborting the whole benchmark; the default
per-request timeout is 600 s because local reasoning models can be slow. Both
committed results were produced with `seed=42`, `limit=20`, and local Ollama
models.

## Results

Two committed runs, each on 20 abstracts with `seed=42` and no failed abstracts.

| Model | Signal | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: |
| `qwen2.5:3b` | Concept nodes — exact | 0.538 | 0.254 | 0.345 |
| `qwen2.5:3b` | Concept nodes — relaxed | 0.723 | 0.341 | 0.464 |
| `qwen2.5:3b` | Paper → concept edges — relaxed | 0.723 | 0.341 | 0.464 |
| `qwen2.5:3b` | Content entities only — exact | 0.521 | 0.297 | 0.378 |
| `qwen2.5:3b` | Content entities only — relaxed | 0.706 | 0.402 | 0.512 |
| `qwen3.5:4b` | Concept nodes — exact | 0.544 | 0.345 | 0.422 |
| `qwen3.5:4b` | Concept nodes — relaxed | 0.750 | 0.476 | 0.583 |
| `qwen3.5:4b` | Paper → concept edges — relaxed | 0.750 | 0.476 | 0.583 |
| `qwen3.5:4b` | Content entities only — exact | 0.525 | 0.402 | 0.455 |
| `qwen3.5:4b` | Content entities only — relaxed | 0.725 | 0.555 | **0.629** |

The extractors produced 5.95 (`qwen2.5:3b`) and 8.0 (`qwen3.5:4b`) concepts per
abstract against 12.6 unique gold mentions. The gap is driven by the pipeline's
per-paper concept budget and by normalisation: LitGraphAgent returns canonical
concepts rather than copying annotated spans, so exact match is a lower bound.
The paper→concept edge row is the bipartite projection of the same matches.

The `qwen3.5:4b` row uses the 6–8 concept synthesis prompt. The earlier prompt
scored 0.349 exact / 0.501 relaxed / 0.549 content relaxed F1; the new prompt
adds +0.073 / +0.082 / +0.080 F1 respectively.

## Reference points

| Reference point | Exact F1 | Relaxed F1 | Content relaxed F1 | What it means |
| --- | ---: | ---: | ---: | --- |
| Empty prediction | 0.000 | 0.000 | 0.000 | lower bound: no concepts extracted |
| `qwen2.5:3b` | 0.345 | 0.464 | 0.512 | smaller model, same 20 abstracts and seed |
| `qwen3.5:4b` (prompt v1) | 0.349 | 0.501 | 0.549 | earlier prompt, kept for comparison |
| `qwen3.5:4b` (prompt v2) | 0.422 | 0.583 | 0.629 | current 6–8 concept prompt |
| Gold oracle | 1.000 | 1.000 | 1.000 | upper bound: every gold mention is returned |
| SciERC SOTA | 73.4 entity F1 | 56.9 relation F1 | 44.3 strict relation F1 | SURE, COLING 2025; span NER/RE, a different task |

The SOTA row is intentionally separate: it scores entity and relation spans with
the official SciERC protocol, while this harness scores canonical concept nodes
and paper→concept edges. Do not read it as a direct leaderboard comparison.

The `qwen3.5:4b` prompt-v2 run took 3571.0 s in total (about 179 s per abstract);
the earlier prompt took 1836.9 s; `qwen2.5:3b` took 252.7 s.

Raw results: [`results/scierc_qwen2.5-3b.json`](results/scierc_qwen2.5-3b.json),
[`results/scierc_qwen3.5-4b.json`](results/scierc_qwen3.5-4b.json),
[`results/scierc_qwen3.5-4b-prompt8.json`](results/scierc_qwen3.5-4b-prompt8.json).

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
