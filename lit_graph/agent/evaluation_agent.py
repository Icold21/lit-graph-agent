"""QA / Evaluation Engineer agent: connectivity, formats and state consistency."""

from typing import Any, Tuple

from ..qa.vault_checks import QAReport, run_state_checks, run_vault_checks
from ..utils.logging_setup import get_logger
from .bus import AgentBus, BaseTeamAgent
from .roles import TEAM_ROLES

logger = get_logger(__name__)


class EvaluationAgent(BaseTeamAgent):
    """Audits the generated vault and the scientific state after every run."""

    role = TEAM_ROLES["qa"]

    def __init__(self, bus: AgentBus | None = None):
        super().__init__(bus)

    def actions(self) -> Tuple[str, ...]:
        return ("audit", "check_vault", "check_state")

    def _handle(self, action: str, **payload: Any) -> Any:
        if action == "check_vault":
            return run_vault_checks(payload["vault_path"])
        if action == "check_state":
            return run_state_checks(payload["state"])

        if action == "audit":
            vault_report = run_vault_checks(payload["vault_path"])
            if payload.get("state") is not None:
                state_report = run_state_checks(payload["state"])
                vault_report.merge(state_report)
            errors = len(vault_report.errors)
            warnings = len(vault_report.warnings)
            if errors:
                logger.error("QA audit found %s errors and %s warnings", errors, warnings)
            elif warnings:
                logger.warning("QA audit found %s warnings", warnings)
            else:
                logger.info("QA audit passed: %s", vault_report.summary())
            return vault_report

        raise ValueError(f"Unsupported QA action: {action}")


__all__ = ["EvaluationAgent", "QAReport"]
