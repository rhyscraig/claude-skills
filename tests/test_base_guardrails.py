"""Tests for base guardrails.

Demonstrates pragmatic testing patterns for safety enforcement:
- Confirmation gates for sensitive operations
- Rate limiting
- Audit logging
- Permission validation
"""

from typing import Any, Dict, List

import pytest

from src.base_guardrails import BaseGuardrails, GuardrailViolation


class TestGuardrails(BaseGuardrails):
    """Test implementation of BaseGuardrails."""

    def actions_requiring_confirmation(self) -> List[str]:
        """Return actions requiring confirmation."""
        return ["delete", "reassign", "transition_to_done"]

    def get_rate_limits(self) -> Dict[str, int]:
        """Return rate limits."""
        return {
            "create": 100,
            "delete": 10,
            "reassign": 50,
        }


class TestBaseGuardrails:
    """Test suite for base guardrails."""

    def test_action_allowed_without_confirmation(self):
        """Test that non-gated actions are allowed."""
        guardrails = TestGuardrails({})

        # 'list' is not in confirmation list
        assert guardrails.can_perform("list", require_confirmation=False)

    def test_action_blocked_without_confirmation(self):
        """Test that gated actions are blocked without confirmation."""
        guardrails = TestGuardrails({})

        # 'delete' requires confirmation
        assert not guardrails.can_perform("delete", require_confirmation=True)

    def test_confirmation_grants_permission(self):
        """Test that confirmation allows action."""
        guardrails = TestGuardrails({})

        # Mock user confirmation
        def mock_confirm():
            return True

        # After confirmation, action should be allowed
        confirmed = guardrails.confirm_action("delete", user_input=mock_confirm)
        assert confirmed is True

    def test_declined_confirmation_blocks_action(self):
        """Test that declined confirmation blocks action."""
        guardrails = TestGuardrails({})

        # Mock user declining
        def mock_decline():
            return False

        confirmed = guardrails.confirm_action("delete", user_input=mock_decline)
        assert confirmed is False

    def test_rate_limit_enforcement(self):
        """Test rate limit enforcement."""
        guardrails = TestGuardrails({})

        # Can perform up to limit
        for i in range(10):
            def mock_confirm():
                return True

            guardrails.confirm_action("delete", user_input=mock_confirm)

        # Exceeding limit should raise
        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.confirm_action("delete", user_input=mock_confirm)

        assert "Rate limit" in str(exc_info.value)

    def test_audit_logging(self):
        """Test audit log recording."""
        guardrails = TestGuardrails({})

        def mock_confirm():
            return True

        guardrails.confirm_action("delete", user_input=mock_confirm, context={"ticket": "TG-123"})

        # Check audit log
        log = guardrails.get_audit_log()
        assert len(log) == 1
        assert log[0].action == "delete"
        assert log[0].status == "confirmed"
        assert log[0].context["ticket"] == "TG-123"

    def test_multiple_actions_tracked(self):
        """Test tracking multiple different actions."""
        guardrails = TestGuardrails({})

        def mock_confirm():
            return True

        guardrails.confirm_action("delete", user_input=mock_confirm)
        guardrails.confirm_action("reassign", user_input=mock_confirm)
        guardrails.confirm_action("delete", user_input=mock_confirm)

        log = guardrails.get_audit_log()
        assert len(log) == 3
        assert log[0].action == "delete"
        assert log[1].action == "reassign"
        assert log[2].action == "delete"

    def test_reset_counters(self):
        """Test resetting rate limit counters."""
        guardrails = TestGuardrails({})

        def mock_confirm():
            return True

        # Use up some deletions
        for _ in range(5):
            guardrails.confirm_action("delete", user_input=mock_confirm)

        # Reset counters
        guardrails.reset_counters()

        # Should be able to delete again
        guardrails.confirm_action("delete", user_input=mock_confirm)

    def test_reset_audit_log(self):
        """Test clearing audit log."""
        guardrails = TestGuardrails({})

        def mock_confirm():
            return True

        guardrails.confirm_action("delete", user_input=mock_confirm)
        guardrails.confirm_action("reassign", user_input=mock_confirm)

        assert len(guardrails.get_audit_log()) == 2

        guardrails.reset_audit_log()

        assert len(guardrails.get_audit_log()) == 0

    def test_context_in_audit_log(self):
        """Test that action context is logged."""
        guardrails = TestGuardrails({})

        def mock_confirm():
            return True

        context = {
            "ticket": "TG-123",
            "reassigning_to": "alice@example.com",
            "reason": "Escalation",
        }

        guardrails.confirm_action("reassign", user_input=mock_confirm, context=context)

        log = guardrails.get_audit_log()
        assert log[0].context == context

    def test_confirmation_prompt_formatting(self):
        """Test confirmation prompt is properly formatted."""
        guardrails = TestGuardrails({})

        prompt = guardrails._format_confirmation_prompt(
            "delete",
            context={"ticket": "TG-123"},
        )

        assert "delete" in prompt
        assert "TG-123" in prompt

    def test_get_current_user(self):
        """Test getting current user (with fallback)."""
        guardrails = TestGuardrails({})

        user = guardrails._get_current_user()
        assert user  # Should have some value
        assert isinstance(user, str)

    def test_blocked_action_raises_violation(self):
        """Test that blocked actions raise GuardrailViolation."""
        guardrails = TestGuardrails({})

        # Custom implementation that blocks specific action
        class BlockingGuardrails(TestGuardrails):
            def _is_blocked_by_config(self, action: str, context: Any = None) -> bool:
                return action == "dangerous_operation"

        guardrails = BlockingGuardrails({})

        with pytest.raises(GuardrailViolation) as exc_info:
            guardrails.can_perform("dangerous_operation", require_confirmation=False)

        assert "not allowed" in str(exc_info.value).lower()

    def test_different_rate_limits_per_action(self):
        """Test that different actions have different rate limits."""
        guardrails = TestGuardrails({})

        def mock_confirm():
            return True

        # Create: limit 100
        # Delete: limit 10
        # Reassign: limit 50

        # Should allow 11 deletes before hitting limit
        for i in range(10):
            guardrails.confirm_action("delete", user_input=mock_confirm)

        # 11th should fail
        with pytest.raises(GuardrailViolation):
            guardrails.confirm_action("delete", user_input=mock_confirm)

        # But reassign should still work
        guardrails.confirm_action("reassign", user_input=mock_confirm)
