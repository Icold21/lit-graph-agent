# 🕸️ LitGraphAgent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Obsidian Ready](https://img.shields.io/badge/Obsidian-Knowledge%20Graph-purple.svg)](https://obsidian.md/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Tests: Pytest](https://img.shields.io/badge/tests-passing-brightgreen.svg)](https://github.com/astral-sh/ruff)

> **Autonomous Literature Research Agent that turns raw papers, preprints, and web sources into structured, interactive Obsidian Knowledge Graphs with scientometric ranking, Elbow-method cutoff, and publication-ready bibliographies.**

---

## 🌟 Key Features

- 🔍 **Iterative Adaptive Search Loop:** Recursively crawls **arXiv** and **Semantic Scholar** (with web fallback), dynamically generating targeted sub-queries until the desired paper quota is fulfilled.
- ⚡ **Optimized Fast Validation:** Consolidated single-round LLM auditing (evaluates topic relevance + strict constraints in one pass), providing 5x speedups for local models like **Qwen 2.5 (3B)**.
- 📐 **Scientometric Ranking & Elbow Cutoff:** Ranks candidates by citation velocity ($V = \frac{C}{\text{Age}}$), influential citation ratio ($R_{inf}$), and log-scaled impact, applying the **Elbow / Kneedle Algorithm** to prune low-impact tails while respecting user-defined bounds (`MIN_PAPERS` to `MAX_PAPERS`).
- 🕸️ **Obsidian Knowledge Graph Native:** Creates atomic Markdown notes linked via bidirectional `[[wikilinks]]`, concept hub clusters, and cross-citation networks (`cites` / `cited_by`).
- 📄 **Publication-Ready Dual Bibliography:**
  - `Formatted_Bibliography.md`: Clean, standardized reference list formatted strictly according to your target standard (**APA 7th, IEEE, Harvard, BibTeX, GOST**) — ready for direct copy-pasting into theses or journal manuscripts.
  - `_Bibliography.md`: Interactive Obsidian master note with direct links to vault source notes.
  - `references.bib`: Generated automatically when BibTeX format is selected for **LaTeX / Overleaf / Zotero** workflows.
- 🔌 **Universal Model-Agnostic Engine:** Switch seamlessly between **Local Ollama** (Qwen 2.5, Llama 3.2), **DeepSeek**, **Groq**, **OpenAI**, or **OpenRouter** strictly via `.env` without modifying a single line of Python code.
- 🔄 **Incremental Graph Mutations:** Update and expand existing research bases with targeted sub-directives without overwriting untouched notes.

---

## 🏗️ Architecture & Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                      User Directive                         │
│       (Topic, Strict Requirements, Citation Format)         │
└──────────────────────────────┬──────────────────────────────┘
                               │
                ┌──────────────▼──────────────┐
                │   Adaptive Search Engine    │◄───┐ (Iterative sub-queries
                │  (arXiv + S2 + Web Scraper) │    │  until target quota)
                └──────────────┬──────────────┘    │
                               │                   │
                ┌──────────────▼──────────────┐    │
                │ Consolidated LLM Validation │────┘
                │  (Topic + Strict Criteria)  │
                └──────────────┬──────────────┘
                               │
                ┌──────────────▼──────────────┐
                │  Scientometric Ranking &    │
                │     Elbow Method Cutoff     │
                └──────────────┬──────────────┘
                               │
                ┌──────────────▼──────────────┐
                │  Citation Graph Expansion   │
                │   & English Synthesis       │
                └──────────────┬──────────────┘
                               │
        ┌──────────────────────▼──────────────────────┐
        │          Obsidian Knowledge Vault           │
        │  ├── Formatted_Bibliography.md (Clean copy) │
        │  ├── _Overview_Synthesis.md                 │
        │  ├── _Bibliography.md (references.bib)      │
        │  ├── Sources/ (Atomic Literature Notes)     │
        │  └── Concepts/ (Concept Graph Hubs)         │
        └─────────────────────────────────────────────┘
