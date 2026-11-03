from lit_graph.agent.core import LiteratureAgent
from lit_graph.agent.retrieval_agent import RetrievalAgent
from lit_graph.config import settings
from lit_graph.search.engine import AcademicSearchEngine
from lit_graph.search.router import SearchRouter
from lit_graph.storage.base_manager import LiteratureManager


class _NoCache:
    def get(self, namespace, key):
        return None

    def set(self, namespace, key, value):
        return None


class _StubClient:
    def __init__(self, name: str, results=None):
        self.name = name
        self.results = results if results is not None else [self._paper()]
        self.calls = 0

    def _paper(self):
        return {
            "id": f"{self.name}_1",
            "title": f"{self.name} result",
            "abstract": "abstract",
            "citation_count": 5,
            "influential_citation_count": 1,
            "year": 2024,
        }

    def search(self, query, **kwargs):
        self.calls += 1
        return [dict(paper) for paper in self.results]


def _engine_with_stubs(arxiv_results=None, s2_results=None, web_results=None):
    engine = AcademicSearchEngine()
    engine._cache = _NoCache()
    stubs = {
        "arxiv": _StubClient("arxiv", arxiv_results),
        "semantic_scholar": _StubClient("s2", s2_results),
        "web": _StubClient("web", web_results),
    }
    engine._clients = stubs
    return engine, stubs


def test_model_choice_is_used_verbatim():
    router = SearchRouter()
    plan = router.build_plan(
        {
            "primary": ["arxiv"],
            "fallback": ["web"],
            "rationale": "Fresh preprints",
            "confidence": 0.87,
        }
    )
    assert plan.primary == ["arxiv"]
    assert plan.fallback == ["web"]
    assert plan.rationale == "Fresh preprints"
    assert plan.confidence == 0.87
    assert plan.source == "llm"


def test_unknown_engines_are_dropped_and_extras_become_fallback():
    router = SearchRouter(max_primary=1)
    plan = router.build_plan({"engines": ["arxiv", "made_up", "web"]})
    assert plan.primary == ["arxiv"]
    assert plan.fallback == ["web"]
    assert "made_up" not in plan.engines


def test_garbage_model_output_falls_back_to_heuristics():
    router = SearchRouter()
    plan = router.build_plan({"unexpected": "shape"})
    assert plan.source == "heuristic"
    assert plan.primary
    assert all(engine in {"semantic_scholar", "arxiv", "web"} for engine in plan.engines)


def test_heuristic_plan_matches_task_signals():
    router = SearchRouter()
    assert router.heuristic_plan("Recent arXiv preprints on induction heads", "").primary == ["arxiv"]
    assert router.heuristic_plan("Systematic review of citation impact", "").primary == [
        "semantic_scholar"
    ]
    assert router.heuristic_plan("Industry white paper on AI policy", "").primary == ["web"]


def test_manual_override_ignores_unknown_engines():
    router = SearchRouter(max_primary=1)
    plan = router.manual_plan(["web", "unknown", "arxiv"])
    assert plan.primary == ["web"]
    assert plan.fallback == ["arxiv"]
    assert plan.source == "manual"


def test_engine_queries_only_the_selected_engine():
    engine, stubs = _engine_with_stubs()
    results = engine.search_and_rank("query", engines=["arxiv"], fallback_engines=[], min_results=0)
    assert stubs["arxiv"].calls == 1
    assert stubs["semantic_scholar"].calls == 0
    assert stubs["web"].calls == 0
    assert all(paper["source_engine"] == "arxiv" for paper in results)


def test_fallback_engine_runs_when_primary_is_empty():
    engine, stubs = _engine_with_stubs(arxiv_results=[], web_results=None)
    results = engine.search_and_rank(
        "query",
        engines=["arxiv"],
        fallback_engines=["web"],
        min_results=1,
    )
    assert stubs["arxiv"].calls == 1
    assert stubs["web"].calls == 1
    assert results and results[0]["source_engine"] == "web"


def test_retrieval_agent_catalog_exposes_descriptions(fake_search_engine):
    catalog = RetrievalAgent(fake_search_engine).catalog()
    assert {tool["key"] for tool in catalog} == {"semantic_scholar", "arxiv", "web"}
    assert all(tool["description"] for tool in catalog)


def test_graph_asks_the_llm_agent_to_select_engines(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    agent.initialize_base(
        base_id="planned",
        topic="Recent arXiv work on induction heads",
        requirements="recent",
        citation_format="APA 7th",
        vault_path=str(tmp_path / "planned"),
        max_papers=1,
    )

    assert agent.last_search_plan["primary"] == ["arxiv"]
    assert agent.last_search_plan["source"] == "llm"
    assert ("llm", "select_search_engines") in {
        (event["recipient"], event["action"]) for event in agent.activity
    }


def test_manual_env_override_bypasses_the_model(monkeypatch, fake_search_engine):
    monkeypatch.setattr(settings, "search_engines_override", "web")
    retrieval = RetrievalAgent(fake_search_engine)
    request = retrieval.plan_request("anything", "")
    plan = retrieval.finalize_plan(
        None,
        task="anything",
        requirements="",
        source=request["source"],
    )
    assert request["needs_llm"] is False
    assert plan["source"] == "manual"
    assert plan["primary"] == ["web"]


def test_disabled_router_uses_heuristics(monkeypatch, fake_search_engine):
    monkeypatch.setattr(settings, "search_engines_override", "")
    monkeypatch.setattr(settings, "search_router_enabled", False)
    retrieval = RetrievalAgent(fake_search_engine)
    request = retrieval.plan_request("Systematic review of citation impact", "")
    plan = retrieval.finalize_plan(
        None,
        task="Systematic review of citation impact",
        requirements="",
        source=request["source"],
    )
    assert request["needs_llm"] is False
    assert plan["source"] == "heuristic"
    assert plan["primary"] == ["semantic_scholar"]


def test_pipeline_uses_the_selected_engines(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    agent.initialize_base(
        base_id="routed",
        topic="Mechanistic Interpretability",
        requirements="Recent",
        citation_format="APA 7th",
        vault_path=str(tmp_path / "routed"),
        max_papers=2,
    )

    assert agent.last_search_plan["primary"] == ["arxiv"]
    assert fake_search_engine.calls
    assert all(call["engines"] == ["arxiv"] for call in fake_search_engine.calls)
    assert all(call["fallback_engines"] == ["semantic_scholar"] for call in fake_search_engine.calls)


def test_search_plan_survives_reload(mock_llm, fake_search_engine, tmp_path):
    agent = LiteratureAgent(llm=mock_llm, search_engine=fake_search_engine)
    manager = LiteratureManager(tmp_path, agent=agent)
    manager.create_base("routed", "Topic", "Recent", max_papers=1)

    reloaded = LiteratureManager(tmp_path).load_base("routed")
    assert reloaded is not None
    assert reloaded.search_plan["primary"] == ["arxiv"]
    assert reloaded.search_plan["source"] == "llm"
