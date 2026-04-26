"""Base guardrails for safety enforcement and permission gating.

This module provides abstract base class for implementing safety checks,
confirmation gates, audit logging, and permission enforcement.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ActionType(Enum):
    """Type of action being gated."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REASSIGN = "reassign"
    TRANSITION = "transition"
    EXECUTE = "execute"


@dataclass
class GuardrailViolation(Exception):
    """Guardrail violation (action blocked for safety)."""

    action: str
    reason: str
    context: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        msg = f"🚫 Action blocked: {self.action}\n   Reason: {self.reason}"
        if self.context:
            msg += f"\n   Context: {self.context}"
        return msg


@dataclass
class AuditLogEntry:
    """Single entry in the audit log."""

    timestamp: datetime
    user: str
    action: str
    status: str  # "allowed", "blocked", "confirmed"
    reason: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class BaseGuardrails(ABC):
    """Abstract base class for safety enforcement.

    Implements:
    - Confirmation gates for sensitive operations
    - Rate limiting and batch operation guards
    - Audit logging
    - Permission enforcement

    Subclasses must implement:
    - actions_requiring_confirmation() → list of action types
    - get_rate_limits() → dict of action → max count/period
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize guardrails with configuration.

        Args:
            config: Configuration dict with guardrail settings
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        self._audit_log: List[AuditLogEntry] = []
        self._action_counts: Dict[str, int] = {}

    @abstractmethod
    def actions_requiring_confirmation(self) -> List[str]:
        """Return list of action names requiring user confirmation.

        Must be implemented by subclasses.

        Returns:
            List of action names (e.g., ["reassign", "delete"])
        """
        pass

    @abstractmethod
    def get_rate_limits(self) -> Dict[str, int]:
        """Return rate limits for actions.

        Format: {"action_name": max_per_run}

        Must be implemented by subclasses.

        Returns:
            Dict mapping action names to maximum count per run
        """
        pass

    def can_perform(
        self, action: str, context: Optional[Dict[str, Any]] = None, require_confirmation: bool = True
    ) -> bool:
        """Check if action is allowed by guardrails.

        Checks:
        1. Is action in blocklist?
        2. Have we hit rate limits?
        3. Does action require confirmation (if enabled)?

        Args:
            action: Action name (e.g., "reassign", "delete")
            context: Optional context dict with action details
            require_confirmation: Whether to require user confirmation

        Returns:
            True if action is allowed, False if blocked

        Raises:
            GuardrailViolation: If action is blocked with reason
        """
        # Check rate limits
        rate_limits = self.get_rate_limits()
        if action in rate_limits:
            current_count = self._action_counts.get(action, 0)
            if current_count >= rate_limits[action]:
                raise GuardrailViolation(
                    action=action,
                    reason=f"Rate limit exceeded: {action} "
                    f"({current_count}/{rate_limits[action]} per run)",
                    context=context,
                )

        # Check if confirmation required
        if require_confirmation and action in self.actions_requiring_confirmation():
            return False  # Not allowed until confirmed

        # Check config-based blockers
        if self._is_blocked_by_config(action, context):
            raise GuardrailViolation(
                action=action,
                reason=f"Action '{action}' is blocked by guardrails",
                context=context,
            )

        return True

    def confirm_action(
        self, action: str, context: Optional[Dict[str, Any]] = None, user_input: Optional[Callable[[], bool]] = None
    ) -> bool:
        """Get user confirmation for an action.

        Args:
            action: Action name requiring confirmation
            context: Optional context (used in confirmation prompt)
            user_input: Optional callable for getting confirmation.
                       If not provided, uses interactive prompt.

        Returns:
            True if user confirmed, False if user declined

        Raises:
            GuardrailViolation: If action is not allowed at all
        """
        # First, check if action is even allowed
        if not self.can_perform(action, context, require_confirmation=False):
            raise GuardrailViolation(
                action=action,
                reason=f"Action '{action}' is not allowed",
                context=context,
            )

        # Prepare confirmation prompt
        prompt = self._format_confirmation_prompt(action, context)

        # Get user response
        if user_input:
            confirmed = user_input()
        else:
            confirmed = self._interactive_confirm(prompt)

        # Log result
        self._log_audit(
            action=action,
            status="confirmed" if confirmed else "declined",
            context=context,
        )

        if confirmed:
            self._action_counts[action] = self._action_counts.get(action, 0) + 1

        return confirmed

    def _is_blocked_by_config(self, action: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """Check if action is blocked by configuration.

        Override in subclasses to implement custom blocking logic.

        Args:
            action: Action name
            context: Optional context

        Returns:
            True if action is blocked, False otherwise
        """
        return False

    def _format_confirmation_prompt(self, action: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Format confirmation prompt for user.

        Override in subclasses for custom prompts.

        Args:
            action: Action name
            context: Optional context

        Returns:
            Formatted prompt string
        """
        prompt = f"⚠️  Action requires confirmation: {action}"
        if context:
            prompt += f"\n   Context: {context}"
        prompt += "\n   Proceed? (yes/no): "
        return prompt

    def _interactive_confirm(self, prompt: str) -> bool:
        """Get interactive confirmation from user.

        Args:
            prompt: Confirmation prompt to display

        Returns:
            True if user confirms (y/yes), False otherwise
        """
        response = input(prompt).strip().lower()
        return response in ("y", "yes")

    def _log_audit(
        self, action: str, status: str, reason: Optional[str] = None, context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Log action to audit log.

        Args:
            action: Action name
            status: Status ("allowed", "blocked", "confirmed")
            reason: Optional reason for status
            context: Optional context dict
        """
        entry = AuditLogEntry(
            timestamp=datetime.now(),
            user=self._get_current_user(),
            action=action,
            status=status,
            reason=reason,
            context=context,
        )
        self._audit_log.append(entry)
        self.logger.info(
            f"Audit: {action} [{status}]",
            extra={"audit": entry.__dict__},
        )

    def _get_current_user(self) -> str:
        """Get current user identifier.

        Override in subclasses for custom user identification.

        Returns:
            User identifier (username, email, etc.)
        """
        import os

        return os.environ.get("USER", "unknown")

    def get_audit_log(self) -> List[AuditLogEntry]:
        """Get audit log entries.

        Returns:
            List of audit log entries
        """
        return self._audit_log.copy()

    def reset_counters(self) -> None:
        """Reset action counters (typically at start of new run)."""
        self._action_counts.clear()

    def reset_audit_log(self) -> None:
        """Clear audit log."""
        self._audit_log.clear()
