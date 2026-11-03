# 🕸️ LitGraphAgent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Obsidian Ready](https://img.shields.io/badge/Obsidian-Knowledge%20Graph-purple.svg)](https://obsidian.md/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: Pytest](https://img.shields.io/badge/tests-passing-brightgreen.svg)](tests/)

> **Autonomous Literature Research Agent that turns raw papers, preprints, and web sources into structured, interactive Obsidian Knowledge Graphs with scientometric ranking, elbow cutoff, publication-ready bibliographies, and a five-role agent team.**

---

## 🌟 Key Features

- 🤖 **Agent team architecture:** five specialist agents (Lead, Graph, Retrieval, QA, LLM) communicate through an explicit `AgentBus`; every pipeline step is a routed message.
- 🔍 **Iterative adaptive search:** recursively queries **arXiv** and **Semantic Scholar** (with a web fallback), generating targeted sub-queries until the paper quota is met.
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

The project is organized around the five roles below. Each role owns a concrete agent and a set of modules; the Lead agent coordinates the others through the message bus.

| Role | Owner | Agent | Responsibility |
| --- | --- | --- | --- |
| **Lead AI Engineer** | Иван Холодило ([@Icold21](https://github.com/Icold21)) | `LeadAIAgent` (`LiteratureAgent`) | End-to-end architecture, orchestration, agent bus, CLI, persistence |
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
                            AgentBus (message log → _Agent_Activity.md)
                                            │
  User ──► LeadAIAgent (LiteratureAgent) ───┼──────────────────────────────────┐
                │                           │                                  │
                ├─► RetrievalAgent ─────────┤ search / citations / PDF pages   │
                │      └─► PromptAgent ─────┘ (asks for next search queries)   │
                │                                                              │
                ├─► PromptAgent ────────────► validate / summarize / define    │
                │                                                              │
                ├─► GraphAgent ─────────────► canonicalize / rebuild / flush   │
                │                                                              │
                └─► EvaluationAgent ────────► audit vault + state ─────────────┘
```

---

## 🏗️ Pipeline

```
User Directive (topic, requirements, format, quota, --deep)
        │
        ▼
LeadAIAgent ──► RetrievalAgent: search + deduplicate + pre-rank
        │
        ▼
LeadAIAgent ──► PromptAgent: consolidated validation (topic + requirements)
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
```

Additional flags: `--no-cache`, `--no-elbow`, `--verbose`, `--version`.

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

The QA agent validates:

- unresolved wikilinks and orphan notes;
- required YAML frontmatter per note type;
- duplicate note names and duplicate graph edges;
- concept → paper → concept hub integrity;
- non-empty bibliographies and overviews;
- canonical concept coverage.

CI runs the full suite on Python 3.10–3.13 and fails on lint errors.

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
