from lit_graph.agent.bus import AgentBus
from lit_graph.agent.core import LiteratureAgent
from lit_graph.agent.evaluation_agent import EvaluationAgent
from lit_graph.agent.prompt_agent import PromptAgent
from lit_graph.agent.retrieval_agent import RetrievalAgent
from lit_graph.agent.roles import TEAM_ORDER, TEAM_ROLES
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


def test_bus_records_and_routes_messages(mock_llm, fake_search_engine):
    bus = AgentBus()
    retrieval = RetrievalAgent(fake_search_engine)
    prompt = PromptAgent(mock_llm)
    evaluation = EvaluationAgent()
    for agent in (retrieval, prompt, evaluation):
        bus.register(agent)

    results = bus.request("retrieval", "search", query="test", top_k=3)
    assert len(results) == 3

    queries = bus.request(
        "retrieval",
        "suggest_queries",
        topic="interpretability",
        requirements="recent",
        existing_queries=["interpretability"],
    )
    assert queries == ["latent circuits", "attention head interpretability"]

    senders = {(message.sender, message.recipient, message.action) for message in bus.history}
    assert ("lead", "retrieval", "search") in senders
    assert ("lead", "retrieval", "suggest_queries") in senders
    assert ("retrieval", "llm", "generate_sub_queries") in senders


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

    participants = {message.recipient for message in agent.bus.history}
    assert {"retrieval", "llm", "graph", "qa"} <= participants
    assert "graph" in agent.bus.registered()


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


def test_create_refuses_to_overwrite_existing_base(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    manager = LiteratureManager(tmp_path, agent=agent)
    assert manager.create_base("dup", "Topic", "Recent", max_papers=1) is not None
    assert manager.create_base("dup", "Other", "Recent", max_papers=1) is None

