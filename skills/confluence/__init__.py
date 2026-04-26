"""Confluence documentation skill."""

from .skill import ConfluenceSkill
from .models import SkillConfig, DocumentGenerationResult
from .confluence_client import ConfluenceClient

__version__ = "1.0.0"
__all__ = [
    "ConfluenceSkill",
    "SkillConfig",
    "DocumentGenerationResult",
    "ConfluenceClient",
]
