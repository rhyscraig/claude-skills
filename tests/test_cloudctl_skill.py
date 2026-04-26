"""Comprehensive tests for CloudctlSkill."""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from skills.cloudctl import (
    CloudctlSkill,
    CloudContext,
    CommandResult,
    CommandStatus,
    SkillConfig,
    CloudProvider,
    TokenStatus,
    HealthCheckResult,
)


# ====================== Fixtures ======================


@pytest.fixture
def skill_config():
    """Create a test skill configuration."""
    return SkillConfig(
        cloudctl_path="cloudctl",
        timeout_seconds=30,
        max_retries=3,
        verify_context_after_switch=True,
        enable_audit_logging=False,  # Disable logging for tests
        dry_run=False,
    )


@pytest.fixture
def skill(skill_config):
    """Create a CloudctlSkill instance for testing."""
    return CloudctlSkill(config=skill_config)


@pytest.fixture
def mock_context():
    """Create a mock CloudContext."""
    return CloudContext(
        provider=CloudProvider.AWS,
        organization="myorg",
        account_id="123456789",
        role="terraform",
        region="us-west-2",
    )


@pytest.fixture
def mock_command_result():
    """Create a successful CommandResult."""
    return CommandResult(
        status=CommandStatus.SUCCESS,
        return_code=0,
        stdout="Success",
        stderr="",
        command="test-command",
        duration_seconds=0.1,
    )


# ====================== Unit Tests: Models ======================


class TestCloudContext:
    """Test CloudContext model."""

    def test_context_creation(self):
        """Test creating a CloudContext."""
        context = CloudContext(
            provider=CloudProvider.AWS,
            organization="myorg",
            account_id="123456789",
            role="terraform",
            region="us-west-2",
        )
        assert context.provider == CloudProvider.AWS
        assert context.organization == "myorg"
        assert context.account_id == "123456789"

    def test_context_str_representation(self):
        """Test CloudContext string representation."""
        context = CloudContext(
            provider=CloudProvider.AWS,
            organization="myorg",
            account_id="123456789",
            role="terraform",
            region="us-west-2",
        )
        str_repr = str(context)
        assert "aws:myorg" in str_repr
        assert "account=" in str_repr
        assert "role=" in str_repr
        assert "region=" in str_repr

    def test_context_validation_empty_org(self):
        """Test validation rejects empty organization."""
        with pytest.raises(ValueError):
            CloudContext(
                provider=CloudProvider.AWS,
                organization="",
                account_id="123456789",
            )

    def test_context_validation_whitespace_org(self):
        """Test validation handles whitespace organization."""
        context = CloudContext(
            provider=CloudProvider.AWS,
            organization="  myorg  ",
            account_id="123456789",
        )
        assert context.organization == "myorg"


class TestCommandResult:
    """Test CommandResult model."""

    def test_success_result(self):
        """Test successful command result."""
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            return_code=0,
            stdout="Success",
            command="test",
        )
        assert result.success is True

    def test_failure_result(self):
        """Test failed command result."""
        result = CommandResult(
            status=CommandStatus.FAILURE,
            return_code=1,
            stderr="Error",
            command="test",
        )
        assert result.success is False

    def test_result_str_representation(self):
        """Test CommandResult string representation."""
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            return_code=0,
            command="test-command",
            duration_seconds=1.5,
        )
        str_repr = str(result)
        assert "test-command" in str_repr
        assert "1.50s" in str_repr


