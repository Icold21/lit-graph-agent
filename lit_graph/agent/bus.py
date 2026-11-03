"""Inter-agent message bus.

The Lead agent orchestrates the pipeline by dispatching actions to specialized
agents.  Agents may also call each other through the same bus (for example the
retrieval agent asks the prompt agent to draft new search queries), which keeps
every role interacting with the agent team instead of calling raw modules.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from ..utils.logging_setup import get_logger
from .roles import TeamRole

logger = get_logger(__name__)


@dataclass
class AgentMessage:
    sender: str
    recipient: str
    action: str
    status: str
    timestamp: str
    summary: str = ""
    payload_keys: Tuple[str, ...] = field(default_factory=tuple)
    duration_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AgentBus:
    """Routes tasks between the lead agent and specialized role agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, "BaseTeamAgent"] = {}
        self.history: List[AgentMessage] = []

    def register(self, agent: "BaseTeamAgent") -> None:
        agent.bind(self)
        self._agents[agent.role.key] = agent

    def get(self, key: str) -> "BaseTeamAgent":
        if key not in self._agents:
            raise KeyError(f"Agent {key!r} is not registered")
        return self._agents[key]

    def registered(self) -> Dict[str, TeamRole]:
        return {key: agent.role for key, agent in self._agents.items()}

    def request(
        self,
        recipient: str,
        action: str,
        *,
        sender: str = "lead",
        **payload: Any,
    ) -> Any:
        started = time.perf_counter()
        try:
            result = self.get(recipient).handle(action, **payload)
        except Exception as exc:
            self._record(sender, recipient, action, "error", str(exc), payload, started)
            logger.error("Agent %s failed on %s: %s", recipient, action, exc)
            raise

        self._record(sender, recipient, action, "ok", self._summarize(result), payload, started)
        return result

    def _record(
        self,
        sender: str,
        recipient: str,
        action: str,
        status: str,
        summary: str,
        payload: Dict[str, Any],
        started: float,
    ) -> None:
        message = AgentMessage(
            sender=sender,
            recipient=recipient,
            action=action,
            status=status,
            timestamp=datetime.now(timezone.utc).isoformat(),
            summary=summary[:240],
            payload_keys=tuple(sorted(payload.keys())),
            duration_ms=int((time.perf_counter() - started) * 1000),
        )
        self.history.append(message)
        log = logger.warning if status == "error" else logger.debug
        log("agent %s -> %s.%s [%s] %s", sender, recipient, action, status, message.summary)

    @staticmethod
    def _summarize(result: Any) -> str:
        if isinstance(result, (list, tuple, set, dict)):
            return f"{type(result).__name__}(len={len(result)})"
        if isinstance(result, bool):
            return str(result)
        return str(result)[:200]

    def to_dicts(self) -> List[Dict[str, Any]]:
        return [message.to_dict() for message in self.history]


class BaseTeamAgent(ABC):
    """A role agent with a declared set of actions and a shared message bus."""

    role: TeamRole

    def __init__(self, bus: Optional[AgentBus] = None):
        self.bus = bus

    def bind(self, bus: AgentBus) -> None:
        self.bus = bus

    @abstractmethod
    def actions(self) -> Tuple[str, ...]:
        """Actions this agent accepts from the orchestration bus."""

    @abstractmethod
    def _handle(self, action: str, **payload: Any) -> Any:
        """Execute one action. Implementations validate required payload keys."""

    def handle(self, action: str, **payload: Any) -> Any:
        if action not in self.actions():
            raise ValueError(f"Agent {self.role.key!r} does not support action {action!r}")
        return self._handle(action, **payload)

    def request(self, recipient: str, action: str, **payload: Any) -> Any:
        if self.bus is None:
            raise RuntimeError("Agent is not bound to a bus")
        return self.bus.request(recipient, action, sender=self.role.key, **payload)
