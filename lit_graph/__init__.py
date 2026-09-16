"""
LitGraphAgent: Autonomous Literature Research Agent with Obsidian Knowledge Graph Synthesis.
"""

from .agent.core import LiteratureAgent as LitGraphAgent
from .llm.providers import UniversalLLMProvider
from .storage.base_manager import LiteratureManager

__version__ = "1.0.0"
__all__ = ["LitGraphAgent", "UniversalLLMProvider", "LiteratureManager"]