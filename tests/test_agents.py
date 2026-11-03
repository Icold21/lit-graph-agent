from lit_graph.agent.core import LiteratureAgent
from lit_graph.agent.roles import TEAM_ORDER, TEAM_ROLES
from lit_graph.agent.workflow import LiteratureWorkflow
from lit_graph.storage.base_manager import LiteratureManager


def test_team_roles_cover_every_specialist():
    assert set(TEAM_ORDER) == set(TEAM_ROLES)
    assert {role.agent for role in TEAM_ROLES.values()} == {
        "LeadAIAgent (LiteratureAgent)",
        "GraphAgent",
        "RetrievalAgent",
        "EvaluationAgent",
        "PromptAgent",
    }
    assert all(role.owner and role.handle for role in TEAM_ROLES.values())


def test_langgraph_exposes_every_pipeline_node(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    agent._open_vault(str(tmp_path / "graph"))
    workflow = LiteratureWorkflow(
        retrieval=agent.retrieval,
        prompt=agent.prompt,
        evaluation=agent.evaluation,
        graph_agent=agent.graph_agent,
    )
    compiled = workflow.build("create")

    nodes = set(compiled.get_graph().nodes)
    assert {
        "plan_request",
        "choose_engines",
        "finalize_plan",
        "search",
        "validate",
        "rank_select",
        "expand_citations",
        "synthesize",
        "rebuild_graph",
        "define_concepts",
        "bibliography",
        "link_network",
        "overview",
        "flush",
        "audit",
    } <= nodes
    assert compiled.checkpointer is not None


def test_full_pipeline_uses_every_agent(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    state, vault = agent.initialize_base(
        base_id="pipeline",
        topic="Mechanistic Interpretability",
        requirements="Recent work",
        citation_format="APA 7th",
        vault_path=str(tmp_path / "pipeline"),
        max_papers=3,
    )

    assert len(state.papers) == 3
    assert state.concepts
    assert state.bibliography_en
    assert state.overall_summary_en
    assert (vault.state_path).exists()
    assert (vault.vault_path / "_Agent_Activity.md").exists()

    recipients = {event["recipient"] for event in agent.activity}
    actions = {event["action"] for event in agent.activity}
    assert {"retrieval", "llm", "graph", "qa"} <= recipients
    assert {"select_search_engines", "search", "validate", "rebuild_graph", "flush", "audit"} <= actions
    assert agent.last_qa_report is not None


def test_manager_persists_and_reloads_base(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    manager = LiteratureManager(tmp_path, agent=agent)
    created = manager.create_base(
        base_id="persisted",
        topic="Topic",
        requirements="Recent",
        max_papers=2,
    )
    assert created is not None
    assert (tmp_path / "persisted" / "_state.json").exists()

    refreshed = LiteratureManager(tmp_path)
    loaded = refreshed.load_base("persisted")
    assert loaded is not None
    assert loaded.base_id == "persisted"
    assert len(loaded.papers) == len(created.papers)


def test_update_extends_a_persisted_base(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    manager = LiteratureManager(tmp_path, agent=agent)
    manager.create_base("growing", "Topic", "Recent", max_papers=1)

    fake_search_engine.set_candidates(
        [
            {
                "id": "new_1",
                "title": "A New Paper",
                "authors": ["Alice Smith"],
                "year": 2025,
                "venue": "NeurIPS",
                "abstract": "Circuits and induction heads.",
                "citation_count": 42,
                "influential_citation_count": 5,
            }
        ]
    )
    updated = manager.update_base("growing", "induction heads", max_new_papers=1)
    assert updated is not None
    assert "new_1" in updated.papers
    assert updated.search_plan["primary"] == ["arxiv"]


def test_create_refuses_to_overwrite_existing_base(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    manager = LiteratureManager(tmp_path, agent=agent)
    assert manager.create_base("dup", "Topic", "Recent", max_papers=1) is not None
    assert manager.create_base("dup", "Other", "Recent", max_papers=1) is None
