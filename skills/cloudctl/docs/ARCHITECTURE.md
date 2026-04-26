# CloudctlSkill Architecture

## Overview

CloudctlSkill is an enterprise-grade, async-first Python skill for managing cloud contexts across multiple cloud providers (AWS, GCP, Azure). It wraps the cloudctl CLI tool and provides type-safe, well-tested interfaces for context management and cloud operations.

## Design Principles

1. **Async-First** — All long-running operations are async, allowing non-blocking execution
2. **Type-Safe** — Pydantic v2 validation ensures data integrity at API boundaries
3. **Fail-Safe** — Comprehensive error handling with auto-recovery where possible
4. **Observable** — Structured logging and audit trails for compliance
5. **Defensive** — Pre-flight checks, context validation, and helpful error messages
6. **Testable** — Designed for mocking and comprehensive unit testing

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     CloudctlSkill API                        │
│                                                              │
│  ┌──────────────────┬──────────────────┬─────────────────┐ │
│  │ Context Ops      │ Credential Mgmt   │ Diagnostics    │ │
│  ├──────────────────┼──────────────────┼─────────────────┤ │
│  │ switch_context   │ verify_creds      │ health_check   │ │
│  │ get_context      │ get_token_status  │ validate_switch│ │
│  │ switch_region    │ check_all_creds   │ execute_cmd    │ │
│  │ switch_project   │ login             │ ensure_access  │ │
│  └──────────────────┴──────────────────┴─────────────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
         ┌────────────────────────────────────┐
         │   _execute_cloudctl (Internal)    │
         │                                    │
         │ - Subprocess management           │
         │ - Error handling                  │
         │ - Retry logic with backoff        │
         │ - Token auto-refresh              │
         │ - Timeout handling                │
         │ - Audit logging                   │
         └────────────────────────────────────┘
                          ↓
         ┌────────────────────────────────────┐
         │      cloudctl CLI Tool             │
         │                                    │
         │ - Context switching               │
         │ - Credential management           │
         │ - Diagnostics                     │
         └────────────────────────────────────┘
                          ↓
         ┌────────────────────────────────────┐
         │   Cloud Providers                  │
         │                                    │
         │ - AWS (SSO/IAM)                    │
         │ - GCP (gcloud/OAuth)               │
         │ - Azure (az CLI)                   │
         └────────────────────────────────────┘
```

## Module Structure

### `models.py` — Data Models (Pydantic v2)

Type-safe data models for all API inputs/outputs:

- **CloudProvider** — Enum for AWS, GCP, Azure
- **CommandStatus** — Success, failure, partial, timeout
- **CommandResult** — Result of a cloudctl command execution
- **CloudContext** — Current cloud context state
- **SkillConfig** — Configuration with validation
- **TokenStatus** — Token validity and expiry info
- **HealthCheckResult** — System health diagnostics
- **OperationLog** — Audit trail entry (JSONL)

**Design**:
```python
# Type-safe validation at boundaries
class CommandResult(BaseModel):
    status: CommandStatus
    return_code: int
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.status == CommandStatus.SUCCESS and self.return_code == 0
```

### `skill.py` — Main Skill Class

The CloudctlSkill class provides the primary API for users:

**Initialization**:
```python
def __init__(self, config: Optional[SkillConfig] = None):
    self.config = config or SkillConfig.from_env()
    self.console = Console()  # Rich output
    self._context_cache = None
    self._operation_log = []
    self._cloudctl_available = self._check_cloudctl_installed()
```

**Core Methods**:

1. **Context Operations**
   - `switch_context(org, account_id, role)` — Switch cloud context
   - `get_context() → CloudContext` — Get current context
   - `switch_region(region)` — Change region
   - `switch_project(project_id)` — Change GCP project

2. **Organization Management**
   - `list_organizations() → list[dict]` — List all orgs
   - `list_accounts(org) → list[dict]` — List accounts
   - `execute_command(cmd, verify=True) → CommandResult` — Run arbitrary command

3. **Credential & Token Management**
   - `verify_credentials(org) → bool` — Check if creds exist
   - `get_token_status(org) → TokenStatus` — Token validity
   - `check_all_credentials() → dict` — Check all orgs
   - `login(org) → CommandResult` — Authenticate

4. **Diagnostics & Validation**
   - `health_check() → HealthCheckResult` — Full system check
   - `validate_switch() → bool` — Verify context switch
   - `ensure_cloud_access(org) → dict` — Guaranteed access with recovery

5. **Logging & Audit**
   - `log_operation(op, result, before, after)` — Record to audit log
   - `get_operation_log() → list[OperationLog]` — Get session log

6. **Display & Debugging**
   - `print_context()` — Pretty-print current context

**Internal Methods**:

```python
async def _execute_cloudctl(
    self,
    args: list[str],
    retries: int = 0,
    auto_refresh_attempted: bool = False
) -> CommandResult:
    """Execute cloudctl command with error handling and retries."""
    # - Subprocess management
    # - Timeout handling
    # - Retry logic with exponential backoff
    # - Token auto-refresh on expiry
    # - Error classification and recovery
