"""Data models for cloudctl skill with validation and serialization."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CloudProvider(str, Enum):
    """Supported cloud providers."""

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


class CommandStatus(str, Enum):
    """Status of command execution."""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    TIMEOUT = "timeout"


class CommandResult(BaseModel):
    """Result of a cloudctl command execution."""

    model_config = ConfigDict(use_enum_values=False)

    status: CommandStatus
    return_code: int
    stdout: str = ""
    stderr: str = ""
    command: str
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        """Check if command succeeded."""
        return self.status == CommandStatus.SUCCESS and self.return_code == 0

    def __str__(self) -> str:
        """Human-readable representation."""
        status_icon = "✅" if self.success else "❌"
        return f"{status_icon} {self.command} (exit: {self.return_code}, {self.duration_seconds:.2f}s)"


class CloudContext(BaseModel):
    """Current cloud context state."""

    model_config = ConfigDict(use_enum_values=False)

    provider: CloudProvider
    organization: str
    account_id: Optional[str] = None
    role: Optional[str] = None
    region: Optional[str] = None
    project_id: Optional[str] = None

    @field_validator("organization")
    @classmethod
    def validate_org(cls, v: str) -> str:
        """Validate organization name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Organization cannot be empty")
        if len(v) > 255:
            raise ValueError("Organization name too long")
        return v.strip()

    def __str__(self) -> str:
        """Human-readable representation."""
        parts = [f"{self.provider.value}:{self.organization}"]
        if self.account_id:
            parts.append(f"account={self.account_id}")
        if self.role:
            parts.append(f"role={self.role}")
        if self.region:
            parts.append(f"region={self.region}")
        if self.project_id:
            parts.append(f"project={self.project_id}")
        return " ".join(parts)


class SkillConfig(BaseModel):
    """Configuration for cloudctl skill."""

    model_config = ConfigDict(validate_assignment=True)

    cloudctl_path: str = "cloudctl"
    timeout_seconds: int = 30
    max_retries: int = 3
    verify_context_after_switch: bool = True
    enable_audit_logging: bool = True
    dry_run: bool = False
    environment_overrides: dict[str, str] = Field(default_factory=dict)

    @field_validator("timeout_seconds")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout value."""
        if v < 1 or v > 300:
            raise ValueError("Timeout must be between 1 and 300 seconds")
        return v

    @field_validator("max_retries")
    @classmethod
    def validate_retries(cls, v: int) -> int:
        """Validate retry count."""
        if v < 0 or v > 10:
            raise ValueError("Max retries must be between 0 and 10")
        return v

    @classmethod
    def from_env(cls) -> "SkillConfig":
        """Create config from environment variables."""
        import os

        return cls(
            cloudctl_path=os.getenv("CLOUDCTL_PATH", "cloudctl"),
            timeout_seconds=int(os.getenv("CLOUDCTL_TIMEOUT", "30")),
            max_retries=int(os.getenv("CLOUDCTL_RETRIES", "3")),
            verify_context_after_switch=os.getenv("CLOUDCTL_VERIFY", "true").lower() == "true",
            enable_audit_logging=os.getenv("CLOUDCTL_AUDIT", "true").lower() == "true",
            dry_run=os.getenv("CLOUDCTL_DRY_RUN", "false").lower() == "true",
        )


class OperationLog(BaseModel):
    """Audit log entry for operations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    timestamp: str
    operation: str
    context_before: Optional[CloudContext] = None
    context_after: Optional[CloudContext] = None
    result: CommandResult
    user: Optional[str] = None
    success: bool
    notes: str = ""


class TokenStatus(BaseModel):
    """Token expiry status for an organization."""

    organization: str
    provider: CloudProvider
    valid: bool
    expires_at: Optional[str] = None
    expires_in_seconds: Optional[int] = None
    is_expired: bool = False

    def __str__(self) -> str:
        """Human-readable representation."""
        if not self.valid:
            return f"❌ {self.organization}: Invalid or missing token"
        if self.is_expired:
            return f"⏰ {self.organization}: Token EXPIRED"
        if self.expires_in_seconds:
            hours = self.expires_in_seconds / 3600
            if hours < 1:
                return f"🔴 {self.organization}: Token expires in {int(self.expires_in_seconds // 60)} minutes"
            elif hours < 24:
                return f"🟡 {self.organization}: Token expires in {int(hours)} hours"
            else:
                return f"✅ {self.organization}: Token valid for {int(hours // 24)} days"
        return f"✅ {self.organization}: Token valid"


class HealthCheckResult(BaseModel):
    """Result of health check operation."""

    cloudctl_installed: bool
    cloudctl_version: Optional[str] = None
    has_credentials: bool = False
    organizations_available: int = 0
    can_access_cloud: bool = False
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    def __str__(self) -> str:
        """Human-readable representation."""
        status = "✅ HEALTHY" if self.is_healthy else "❌ ISSUES FOUND"
        lines = [f"[bold]{status}[/bold]"]
        lines.append(f"  cloudctl installed: {'✅' if self.cloudctl_installed else '❌'}")
        if self.cloudctl_version:
            lines.append(f"  cloudctl version: {self.cloudctl_version}")
        lines.append(f"  credentials: {'✅' if self.has_credentials else '❌'}")
        lines.append(f"  organizations: {self.organizations_available}")
        lines.append(f"  cloud access: {'✅' if self.can_access_cloud else '❌'}")
        if self.issues:
            lines.append("[bold red]Issues:[/bold red]")
            for issue in self.issues:
                lines.append(f"  • {issue}")
        if self.warnings:
            lines.append("[bold yellow]Warnings:[/bold yellow]")
            for warning in self.warnings:
                lines.append(f"  • {warning}")
        return "\n".join(lines)

    @property
    def is_healthy(self) -> bool:
        """Check if system is healthy."""
        return (
            self.cloudctl_installed
            and self.has_credentials
            and self.organizations_available > 0
            and not self.issues
        )
