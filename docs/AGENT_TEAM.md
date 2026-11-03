# Agent Team & LangGraph Workflow

LitGraphAgent is split into five role agents. The Lead agent is the only entry
point for a pipeline run; it executes a [LangGraph](https://github.com/langchain-ai/langgraph)
`StateGraph` that routes work to the specialists. Business logic stays inside
the role agents — the graph only decides *when* each step runs and carries the
shared state between them.

## Roles and agents

| Role key | Agent class | Owner | Owns |
| --- | --- | --- | --- |
| `lead` | `LiteratureAgent` | @Icold21 | orchestration, state, CLI |
| `graph` | `GraphAgent` | @Geniy_molodec | ontology, wikilinks, vault output |
| `retrieval` | `RetrievalAgent` | @NodarNeo | academic APIs, search, PDFs, cache |
| `qa` | `EvaluationAgent` | @David52228 | vault/state audits, formats |
| `llm` | `PromptAgent` | @mang1ch5 | prompts, filtering, synthesis |

Role metadata lives in `lit_graph/agent/roles.py`; the CLI renders it with
`litgraph --team`.

## LangGraph workflow

`lit_graph/agent/workflow.py` defines `LiteratureWorkflow`:

1. `build(mode)` creates a `StateGraph(ResearchState)` for `create` or `update`.
2. Every pipeline step is registered as a node through
   `_step(recipient, action, fn)`. The wrapper calls the role's method, appends
   one event to the `activity` channel (an `Annotated[List[dict], merge_activity]`
   reducer) and returns only the state keys the node changed.
3. Hand-offs are plain edges; decisions are `add_conditional_edges` routers such
   as `_after_validate_create` and `_after_commit`.
4. The graph is compiled with a `MemorySaver` checkpointer. Each run gets a
   unique `thread_id`, so `graph.get_state(config)` exposes the final state to
   the Lead agent, while `_state.json` remains the durable store across runs.

`ResearchState` (`lit_graph/agent/graph_state.py`) is JSON-serialisable: the
literature base is stored as a dict and re-hydrated into `LiteratureBaseState`
inside the nodes. Runtime dependencies (LLM client, vault, agents) live on the
workflow object, never in graph state.

The model still chooses the search engines, but the decision is now split into
three nodes: `plan_request` → `choose_engines` (LLM) → `finalize_plan`
(`SearchRouter` validation/normalisation). A manual `SEARCH_ENGINES_OVERRIDE` or
`--no-router` routes straight from `plan_request` to `finalize_plan`, so the
LLM is never called. The plan is persisted in `state.search_plan`.

## Role services and nodes

### RetrievalAgent (`retrieval`)

| Method / node | Payload | Result |
| --- | --- | --- |
| `plan_request` (node `plan_request`) | `task`, `requirements`, `context` | routing decision (`needs_llm`, `source`) |
| `finalize_plan` (node `finalize_plan`) | `decision`, `task`, `requirements` | `{primary, fallback, rationale, confidence, source}` |
| `catalog` / `catalog_prompt` | - | engine catalog (key/label/description/best_for) |
| `search` (node `search`) | `query`, `top_k`, `engines`, `fallback_engines`, `min_results` | ranked candidate dictionaries |
| `expand_citations` (node `expand_citations`) | `paper_id`, `limit` | `{"references": [...], "citations": [...]}` |
| `fetch_pages` (node `fetch_pages`) | `doi_or_url`, `pdf_url`, `max_pages` | `{page_number: text}` |

### PromptAgent (`llm`)

| Method / node | Payload | Result |
| --- | --- | --- |
| `choose_engines` (node `choose_engines`) | `task`, `requirements`, `catalog`, `context` | `{primary, fallback, rationale, confidence}` |
| `generate_sub_queries` (node `suggest_queries`) | `topic`, `requirements`, `existing_queries` | query strings |
| `validate_candidate` (node `validate`) | `paper`, `topic`, `requirements` | `bool` |
| `synthesize_paper` (node `synthesize`) | `paper` | updated paper |
| `ground_concepts` (node `ground_concepts`) | `paper`, `pages` | mention count |
| `define_concepts` (node `define_concepts`) | `state` | hub count |
| `build_bibliography` (node `bibliography`) | `state` | paper count |
| `link_network` (node `link_network`) | `state` | edge count |
| `build_overview` (node `overview`) | `state` | review length |

### GraphAgent (`graph`)

| Method / node | Payload | Result |
| --- | --- | --- |
| `rebuild_graph` (node `rebuild_graph`) | `state`, `papers` | `{papers, concepts, edges}` |
| `flush` (node `flush`) | `state`, `activity` | written counts |
| `save_state` (node `save_state`) | `state` | `_state.json` written |
| `load_state` | `base_id` | persisted state |

### EvaluationAgent (`qa`)

| Method / node | Payload | Result |
| --- | --- | --- |
| `audit` (node `audit`) | `state`, `vault_path` | merged `QAReport` |
| `check_vault` | `vault_path` | vault `QAReport` |
| `check_state` | `state` | state `QAReport` |

## Graph routing

```
initial state
  └─► plan_request ──┬─► choose_engines ─► finalize_plan ─► search ─► validate
                     └────────────────────► finalize_plan

create: validate ──► search | suggest_queries | rank_select
        rank_select ──► expand_citations | flush

update: validate ──► expand_citations | save_state
        save_state ──► audit

ingest (loop over selected papers):
  expand_citations ─► synthesize ─┬─► fetch_pages ─► ground_concepts ─┐
                                  └────────────────► commit_paper ◄───┘
  commit_paper ──► expand_citations (next paper) | rebuild_graph

tail: rebuild_graph ─► define_concepts ─► bibliography ─► link_network
      ─► overview ─► flush ─► audit ─► END
```

`_Agent_Activity.md` is generated from the accumulated `activity` state, so
every node execution and its duration is visible in the vault.

## Adding a new agent

1. Add a `TeamRole` entry to `TEAM_ROLES` (`agent/roles.py`), including owner, handle, agent name and module list.
2. Implement the service class with plain methods (no base class or bus required).
3. Instantiate it in `LiteratureAgent.__init__` / `_open_vault` (`agent/core.py`).
4. Pass it to `LiteratureWorkflow` and register a node with
   `graph.add_node(...)`, plus edges or a conditional router in `workflow.py`.
5. Add a row to `CONTRIBUTORS.md`, `docs/AGENT_TEAM.md`, `README.md` and `.github/CODEOWNERS`.
6. Add a QA check or test that exercises the new node.

## Invariants

- A specialist never writes another specialist's data directly.
- All LLM prompts live in `lit_graph/llm/prompts.py`.
- Search-engine descriptions live in `lit_graph/search/tools.py`; the model
  chooses from that catalog and the choice is validated/persisted before use.
- All graph/vault writes go through `GraphAgent`.
- QA never mutates state; it only reports.
- Nodes return only declared `ResearchState` keys; the base travels as a JSON dict.
- Every run ends with a persisted `_state.json`.