```

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/Icold21/LitGraphAgent.git
cd LitGraphAgent
```

### 2. Set up a virtual environment
```bash
python -m venv .venv

# On Windows:
.venv\Scripts\activate

# On macOS / Linux:
source .venv/bin/activate
```

### 3. Install in development mode
```bash
pip install -e .
```

---

## ⚙️ Configuration (`.env`)

Create a `.env` file in the project root:

```bash
# ==============================================================================
# 🎯 Option A: Local Ollama (100% Free, Zero Rate Limits, Runs Offline)
# ==============================================================================
LLM_API_KEY=ollama
LLM_BASE_URL=http://localhost:11434/v1
LLM_MODEL=qwen2.5:3b

# ==============================================================================
# 🎯 Option B: DeepSeek (High Intelligence & Affordable)
# ==============================================================================
# LLM_API_KEY=sk-your-deepseek-api-key
# LLM_BASE_URL=https://api.deepseek.com
# LLM_MODEL=deepseek-chat

# ==============================================================================
# 🎯 Option C: Groq Cloud (Ultra Fast Cloud Inference)
# ==============================================================================
# LLM_API_KEY=gsk_your-groq-key
# LLM_BASE_URL=https://api.groq.com/openai/v1
# LLM_MODEL=llama-3.3-70b-versatile

# ==============================================================================
# Vault Storage & Scientometric Limits
# ==============================================================================
SEMANTIC_SCHOLAR_API_KEY=
DEFAULT_VAULTS_DIR=./vaults
MAX_PAPERS_PER_RUN=5
MIN_PAPERS_PER_RUN=2
MAX_SEARCH_CANDIDATES=15
CITATION_EXPANSION_LIMIT=3
ENABLE_ELBOW_CUTOFF=true
```

---

## 🚀 Quickstart & Usage

### 1. Build a New Research Knowledge Base
Run `litgraph` directly from your terminal:

```bash
litgraph \
  --id "transformer_circuits" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --requirements "Peer-reviewed or high-impact preprints published after 2021" \
  --format "APA 7th" \
  --max-papers 5
```

### 2. Incrementally Expand an Existing Base
Add new research depth or sub-topics without losing previous notes:

```bash
litgraph \
  --id "transformer_circuits" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --update "Sparse Autoencoders and Superposition in Language Models" \
  --max-papers 3
```

---

## 📖 Exploring in Obsidian

1. Open the **Obsidian** app.
2. Click **"Open folder as vault"**.
3. Select the generated directory: `./vaults/transformer_circuits`.
4. Open the **Graph view** (`Ctrl/Cmd + G`) to explore your interactive 3D knowledge network!

### Generated Vault Structure
```text
vaults/transformer_circuits/
├── Formatted_Bibliography.md    # Pure literature list (clean copy for Word/LaTeX)
├── _Bibliography.md             # Interactive Obsidian bibliography with [[links]]
├── _Overview_Synthesis.md       # Master executive review synthesized in English
├── references.bib               # (Generated if BibTeX format is chosen)
├── Sources/                     # Atomic notes for each verified paper
│   ├── In-context Learning and Induction Heads.md
│   ├── Toy Models of Superposition.md
│   └── ...
└── Concepts/                    # Conceptual graph hubs
    ├── Induction Heads.md
    ├── Sparse Autoencoders.md
    └── Superposition.md
```

---

## 🧪 Testing Suite

Run the test suite with `pytest`:

```bash
pytest
```

---

## 👥 Contributors

Thanks to all the contributors who built and improved this project:

- [@Icold21](https://github.com/Icold21) (Project Lead)
- [@David200109](https://github.com/David200109)
- [@Geniy-molodec](https://github.com/Geniy-molodec)
- [@NodarChigladse](https://github.com/NodarChigladse)
- [@podorogn1k](https://github.com/podorogn1k)

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.