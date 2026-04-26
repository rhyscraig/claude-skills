# CloudctlSkill Deployment & Integration Guide

This guide explains how to deploy the CloudctlSkill so all your Claude sessions can securely manage cloud contexts with robust auto-recovery.

## Quick Start

### 1. Install the Skill (Already Done)

```bash
pip install -e /Users/craighoad/Repos/claude-skills
```

Verify:
```bash
python -c "from skills.cloudctl import CloudctlSkill; print('✅ Ready')"
```

### 2. Configure cloudctl Binary

The skill wraps your local `cloudctl` binary. Ensure it's installed:

```bash
which cloudctl
# or
cloudctl --version
```

If not installed:
```bash
pip install cloudctl  # or your custom cloudctl installation
```

Override the path if needed:
```bash
export CLOUDCTL_PATH="/custom/path/to/cloudctl"
```

### 3. Register Skill in Claude Sessions

The skill is now available in Python. For Claude to use it:

**Option A: Via Claude.ai Dashboard (Coming Soon)**
- Go to Claude.ai → Settings → Skills → Add Custom Skill
- Name: `cloudctl`
- Python: `from skills.cloudctl import CloudctlSkill`
- Auto-execute: `ensure_cloud_access()`

**Option B: Via Claude API** (For programmatic use)
```python
from skills.cloudctl import CloudctlSkill

# In your Claude session initialization
skill = CloudctlSkill()
# Now available to Claude for autonomous calls
```

## Best Practices

### Always Use `ensure_cloud_access()` Entry Point

✅ **Good:**
```python
result = await skill.ensure_cloud_access("prod", "123456789", "terraform")
if result["success"]:
    # Safe to proceed - cloudctl is ready
    pass
else:
    print(f"Error: {result['error']}")
    print(f"Fix: {result['fix']}")
```

❌ **Don't:**
```python
# Risky - no pre-flight checks
await skill.switch_context("prod", "123456789", "terraform")
```

### Configuration

Set these environment variables for robust operation:

```bash
# Path to cloudctl binary
export CLOUDCTL_PATH="/usr/local/bin/cloudctl"

# Command timeout (1-300 seconds)
export CLOUDCTL_TIMEOUT="60"

# Auto-retry count (0-10)
export CLOUDCTL_RETRIES="3"

# Verify context after switching
export CLOUDCTL_VERIFY="true"

# Enable audit logging
export CLOUDCTL_AUDIT="true"

# Test mode (doesn't execute commands)
export CLOUDCTL_DRY_RUN="false"
```

Add to `~/.bashrc`, `~/.zshrc`, or `~/.config/cloudctl/env`:

```bash
# ~/.bashrc
export CLOUDCTL_PATH="/usr/local/bin/cloudctl"
export CLOUDCTL_TIMEOUT="60"
export CLOUDCTL_VERIFY="true"
```

### Audit Trail

All operations are logged to: `~/.config/cloudctl/audit/operations_YYYYMMDD.jsonl`

Each entry includes:
- Timestamp (ISO 8601)
- Operation name
- Context before/after
- Command result
- User who ran it
- Success status

Access logs:
```bash
# View today's operations
cat ~/.config/cloudctl/audit/operations_$(date +%Y%m%d).jsonl | jq .

# Find failed operations
cat ~/.config/cloudctl/audit/operations_*.jsonl | jq 'select(.success == false)'
```

## Usage Examples

### Basic Context Switch with Safety

```python
from skills.cloudctl import CloudctlSkill

skill = CloudctlSkill()

# Guaranteed safe context switch
result = await skill.ensure_cloud_access("prod", "987654321", "terraform")

if not result["success"]:
    print(f"Cannot access cloud: {result['error']}")
    print(f"To fix: {result['fix']}")
else:
    print(f"Ready in: {result['context']}")
    # Now safe to run Terraform, kubectl, etc.
```

### Batch Credential Check