class TestSkillConfig:
    """Test SkillConfig model."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = SkillConfig()
        assert config.cloudctl_path == "cloudctl"
        assert config.timeout_seconds == 30
        assert config.max_retries == 3
        assert config.verify_context_after_switch is True
        assert config.enable_audit_logging is True
        assert config.dry_run is False

    def test_config_validation_timeout(self):
        """Test timeout validation."""
        with pytest.raises(ValueError):
            SkillConfig(timeout_seconds=0)  # Too low
        with pytest.raises(ValueError):
            SkillConfig(timeout_seconds=301)  # Too high

    def test_config_validation_retries(self):
        """Test retry validation."""
        with pytest.raises(ValueError):
            SkillConfig(max_retries=-1)  # Negative
        with pytest.raises(ValueError):
            SkillConfig(max_retries=11)  # Too high

    def test_config_from_env(self):
        """Test creating config from environment variables."""
        import os
        os.environ["CLOUDCTL_PATH"] = "/custom/path"
        os.environ["CLOUDCTL_TIMEOUT"] = "60"
        os.environ["CLOUDCTL_RETRIES"] = "5"

        config = SkillConfig.from_env()
        assert config.cloudctl_path == "/custom/path"
        assert config.timeout_seconds == 60
        assert config.max_retries == 5

        # Cleanup
        del os.environ["CLOUDCTL_PATH"]
        del os.environ["CLOUDCTL_TIMEOUT"]
        del os.environ["CLOUDCTL_RETRIES"]


# ====================== Unit Tests: CloudctlSkill ======================


class TestCloudctlSkillInit:
    """Test CloudctlSkill initialization."""

    def test_skill_init_with_config(self, skill_config):
        """Test initializing skill with custom config."""
        skill = CloudctlSkill(config=skill_config)
        assert skill.config == skill_config
        assert skill.console is not None

    def test_skill_init_default_config(self):
        """Test initializing skill with default config."""
        skill = CloudctlSkill()
        assert skill.config is not None
        assert skill.config.cloudctl_path == "cloudctl"

    def test_skill_cloudctl_check(self):
        """Test cloudctl installation check."""
        skill = CloudctlSkill()
        # Should check if cloudctl is available
        assert isinstance(skill._cloudctl_available, bool)


class TestCloudctlSkillContextOperations:
    """Test context-related operations."""

    @pytest.mark.asyncio
    async def test_get_context(self, skill, mock_context):
        """Test getting current context."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="ORGANIZATION=myorg\nACCOUNT_ID=123456789\nROLE=terraform\nREGION=us-west-2\nPROVIDER=aws",
                command="env",
            )

            context = await skill.get_context()
            assert context.organization == "myorg"
            assert context.account_id == "123456789"
            assert context.role == "terraform"
            assert context.region == "us-west-2"
            assert context.provider == CloudProvider.AWS

    @pytest.mark.asyncio
    async def test_switch_context(self, skill):
        """Test switching cloud context."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            # Return different values for env (before/after) and switch calls
            mock_exec.side_effect = [
                CommandResult(  # get_context before (from switch_context)
                    status=CommandStatus.SUCCESS,
                    return_code=0,
                    stdout="ORGANIZATION=myorg\nPROVIDER=aws",
                    command="env",
                ),
                CommandResult(  # switch command
                    status=CommandStatus.SUCCESS,
                    return_code=0,
                    stdout="",
                    command="switch myorg",
                ),
                CommandResult(  # get_context after (from switch_context)
                    status=CommandStatus.SUCCESS,
                    return_code=0,
                    stdout="ORGANIZATION=myorg\nPROVIDER=aws",
                    command="env",
                ),
            ]

            result = await skill.switch_context("myorg")
            assert result.success is True
            assert mock_exec.call_count == 3  # env (before), switch, env (after)

    @pytest.mark.asyncio
    async def test_switch_context_invalid_org(self, skill):
        """Test switching to invalid organization."""
        with pytest.raises(ValueError):
            await skill.switch_context("")

    @pytest.mark.asyncio
    async def test_switch_region(self, skill):
        """Test switching region."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="",
                command="switch region us-east-1",
            )

            result = await skill.switch_region("us-east-1")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_switch_project(self, skill):
        """Test switching GCP project."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="",
                command="switch project my-project",
            )

            result = await skill.switch_project("my-project")
            assert result.success is True


class TestCloudctlSkillOrganizations:
    """Test organization listing and management."""

    @pytest.mark.asyncio
    async def test_list_organizations(self, skill):
        """Test listing organizations."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="Configured Organizations\n  myorg  [AWS]  enabled  https://...\n  gcp-terrorgems  [GCP]  enabled  https://...",
                command="org list",
            )

            orgs = await skill.list_organizations()
            assert len(orgs) == 2
            assert orgs[0]["name"] == "myorg"
            assert orgs[0]["provider"] == "aws"
            assert orgs[1]["name"] == "gcp-terrorgems"
            assert orgs[1]["provider"] == "gcp"

    @pytest.mark.asyncio
    async def test_list_accounts(self, skill):
        """Test listing accounts in an organization."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="Accounts\n  123456789  production\n  987654321  staging",
                command="accounts myorg",
            )

            accounts = await skill.list_accounts("myorg")
            assert len(accounts) == 2
            assert accounts[0]["id"] == "123456789"
            assert accounts[0]["name"] == "production"


class TestCloudctlSkillCredentials:
    """Test credential validation and token management."""

    @pytest.mark.asyncio
    async def test_verify_credentials(self, skill):
        """Test verifying credentials."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="ORGANIZATION=myorg",
                command="env myorg",
            )

            is_valid = await skill.verify_credentials("myorg")
            assert is_valid is True

    @pytest.mark.asyncio
    async def test_verify_credentials_invalid(self, skill):
        """Test verifying invalid credentials."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.FAILURE,
                return_code=1,
                stderr="Not authenticated",
                command="env myorg",
            )

            is_valid = await skill.verify_credentials("myorg")
            assert is_valid is False

    @pytest.mark.asyncio
    async def test_get_token_status(self, skill):
        """Test getting token status."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="ORGANIZATION=myorg",
                command="env myorg",
            )

            with patch.object(skill, "list_organizations") as mock_list_orgs:
                mock_list_orgs.return_value = [{"name": "myorg", "provider": "aws"}]

                status = await skill.get_token_status("myorg")
                assert status.valid is True
                assert status.organization == "myorg"
                assert status.provider == CloudProvider.AWS

    @pytest.mark.asyncio
    async def test_check_all_credentials(self, skill):
        """Test checking all credentials."""
        with patch.object(skill, "list_organizations") as mock_list_orgs:
            mock_list_orgs.return_value = [{"name": "myorg", "provider": "aws"}]

            with patch.object(skill, "verify_credentials") as mock_verify:
                mock_verify.return_value = True

                with patch.object(skill, "get_token_status") as mock_status:
                    mock_status.return_value = TokenStatus(
                        organization="myorg",
                        provider=CloudProvider.AWS,
                        valid=True,
                        expires_in_seconds=3600,
                    )

                    creds = await skill.check_all_credentials()
                    assert "myorg" in creds
                    assert creds["myorg"]["valid"] is True


