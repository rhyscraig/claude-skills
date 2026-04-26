"""cloudctl Integration Skill for Claude.

Enterprise-grade skill for managing cloud contexts and operations across AWS, Azure, and GCP
using the cloudctl CLI tool. Enables autonomous context switching, credential management,
and multi-cloud operations.
"""

__version__ = "1.2.0"
__author__ = "Craig Hoad"
__license__ = "MIT"

from .skill import CloudctlSkill
from .models import (
    CloudContext,
    CommandResult,
    SkillConfig,
    TokenStatus,
    HealthCheckResult,
)

__all__ = [
    "CloudctlSkill",
    "CloudContext",
    "CommandResult",
    "SkillConfig",
    "TokenStatus",
    "HealthCheckResult",
]
