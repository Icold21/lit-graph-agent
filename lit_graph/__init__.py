"""
LitGraphAgent: Autonomous Literature Research Agent with Obsidian Knowledge Graph Synthesis.
"""

from .agent.core import LiteratureAgent
from .agent.evaluation_agent import EvaluationAgent
from .agent.graph_agent import GraphAgent
from .agent.graph_state import ResearchState
from .agent.prompt_agent import PromptAgent
from .agent.retrieval_agent import RetrievalAgent
from .agent.roles import TEAM_ORDER, TEAM_ROLES, TeamRole, get_role
from .agent.workflow import LiteratureWorkflow
from .llm.providers import UniversalLLMProvider
from .search.router import SearchPlan, SearchRouter
from .storage.base_manager import LiteratureManager

LitGraphAgent = LiteratureAgent

__version__ = "1.0.0"
__all__ = [
    "LitGraphAgent",
    "LiteratureAgent",
    "LiteratureManager",
    "UniversalLLMProvider",
    "EvaluationAgent",
    "GraphAgent",
    "PromptAgent",
    "RetrievalAgent",
    "LiteratureWorkflow",
    "ResearchState",
    "SearchPlan",
    "SearchRouter",
    "TEAM_ORDER",
    "TEAM_ROLES",
    "TeamRole",
    "get_role",
]