class TestCloudctlSkillHealthCheck:
    """Test health check functionality."""

    @pytest.mark.asyncio
    async def test_health_check_healthy_system(self, skill):
        """Test health check on healthy system."""
        with patch.object(skill, "list_organizations") as mock_list_orgs:
            mock_list_orgs.return_value = [{"name": "myorg", "provider": "aws"}]

            with patch.object(skill, "verify_credentials") as mock_verify:
                mock_verify.return_value = True

                with patch.object(skill, "_execute_cloudctl") as mock_exec:
                    mock_exec.return_value = CommandResult(
                        status=CommandStatus.SUCCESS,
                        return_code=0,
                        stdout="✓ Everything looks good",
                        command="doctor",
                    )

                    with patch.object(skill, "_cloudctl_available", True):
                        health = await skill.health_check()
                        assert health.is_healthy is True
                        assert health.cloudctl_installed is True
                        assert health.has_credentials is True
                        assert health.can_access_cloud is True

    @pytest.mark.asyncio
    async def test_validate_switch(self, skill):
        """Test validating a context switch."""
        with patch.object(skill, "get_context") as mock_get_context:
            mock_get_context.return_value = CloudContext(
                provider=CloudProvider.AWS,
                organization="myorg",
            )

            with patch.object(skill, "_execute_cloudctl") as mock_exec:
                mock_exec.return_value = CommandResult(
                    status=CommandStatus.SUCCESS,
                    return_code=0,
                    stdout="",
                    command="env myorg",
                )

                is_valid = await skill.validate_switch()
                assert is_valid is True


