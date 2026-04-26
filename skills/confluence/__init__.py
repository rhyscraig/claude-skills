"""Confluence documentation skill."""

from .skill import ConfluenceSkill
from .models import SkillConfig, LocalConfig, DocumentGenerationResult, JiraConfig
from .confluence_client import ConfluenceClient
from .jira_integration import JiraIntegration

__version__ = "1.2.0"
__all__ = [
    "ConfluenceSkill",
    "SkillConfig",
    "LocalConfig",
    "DocumentGenerationResult",
    "ConfluenceClient",
    "JiraIntegration",
    "JiraConfig",
]
