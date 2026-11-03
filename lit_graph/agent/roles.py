"""Team roles and ownership map.

Every role owns a concrete agent class and a set of modules.  The orchestrator
(LeadAIAgent) never calls role modules directly: it dispatches tasks through the
agent bus, so all five roles are active participants in one pipeline.
"""

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class TeamRole:
    key: str
    title: str
    owner: str
    handle: str
    responsibility: str
    agent: str
    modules: Tuple[str, ...] = field(default_factory=tuple)


TEAM_ROLES: Dict[str, TeamRole] = {
    "lead": TeamRole(
        key="lead",
        title="Lead AI Engineer",
        owner="Иван Холодило",
        handle="@Icold21",
        responsibility="Сквозная архитектура, LangGraph-оркестрация и координация ролей",
        agent="LeadAIAgent (LiteratureAgent)",
        modules=(
            "lit_graph/agent/core.py",
            "lit_graph/agent/workflow.py",
            "lit_graph/agent/graph_state.py",
            "lit_graph/agent/roles.py",
            "lit_graph/cli.py",
            "lit_graph/config.py",
            "lit_graph/__init__.py",
        ),
    ),
    "graph": TeamRole(
        key="graph",
        title="Graph & Knowledge Engineer",
        owner="Вадим Лялькин",
        handle="@Geniy_molodec",
        responsibility="Онтология графа, связи [[wikilinks]], структура Obsidian",
        agent="GraphAgent",
        modules=(
            "lit_graph/agent/graph_agent.py",
            "lit_graph/agent/concepts.py",
            "lit_graph/storage/obsidian_vault.py",
            "lit_graph/storage/base_manager.py",
            "lit_graph/storage/graph_preset.json",
            "lit_graph/models.py",
        ),
    ),
    "retrieval": TeamRole(
        key="retrieval",
        title="Data / IR Engineer",
        owner="Нодар Чигладзе",
        handle="@NodarNeo",
        responsibility="Интеграция академических API (arXiv, Semantic Scholar), поисковый движок",
        agent="RetrievalAgent",
        modules=(
            "lit_graph/agent/retrieval_agent.py",
            "lit_graph/search/",
            "lit_graph/utils/http.py",
            "lit_graph/utils/cache.py",
        ),
    ),
    "qa": TeamRole(
        key="qa",
        title="QA / Evaluation Engineer",
        owner="Давид Чигладзе",
        handle="@David52228",
        responsibility="Стенд тестирования качества, валидация связности и форматов",
        agent="EvaluationAgent",
        modules=(
            "lit_graph/agent/evaluation_agent.py",
            "lit_graph/qa/",
            "tests/",
            ".github/workflows/",
        ),
    ),
    "llm": TeamRole(
        key="llm",
        title="LLM Engineer",
        owner="Илья Синко",
        handle="@mang1ch5",
        responsibility="Промпт-инжиниринг, критериальная фильтрация абстрактов, синтез выжимок",
        agent="PromptAgent",
        modules=(
            "lit_graph/agent/prompt_agent.py",
            "lit_graph/agent/validator.py",
            "lit_graph/agent/synthesizer.py",
            "lit_graph/llm/",
        ),
    ),
}

# Order used by the CLI and documentation tables.
TEAM_ORDER = ("lead", "graph", "retrieval", "qa", "llm")


def get_role(key: str) -> TeamRole:
    try:
        return TEAM_ROLES[key]
    except KeyError as exc:
        raise ValueError(f"Unknown team role: {key}") from exc
