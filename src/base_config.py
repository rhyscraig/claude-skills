"""Base configuration loader with hierarchy and validation.

This module provides the abstract base class for configuration management
following the 12-factor app principles: all configuration from environment.
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import jsonschema


@dataclass
class ConfigError(Exception):
    """Configuration loading or validation error."""

    message: str
    field: Optional[str] = None
    details: Optional[str] = None

    def __str__(self) -> str:
        msg = f"Config Error: {self.message}"
        if self.field:
            msg += f" (field: {self.field})"
        if self.details:
            msg += f"\n  {self.details}"
        return msg


class BaseConfigLoader(ABC):
    """Abstract base class for configuration management.

    Implements configuration hierarchy:
    1. Master config from ~/.claude/{skill}/config.json
    2. Repo config from .claude/claude.json
    3. Environment variables for secrets
    4. Programmatic defaults

    Subclasses must implement:
    - schema() → JSON schema for validation
    - load_defaults() → default configuration
    """

    def __init__(self, skill_name: str, validate: bool = True):
        """Initialize configuration loader.

        Args:
            skill_name: Name of the skill (e.g., 'jira')
            validate: Whether to validate against schema on load
        """
        self.skill_name = skill_name
        self.validate = validate
        self._config: Optional[Dict[str, Any]] = None

    @abstractmethod
    def schema(self) -> Dict[str, Any]:
        """Return JSON schema for configuration validation.

        Must be implemented by subclasses.

        Returns:
            JSON schema as dict
        """
        pass

    @abstractmethod
    def load_defaults(self) -> Dict[str, Any]:
        """Return default configuration values.

        Must be implemented by subclasses.

        Returns:
            Default configuration as dict
        """
        pass

    def _master_config_path(self) -> Path:
        """Return path to master configuration file.

        Master config lives at ~/.claude/{skill_name}/config.json
        """
        home = Path.home()
        return home / ".claude" / self.skill_name / "config.json"

    def _repo_config_path(self) -> Path:
        """Return path to repository-specific configuration file.

        Repo config lives at .claude/claude.json in current repo.
        """
        return Path.cwd() / ".claude" / "claude.json"

    def load(self) -> Dict[str, Any]:
        """Load and merge configuration from all sources.

        Configuration hierarchy (lowest to highest priority):
        1. Built-in defaults
        2. Master config (~/.claude/{skill}/config.json)
        3. Repo config (.claude/claude.json)
        4. Environment variable overrides

        Returns:
            Merged configuration dict

        Raises:
            ConfigError: If validation fails
        """
        if self._config is not None:
            return self._config

        # Start with defaults
        config = self.load_defaults()

        # Merge master config if exists
        master_path = self._master_config_path()
        if master_path.exists():
            master_config = self._load_json_file(master_path)
            config = self._deep_merge(config, master_config)

        # Merge repo config if exists
        repo_path = self._repo_config_path()
        if repo_path.exists():
            repo_config = self._load_json_file(repo_path)
            config = self._deep_merge(config, repo_config)

        # Apply environment variable overrides
        config = self._apply_env_overrides(config)

        # Validate
        if self.validate:
            self._validate(config)

        self._config = config
        return config

    def _load_json_file(self, path: Path) -> Dict[str, Any]:
        """Load JSON file with error handling.

        Args:
            path: Path to JSON file

        Returns:
            Parsed JSON as dict

        Raises:
            ConfigError: If file cannot be read or is invalid JSON
        """
        try:
            with open(path) as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Invalid JSON in {path}",
                details=str(e),
            )
        except OSError as e:
            raise ConfigError(
                f"Cannot read config file {path}",
                details=str(e),
            )

    def _deep_merge(self, base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dicts, with overrides taking precedence.

        Args:
            base: Base configuration
            overrides: Overriding configuration

        Returns:
            Merged configuration
        """
        result = base.copy()
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides.

        Environment variables matching pattern {SKILL_UPPER}_{KEY_UPPER}
        override config values. For example, JIRA_CLOUD_ID overrides
        config["jira"]["cloudId"].

        Args:
            config: Base configuration

        Returns:
            Configuration with env overrides applied
        """
        prefix = self.skill_name.upper() + "_"

        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # Extract config path from env variable name
            # e.g., JIRA_CLOUD_ID → ["cloud_id"]
            config_path = key[len(prefix):].lower().split("_")

            # Apply override by navigating config tree
            self._set_nested_value(config, config_path, value)

        return config

    def _set_nested_value(self, obj: Dict[str, Any], path: list[str], value: Any) -> None:
        """Set value in nested dict by path.

        Args:
            obj: Target dict
            path: List of keys to traverse
            value: Value to set
        """
        for key in path[:-1]:
            if key not in obj:
                obj[key] = {}
            obj = obj[key]

        obj[path[-1]] = value

    def _validate(self, config: Dict[str, Any]) -> None:
        """Validate configuration against schema.

        Args:
            config: Configuration to validate

        Raises:
            ConfigError: If validation fails
        """
        try:
            jsonschema.validate(config, self.schema())
        except jsonschema.ValidationError as e:
            raise ConfigError(
                f"Configuration validation failed: {e.message}",
                field=".".join(str(p) for p in e.absolute_path),
                details=e.validator_value,
            )
        except jsonschema.SchemaError as e:
            raise ConfigError(
                "Configuration schema is invalid",
                details=str(e),
            )

    def show(self) -> str:
        """Return human-readable configuration summary.

        For debugging and inspection. Never includes secrets.

        Returns:
            Pretty-printed configuration summary
        """
        config = self.load()
        return json.dumps(config, indent=2)

    def reset(self) -> None:
        """Reset cached configuration (forces reload on next load())."""
        self._config = None
