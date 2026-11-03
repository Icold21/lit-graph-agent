from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from ..models import LiteratureBaseState
from ..utils.logging_setup import get_logger
from .obsidian_vault import ObsidianVaultManager

if TYPE_CHECKING:
    from ..agent.core import LiteratureAgent

logger = get_logger(__name__)


class LiteratureManager:
    """Manages lifecycle (CRUD) of multiple independent Obsidian literature vaults."""

    def __init__(self, root_vaults_dir: Path | str, agent: LiteratureAgent | None = None):
        self.root_dir = Path(root_vaults_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.agent = agent
        self.active_bases: Dict[str, LiteratureBaseState] = {}
        self.vaults: Dict[str, ObsidianVaultManager] = {}

    def _require_agent(self) -> "LiteratureAgent":
        if self.agent is None:
            raise RuntimeError("LiteratureManager was created without a LiteratureAgent")
        return self.agent

    @staticmethod
    def _validate_base_id(base_id: str) -> str:
        cleaned = str(base_id).strip()
        if (
            not cleaned
            or cleaned in {".", ".."}
            or ".." in cleaned
            or any(char in cleaned for char in '\\/:*?"<>|')
        ):
            raise ValueError(f"Invalid base id: {base_id!r}")
        return cleaned

    def _vault_for(self, base_id: str) -> ObsidianVaultManager:
        if base_id not in self.vaults:
            self.vaults[base_id] = ObsidianVaultManager(self.root_dir / base_id)
        return self.vaults[base_id]

    def load_base(self, base_id: str) -> Optional[LiteratureBaseState]:
        """Load a base from disk, reusing the in-memory copy when available."""
        base_id = self._validate_base_id(base_id)
        if base_id in self.active_bases:
            return self.active_bases[base_id]

        vault = self._vault_for(base_id)
        state = vault.load_state(base_id)
        if state is None:
            return None
        self.active_bases[base_id] = state
        return state

    def create_base(
        self,
        base_id: str,
        topic: str,
        requirements: str,
        citation_format: str = "APA 7th",
        max_papers: int = 5,
        deep_scan: bool = False,
    ) -> Optional[LiteratureBaseState]:
        base_id = self._validate_base_id(base_id)
        vault = self._vault_for(base_id)
        if vault.state_path.exists():
            logger.error(
                "Base %r already exists at %s. Use --update to extend it.",
                base_id,
                self.root_dir / base_id,
            )
            return None

        state, vault = self._require_agent().initialize_base(
            base_id=base_id,
            topic=topic,
            requirements=requirements,
            citation_format=citation_format,
            vault_path=str(self.root_dir / base_id),
            max_papers=max_papers,
            deep_scan=deep_scan,
        )
        self.active_bases[base_id] = state
        self.vaults[base_id] = vault
        vault.save_state(state)
        return state

    def update_base(
        self,
        base_id: str,
        directive: str,
        max_new_papers: int = 5,
        deep_scan: bool = False,
    ) -> Optional[LiteratureBaseState]:
        try:
            base_id = self._validate_base_id(base_id)
        except ValueError as exc:
            logger.error("%s", exc)
            return None

        state = self.load_base(base_id)
        if state is None:
            logger.error("Base %r not found. Create it first with --topic.", base_id)
            return None

        vault = self._vault_for(base_id)
        state = self._require_agent().update_base(
            state,
            vault,
            directive,
            max_new_papers=max_new_papers,
            deep_scan=deep_scan,
        )
        self.active_bases[base_id] = state
        vault.save_state(state)
        return state

    def delete_base(self, base_id: str) -> None:
        base_id = self._validate_base_id(base_id)
        vault_path = self.root_dir / base_id
        if vault_path.exists():
            shutil.rmtree(vault_path)
        self.active_bases.pop(base_id, None)
        self.vaults.pop(base_id, None)
        logger.info("Vault %r deleted.", base_id)

    def list_bases(self) -> List[str]:
        return sorted(
            directory.name
            for directory in self.root_dir.iterdir()
            if directory.is_dir() and not directory.name.startswith(".")
        )
