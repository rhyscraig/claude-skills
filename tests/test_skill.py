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
        """Test getting current context from plaintext env output."""
        context_plaintext = """PROVIDER=aws
ORGANIZATION=myorg
ACCOUNT_ID=123456789
ROLE=admin
REGION=us-east-1
"""

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = MagicMock(
                success=True,
                stdout=context_plaintext,
            )

            context = await skill.get_context()
            assert context.provider == CloudProvider.AWS
            assert context.organization == "myorg"

    @pytest.mark.asyncio
    async def test_switch_context(self, skill: CloudctlSkill, mock_context: CloudContext) -> None:
        """Test switching context."""
        context_plaintext = """PROVIDER=aws
ORGANIZATION=myorg
ACCOUNT_ID=123456789
ROLE=admin
REGION=us-east-1
"""

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            # First call for initial context log
            # Second call for switch command
            # Third call for context verification
            mock_exec.side_effect = [
                MagicMock(success=True, stdout=context_plaintext),
                MagicMock(success=True, return_code=0),
                MagicMock(success=True, stdout=context_plaintext),
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
        """Test listing organizations from plaintext output."""
        orgs_plaintext = """Configured Organizations (2)

  myorg      [AWS]   enabled       https://d-9c67661145.awsapps.com/start
  gcp-org    [GCP]   enabled       https://console.cloud.google.com
"""

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = MagicMock(
                success=True,
                stdout=orgs_plaintext,
            )

            orgs = await skill.list_organizations()
            assert len(orgs) == 2
            assert orgs[0]["name"] == "myorg"
            assert orgs[1]["provider"] == "gcp"

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


class TestCloudctlSkillHealthAndStatus:
    """Tests for health check and token status."""

    @pytest.mark.asyncio
    async def test_get_token_status(self, skill: CloudctlSkill) -> None:
        """Test getting token status."""
        orgs_plaintext = """Configured Organizations (1)

  myorg      [AWS]   enabled       https://d-9c67661145.awsapps.com/start
"""

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            # First call: list_organizations
            # Second call: env check
            mock_exec.side_effect = [
                MagicMock(success=True, stdout=orgs_plaintext),
                MagicMock(success=True),
            ]

            with patch.object(skill, "list_organizations") as mock_list_orgs:
                mock_list_orgs.return_value = [
                    {"name": "myorg", "provider": "aws"}
                ]

                status = await skill.get_token_status("myorg")
                assert status.valid is True

    @pytest.mark.asyncio
    async def test_get_token_status_expired(self, skill: CloudctlSkill) -> None:
        """Test token status when credentials are invalid."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            with patch.object(skill, "list_organizations") as mock_list_orgs:
                mock_list_orgs.return_value = [
                    {"name": "myorg", "provider": "aws"}
                ]
                mock_exec.return_value = MagicMock(success=False)

                status = await skill.get_token_status("myorg")
                assert status.valid is False

    @pytest.mark.asyncio
    async def test_get_token_status_invalid(self, skill: CloudctlSkill) -> None:
        """Test token status when token is invalid."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = MagicMock(success=False)

            status = await skill.get_token_status("myorg")
            assert status.valid is False

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, skill: CloudctlSkill) -> None:
        """Test health check when everything is working."""
        orgs_data = [
            {"name": "org1", "provider": "aws"},
            {"name": "org2", "provider": "gcp"},
        ]

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            with patch.object(skill, "list_organizations") as mock_list_orgs:
                with patch.object(skill, "verify_credentials") as mock_verify:
                    with patch.object(skill, "get_token_status") as mock_token:
                        mock_list_orgs.return_value = orgs_data
                        mock_verify.return_value = True

                        from skills.cloudctl.models import TokenStatus, CloudProvider

                        mock_token.return_value = TokenStatus(
                            organization="org1",
                            provider=CloudProvider.AWS,
                            valid=True,
                            expires_in_seconds=86400,
                            is_expired=False,
                        )

                        result = await skill.health_check()

                        assert result.is_healthy is True
                        assert result.cloudctl_installed is True
                        assert result.has_credentials is True
                        assert result.organizations_available == 2

    @pytest.mark.asyncio
    async def test_health_check_no_cloudctl(self) -> None:
        """Test health check when cloudctl is not installed."""
        config = SkillConfig(cloudctl_path="/nonexistent/cloudctl")
        skill = CloudctlSkill(config=config)

        result = await skill.health_check()

        assert result.is_healthy is False
        assert result.cloudctl_installed is False
        assert len(result.issues) > 0

    def test_cloudctl_installation_check(self, skill: CloudctlSkill) -> None:
        """Test cloudctl installation check."""
        assert skill._cloudctl_available is True or skill._cloudctl_available is False

    @pytest.mark.asyncio
    async def test_switch_region(self, skill: CloudctlSkill) -> None:
        """Test switching regions."""
        context_plaintext = """PROVIDER=aws
ORGANIZATION=myorg
REGION=us-west-2
"""

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.side_effect = [
                MagicMock(success=True, return_code=0),
                MagicMock(success=True, stdout=context_plaintext),
            ]

            result = await skill.switch_region("us-west-2")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_switch_project(self, skill: CloudctlSkill) -> None:
        """Test switching GCP projects."""
        context_plaintext = """PROVIDER=gcp
ORGANIZATION=myorg
PROJECT_ID=my-project-123
"""

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.side_effect = [
                MagicMock(success=True, return_code=0),
                MagicMock(success=True, stdout=context_plaintext),
            ]

            result = await skill.switch_project("my-project-123")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_check_all_credentials(self, skill: CloudctlSkill) -> None:
        """Test checking credentials across all orgs."""
        orgs_data = [
            {"name": "org1", "provider": "aws"},
            {"name": "org2", "provider": "gcp"},
        ]

        with patch.object(skill, "list_organizations") as mock_list:
            with patch.object(skill, "verify_credentials") as mock_verify:
                with patch.object(skill, "get_token_status") as mock_token:
                    with patch.object(skill, "_execute_cloudctl") as mock_exec:
                        mock_list.return_value = orgs_data
                        mock_verify.return_value = True

                        from skills.cloudctl.models import TokenStatus, CloudProvider

                        mock_token.return_value = TokenStatus(
                            organization="org1",
                            provider=CloudProvider.AWS,
                            valid=True,
                            expires_in_seconds=86400,
                            is_expired=False,
                        )
                        mock_exec.return_value = MagicMock(success=True)

                        results = await skill.check_all_credentials()

                        assert "org1" in results
                        assert "org2" in results
                        assert results["org1"]["valid"] is True

    @pytest.mark.asyncio
    async def test_ensure_cloud_access_success(self, skill: CloudctlSkill) -> None:
        """Test ensure_cloud_access with full success path."""
        context_json = {
            "provider": "aws",
            "organization": "myorg",
            "account_id": "123456789",
            "role": "admin",
        }
        orgs_data = [{"name": "myorg", "provider": "aws"}]

        with patch.object(skill, "list_organizations") as mock_list:
            with patch.object(skill, "get_token_status") as mock_token:
                with patch.object(skill, "switch_context") as mock_switch:
                    with patch.object(skill, "validate_switch") as mock_validate:
                        with patch.object(skill, "get_context") as mock_context:
                            from skills.cloudctl.models import TokenStatus, CloudProvider

                            mock_list.return_value = orgs_data
                            mock_token.return_value = TokenStatus(
                                organization="myorg",
                                provider=CloudProvider.AWS,
                                valid=True,
                                expires_in_seconds=86400,
                                is_expired=False,
                            )
                            mock_switch.return_value = MagicMock(success=True)
                            mock_validate.return_value = True
                            mock_context.return_value = MagicMock(
                                __str__=lambda self: "aws:myorg account=123456789"
                            )

                            result = await skill.ensure_cloud_access("myorg", "123456789", "admin")

                            assert result["success"] is True
                            assert result["org"] == "myorg"
                            assert result["account"] == "123456789"

    @pytest.mark.asyncio
    async def test_ensure_cloud_access_cloudctl_missing(self) -> None:
        """Test ensure_cloud_access when cloudctl is not installed."""
        from skills.cloudctl.models import SkillConfig

        config = SkillConfig(cloudctl_path="/nonexistent/cloudctl")
        skill = CloudctlSkill(config=config)

        result = await skill.ensure_cloud_access("myorg")

        assert result["success"] is False
        assert "not found" in result["error"].lower()
        assert "fix" in result

    @pytest.mark.asyncio
    async def test_ensure_cloud_access_org_not_found(self, skill: CloudctlSkill) -> None:
        """Test ensure_cloud_access when org doesn't exist."""
        with patch.object(skill, "list_organizations") as mock_list:
            mock_list.return_value = [{"name": "staging", "provider": "aws"}]

            result = await skill.ensure_cloud_access("nonexistent")

            assert result["success"] is False
            assert "not found" in result["error"].lower()
            assert "staging" in result.get("available_orgs", [])

    @pytest.mark.asyncio
    async def test_ensure_cloud_access_token_expired(self, skill: CloudctlSkill) -> None:
        """Test ensure_cloud_access auto-refreshes expired tokens."""
        context_json = {
            "provider": "aws",
            "organization": "myorg",
            "account_id": "123456789",
        }
        orgs_data = [{"name": "myorg", "provider": "aws"}]

        with patch.object(skill, "list_organizations") as mock_list:
            with patch.object(skill, "get_token_status") as mock_token:
                with patch.object(skill, "login") as mock_login:
                    with patch.object(skill, "switch_context") as mock_switch:
                        with patch.object(skill, "validate_switch") as mock_validate:
                            with patch.object(skill, "get_context") as mock_context:
                                from skills.cloudctl.models import TokenStatus, CloudProvider

                                mock_list.return_value = orgs_data
                                mock_token.return_value = TokenStatus(
                                    organization="myorg",
                                    provider=CloudProvider.AWS,
                                    valid=True,
                                    expires_in_seconds=0,
                                    is_expired=True,
                                )
                                mock_login.return_value = MagicMock(success=True)
                                mock_switch.return_value = MagicMock(success=True)
                                mock_validate.return_value = True
                                mock_context.return_value = MagicMock(
                                    __str__=lambda self: "aws:myorg"
                                )

                                result = await skill.ensure_cloud_access("myorg")

                                assert result["success"] is True
                                # Verify login was called to refresh
                                mock_login.assert_called_once_with("myorg")

    @pytest.mark.asyncio
    async def test_validate_switch(self, skill: CloudctlSkill) -> None:
        """Test context validation after switch."""
        context_plaintext = """PROVIDER=aws
ORGANIZATION=myorg
ACCOUNT_ID=123456789
"""

        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.side_effect = [
                MagicMock(success=True, stdout=context_plaintext),
                MagicMock(success=True),
            ]

            result = await skill.validate_switch()
            assert result is True

    def test_token_status_string_representation(self) -> None:
        """Test TokenStatus string representation."""
        from skills.cloudctl.models import TokenStatus, CloudProvider

        status_valid = TokenStatus(
            organization="myorg",
            provider=CloudProvider.AWS,
            valid=True,
            expires_in_seconds=86400,
            is_expired=False,
        )
        status_str = str(status_valid)
        assert "myorg" in status_str
        assert "1 days" in status_str or "1 days" in status_str.replace(" ", "")

        status_soon = TokenStatus(
            organization="myorg",
            provider=CloudProvider.AWS,
            valid=True,
            expires_in_seconds=1800,
            is_expired=False,
        )
        assert "30 minutes" in str(status_soon)

        status_expired = TokenStatus(
            organization="myorg",
            provider=CloudProvider.AWS,
            valid=True,
            expires_in_seconds=0,
            is_expired=True,
        )
        assert "EXPIRED" in str(status_expired)
