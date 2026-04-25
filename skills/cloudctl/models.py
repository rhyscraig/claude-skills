"""Data models for cloudctl skill with validation and serialization."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, validator


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

    status: CommandStatus
    return_code: int
    stdout: str = ""
    stderr: str = ""
    command: str
    duration_seconds: float = 0.0

    class Config:
        use_enum_values = False
        json_encoders = {CommandStatus: lambda v: v.value}

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

    provider: CloudProvider
    organization: str
    account_id: Optional[str] = None
    role: Optional[str] = None
    region: Optional[str] = None
    project_id: Optional[str] = None

    @validator("organization")
    def validate_org(cls, v: str) -> str:
        """Validate organization name."""
        if not v or len(v.strip()) == 0:
            raise ValueError("Organization cannot be empty")
        if len(v) > 255:
            raise ValueError("Organization name too long")
        return v.strip()

    class Config:
        use_enum_values = False
        json_encoders = {CloudProvider: lambda v: v.value}

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

    cloudctl_path: str = "cloudctl"
    timeout_seconds: int = 30
    max_retries: int = 3
    verify_context_after_switch: bool = True
    enable_audit_logging: bool = True
    dry_run: bool = False
    environment_overrides: dict[str, str] = Field(default_factory=dict)

    @validator("timeout_seconds")
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout value."""
        if v < 1 or v > 300:
            raise ValueError("Timeout must be between 1 and 300 seconds")
        return v

    @validator("max_retries")
    def validate_retries(cls, v: int) -> int:
        """Validate retry count."""
        if v < 0 or v > 10:
            raise ValueError("Max retries must be between 0 and 10")
        return v

    class Config:
        validate_assignment = True

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

    timestamp: str
    operation: str
    context_before: Optional[CloudContext] = None
    context_after: Optional[CloudContext] = None
    result: CommandResult
    user: Optional[str] = None
    success: bool
    notes: str = ""

    class Config:
        arbitrary_types_allowed = True
