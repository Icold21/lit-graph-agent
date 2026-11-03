# Agent Team & Message Protocol

LitGraphAgent is split into five role agents. The Lead agent is the only entry
point for a pipeline run; it dispatches work through `AgentBus` and never calls
a specialist's internal modules directly.

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

## Bus protocol

`AgentBus.request(recipient, action, sender="lead", **payload)`:

1. Looks up the registered agent by role key.
2. Checks that `action` is declared in `agent.actions()`.
3. Executes `agent._handle(action, **payload)`.
4. Appends an `AgentMessage` (`sender`, `recipient`, `action`, `status`,
   `duration_ms`, short summary) to `bus.history`.
5. Re-raises failures after recording them as `status="error"`.

Agents can call each other via `BaseTeamAgent.request(...)`; the sender is then
the role key, not `lead`. The current cross-role calls are:

```
RetrievalAgent.plan_search     → PromptAgent.select_search_engines
RetrievalAgent.suggest_queries → PromptAgent.generate_sub_queries
```

`select_search_engines` receives the catalog from `lit_graph/search/tools.py`
(one natural-language description per backend) plus the task and requirements.
The returned primary/fallback set is validated by `SearchRouter`, persisted in
`state.search_plan`, and only then executed.

## Actions

### RetrievalAgent (`retrieval`)

| Action | Payload | Result |
| --- | --- | --- |
| `plan_search` | `task`, `requirements`, `context` | `{primary, fallback, rationale, confidence, source}` |
| `describe_engines` | - | engine catalog (key/label/description/best_for) |
| `search` | `query`, `top_k`, `engines`, `fallback_engines`, `min_results` | ranked candidate dictionaries |
| `expand_citations` | `paper_id`, `limit` | `{"references": [...], "citations": [...]}` |
| `fetch_pages` | `doi_or_url`, `pdf_url`, `max_pages` | `{page_number: text}` |
| `suggest_queries` | `topic`, `requirements`, `existing_queries` | next query strings |

### PromptAgent (`llm`)

| Action | Payload | Result |
| --- | --- | --- |
| `generate_sub_queries` | `topic`, `requirements`, `existing_queries` | query strings |
| `select_search_engines` | `task`, `requirements`, `catalog`, `context` | `{primary, fallback, rationale, confidence}` |
| `validate` | `paper`, `topic`, `requirements` | `bool` |
| `synthesize_paper` | `paper` | `True` |
| `define_concepts` | `state` | hub count |
| `ground_concepts` | `paper`, `pages` | mention count |
| `bibliography` | `state` | paper count |
| `link_network` | `state` | edge count |
| `overview` | `state` | review length |

### GraphAgent (`graph`)

| Action | Payload | Result |
| --- | --- | --- |
| `rebuild_graph` | `state`, `papers` | `{papers, concepts, edges}` |
| `flush` | `state`, `activity` | written counts |
| `save_state` / `load_state` | `state` / `base_id` | state or `True` |

### EvaluationAgent (`qa`)

| Action | Payload | Result |
| --- | --- | --- |
| `audit` | `state`, `vault_path` | merged `QAReport` |
| `check_vault` | `vault_path` | vault `QAReport` |
| `check_state` | `state` | state `QAReport` |

## Run sequence

```
lead → retrieval.plan_search            → llm.select_search_engines
lead → retrieval.search                 (selected engines + fallback)
lead → llm.validate                     (per candidate)
lead → retrieval.expand_citations       (per selected paper)
lead → llm.synthesize_paper
lead → retrieval.fetch_pages            (--deep only)
lead → llm.ground_concepts              (--deep only)
lead → graph.rebuild_graph
lead → graph.save_state
lead → llm.define_concepts
lead → llm.bibliography
lead → llm.link_network
lead → llm.overview
lead → graph.flush                      → writes _Agent_Activity.md
lead → qa.audit
```

`_Agent_Activity.md` is generated from `bus.history`, so every hand-off and its
duration is visible in the vault.

## Adding a new agent

1. Add a `TeamRole` entry to `TEAM_ROLES` (`agent/roles.py`), including owner, handle, agent name and module list.
2. Subclass `BaseTeamAgent`, declare `role` and `actions()`, implement `_handle`.
3. Register the agent in `LiteratureAgent.__init__` or `_open_vault` (`agent/core.py`).
4. Add a row to `CONTRIBUTORS.md`, `docs/AGENT_TEAM.md`, `README.md` and `.github/CODEOWNERS`.
5. Add a QA check or test that exercises the new action.

## Invariants

- A specialist never writes another specialist's data directly.
- All LLM prompts live in `lit_graph/llm/prompts.py`.
- Search-engine descriptions live in `lit_graph/search/tools.py`; the model
  chooses from that catalog and the choice is validated/persisted before use.
- All graph/vault writes go through `GraphAgent`.
- QA never mutates state; it only reports.
- Every run ends with a persisted `_state.json`.
