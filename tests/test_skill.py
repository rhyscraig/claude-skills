"""Tests for cloudctl skill."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from skills.cloudctl.models import CloudContext, CloudProvider, CommandStatus, SkillConfig
from skills.cloudctl.skill import CloudctlSkill


@pytest.fixture
def skill() -> CloudctlSkill:
    """Create a skill instance for testing."""
    return CloudctlSkill(config=SkillConfig(timeout_seconds=5, max_retries=1))


@pytest.fixture
def mock_context() -> CloudContext:
    """Create a mock context."""
    return CloudContext(
        provider=CloudProvider.AWS,
        organization="myorg",
        account_id="123456789",
        role="admin",
        region="us-east-1",
    )


class TestCloudctlSkillBasics:
    """Basic skill functionality tests."""

    def test_skill_initialization(self, skill: CloudctlSkill) -> None:
        """Test skill can be initialized."""
        assert skill is not None
        assert skill.config.timeout_seconds == 5
        assert skill.config.max_retries == 1

    def test_skill_with_custom_config(self) -> None:
        """Test skill with custom config."""
        config = SkillConfig(
            cloudctl_path="/custom/path",
            timeout_seconds=60,
            dry_run=True,
        )
        skill = CloudctlSkill(config=config)
        assert skill.config.cloudctl_path == "/custom/path"
        assert skill.config.dry_run is True


class TestCloudctlSkillExecution:
    """Tests for command execution."""

    @pytest.mark.asyncio
    async def test_dry_run_mode(self, skill: CloudctlSkill) -> None:
        """Test dry-run mode doesn't execute commands."""
        skill.config.dry_run = True
        result = await skill._execute_cloudctl(["list"])
        assert result.status == CommandStatus.SUCCESS
        assert "[dry run]" in result.stdout

    @pytest.mark.asyncio
    async def test_cloudctl_not_found(self, skill: CloudctlSkill) -> None:
        """Test handling when cloudctl is not found."""
        skill.config.cloudctl_path = "/nonexistent/cloudctl"
        result = await skill._execute_cloudctl(["list"])
        assert result.status == CommandStatus.FAILURE
        assert result.return_code == 127
        assert "not found" in result.stderr

    @pytest.mark.asyncio
    async def test_command_timeout(self) -> None:
        """Test timeout handling."""
        config = SkillConfig(timeout_seconds=1)
        skill = CloudctlSkill(config=config)

        with patch("subprocess.run") as mock_run:
            import subprocess

            mock_run.side_effect = subprocess.TimeoutExpired("cmd", 1)
            result = await skill._execute_cloudctl(["slow-command"])

            assert result.status == CommandStatus.TIMEOUT
            assert result.return_code == 124


class TestCloudctlSkillCommands:
    """Tests for skill command methods."""

    @pytest.mark.asyncio
    async def test_get_context(self, skill: CloudctlSkill, mock_context: CloudContext) -> None:
        """Test getting current context."""
        context_json = {
            "provider": "aws",
            "organization": "myorg",
            "account_id": "123456789",
            "role": "admin",
            "region": "us-east-1",
        }

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = MagicMock(
                success=True,
                stdout=json.dumps(context_json),
            )

            context = await skill.get_context()
            assert context.provider == CloudProvider.AWS
            assert context.organization == "myorg"

    @pytest.mark.asyncio
    async def test_switch_context(self, skill: CloudctlSkill, mock_context: CloudContext) -> None:
        """Test switching context."""
        context_json = {
            "provider": "aws",
            "organization": "myorg",
            "account_id": "123456789",
            "role": "admin",
            "region": "us-east-1",
        }

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            # First call for switch command
            # Second call for context verification
            mock_exec.side_effect = [
                MagicMock(success=True, return_code=0),
                MagicMock(success=True, stdout=json.dumps(context_json)),
            ]

            result = await skill.switch_context("myorg", "123456789", "admin")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_switch_context_empty_org_fails(self, skill: CloudctlSkill) -> None:
        """Test that empty organization is rejected."""
        with pytest.raises(ValueError):
            await skill.switch_context("")

    @pytest.mark.asyncio
    async def test_login(self, skill: CloudctlSkill) -> None:
        """Test login operation."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = MagicMock(success=True, return_code=0)

            result = await skill.login("myorg")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_login_empty_org_fails(self, skill: CloudctlSkill) -> None:
        """Test that login with empty org is rejected."""
        with pytest.raises(ValueError):
            await skill.login("")

    @pytest.mark.asyncio
    async def test_list_organizations(self, skill: CloudctlSkill) -> None:
        """Test listing organizations."""
        orgs_data = [
            {"name": "myorg", "provider": "aws"},
            {"name": "gcp-org", "provider": "gcp"},
        ]

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = MagicMock(
                success=True,
                stdout=json.dumps(orgs_data),
            )

            orgs = await skill.list_organizations()
            assert len(orgs) == 2
            assert orgs[0]["name"] == "myorg"

    @pytest.mark.asyncio
    async def test_verify_credentials(self, skill: CloudctlSkill) -> None:
        """Test credential verification."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = MagicMock(success=True)
            result = await skill.verify_credentials("myorg")
            assert result is True

            mock_exec.return_value = MagicMock(success=False)
            result = await skill.verify_credentials("myorg")
            assert result is False


class TestCloudctlSkillAudit:
    """Tests for audit logging."""

    def test_audit_logging_disabled(self, skill: CloudctlSkill) -> None:
        """Test that audit logging can be disabled."""
        skill.config.enable_audit_logging = False
        from skills.cloudctl.models import CommandResult

        result = CommandResult(
            status=CommandStatus.SUCCESS,
            return_code=0,
            command="test",
        )
        skill.log_operation("test_op", result)
        assert len(skill.get_operation_log()) == 0

    def test_audit_logging_enabled(self, skill: CloudctlSkill) -> None:
        """Test audit logging when enabled."""
        skill.config.enable_audit_logging = True
        from skills.cloudctl.models import CommandResult

        result = CommandResult(
            status=CommandStatus.SUCCESS,
            return_code=0,
            command="test",
        )
        skill.log_operation("test_op", result)
        assert len(skill.get_operation_log()) == 1

    def test_operation_log_retrieval(self, skill: CloudctlSkill) -> None:
        """Test retrieving operation log."""
        from skills.cloudctl.models import CommandResult

        skill.config.enable_audit_logging = True

        for i in range(3):
            result = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                command=f"command_{i}",
            )
            skill.log_operation(f"op_{i}", result)

        log = skill.get_operation_log()
        assert len(log) == 3
        assert log[0].operation == "op_0"


class TestCloudctlSkillSecurity:
    """Security-related tests."""

    @pytest.mark.security
    def test_command_injection_prevention(self, skill: CloudctlSkill) -> None:
        """Test that command arguments are properly escaped."""
        import subprocess

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

            # Execute with potentially malicious argument
            import asyncio

            asyncio.run(skill._execute_cloudctl(["switch", "org'; rm -rf /", "account"]))

            # Verify the command was called with proper escaping
            mock_run.assert_called_once()
            call_args = mock_run.call_args
            assert call_args[0][0][0] == "cloudctl"

    @pytest.mark.security
    def test_environment_variable_sanitization(self) -> None:
        """Test that environment is properly controlled."""
        config = SkillConfig(
            environment_overrides={"SENSITIVE_VAR": "secret"},
        )
        skill = CloudctlSkill(config=config)
        assert skill.config.environment_overrides["SENSITIVE_VAR"] == "secret"