```python
# Check all orgs at once
credentials = await skill.check_all_credentials()

for org, status in credentials.items():
    if status["is_expired"]:
        print(f"⏰ {org}: Token EXPIRED - run: cloudctl login {org}")
    elif status["token_expires_in"] and status["token_expires_in"] < 3600:
        hours = status["token_expires_in"] / 3600
        print(f"🟡 {org}: Expires in {int(hours)}h - refresh soon")
    elif status["accessible"]:
        print(f"✅ {org}: Ready")
    else:
        print(f"❌ {org}: Not accessible")
```

### Health Check Before Operations

```python
# Validate everything is ready
health = await skill.health_check()

if not health.is_healthy:
    print("System not healthy:")
    for issue in health.issues:
        print(f"  • {issue}")
    for warning in health.warnings:
        print(f"  ⚠️  {warning}")
else:
    print(f"✅ Healthy - {health.organizations_available} orgs ready")
```

### Token Status & Expiry

```python
# Check specific org token
status = await skill.get_token_status("prod")

print(status)  # Pretty-printed with emoji
# Output: ✅ prod: Token valid for 2 days
# or: 🔴 prod: Token expires in 30 minutes
# or: ⏰ prod: Token EXPIRED

if status.is_expired:
    print(f"Auto-refreshing...")
    await skill.login("prod")
```

## Troubleshooting

### "cloudctl not found"

```
Error: cloudctl not found at /usr/local/bin/cloudctl
Fix: Install cloudctl or set CLOUDCTL_PATH environment variable
```

**Solution:**
```bash
# Install cloudctl
pip install cloudctl

# Or set path to custom installation
export CLOUDCTL_PATH="/my/cloudctl"

# Verify
cloudctl --version
```

### "Token expired"

```
Error: Token expired and refresh failed
Fix: Run 'cloudctl login prod' manually to re-authenticate
```

**Solution:**
```bash
# Manual login
cloudctl login prod

# Verify
cloudctl token status prod

# Retry operation
```

### "Organization not found"

```
Error: Organization 'prod' not found
Available orgs: ['staging', 'dev']
Fix: Use one of the available organizations listed above
```

**Solution:**
```bash
# Check configured orgs
cloudctl org list

# Add org if needed
cloudctl org add prod ...
```

### "Context switch reported success but validation failed"

This means `cloudctl switch` succeeded but `cloudctl env` returned different context.

**Diagnosis:**
```bash
# Check current context
cloudctl env

# Try switching again
cloudctl switch prod 123456789 terraform

# Check again
cloudctl env
```

**Solution:** Usually indicates cloudctl state issue - try:
```bash
# Logout and login
cloudctl logout prod
cloudctl login prod

# Then retry
```

### Timeout on Long Operations

If `ensure_cloud_access()` times out:

```bash
# Increase timeout (default 30s)
export CLOUDCTL_TIMEOUT="120"

# Or configure in code
from skills.cloudctl import SkillConfig, CloudctlSkill

config = SkillConfig(timeout_seconds=120)
skill = CloudctlSkill(config=config)
```

## Multi-Cloud Best Practices

### Switch Between Clouds Safely

```python
# AWS
result_aws = await skill.ensure_cloud_access("aws-prod")
# [Run AWS operations]

# GCP
result_gcp = await skill.ensure_cloud_access("gcp-prod")
# [Run GCP operations]

# Azure
result_azure = await skill.ensure_cloud_access("azure-prod")
# [Run Azure operations]
```

### Validate Before Destructive Operations

```python
# Before terraform destroy, verify context
is_valid = await skill.validate_switch()
if not is_valid:
    raise RuntimeError("Context validation failed - aborting destroy")

current = await skill.get_context()
if current.organization != "prod":
    raise RuntimeError(f"Expected prod but in {current.organization}")

# Now safe to proceed
```

## Security Considerations

### Credentials

- CloudctlSkill **never logs credentials** or tokens
- **Never commit** `~/.config/cloudctl/` to git
- Add to `.gitignore`:
  ```
  ~/.config/cloudctl/
  ```

### Audit Trail

- All operations logged with user ID
- Audit files in: `~/.config/cloudctl/audit/`
- For security: **rotate audit logs daily**
  ```bash
  find ~/.config/cloudctl/audit -mtime +7 -delete
  ```

