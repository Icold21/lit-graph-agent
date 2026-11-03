"""QA / Evaluation Engineer agent: connectivity, formats and state consistency."""

from ..models import LiteratureBaseState
from ..qa.vault_checks import QAReport, run_state_checks, run_vault_checks
from ..utils.logging_setup import get_logger
from .roles import TEAM_ROLES

logger = get_logger(__name__)


class EvaluationAgent:
    """Audits the generated vault and the scientific state after every run."""

    role = TEAM_ROLES["qa"]

    def check_vault(self, vault_path: str) -> QAReport:
        return run_vault_checks(vault_path)

    def check_state(self, state: LiteratureBaseState) -> QAReport:
        return run_state_checks(state)

    def audit(self, state: LiteratureBaseState, vault_path: str) -> QAReport:
        report = run_vault_checks(vault_path)
        report.merge(run_state_checks(state))

        errors = len(report.errors)
        warnings = len(report.warnings)
        if errors:
            logger.error("QA audit found %s errors and %s warnings", errors, warnings)
        elif warnings:
            logger.warning("QA audit found %s warnings", warnings)
        else:
            logger.info("QA audit passed: %s", report.summary())
        return report


__all__ = ["EvaluationAgent", "QAReport"]