```

## Configuration

CloudctlSkill supports 3-level configuration merging:

```
┌──────────────────────────────────────────────────────┐
│ 1. System Environment Variables (CLOUDCTL_*)        │
│    (Highest Priority)                                │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ 2. Central Config (~/.cloudctl/config.yaml)         │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│ 3. Local Repo Config (.cloudctl.yaml)               │
│    (Lowest Priority)                                 │
└──────────────────────────────────────────────────────┘
```

**SkillConfig** validates all settings:

```python
class SkillConfig(BaseModel):
    cloudctl_path: str = "cloudctl"
    timeout_seconds: int = 30  # Validated: 1-300
    max_retries: int = 3       # Validated: 0-10
    verify_context_after_switch: bool = True
    enable_audit_logging: bool = True
    dry_run: bool = False
    environment_overrides: dict[str, str] = {}
```

## Error Handling Strategy

CloudctlSkill implements comprehensive error handling with auto-recovery:

### Error Classification

1. **Transient Errors** (auto-retry)
   - Timeout (retry with backoff)
   - Temporary network issues

2. **Token Errors** (auto-refresh)
   - Token expired
   - Not authenticated
   - Invalid credentials

3. **Context Errors** (validation)
   - Invalid organization
   - Context switch failed
   - Access denied

4. **Permanent Errors** (fail-fast)
   - cloudctl not installed
   - Invalid configuration
   - Unsupported operation

### Recovery Strategies

```python
# Auto-retry with exponential backoff
if retries < max_retries:
    await asyncio.sleep(2 ** retries)  # 2, 4, 8 seconds
    return await _execute_cloudctl(args, retries + 1)

# Token auto-refresh
if "token expired" in stderr and not auto_refresh_attempted:
    result = await login(org)
    if result.success:
        return await _execute_cloudctl(args, auto_refresh_attempted=True)

# Context validation
is_valid = await validate_switch()
if not is_valid:
    raise RuntimeError("Context switch validation failed")
```

## Audit Logging

Operations are logged to JSONL format for compliance and debugging:

```json
{
  "timestamp": "2026-04-26T10:30:45.123456",
  "operation": "switch_context",
  "context_before": {
    "provider": "aws",
    "organization": "myorg",
    "account_id": "123456789"
  },
  "context_after": {
    "provider": "aws",
    "organization": "prod-org",
    "account_id": "987654321"
  },
  "result": {
    "status": "success",
    "return_code": 0,
    "duration_seconds": 0.5,
    "command": "switch prod-org"
  },
  "user": "craig",
  "success": true,
  "notes": ""
}
```

**Location**: `~/.config/cloudctl/audit/operations_YYYYMMDD.jsonl`

## Performance Optimizations

### 1. Context Caching

```python
self._context_cache: Optional[CloudContext] = None

# Reuse cached context
if self._context_cache:
    return self._context_cache

# Update cache on change
context = await self.get_context()
self._context_cache = context
```

### 2. Token Caching & Proactive Refresh

```python
# Get token status with expiry
status = await get_token_status(org)

# Proactively refresh before expiry
if status.expires_in_seconds < 300:  # 5 minutes
    await login(org)  # Refresh token
```

### 3. Lazy Loading

- cloudctl availability check happens once on init
- Organization list cached until invalidated
- Provider detection deferred until needed

## Security Considerations

### 1. Credential Handling

- Credentials never printed or logged
- Tokens passed through environment variables only
- No hardcoding of secrets in config files

### 2. Input Validation

```python
# All user input validated with Pydantic
@validator("organization")
def validate_org(cls, v: str) -> str:
    if not v or len(v.strip()) == 0:
        raise ValueError("Organization cannot be empty")
    if len(v) > 255:
        raise ValueError("Organization name too long")
    return v.strip()
```

### 3. Audit Logging

- All operations logged for compliance
- User identity captured
- Before/after context recorded
- Success/failure tracked

## Testing Strategy

### Test Categories

1. **Unit Tests** (`test_cloudctl_skill.py`)
   - Model validation
   - Config management
   - Error handling
   - Context operations
   - Credential verification
   - Health checks

2. **Integration Tests** (marked `@pytest.mark.integration`)
   - Real cloudctl interactions
   - Multi-cloud operations
   - Credential flows
   - Skipped if cloudctl not installed

3. **Security Tests** (marked `@pytest.mark.security`)
   - Input validation
   - Credential handling
   - Error message sanitization

### Mock Strategy

```python
# Mock cloudctl execution
with patch.object(skill, "_execute_cloudctl") as mock_exec:
    mock_exec.return_value = CommandResult(...)
    
    # Test skill logic without actual cloudctl
    context = await skill.get_context()
    assert context.organization == "myorg"
```

## Extending CloudctlSkill

### Adding a New Method

```python
async def get_cloud_config(self, org: str) -> dict:
    """Get cloud-specific configuration."""
    result = await self._execute_cloudctl(["config", "get", org])
    if not result.success:
        raise RuntimeError(f"Failed to get config: {result.stderr}")
    
    return json.loads(result.stdout)
```

### Custom Configuration

```python
# Add to SkillConfig
class SkillConfig(BaseModel):
    cloudctl_path: str = "cloudctl"
    custom_field: str = "default"  # New field
    
    @validator("custom_field")
    def validate_custom(cls, v: str) -> str:
        # Custom validation logic
        return v.strip()
```

## Troubleshooting Guide

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and solutions.

## Contributing

See [../../CONTRIBUTING.md](../../CONTRIBUTING.md) for contribution guidelines.

---

**Last Updated**: 2026-04-26
**Version**: 1.2.0
