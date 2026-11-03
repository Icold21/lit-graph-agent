# Contributors & Role Ownership

This project is built as a five-role agent team. Each role owns a specialist
agent, a set of modules, and a clear part of the pipeline. The Lead agent
orchestrates every other agent through a LangGraph `StateGraph`
(`lit_graph/agent/workflow.py`).

## Team

| Role | Owner | GitHub | Agent |
| --- | --- | --- | --- |
| Lead AI Engineer | Иван Холодило | [@Icold21](https://github.com/Icold21) | `LeadAIAgent` (`LiteratureAgent`) |
| Graph & Knowledge Engineer | Вадим Лялькин | [@Geniy_molodec](https://github.com/Geniy_molodec) | `GraphAgent` |
| Data / IR Engineer | Нодар Чигладзе | [@NodarNeo](https://github.com/NodarNeo) | `RetrievalAgent` |
| QA / Evaluation Engineer | Давид Чигладзе | [@David52228](https://github.com/David52228) | `EvaluationAgent` |
| LLM Engineer | Илья Синко | [@mang1ch5](https://github.com/mang1ch5) | `PromptAgent` |

## What each role brought to the project

### Иван Холодило (@Icold21) — Lead AI Engineer

**Zone:** end-to-end architecture and module coordination.

- Designed the agent-team architecture: `LeadAIAgent` + LangGraph `StateGraph` + five role agents.
- Wrote the orchestration pipeline in `lit_graph/agent/core.py` (create, update, ranking, ingestion, flush, audit).
- Introduced the LangGraph workflow (`ResearchState`, node wrappers, conditional routing, `MemorySaver`) and the `_Agent_Activity.md` hand-off log.
- Owned configuration and runtime boundaries: `config.py` (paths, limits, batching, caching), `cli.py`, package entry points.
- Added persistent base lifecycle and safe state handling (`_state.json`, atomic writes, reload for `--update`).
- Coordinated Graph/Retrieval/LLM/QA contracts so each agent can evolve independently.

**Key files:** `agent/core.py`, `agent/workflow.py`, `agent/graph_state.py`, `agent/roles.py`, `cli.py`, `config.py`, `__init__.py`.

### Вадим Лялькин (@Geniy_molodec) — Graph & Knowledge Engineer

**Zone:** graph ontology, `[[wikilinks]]`, Obsidian structure.

- Designed the Obsidian vault model: atomic source notes, concept hubs, synthesis/bibliography hubs, external-reference stubs.
- Implemented `GraphAgent`: concept canonicalization, node-weight normalization, hub rebuilding with definition preservation.
- Built `concepts.py`: plural/casing normalization, acronym resolution, parenthetical merging, deterministic display names.
- Implemented stable, collision-safe note naming (hash-suffixed long titles, deterministic ordering) so links never break.
- Wrote link generation, typed edge rendering, external stubs, multiblock abstract formatting and safe YAML.
- Made `graph.json` merging non-destructive; implemented state persistence and activity-log writing.
- Owned `LiteratureManager` lifecycle (create/load/update/delete/list) and `graph_preset.json`.

**Key files:** `agent/graph_agent.py`, `agent/concepts.py`, `storage/obsidian_vault.py`, `storage/base_manager.py`, `models.py`.

### Нодар Чигладзе (@NodarNeo) — Data / IR Engineer

**Zone:** academic API integration and the search engine.

- Implemented `RetrievalAgent` and the arXiv / Semantic Scholar / DuckDuckGo clients.
- Built query aggregation, title deduplication and metadata merging across sources.
- Added the pre-ranking heuristic (popularity, recency, lexical match) and citation expansion.
- Fixed Semantic Scholar identifiers: arXiv IDs are queried with the required `ARXIV:` prefix; web sources are skipped.
- Added retry/backoff for 429/5xx, configurable HTTP timeouts, stable web-result IDs and URL unwrapping.
- Added the on-disk network cache for searches and citation lookups.
- Built the search-engine catalog (`search/tools.py`) with per-engine descriptions, strengths, limitations and best-fit tasks.
- Implemented `SearchRouter` validation/normalisation and the fallback heuristic used when the model cannot decide.
- Added `plan_request` / `finalize_plan` nodes so the agent asks the LLM engineer which engines to use, then executes primary + fallback with per-paper `source_engine` provenance.
- Implemented PDF ingestion for `--deep`, including open-access PDF URLs, size limits and page extraction.

**Key files:** `agent/retrieval_agent.py`, `search/`, `utils/http.py`, `utils/cache.py`.

### Давид Чигладзе (@David52228) — QA / Evaluation Engineer

**Zone:** quality bench, connectivity and format validation.

- Implemented `EvaluationAgent` and the QA package: vault audit + state audit.
- Added checks for unresolved wikilinks, orphan notes, duplicate names, duplicate edges, frontmatter completeness and empty bibliographies.
- Added state-level checks: concept ↔ paper integrity, missing summaries/citations, edge endpoints and duplicate edges.
- Wrote the automated test suite (pipeline, agents, persistence, canonicalization, vault naming, QA, batching, provider sanitizer).
- Hardened CI: Python 3.10–3.13 matrix, `ruff check` now fails the build, `pytest` runs on every push/PR.
- Added the `litgraph --check` command and severity-based reporting.

**Key files:** `agent/evaluation_agent.py`, `qa/`, `tests/`, `.github/workflows/ci.yml`.

### Илья Синко (@mang1ch5) — LLM Engineer

**Zone:** prompt engineering, abstract-level criteria filtering, synthesis.

- Centralized all prompts in `llm/prompts.py` (search planning, validation, summaries, concepts, grounding, bibliography, relations, review).
- Added `engine_selection_prompt` and the `select_search_engines` action: the model reads the engine catalog and picks primary/fallback engines for the task.
- Implemented consolidated relevance + requirements validation in `validator.py`.
- Built paper synthesis: executive summary, key findings, methodology, limitations, concepts.
- Added bounded batching for concept definitions and bibliographies to avoid output truncation.
- Added deterministic bibliography fallbacks and batched master-review synthesis.
- Hardened JSON parsing for reasoning models (`<think>` tags, code fences, wrapped arrays) and LLM retries.
- Implemented concept-grounded page citations for deep mode.

**Key files:** `agent/prompt_agent.py`, `agent/validator.py`, `agent/synthesizer.py`, `llm/`.

## Interaction map

| Caller | Callee | Purpose |
| --- | --- | --- |
| Lead | Retrieval | Search, citation expansion, PDF page fetch |
| Retrieval | LLM | Choose search engines from the catalog |
| Retrieval | LLM | Draft the next search queries |
| Lead | LLM | Validate papers, synthesize content, define concepts, build bibliography/review |
| Lead | Graph | Rebuild ontology, flush vault, persist state |
| Lead | QA | Audit the generated vault and state |
| Graph | Obsidian vault | Write notes, links, stubs, hubs, activity log |

All calls run as LangGraph nodes and are recorded in the graph's `activity`
channel, then rendered into `_Agent_Activity.md`, so each run shows exactly
which role contributed which step.
