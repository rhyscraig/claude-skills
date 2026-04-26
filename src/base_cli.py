"""Base CLI framework for Claude skills.

This module provides the abstract base class for building command-line skills
with proper argument parsing, error handling, and logging.
"""

import argparse
import logging
import sys
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional

from .base_config import BaseConfigLoader, ConfigError
from .base_guardrails import BaseGuardrails, GuardrailViolation


class Command:
    """Represents a single CLI command."""

    def __init__(
        self,
        name: str,
        handler: Callable,
        help_text: str,
        aliases: Optional[List[str]] = None,
    ):
        """Initialize command.

        Args:
            name: Command name
            handler: Callable that executes the command
            help_text: Help text for the command
            aliases: Optional list of aliases
        """
        self.name = name
        self.handler = handler
        self.help_text = help_text
        self.aliases = aliases or []


class BaseSkillCLI(ABC):
    """Abstract base class for skill CLI.

    Implements:
    - Argument parsing and routing
    - Command registration
    - Error handling with user-friendly messages
    - Logging configuration
    - Version display

    Subclasses must implement:
    - skill_name() → name of the skill
    - skill_version() → version string
    - get_config_loader() → ConfigLoader instance
    - get_guardrails() → Guardrails instance
    - register_commands() → register all commands
    """

    def __init__(self):
        """Initialize CLI."""
        self.logger = self._configure_logging()
        self.config_loader = self.get_config_loader()
        self.guardrails = self.get_guardrails()
        self.commands: Dict[str, Command] = {}

    @abstractmethod
    def skill_name(self) -> str:
        """Return skill name.

        Must be implemented by subclasses.

        Returns:
            Skill name (e.g., "jira")
        """
        pass

    @abstractmethod
    def skill_version(self) -> str:
        """Return skill version.

        Must be implemented by subclasses.

        Returns:
            Version string (e.g., "2.0.0")
        """
        pass

    @abstractmethod
    def get_config_loader(self) -> BaseConfigLoader:
        """Return configuration loader.

        Must be implemented by subclasses.

        Returns:
            ConfigLoader instance
        """
        pass

    @abstractmethod
    def get_guardrails(self) -> BaseGuardrails:
        """Return guardrails enforcer.

        Must be implemented by subclasses.

        Returns:
            Guardrails instance
        """
        pass

    @abstractmethod
    def register_commands(self) -> None:
        """Register all available commands.

        Must be implemented by subclasses.
        Use register_command() to add commands.
        """
        pass

    def register_command(
        self,
        name: str,
        handler: Callable,
        help_text: str,
        aliases: Optional[List[str]] = None,
    ) -> None:
        """Register a command.

        Args:
            name: Command name
            handler: Callable that executes the command
            help_text: Help text for the command
            aliases: Optional list of aliases
        """
        command = Command(name, handler, help_text, aliases)
        self.commands[name] = command
        for alias in (aliases or []):
            self.commands[alias] = command

    def main(self, argv: Optional[List[str]] = None) -> int:
        """Main entry point for CLI.

        Args:
            argv: Command line arguments (defaults to sys.argv[1:])

        Returns:
            Exit code (0 = success, 1 = error)
        """
        try:
            return self._run(argv or sys.argv[1:])
        except KeyboardInterrupt:
            print("\n❌ Interrupted by user")
            return 130
        except Exception as e:
            self.logger.exception("Unexpected error")
            print(f"❌ Unexpected error: {e}")
            return 1

    def _run(self, argv: List[str]) -> int:
        """Internal run logic.

        Args:
            argv: Command line arguments

        Returns:
            Exit code
        """
        # Handle no arguments
        if not argv:
            return self._show_help()

        # Handle global flags
        if argv[0] in ("--version", "-v"):
            return self._show_version()

        if argv[0] in ("--help", "-h", "help"):
            return self._show_help()

        # Route to command
        command_name = argv[0]
        command_args = argv[1:]

        if command_name not in self.commands:
            print(f"❌ Unknown command: {command_name}")
            print(f"   Use '{self.skill_name()} --help' for available commands")
            return 1

        try:
            command = self.commands[command_name]
            return command.handler(command_args) or 0
        except ConfigError as e:
            self.logger.error(f"Configuration error: {e}")
            print(f"❌ {e}")
            return 1
        except GuardrailViolation as e:
            self.logger.warning(f"Guardrail violation: {e.action}")
            print(f"{e}")
            return 1
        except Exception as e:
            self.logger.exception(f"Error in {command_name}")
            print(f"❌ Error: {e}")
            return 1

    def _show_version(self) -> int:
        """Show skill version.

        Returns:
            Exit code (0)
        """
        print(f"{self.skill_name()} v{self.skill_version()}")
        return 0

    def _show_help(self) -> int:
        """Show help text.

        Returns:
            Exit code (0)
        """
        help_text = f"""{self.skill_name()} v{self.skill_version()}

Usage: {self.skill_name()} <command> [options]

Global Options:
  --version, -v     Show version
  --help, -h        Show this help text

Available Commands:
"""

        # Group commands by category if available
        commands_shown = set()
        for name, command in self.commands.items():
            if name in commands_shown or name in (a for c in self.commands.values() for a in c.aliases):
                continue

            aliases_text = ""
            if command.aliases:
                aliases_text = f" ({', '.join(command.aliases)})"

            help_text += f"  {command.name:<20} {command.help_text}{aliases_text}\n"
            commands_shown.add(command.name)

        help_text += f"""
Examples:
  {self.skill_name()} --version
  {self.skill_name()} --help
  {self.skill_name()} <command> --help

For more information, visit: https://github.com/rhyscraig/claude-skills
"""

        print(help_text)
        return 0

    def _configure_logging(self) -> logging.Logger:
        """Configure logging.

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(self.skill_name())

        # Only configure if not already configured
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)

        return logger

    def run_with_confirmation(
        self,
        action: str,
        handler: Callable,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Run action with guardrail confirmation if needed.

        Args:
            action: Action name
            handler: Callable to execute if approved
            context: Optional context for confirmation prompt

        Returns:
            True if action was executed, False if declined

        Raises:
            GuardrailViolation: If action is not allowed
        """
        # Check if confirmation is required
        actions_requiring_confirmation = self.guardrails.actions_requiring_confirmation()

        if action not in actions_requiring_confirmation:
            # No confirmation needed, just execute
            try:
                handler()
                return True
            except Exception as e:
                self.logger.error(f"Error in {action}: {e}")
                raise

        # Confirmation required
        confirmed = self.guardrails.confirm_action(
            action, context, user_input=None  # Use interactive prompt
        )

        if not confirmed:
            print(f"❌ Action cancelled: {action}")
            return False

        # Execute action
        try:
            handler()
            return True
        except Exception as e:
            self.logger.error(f"Error in {action}: {e}")
            raise
