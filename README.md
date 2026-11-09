# 🕸️ LitGraphAgent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Obsidian Ready](https://img.shields.io/badge/Obsidian-Knowledge%20Graph-purple.svg)](https://obsidian.md/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: Pytest](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

> Autonomous literature research agent that turns papers, preprints and web
> sources into a structured, interactive Obsidian knowledge graph with
> scientometric ranking, elbow cutoff, publication-ready bibliographies and a
> five-role agent team.

## 📊 Benchmark: SciERC

The graph-construction core is evaluated on [SciERC](https://nlp.cs.washington.edu/sciIE/),
the standard benchmark for scientific knowledge-graph construction (500
abstracts, 6 entity types, EMNLP 2018). The production
`PromptAgent.synthesize_paper` step extracts concepts from **20 abstracts**;
they are compared with gold SciERC entity mentions.

| Model | Graph signal | Precision | Recall | F1 |
| --- | --- | ---: | ---: | ---: |
| `qwen2.5:3b` | Concept nodes, exact | 0.538 | 0.254 | 0.345 |
| `qwen2.5:3b` | Concept nodes, relaxed | 0.723 | 0.341 | 0.464 |
| `qwen2.5:3b` | Content entities only, relaxed | 0.706 | 0.402 | 0.512 |
| `qwen3.5:4b` | Concept nodes, exact | 0.544 | 0.345 | 0.422 |
| `qwen3.5:4b` | Concept nodes, relaxed | 0.750 | 0.476 | 0.583 |
| `qwen3.5:4b` | Content entities only, relaxed | 0.725 | 0.555 | **0.629** |

**Setup:** both models via Ollama, 20 abstracts (`seed=42`), zero failures.
The models produced 5.95 and 8.0 concepts per abstract against 12.6 gold
mentions. Exact means normalised string equality; relaxed means token Jaccard
overlap of at least 0.5. Paper to concept edges are the bipartite projection of
the same node matches, so edge scores equal relaxed concept scores. Typed
relations are not scored because the pipeline does not predict SciERC relation
types. This is a regression sample, not a state-of-the-art claim.

The `qwen3.5:4b` run uses the 6–8 concept synthesis prompt. The previous prompt
scored 0.349 exact / 0.501 relaxed / 0.549 content relaxed F1; the new one adds
+0.073 / +0.082 / +0.080 F1 respectively, at the cost of longer runs (~59 min
instead of ~31 min for 20 abstracts).

**Reference points.** We compare against the smaller `qwen2.5:3b` on the same
20 abstracts (exact F1 0.345, relaxed 0.464, content relaxed 0.512), an empty
prediction (F1 = 0) and the gold oracle (F1 = 1.0). SciERC literature SOTA
(entity F1 73.4, relation F1 56.9, strict relation F1 44.3) is shown only as an
external context: it scores span-level NER/RE, not canonical concept extraction,
so the numbers are not directly comparable.

Protocol and reproduction: [benchmarks/README.md](benchmarks/README.md).
Harness: [benchmarks/scierc_benchmark.py](benchmarks/scierc_benchmark.py).
Raw results: [qwen2.5:3b](benchmarks/results/scierc_qwen2.5-3b.json),
[qwen3.5:4b baseline](benchmarks/results/scierc_qwen3.5-4b.json),
[qwen3.5:4b prompt v2](benchmarks/results/scierc_qwen3.5-4b-prompt8.json).

## Key capabilities

- **Agent team architecture.** Five specialist agents (Lead, Graph, Retrieval,
  QA, LLM) run as nodes of a LangGraph `StateGraph`; the Lead compiles the
  workflow and each hand-off is an explicit edge with a recorded activity event.
- **Model-driven search-engine routing.** The LLM reads a catalog of engine
  descriptions (Semantic Scholar, arXiv, open web) and selects the
  primary/fallback set that fits the task instead of querying everything.
- **Iterative adaptive search.** Queries the selected engines, adds a fallback
  round when results are thin, and generates targeted sub-queries until the
  paper quota is met.
- **Consolidated validation.** A single LLM pass checks topic relevance and
  strict requirements simultaneously.
- **Scientometric ranking and elbow cutoff.** Ranks candidates by citation
  velocity, influential-citation ratio and log-scaled impact, then prunes the
  low-impact tail with a curvature-based elbow heuristic.
- **Concept canonicalization.** Plural forms, casing and parenthetical acronyms
  are merged (`GNNs` becomes `Graph Neural Networks`), and one-off noise
  concepts are filtered with `MIN_CONCEPT_PAPERS`.
- **Obsidian-native graph.** Atomic notes, bidirectional `[[wikilinks]]`,
  concept hubs, typed citation edges and lightweight stubs for external
  references, so links never dangle.
- **Persistent incremental updates.** The full research state is saved to
  `_state.json`, so `--update` works across separate CLI invocations and
  preserves existing definitions.
- **Resilient networking.** Retries with backoff for Semantic Scholar rate
  limits, a disk cache for searches and citations, and optional LLM response
  caching.
- **Publication-ready bibliography.** `Formatted_Bibliography.md`, an
  interactive `_Bibliography.md` and `references.bib` for BibTeX workflows.
  Formatting is batched and has deterministic fallbacks.
- **Model-agnostic LLM layer.** DeepSeek, OpenAI, Groq, OpenRouter, Ollama,
  vLLM or any OpenAI-compatible endpoint via `.env`.

## Agent team

The project is organized around five roles. Each role owns a concrete agent and
a set of modules; the Lead agent compiles a LangGraph `StateGraph` that routes
the pipeline to the specialists.

| Role | Owner | Agent | Responsibility |
| --- | --- | --- | --- |
| Lead AI Engineer | Иван Холодило ([@Icold21](https://github.com/Icold21)) | `LeadAIAgent` (`LiteratureAgent`) | End-to-end architecture, LangGraph workflow, CLI, persistence |
| Graph & Knowledge Engineer | Вадим Лялькин ([@Geniy_molodec](https://github.com/Geniy_molodec)) | `GraphAgent` | Graph ontology, `[[wikilinks]]`, concept canonicalization, Obsidian structure |
| Data / IR Engineer | Нодар Чигладзе ([@NodarNeo](https://github.com/NodarNeo)) | `RetrievalAgent` | arXiv, Semantic Scholar and web APIs, search ranking, PDF retrieval, cache |
| QA / Evaluation Engineer | Давид Чигладзе ([@David52228](https://github.com/David52228)) | `EvaluationAgent` | Quality bench, connectivity and format validation, CI |
| LLM Engineer | Илья Синко ([@mang1ch5](https://github.com/mang1ch5)) | `PromptAgent` | Prompt engineering, abstract criteria filtering, synthesis, bibliographies |

```bash
litgraph --team   # show the role/agent ownership table
```

Detailed contribution history: [CONTRIBUTORS.md](CONTRIBUTORS.md).
Agent protocol: [docs/AGENT_TEAM.md](docs/AGENT_TEAM.md).
Ownership rules: [.github/CODEOWNERS](.github/CODEOWNERS).

### How the agents interact

```text
                    LangGraph StateGraph (activity -> _Agent_Activity.md)
                                        |
  User --> LeadAIAgent (LiteratureAgent) +----------------------------------+
                |                         |                                  |
                +-> RetrievalAgent -------+ plan / search / citations / PDFs |
                |      +-> PromptAgent ---+ (LLM picks search engines)       |
                |                                                            |
                +-> PromptAgent ----------> validate / summarize / define    |
                |                                                            |
                +-> GraphAgent -----------> canonicalize / rebuild / flush   |
                |                                                            |
                +-> EvaluationAgent ------> audit vault + state -------------+
```

## Pipeline

```text
User directive (topic, requirements, format, quota, --deep)
        |
        v
LangGraph nodes: plan_request --> PromptAgent: choose engines from descriptions
        |                         +-> SearchRouter: validate and persist plan
        v
RetrievalAgent: search selected engines (+ fallback if the result set is thin)
        |
        v
PromptAgent: consolidated validation (topic + requirements)
        |
        v
Scientometric ranking + elbow cutoff (MIN_PAPERS ... MAX_PAPERS)
        |
        v
RetrievalAgent: citation expansion (+ page-level PDF scan in --deep)
        |
        v
PromptAgent: paper summaries, batched concept definitions, bibliography,
             typed cross-links, master literature review
        |
        v
GraphAgent: concept canonicalization, node weights, wikilinks, Obsidian notes
        |
        v
EvaluationAgent: connectivity / format / state audit --> QA report
```

## Installation

```bash
git clone https://github.com/Icold21/LitGraphAgent.git
cd LitGraphAgent
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -e ".[dev]"
```

`pypdf` is a core dependency (required for `--deep`), not an optional extra.

## Configuration

Create `.env` in the project root:

```bash
# Universal LLM (any OpenAI-compatible endpoint)
LLM_API_KEY=sk-your-key
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-chat

# Optional networking
LLM_TIMEOUT=90
LLM_MAX_RETRIES=3
LLM_CACHE_ENABLED=false      # cache LLM responses by prompt hash
SEMANTIC_SCHOLAR_API_KEY=
HTTP_TIMEOUT=15
HTTP_MAX_RETRIES=3
CACHE_ENABLED=true
CACHE_TTL_HOURS=168

# Vault storage (relative paths resolve against the project root)
DEFAULT_VAULTS_DIR=./vaults

# Scientometric limits
MAX_PAPERS_PER_RUN=5
MIN_PAPERS_PER_RUN=2
MAX_SEARCH_CANDIDATES=15
CANDIDATE_EVAL_LIMIT=8
CITATION_EXPANSION_LIMIT=2
ENABLE_ELBOW_CUTOFF=true

# Dynamic search-engine routing
SEARCH_ROUTER_ENABLED=true
SEARCH_ROUTER_MAX_PRIMARY=2
SEARCH_FALLBACK_MIN_RESULTS=5
# SEARCH_ENGINES_OVERRIDE=arxiv,web   # bypass the model and pin engines

# Knowledge-graph quality
MIN_CONCEPT_PAPERS=2        # drop concepts that appear in fewer papers
MAX_CONCEPTS_PER_PAPER=8
CONCEPT_BATCH_SIZE=12       # concepts per LLM response (avoids truncation)
BIBLIOGRAPHY_BATCH_SIZE=20
```

Profiles:

```bash
# Local Ollama
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b

# Groq
LLM_API_KEY=gsk_...
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.3-70b-versatile
```

## Usage

```bash
# Create a new knowledge base
litgraph \
  --id "transformer_circuits" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --requirements "Peer-reviewed or high-impact preprints published after 2021" \
  --format "APA 7th" \
  --max-papers 5

# Expand an existing base (works across separate CLI runs via _state.json)
litgraph \
  --id "transformer_circuits" \
  --update "Sparse Autoencoders and Superposition in Language Models" \
  --max-papers 3

# Deep mode: download open-access PDFs and cite concept mentions by page
litgraph --id "transformer_circuits" --update "Induction heads" --deep

# Inspect, audit or remove bases
litgraph --list
litgraph --check --id "transformer_circuits"
litgraph --delete --id "transformer_circuits"

# Team and agent ownership
litgraph --team

# Inspect the search-engine catalog the model chooses from
litgraph --tools

# Model picks the engines automatically (default); these flags override it
litgraph --id "transformer_circuits" --update "Induction heads" --engines arxiv,web
litgraph --id "transformer_circuits" --update "Induction heads" --no-router
```

Additional flags: `--no-cache`, `--no-elbow`, `--no-router`, `--engines`,
`--verbose`, `--version`.

## Obsidian integration

1. Open **Obsidian**, then **Open folder as vault**.
2. Select `./vaults/transformer_circuits`.
3. Press `Ctrl/Cmd + G` for the graph view.

The graph preset is installed on first use and merged, not overwritten, so
manual graph settings survive later runs.

### Generated vault structure

```text
vaults/transformer_circuits/
├── Formatted_Bibliography.md    # clean copy-paste bibliography
├── _Bibliography.md             # interactive bibliography with [[links]]
├── _Overview_Synthesis.md       # master review + index + typed citation edges
├── _Agent_Activity.md           # which agent did what (hand-off log)
├── _state.json                  # persistent research state (incremental updates)
├── references.bib               # generated for BibTeX format
├── Sources/
│   ├── <paper title>.md         # atomic literature notes
│   └── <external reference>.md  # lightweight citation stubs
└── Concepts/                    # canonical concept hubs
```

## 🧪 Quality and testing

```bash
pytest -q
ruff check lit_graph tests
litgraph --check --id your_base
```

The Retrieval agent asks the LLM agent to choose a search strategy from the
engine catalog before each run. The decision (primary, fallback, reason,
source) is printed, recorded in the graph's `activity` channel and persisted in
`_state.json` as `search_plan`. Per-paper provenance is stored as
`source_engine` in the note frontmatter.

The QA agent validates:

- unresolved wikilinks and orphan notes;
- required YAML frontmatter per note type;
- duplicate note names and duplicate graph edges;
- concept to paper to concept hub integrity;
- non-empty bibliographies and overviews;
- canonical concept coverage.

CI runs the full suite on Python 3.10 to 3.13 and fails on lint errors.

The graph-construction core is additionally benchmarked on **SciERC**; see
[benchmarks/README.md](benchmarks/README.md) for the protocol and the
reproducible command.

Project documents:

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — components, workflows and data flow;
- [docs/RETRIEVAL.md](docs/RETRIEVAL.md) — search routing, candidate collection and ranking;
- [docs/GRAPH_MODEL.md](docs/GRAPH_MODEL.md) — vault ontology and concept canonicalization;
- [docs/LLM_LAYER.md](docs/LLM_LAYER.md) — prompts, validation and synthesis;
- [docs/KG_METRICS.md](docs/KG_METRICS.md) — standard metrics for KG benchmarks and what to report;
- [docs/LitGraphAgent_Handbook.pdf](docs/LitGraphAgent_Handbook.pdf) — full 60+ page technical handbook for newcomers (architecture, agents, metrics, runbook);
- [docs/kp2/README.md](docs/kp2/README.md) — milestone 2 report, slides, demo script and contribution evidence.

## Contributors

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for the detailed, mapped list of
contributions.

- **Иван Холодило** ([@Icold21](https://github.com/Icold21)): Lead AI Engineer
- **Вадим Лялькин** ([@Geniy_molodec](https://github.com/Geniy_molodec)): Graph & Knowledge Engineer
- **Нодар Чигладзе** ([@NodarNeo](https://github.com/NodarNeo)): Data / IR Engineer
- **Давид Чигладзе** ([@David52228](https://github.com/David52228)): QA / Evaluation Engineer
- **Илья Синко** ([@mang1ch5](https://github.com/mang1ch5)): LLM Engineer

## License

Distributed under the **MIT License**. See [LICENSE](LICENSE).
