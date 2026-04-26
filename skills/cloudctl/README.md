# Cloud Context & Operations Skill

**Enterprise-grade multi-cloud context management and autonomous operations across AWS, Azure, and GCP.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org)
[![Type Hints](https://img.shields.io/badge/typing-strict-brightgreen)](https://mypy.readthedocs.io)

## Overview

CloudctlSkill enables Claude to autonomously manage cloud context across AWS, GCP, and Azure. It provides:

- **Multi-Cloud Context Switching** — Switch between organizations, accounts, roles, and projects seamlessly
- **Credential Management** — Validate, monitor, and auto-refresh tokens with intelligent recovery
- **Health Diagnostics** — Comprehensive system checks and pre-flight validation
- **Audit Logging** — JSONL-formatted operation trails for compliance and debugging
- **Error Recovery** — Auto-retry, token refresh, context validation with helpful error messages
- **Async-First Architecture** — Non-blocking operations with proper resource cleanup

## Features

✅ **Multi-Provider Support** (AWS, GCP, Azure)
✅ **Async/Await Throughout** — Non-blocking operations
✅ **Pydantic v2 Validation** — Type-safe data handling
✅ **Structured Error Handling** — Helpful suggestions for every failure mode
✅ **Token Auto-Refresh** — Proactive credential refresh before expiry
✅ **Context Caching** — Performance optimization for repeated operations
✅ **Audit Logging** — JSONL format for compliance and debugging
✅ **Health Checks** — Pre-flight diagnostics before operations
✅ **Rich Output** — Beautiful CLI feedback with emojis and colors
✅ **Production-Ready** — Comprehensive testing, strict typing, full documentation

## Quick Start

### Installation

```bash
# Install from local repo
pip install -e /path/to/claude-skills

# Or from PyPI (when published)
pip install cloudctl-skill
```

### Basic Usage

```python
from skills.cloudctl import CloudctlSkill

# Initialize the skill
skill = CloudctlSkill()

# Get current context
context = await skill.get_context()
print(context)  # aws:myorg account=123456789 role=terraform region=us-west-2

# Switch context
result = await skill.switch_context("myorg")
print(result.success)  # True

# List all organizations
orgs = await skill.list_organizations()
print(orgs)  # [{"name": "myorg", "provider": "aws", "status": "enabled"}, ...]

# Check credentials
creds = await skill.check_all_credentials()
print(creds)  # {"myorg": {"valid": True, ...}, "gcp-terrorgems": {...}}

# Health check
health = await skill.health_check()
print(health.is_healthy)  # True
```

### Pre-Flight Cloud Access (Recommended)

Use `ensure_cloud_access()` for guaranteed cloud access with automatic recovery:

```python
from skills.cloudctl import CloudctlSkill

skill = CloudctlSkill()

# Guarantees:
# - cloudctl is installed
# - credentials exist and are valid
# - tokens are not expired (auto-refreshes if needed)
# - context switch succeeds
# - final context is validated

result = await skill.ensure_cloud_access("myorg")
if result["success"]:
    print(f"✅ Ready to operate in {result['context']}")
else:
    print(f"❌ Error: {result['error']}")
    print(f"💡 Fix: {result['fix']}")
```

## Configuration

### Environment Variables

```bash
# Core configuration
export CLOUDCTL_PATH="cloudctl"              # Path to cloudctl binary
export CLOUDCTL_TIMEOUT="30"                 # Command timeout in seconds
export CLOUDCTL_RETRIES="3"                  # Max retry attempts
export CLOUDCTL_VERIFY="true"                # Verify context after switch
export CLOUDCTL_AUDIT="true"                 # Enable audit logging
export CLOUDCTL_DRY_RUN="false"              # Dry-run mode (no-op)
```

### Configuration File (.cloudctl.yaml)

Create `.cloudctl.yaml` in your repo root or home directory:

```yaml
# Cloud Context & Operations Configuration
cloudctl:
  # Path to cloudctl binary (default: cloudctl)
  path: "/usr/local/bin/cloudctl"
  
  # Command timeout in seconds (1-300, default: 30)
  timeout_seconds: 30
  
  # Max retry attempts for transient errors (0-10, default: 3)
  max_retries: 3
  
  # Verify context after switch operations (default: true)
  verify_context_after_switch: true
  
  # Enable audit logging to ~/.config/cloudctl/audit/ (default: true)
  enable_audit_logging: true
  
  # Dry-run mode (no-op, show what would happen) (default: false)
  dry_run: false
  
  # Environment variable overrides
  environment_overrides:
    AWS_REGION: "eu-west-2"
    GCLOUD_PROJECT: "my-project"
```

See `.cloudctl.example.yaml` for a fully commented example.

## API Reference

### Core Methods

#### `switch_context(organization, account_id=None, role=None)`
Switch to a cloud context (organization, account, role).

**Note:** cloudctl v4.0.0 requires interactive account/role selection.

```python
result = await skill.switch_context("myorg")
# Context: aws:myorg account=123456789 role=terraform region=us-west-2
```

#### `get_context() → CloudContext`
Get current cloud context.

```python
context = await skill.get_context()
print(context.provider)      # CloudProvider.AWS
print(context.organization)  # "myorg"
print(context.account_id)    # "123456789"
print(context.role)          # "terraform"
print(context.region)        # "us-west-2"
```

#### `list_organizations() → list[dict]`
List all configured organizations.

```python
orgs = await skill.list_organizations()
# [{"name": "myorg", "provider": "aws", "status": "enabled"},
#  {"name": "gcp-terrorgems", "provider": "gcp", "status": "enabled"}]
```

#### `list_accounts(organization) → list[dict]`
List accounts in an organization.

```python
accounts = await skill.list_accounts("myorg")
# [{"id": "123456789", "name": "production"},
#  {"id": "987654321", "name": "staging"}]
```

#### `verify_credentials(organization) → bool`
Check if credentials are valid for an organization.

```python
is_valid = await skill.verify_credentials("myorg")
# True
```

#### `get_token_status(organization) → TokenStatus`
Get token validity information.

```python
status = await skill.get_token_status("myorg")
print(status.valid)              # True
print(status.expires_in_seconds)  # 3600
print(status.is_expired)         # False
```

#### `check_all_credentials() → dict`
Check credentials across all organizations.

```python
creds = await skill.check_all_credentials()
# {
#   "myorg": {
#     "valid": True,
#     "token_expires_in": 3600,
#     "is_expired": False,
#     "accessible": True
#   },
#   "gcp-terrorgems": {
#     "valid": True,
#     "token_expires_in": 7200,
#     "is_expired": False,
#     "accessible": True
#   }
# }
```

#### `health_check() → HealthCheckResult`
Comprehensive health check of cloudctl setup.

```python
health = await skill.health_check()
print(health.is_healthy)             # True
print(health.cloudctl_installed)    # True
print(health.has_credentials)       # True
print(health.organizations_available) # 2
print(health.can_access_cloud)      # True
print(health.issues)                # []
```

#### `ensure_cloud_access(organization, account_id=None, role=None) → dict`
**Recommended entry point:** Guarantees cloud access with auto-recovery.

```python
result = await skill.ensure_cloud_access("myorg")
# Returns:
# {
#   "success": True,
#   "org": "myorg",
#   "account": "123456789",
#   "role": "terraform",
#   "context": "aws:myorg account=123456789 role=terraform region=us-west-2",
#   "token_expires_in": 3600
# }
```

### Logging & Audit

#### `log_operation(operation, result, context_before=None, context_after=None)`
Log an operation for audit trail (called automatically by internal methods).

```python
skill.log_operation(
    "switch_context",
    cmd_result,
    context_before=old_context,
    context_after=new_context
)
```

#### `get_operation_log() → list[OperationLog]`
Get in-memory operation log for this session.

```python
logs = skill.get_operation_log()
for log in logs:
    print(f"{log.timestamp} - {log.operation}: {log.success}")
```

### Debug & Display

#### `print_context()`
Print current context in human-readable format.

```python
skill.print_context()
# Output:
# Current Cloud Context
#   Provider:     aws
#   Organization: myorg
#   Account:      123456789
#   Role:         terraform
#   Region:       us-west-2
```

## Error Handling

CloudctlSkill provides comprehensive error handling with helpful suggestions:

```python
result = await skill.switch_context("nonexistent-org")
if not result.success:
    print(f"Error: {result.stderr}")
    # Error: Organization 'nonexistent-org' not found
```

**Common Error Scenarios:**

| Scenario | Error | Fix |
|----------|-------|-----|
| `cloudctl` not installed | "cloudctl not found at ..." | `pip install cloudctl` |
| Invalid organization | "Organization 'X' not found" | Check organization name, use `cloudctl org list` |
| Token expired | "Token expired, attempting refresh..." | Automatic retry with login |
| No credentials | "No organizations configured" | Run `cloudctl login <org>` |
| GCP non-interactive | "cannot prompt during non-interactive execution" | Run `gcloud auth login` manually |

## Performance

- **Context Caching** — Repeated `get_context()` calls use cached result unless invalidated
- **Async/Await** — Non-blocking operations allow concurrent tasks
- **Timeout Handling** — Configurable timeout (1-300 seconds) with automatic retry
- **Token Auto-Refresh** — Proactive refresh before expiry reduces auth failures

## Testing

Run the comprehensive test suite:

```bash
# All tests
pytest tests/test_cloudctl_skill.py -v

# With coverage
pytest tests/test_cloudctl_skill.py --cov=skills.cloudctl --cov-report=html

# By category
pytest tests/test_cloudctl_skill.py -m unit       # Unit tests only
pytest tests/test_cloudctl_skill.py -m integration # Integration tests (requires cloudctl)
```

## Audit Logging

Operations are logged to JSONL format at `~/.config/cloudctl/audit/operations_YYYYMMDD.jsonl`:

```json
{
  "timestamp": "2026-04-26T10:30:45.123456",
  "operation": "switch_context",
  "context_before": {"provider": "aws", "organization": "myorg", ...},
  "context_after": {"provider": "aws", "organization": "myorg", ...},
  "result": {"status": "success", "return_code": 0, ...},
  "user": "craig",
  "success": true,
  "notes": ""
}
```

## Advanced Topics

### Context Manager (Best Practice)

```python
from skills.cloudctl import CloudctlSkill

async def deploy_to_production():
    skill = CloudctlSkill()
    result = await skill.ensure_cloud_access("production-org")
    
    if result["success"]:
        # Safe to operate
        context = await skill.get_context()
        print(f"Operating in: {context}")
```

### Multiple Organizations

```python
skill = CloudctlSkill()

# Check all credentials
creds = await skill.check_all_credentials()

# Switch between orgs
for org in creds.keys():
    if creds[org]["valid"]:
        await skill.switch_context(org)
        context = await skill.get_context()
        print(f"Context: {context}")
```

### Dry-Run Mode

Test operations without making changes:

```python
from skills.cloudctl import SkillConfig, CloudctlSkill

config = SkillConfig(dry_run=True)
skill = CloudctlSkill(config)

result = await skill.switch_context("myorg")
# Shows what would happen, but doesn't execute
```

## Architecture

- **Models** (`models.py`) — Pydantic v2 data models with validation
- **Skill** (`skill.py`) — Main CloudctlSkill class with all methods
- **Configuration** — Environment variables, config files, runtime parameters
- **Error Handling** — Comprehensive with helpful suggestions
- **Logging** — JSONL audit trail, structured console output
- **Testing** — Unit and integration tests with >85% coverage

## Contributing

See [CONTRIBUTING.md](../../CONTRIBUTING.md) for guidelines.

## License

MIT — See [LICENSE](../../LICENSE) for details.

## Version History

**1.2.0** (2026-04-26)
- Enhanced GCP authentication with pre-flight checks
- Improved error messages with helpful suggestions
- Auto-token-refresh on expiry
- Comprehensive health check diagnostics
- Async/await throughout
- Context caching for performance
- Audit logging to JSONL format

**1.1.0** (2026-04-25)
- Initial release
- Multi-cloud support (AWS, GCP, Azure)
- Context switching and credential management
- Token validation and monitoring
- Health checks and diagnostics

---

**Questions?** See the docs/ directory for detailed guides, troubleshooting, and architecture documentation.
