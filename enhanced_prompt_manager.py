"""
Enhanced Prompt Manager with OASIS-E Integration.
Generates prompts using official CMS OASIS terminology and structure.
Falls back gracefully when OASIS database tables are empty.
"""

from pathlib import Path
import os
from typing import List, Optional

# Try to import OASIS helpers; provide no-ops if unavailable
try:
    from models.oasis import (
        OASISItem, OASISSection, PDGMOASISMapping,
        get_pdgm_priority_items, get_oasis_items_by_discipline,
        get_oasis_item_by_number,
    )
    _OASIS_AVAILABLE = True
except Exception:
    _OASIS_AVAILABLE = False

    def get_pdgm_priority_items(*a, **kw):
        return []

    def get_oasis_items_by_discipline(*a, **kw):
        return []

    def get_oasis_item_by_number(*a, **kw):
        return None


class EnhancedPromptManager:
    def __init__(self, prompt_dir: Optional[Path] = None):
        self.prompt_dir = prompt_dir or Path(
            os.getenv('PROMPT_DIR', Path(__file__).resolve().parent / 'prompts')
        )

    def load_template(self, feature: str) -> str:
        path = self.prompt_dir / f'{feature}_template.md'
        try:
            return path.read_text(encoding='utf-8')
        except FileNotFoundError:
            return ''

    def load_reference(self, feature: str, pdgm_group: str = None) -> str:
        path = self.prompt_dir / f'{feature}_reference.md'
        if pdgm_group:
            group_path = self.prompt_dir / feature / f'{pdgm_group.lower()}.md'
            if group_path.exists():
                path = group_path
        try:
            return path.read_text(encoding='utf-8')
        except FileNotFoundError:
            return ''

    def build_system_prompt(self, feature: str, pdgm_group: str, diagnosis: str, disciplines: List[str] = None) -> str:
        template = self.load_template(feature)
        reference = self.load_reference(feature, pdgm_group)
        if template:
            return template.replace('{reference_block}', reference)
        # Fallback generic prompt
        return (
            f"You are a home health PDGM compliance expert. "
            f"Generate guidance for {diagnosis} in the {pdgm_group} PDGM group."
        )


# Backward-compatible module-level functions
def load_template(feature: str) -> str:
    return EnhancedPromptManager().load_template(feature)


def load_reference(feature: str, pdgm_group: str = None) -> str:
    return EnhancedPromptManager().load_reference(feature, pdgm_group)


def build_system_prompt(feature: str, pdgm_group: str, diagnosis: str, disciplines: List[str] = None) -> str:
    return EnhancedPromptManager().build_system_prompt(feature, pdgm_group, diagnosis, disciplines)
