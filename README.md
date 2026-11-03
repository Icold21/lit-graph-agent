# 🕸️ LitGraphAgent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Obsidian Ready](https://img.shields.io/badge/Obsidian-Knowledge%20Graph-purple.svg)](https://obsidian.md/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: Pytest](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

> **Autonomous Literature Research Agent that turns raw papers, preprints, and web sources into structured, interactive Obsidian Knowledge Graphs with scientometric ranking, elbow cutoff, publication-ready bibliographies, and a five-role agent team.**

---

## 📊 Benchmark: SciERC

The graph-construction core is evaluated on [SciERC](https://nlp.cs.washington.edu/sciIE/), the standard benchmark for scientific knowledge-graph construction (500 abstracts, 6 entity types, EMNLP 2018). The production `PromptAgent.synthesize_paper` step extracts concepts from **20 abstracts**; they are compared with gold SciERC entity mentions.

| Graph signal | Precision | Recall | F1 |
| --- | ---: | ---: | ---: |
| Concept nodes — exact match | 0.538 | 0.254 | 0.345 |
| Concept nodes — relaxed match | 0.723 | 0.341 | 0.464 |
| Paper → concept edges — relaxed | 0.723 | 0.341 | 0.464 |
| Content entities only — relaxed | 0.706 | 0.402 | **0.512** |

**Setup:** `qwen2.5:3b` via Ollama · 20 abstracts (`seed=42`) · 5.95 concepts per abstract vs 12.6 gold mentions. Exact = normalised string equality; relaxed = token Jaccard ≥ 0.5. The edge row is the bipartite projection of the same node matches. Typed relations are not scored because the pipeline does not predict SciERC relation types. This is a regression sample, not a state-of-the-art claim. [Protocol & reproduction](benchmarks/README.md) · [script](benchmarks/scierc_benchmark.py) · [raw JSON](benchmarks/results/scierc_qwen2.5-3b.json).

---

## 🌟 Key Features

- 🤖 **Agent team architecture:** five specialist agents (Lead, Graph, Retrieval, QA, LLM) run as nodes of a LangGraph `StateGraph`; the Lead compiles the workflow and each hand-off is an explicit edge with a recorded activity event.
- 🧭 **Model-driven search-engine routing:** the LLM reads a catalog of engine descriptions (Semantic Scholar, arXiv, open web) and picks the primary/fallback set that fits the task, instead of blindly querying everything.
- 🔍 **Iterative adaptive search:** queries the model-selected engines (**Semantic Scholar / arXiv / open web**), adds a fallback round when results are thin, and generates targeted sub-queries until the paper quota is met.
- ⚡ **Fast consolidated validation:** one LLM pass checks topic relevance and strict requirements simultaneously.
- 📐 **Scientometric ranking & elbow cutoff:** ranks candidates by citation velocity, influential-citation ratio and log-scaled impact, then prunes the low-impact tail with a curvature-based elbow (Kneedle-style) heuristic.
- 🧹 **Concept canonicalization:** plural forms, casing and parenthetical acronyms (`GNNs` → `Graph Neural Networks`) are merged, and one-off noise concepts are filtered (`MIN_CONCEPT_PAPERS`).
- 🕸️ **Obsidian-native graph:** atomic notes, bidirectional `[[wikilinks]]`, concept hubs, typed citation edges, and lightweight stubs for external references so links never dangle.
- 🔁 **Persistent incremental updates:** the full research state is saved to `_state.json`, so `--update` works across separate CLI invocations and preserves existing definitions.
- 💾 **Resilient networking:** retries with backoff for Semantic Scholar rate limits, a disk cache for searches/citations, and optional LLM response caching.
- 📄 **Publication-ready bibliography:** `Formatted_Bibliography.md`, interactive `_Bibliography.md`, and `references.bib` for BibTeX workflows. Formatting is batched and has deterministic fallbacks.
- 🔌 **Model-agnostic LLM layer:** DeepSeek, OpenAI, Groq, OpenRouter, Ollama, vLLM or any OpenAI-compatible endpoint via `.env`.

---

## 👥 Agent Team & Zones of Responsibility

The project is organized around the five roles below. Each role owns a concrete agent and a set of modules; the Lead agent compiles a LangGraph `StateGraph` that routes the pipeline to the specialists.

| Role | Owner | Agent | Responsibility |
| --- | --- | --- | --- |
| **Lead AI Engineer** | Иван Холодило ([@Icold21](https://github.com/Icold21)) | `LeadAIAgent` (`LiteratureAgent`) | End-to-end architecture, LangGraph workflow, CLI, persistence |
| **Graph & Knowledge Engineer** | Вадим Лялькин ([@Geniy_molodec](https://github.com/Geniy_molodec)) | `GraphAgent` | Graph ontology, `[[wikilinks]]`, concept canonicalization, Obsidian structure |
| **Data / IR Engineer** | Нодар Чигладзе ([@NodarNeo](https://github.com/NodarNeo)) | `RetrievalAgent` | arXiv / Semantic Scholar / web APIs, search ranking, PDF retrieval, cache |
| **QA / Evaluation Engineer** | Давид Чигладзе ([@David52228](https://github.com/David52228)) | `EvaluationAgent` | Quality bench, connectivity and format validation, CI |
| **LLM Engineer** | Илья Синко ([@mang1ch5](https://github.com/mang1ch5)) | `PromptAgent` | Prompt engineering, abstract criteria filtering, synthesis and bibliographies |

```bash
litgraph --team   # show the role/agent ownership table
```

Detailed contribution history: [CONTRIBUTORS.md](CONTRIBUTORS.md). Agent protocol: [docs/AGENT_TEAM.md](docs/AGENT_TEAM.md). Ownership rules: [.github/CODEOWNERS](.github/CODEOWNERS).

### How the agents interact

```
                    LangGraph StateGraph (activity → _Agent_Activity.md)
                                        │
  User ──► LeadAIAgent (LiteratureAgent) ─┼──────────────────────────────────┐
                │                         │                                  │
                ├─► RetrievalAgent ───────┤ plan / search / citations / PDFs │
                │      └─► PromptAgent ───┘ (LLM picks search engines)        │
                │                                                            │
                ├─► PromptAgent ──────────► validate / summarize / define     │
                │                                                            │
                ├─► GraphAgent ───────────► canonicalize / rebuild / flush    │
                │                                                            │
                └─► EvaluationAgent ──────► audit vault + state ──────────────┘
```

---

## 🏗️ Pipeline

```
User Directive (topic, requirements, format, quota, --deep)
        │
        ▼
LangGraph nodes: plan_request ──► PromptAgent: choose engines from descriptions
        │                         └─► SearchRouter: validate + persist plan
        ▼
RetrievalAgent: search selected engines (+ fallback if the result set is thin)
        │
        ▼
PromptAgent: consolidated validation (topic + requirements)
        │
        ▼
Scientometric ranking + elbow cutoff (MIN_PAPERS … MAX_PAPERS)
        │
        ▼
RetrievalAgent: citation expansion (+ page-level PDF scan in --deep)
        │
        ▼
PromptAgent: paper summaries, batched concept definitions, bibliography,
             typed cross-links, master literature review
        │
        ▼
GraphAgent: concept canonicalization, node weights, wikilinks, Obsidian notes
        │
        ▼
EvaluationAgent: connectivity/format/state audit ──► QA report
```

---

## 📦 Installation

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

---

## ⚙️ Configuration (`.env`)

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

---

## 🚀 Usage

```bash
# Create a new knowledge base
litgraph \
  --id "transformer_circuits" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --requirements "Peer-reviewed or high-impact preprints published after 2021" \
  --format "APA 7th" \
  --max-papers 5

# Expand an existing base (works across separate CLI runs thanks to _state.json)
litgraph \
  --id "transformer_circuits" \
  --update "Sparse Autoencoders and Superposition in Language Models" \
  --max-papers 3

# Deep mode: download open-access PDFs and cite concept mentions by page
litgraph --id "transformer_circuits" --update "Induction heads" --deep

# Inspect, audit, or remove bases
litgraph --list
litgraph --check --id "transformer_circuits"
litgraph --delete --id "transformer_circuits"

# Team / agent ownership
litgraph --team

# Inspect the search-engine catalog the model chooses from
litgraph --tools

# Model picks the engines automatically (default); these flags override it
litgraph --id "transformer_circuits" --update "Induction heads" --engines arxiv,web
litgraph --id "transformer_circuits" --update "Induction heads" --no-router
```

Additional flags: `--no-cache`, `--no-elbow`, `--no-router`, `--engines`, `--verbose`, `--version`.

---

## 📖 Exploring in Obsidian

1. Open **Obsidian** → **Open folder as vault**.
2. Select `./vaults/transformer_circuits`.
3. Press `Ctrl/Cmd + G` for the graph view.

The graph preset is installed on first use and **merged, not overwritten**, so your manual graph settings survive later runs.

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

---

## 🧪 Quality & Testing

```bash
pytest -q
ruff check lit_graph tests
litgraph --check --id your_base
```

The Retrieval agent asks the LLM agent to choose a search strategy from the
engine catalog before each run; the decision (primary/fallback/reason/source)
is printed, recorded in the graph's `activity` channel and persisted in
`_state.json` as `search_plan`. Per-paper provenance is stored as
`source_engine` in the note frontmatter.

The QA agent validates:

- unresolved wikilinks and orphan notes;
- required YAML frontmatter per note type;
- duplicate note names and duplicate graph edges;
- concept → paper → concept hub integrity;
- non-empty bibliographies and overviews;
- canonical concept coverage.

CI runs the full suite on Python 3.10–3.13 and fails on lint errors.

The graph-construction core is additionally benchmarked on **SciERC**; see
[benchmarks/README.md](benchmarks/README.md) for the protocol and the
reproducible command.

---

## 👥 Contributors

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for the detailed, mapped list of contributions.

- **Иван Холодило** ([@Icold21](https://github.com/Icold21)) — Lead AI Engineer
- **Вадим Лялькин** ([@Geniy_molodec](https://github.com/Geniy_molodec)) — Graph & Knowledge Engineer
- **Нодар Чигладзе** ([@NodarNeo](https://github.com/NodarNeo)) — Data / IR Engineer
- **Давид Чигладзе** ([@David52228](https://github.com/David52228)) — QA / Evaluation Engineer
- **Илья Синко** ([@mang1ch5](https://github.com/mang1ch5)) — LLM Engineer

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE).