### Token Refresh

- Auto-refresh happens transparently for expired tokens
- Credentials are refreshed **before** operations (via `ensure_cloud_access()`)
- If token expires **during** operation: operation fails, logs error, suggests re-auth

### Error Messages

- Error messages are **secrets-safe**: never include tokens, keys, or sensitive data
- Only include: org name, account ID, region
- Check logs for sensitive details (not printed to console)

## Integration with CI/CD

### GitHub Actions

```yaml
- name: Setup Cloud Context
  env:
    CLOUDCTL_PATH: /usr/local/bin/cloudctl
    CLOUDCTL_TIMEOUT: 60
    CLOUDCTL_AUDIT: false  # Don't log in CI
  run: |
    python -c "
    from skills.cloudctl import CloudctlSkill
    import asyncio
    
    async def setup():
        skill = CloudctlSkill()
        result = await skill.ensure_cloud_access('ci-prod')
        assert result['success'], f\"Failed: {result.get('error')}\"
        print(f\"✅ Ready: {result['context']}\")
    
    asyncio.run(setup())
    "
```

### GitLab CI

```yaml
cloud_setup:
  script:
    - |
      python3 -c "
      from skills.cloudctl import CloudctlSkill
      import asyncio
      
      async def setup():
          skill = CloudctlSkill()
          result = await skill.ensure_cloud_access('ci-prod')
          if not result['success']:
              raise RuntimeError(result['error'])
      
      asyncio.run(setup())
      "
  environment:
    CLOUDCTL_TIMEOUT: "60"
```

## Monitoring & Observability

### Check Health Regularly

```bash
# Add to your monitoring/dashboard
python3 -c "
from skills.cloudctl import CloudctlSkill
import asyncio

async def monitor():
    skill = CloudctlSkill()
    health = await skill.health_check()
    
    if not health.is_healthy:
        # Alert
        print('ALERT: Cloud access degraded')
        for issue in health.issues:
            print(f'  {issue}')
    
    # Check expiring tokens
    creds = await skill.check_all_credentials()
    for org, status in creds.items():
        if status.get('token_expires_in', 0) < 3600:
            print(f'WARN: {org} token expires soon')

asyncio.run(monitor())
"
```

### Log Analysis

```bash
# Find all failed operations
jq 'select(.success == false)' ~/.config/cloudctl/audit/operations_*.jsonl

# Count operations by type
jq -r '.operation' ~/.config/cloudctl/audit/operations_*.jsonl | sort | uniq -c

# Identify slow operations
jq 'select(.result.duration_seconds > 10)' ~/.config/cloudctl/audit/operations_*.jsonl
```

## Support & Issues

### Debug Mode

```python
from skills.cloudctl import SkillConfig, CloudctlSkill
import logging

# Enable detailed logging
logging.basicConfig(level=logging.DEBUG)

config = SkillConfig(dry_run=False)  # Set to True to test without executing
skill = CloudctlSkill(config=config)

# Now all operations log detailed output
```

### Test Mode (Dry Run)

```python
from skills.cloudctl import SkillConfig, CloudctlSkill

config = SkillConfig(dry_run=True)
skill = CloudctlSkill(config=config)

# Commands won't execute, just printed
result = await skill.ensure_cloud_access("prod")
# Returns: [dry run] switch prod
```

### Getting Help

1. **Check health:**
   ```bash
   python3 -c "from skills.cloudctl import CloudctlSkill; import asyncio; asyncio.run(CloudctlSkill().health_check())"
   ```

2. **Review logs:**
   ```bash
   tail -f ~/.config/cloudctl/audit/operations_$(date +%Y%m%d).jsonl | jq .
   ```

3. **Test cloudctl directly:**
   ```bash
   cloudctl env --json
   cloudctl org list
   cloudctl token status <org>
   ```

4. **Check configuration:**
   ```bash
   echo "CLOUDCTL_PATH=$CLOUDCTL_PATH"
   echo "CLOUDCTL_TIMEOUT=$CLOUDCTL_TIMEOUT"
   ```
