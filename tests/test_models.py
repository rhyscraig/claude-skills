"""Tests for data models."""

import pytest
from pydantic import ValidationError

from skills.cloudctl.models import CloudContext, CloudProvider, CommandResult, CommandStatus, SkillConfig


class TestCommandResult:
    """Tests for CommandResult model."""

    def test_successful_result(self) -> None:
        """Test successful command result."""
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            return_code=0,
            stdout="output",
            command="test",
        )
        assert result.success is True
        assert result.return_code == 0

    def test_failed_result(self) -> None:
        """Test failed command result."""
        result = CommandResult(
            status=CommandStatus.FAILURE,
            return_code=1,
            stderr="error",
            command="test",
        )
        assert result.success is False
        assert result.return_code == 1

    def test_timeout_result(self) -> None:
        """Test timeout result."""
        result = CommandResult(
            status=CommandStatus.TIMEOUT,
            return_code=124,
            command="test",
        )
        assert result.success is False

    def test_str_representation(self) -> None:
        """Test string representation."""
        result = CommandResult(
            status=CommandStatus.SUCCESS,
            return_code=0,
            command="cloudctl list",
            duration_seconds=1.5,
        )
        str_repr = str(result)
        assert "✅" in str_repr
        assert "cloudctl list" in str_repr


class TestCloudContext:
    """Tests for CloudContext model."""

    def test_valid_context(self) -> None:
        """Test valid context."""
        context = CloudContext(
            provider=CloudProvider.AWS,
            organization="myorg",
            account_id="123456789",
            role="admin",
            region="us-east-1",
        )
        assert context.provider == CloudProvider.AWS
        assert context.organization == "myorg"

    def test_empty_organization_fails(self) -> None:
        """Test that empty organization is rejected."""
        with pytest.raises(ValidationError):
            CloudContext(provider=CloudProvider.AWS, organization="")

    def test_long_organization_fails(self) -> None:
        """Test that very long organization name is rejected."""
        with pytest.raises(ValidationError):
            CloudContext(provider=CloudProvider.AWS, organization="x" * 300)

    def test_context_str_representation(self) -> None:
        """Test string representation includes all parts."""
        context = CloudContext(
            provider=CloudProvider.GCP,
            organization="gcp-org",
            project_id="my-project",
            role="editor",
        )
        str_repr = str(context)
        assert "gcp-org" in str_repr
        assert "my-project" in str_repr

    def test_context_with_minimal_fields(self) -> None:
        """Test context with only required fields."""
        context = CloudContext(
            provider=CloudProvider.AZURE,
            organization="azure-org",
        )
        assert context.account_id is None
        assert context.region is None


class TestSkillConfig:
    """Tests for SkillConfig model."""

    def test_default_config(self) -> None:
        """Test default configuration."""
        config = SkillConfig()
        assert config.cloudctl_path == "cloudctl"
        assert config.timeout_seconds == 30
        assert config.max_retries == 3

    def test_invalid_timeout(self) -> None:
        """Test that invalid timeout is rejected."""
        with pytest.raises(ValidationError):
            SkillConfig(timeout_seconds=0)

        with pytest.raises(ValidationError):
            SkillConfig(timeout_seconds=400)

    def test_invalid_retries(self) -> None:
        """Test that invalid retry count is rejected."""
        with pytest.raises(ValidationError):
            SkillConfig(max_retries=-1)

        with pytest.raises(ValidationError):
            SkillConfig(max_retries=15)

    def test_custom_config(self) -> None:
        """Test custom configuration."""
        config = SkillConfig(
            cloudctl_path="/usr/local/bin/cloudctl",
            timeout_seconds=60,
            max_retries=5,
            dry_run=True,
        )
        assert config.cloudctl_path == "/usr/local/bin/cloudctl"
        assert config.timeout_seconds == 60
        assert config.dry_run is True

    def test_environment_overrides(self) -> None:
        """Test environment variable overrides."""
        config = SkillConfig(
            environment_overrides={
                "AWS_REGION": "eu-west-1",
                "CUSTOM_VAR": "value",
            }
        )
        assert config.environment_overrides["AWS_REGION"] == "eu-west-1"
