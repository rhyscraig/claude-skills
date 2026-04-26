"""Claude Skills Platform — Framework for building Claude skills.

Production-grade foundation for building AI automation tools with:
- Configuration hierarchy (master + repo overrides + environment)
- Safety guardrails with confirmation gates and audit logging
- Clean layered architecture
- Type safety and validation
- Comprehensive testing support

Example usage:

    from src.base_config import BaseConfigLoader
    from src.base_guardrails import BaseGuardrails
    from src.base_cli import BaseSkillCLI

    class MySkillConfig(BaseConfigLoader):
        def schema(self): ...
        def load_defaults(self): ...

    class MySkillCLI(BaseSkillCLI):
        def skill_name(self): return "my-skill"
        def skill_version(self): return "1.0.0"
        def register_commands(self): ...
"""

__version__ = "1.0.0"
__author__ = "Craig Hoad"

from .base_config import BaseConfigLoader, ConfigError
from .base_guardrails import BaseGuardrails, GuardrailViolation, ActionType
from .base_cli import BaseSkillCLI, Command

__all__ = [
    # Core classes
    "BaseConfigLoader",
    "BaseGuardrails",
    "BaseSkillCLI",
    # Exceptions
    "ConfigError",
    "GuardrailViolation",
    # Types
    "ActionType",
    "Command",
    # Metadata
    "__version__",
    "__author__",
]