class TestCloudctlSkillLogin:
    """Test login functionality."""

    @pytest.mark.asyncio
    async def test_login_success(self, skill):
        """Test successful login."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.SUCCESS,
                return_code=0,
                stdout="Authenticated",
                command="login myorg",
            )

            result = await skill.login("myorg")
            assert result.success is True

    @pytest.mark.asyncio
    async def test_login_failure(self, skill):
        """Test failed login."""
        with patch.object(skill, "_execute_cloudctl") as mock_exec:
            mock_exec.return_value = CommandResult(
                status=CommandStatus.FAILURE,
                return_code=1,
                stderr="Authentication failed",
                command="login myorg",
            )

            result = await skill.login("myorg")
            assert result.success is False


class TestCloudctlSkillEnsureAccess:
    """Test ensure_cloud_access method."""

    @pytest.mark.asyncio
    async def test_ensure_access_success(self, skill):
        """Test ensure_cloud_access success path."""
        with patch.object(skill, "list_organizations") as mock_list_orgs:
            mock_list_orgs.return_value = [{"name": "myorg", "provider": "aws"}]

            with patch.object(skill, "get_token_status") as mock_status:
                mock_status.return_value = TokenStatus(
                    organization="myorg",
                    provider=CloudProvider.AWS,
                    valid=True,
                )

                with patch.object(skill, "switch_context") as mock_switch:
                    mock_switch.return_value = CommandResult(
                        status=CommandStatus.SUCCESS,
                        return_code=0,
                        stdout="",
                        command="switch myorg",
                    )

                    with patch.object(skill, "validate_switch") as mock_validate:
                        mock_validate.return_value = True

                        with patch.object(skill, "get_context") as mock_get_context:
                            mock_get_context.return_value = CloudContext(
                                provider=CloudProvider.AWS,
                                organization="myorg",
                            )

                            result = await skill.ensure_cloud_access("myorg")
                            assert result["success"] is True
                            assert result["org"] == "myorg"

    @pytest.mark.asyncio
    async def test_ensure_access_invalid_org(self, skill):
        """Test ensure_cloud_access with invalid org."""
        with patch.object(skill, "list_organizations") as mock_list_orgs:
            mock_list_orgs.return_value = []

            result = await skill.ensure_cloud_access("nonexistent")
            assert result["success"] is False
            assert "Organization" in result["error"]


# ====================== Integration Tests ======================


@pytest.mark.integration
class TestCloudctlSkillIntegration:
    """Integration tests requiring actual cloudctl installation."""

    @pytest.mark.asyncio
    async def test_integration_get_context(self, skill):
        """Test getting actual context from cloudctl."""
        # Skip if cloudctl not installed
        if not skill._cloudctl_available:
            pytest.skip("cloudctl not installed")

        context = await skill.get_context()
        assert isinstance(context, CloudContext)
        assert context.provider in [CloudProvider.AWS, CloudProvider.GCP, CloudProvider.AZURE]
        assert context.organization

    @pytest.mark.asyncio
    async def test_integration_list_orgs(self, skill):
        """Test listing actual organizations."""
        if not skill._cloudctl_available:
            pytest.skip("cloudctl not installed")

        orgs = await skill.list_organizations()
        assert isinstance(orgs, list)


# ====================== Test Cloud Providers ======================


class TestCloudProviderEnum:
    """Test CloudProvider enum."""

    def test_cloud_provider_values(self):
        """Test CloudProvider enum values."""
        assert CloudProvider.AWS.value == "aws"
        assert CloudProvider.GCP.value == "gcp"
        assert CloudProvider.AZURE.value == "azure"

    def test_cloud_provider_creation(self):
        """Test creating CloudProvider from string."""
        assert CloudProvider("aws") == CloudProvider.AWS
        assert CloudProvider("gcp") == CloudProvider.GCP
        assert CloudProvider("azure") == CloudProvider.AZURE


# ====================== Markers & Configuration ======================


pytestmark = [
    pytest.mark.unit,  # Default to unit tests
]
