# 🕸️ LitGraphAgent

[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Obsidian Ready](https://img.shields.io/badge/Obsidian-Knowledge%20Graph-purple.svg)](https://obsidian.md/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)

> **Autonomous Literature Research Agent that turns unorganized papers and web sources into structured, interactive Obsidian Knowledge Graphs with scientometric ranking and publication-ready bibliographies.**

---

## 🌟 Key Features

- 🔍 **Adaptive Search Loop:** Automatically crawls academic engines (**arXiv**, **Semantic Scholar**) and web sources, generating iterative sub-queries until the target paper count is reached.
- 🛡️ **3-Stage Scientific Validation:** Evaluates candidates for topic relevance, strict constraints (publication year, peer-review venue, methodology), and novelty/redundancy.
- 📐 **Scientometric Ranking & Elbow Cutoff:** Uses citation velocity ($V = \frac{C}{\text{Age}}$) and influential citation ratio ($R_{inf}$), applying the **Elbow / Kneedle Method** to mathematically discard low-impact papers.
- 🕸️ **Obsidian Knowledge Graph Native:** Creates atomic literature notes linked by bidirectional `[[wikilinks]]`, concept hubs, and cross-citation networks (`cites` / `cited_by`).
- 📄 **Dual-Layer Master Bibliography:**
  - `Formatted_Bibliography.md`: Clean, copy-paste ready literature list formatted strictly according to your target standard (**APA 7th, IEEE, Harvard, BibTeX, GOST**).
  - `_Bibliography.md`: Interactive Obsidian hub linked to local vault notes.
  - `references.bib`: Generated automatically when BibTeX is selected for LaTeX / Overleaf / Zotero workflows.
- 🔌 **Universal Model-Agnostic Engine:** Seamlessly switch between **Local Ollama** (Qwen 2.5, Llama 3.2), **DeepSeek**, **Groq**, **OpenAI**, or **OpenRouter** via `.env` without modifying Python code.
- ⚡ **Incremental Updates:** Expand existing research vaults with targeted directives without overwriting existing notes.

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
                │  (arXiv + S2 + Web Scraper) │    │  if candidates < target)
                └──────────────┬──────────────┘    │
                               │                   │
                ┌──────────────▼──────────────┐    │
                │ 3-Stage Consolidated LLM    │────┘
                │ Validation (Topic + Rules)  │
                └──────────────┬──────────────┘
                               │
                ┌──────────────▼──────────────┐
                │  Scientometric Ranking &    │
                │     Elbow Method Cutoff     │
                └──────────────┬──────────────┘
                               │
                ┌──────────────▼──────────────┐
                │  Citation Graph Expansion   │
                │   & Synthesis in English    │
                └──────────────┬──────────────┘
                               │
        ┌──────────────────────▼──────────────────────┐
        │          Obsidian Knowledge Vault           │
        │  ├── _Overview_Synthesis.md                 │
        │  ├── Formatted_Bibliography.md              │
        │  ├── _Bibliography.md (references.bib)      │
        │  ├── Sources/ (Atomic Literature Notes)     │
        │  └── Concepts/ (Concept Graph Hubs)         │
        └─────────────────────────────────────────────┘
```

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/lit-graph-agent.git
cd lit-graph-agent
```

### 2. Set up virtual environment
```bash
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS / Linux:
source .venv/bin/activate
```

### 3. Install in editable mode
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
# 🎯 Option C: Groq Cloud (Ultra Fast)
# ==============================================================================
# LLM_API_KEY=gsk_your-groq-key
# LLM_BASE_URL=https://api.groq.com/openai/v1
# LLM_MODEL=llama-3.3-70b-versatile

# ==============================================================================
# Vault & Search Parameters
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

### 1. Create a New Research Knowledge Base
Run `litgraph` directly from your terminal:

```bash
litgraph \
  --id "transformer_interpretability" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --requirements "Peer-reviewed or high-impact preprints published after 2021" \
  --format "APA 7th" \
  --max-papers 5
```

### 2. Incrementally Expand an Existing Base
Add new research depth or sub-topics without losing previous notes:

```bash
litgraph \
  --id "transformer_interpretability" \
  --topic "Mechanistic Interpretability and Induction Heads in Transformers" \
  --update "Sparse Autoencoders and Superposition in Language Models" \
  --max-papers 3
```

---

## 📖 Viewing in Obsidian

1. Open the **Obsidian** app.
2. Click **"Open folder as vault"**.
3. Select the generated directory: `./vaults/transformer_interpretability`.
4. Click **Graph view** (or press `Ctrl/Cmd + G`) to explore your interactive 3D knowledge graph!

### Generated Vault Structure
```text
vaults/transformer_interpretability/
├── Formatted_Bibliography.md    # Clean literature list (ready to copy into papers/theses)
├── _Bibliography.md             # Interactive Obsidian bibliography with [[links]]
├── _Overview_Synthesis.md       # Master executive review synthesized in English
├── references.bib               # (Generated if BibTeX format is chosen)
├── Sources/                     # Atomic notes for each paper
│   ├── In-context Learning and Induction Heads.md
│   ├── Toy Models of Superposition.md
│   └── ...
└── Concepts/                    # Conceptual graph hubs
    ├── Induction Heads.md
    ├── Sparse Autoencoders.md
    └── Superposition.md
```

---

## 🐍 Python API Usage

You can also use `LitGraphAgent` directly inside your Python scripts:

```python
from lit_graph import LitGraphAgent, UniversalLLMProvider, LiteratureManager
from lit_graph.search.engine import AcademicSearchEngine
from lit_graph.config import settings

# 1. Initialize universal provider
llm = UniversalLLMProvider(
    api_key=settings.llm_api_key,
    model_name=settings.llm_model,
    base_url=settings.llm_base_url
)

# 2. Initialize Agent
searcher = AcademicSearchEngine()
agent = LitGraphAgent(llm=llm, search_engine=searcher)
manager = LiteratureManager(root_vaults_dir="./vaults", agent=agent)

# 3. Create research vault
state = manager.create_base(
    base_id="quantum_ml",
    topic="Variational Quantum Algorithms for Optimization",
    requirements="Recent papers with empirical benchmarks",
    citation_format="IEEE",
    max_papers=5
)
```

---

## 🧪 Testing Suite

Run the unit and integration tests with `pytest`:

```bash
pytest
```

---

## 📄 License

Distributed under the **MIT License**. See `LICENSE` for more information.