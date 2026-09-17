from __future__ import annotations

import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from ..models import LiteratureBaseState
from .obsidian_vault import ObsidianVaultManager

if TYPE_CHECKING:
    from ..agent.core import LiteratureAgent


class LiteratureManager:
    """Manages lifecycle (CRUD) of multiple independent Obsidian literature vaults."""

    def __init__(self, root_vaults_dir: Path | str, agent: LiteratureAgent):
        self.root_dir = Path(root_vaults_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self.agent = agent
        self.active_bases: Dict[str, LiteratureBaseState] = {}
        self.vaults: Dict[str, ObsidianVaultManager] = {}

    def create_base(
        self,
        base_id: str,
        topic: str,
        requirements: str,
        citation_format: str = "APA 7th",
        max_papers: int = 5,
        deep_scan: bool = False
    ) -> LiteratureBaseState:
        vault_path = self.root_dir / base_id
        state, vault = self.agent.initialize_base(
            base_id=base_id,
            topic=topic,
            requirements=requirements,
            citation_format=citation_format,
            vault_path=str(vault_path),
            max_papers=max_papers,
            deep_scan=deep_scan
        )
        self.active_bases[base_id] = state
        self.vaults[base_id] = vault
        return state

    def update_base(
        self,
        base_id: str,
        directive: str,
        max_new_papers: int = 5,
        deep_scan: bool = False
    ) -> Optional[LiteratureBaseState]:
        if base_id not in self.active_bases:
            print(f"[Manager] Base '{base_id}' is not loaded in memory.")
            return None
        return self.agent.update_base(
            self.active_bases[base_id],
            self.vaults[base_id],
            directive,
            max_new_papers=max_new_papers,
            deep_scan=deep_scan
        )

    def delete_base(self, base_id: str) -> None:
        vault_path = self.root_dir / base_id
        if vault_path.exists():
            shutil.rmtree(vault_path)
        self.active_bases.pop(base_id, None)
        self.vaults.pop(base_id, None)
        print(f"[Manager] Vault '{base_id}' deleted.")

    def list_bases(self) -> List[str]:
        return [d.name for d in self.root_dir.iterdir() if d.is_dir()]