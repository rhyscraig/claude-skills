# CloudctlSkill Troubleshooting Guide

## Common Issues & Solutions

### Installation & Setup

#### ❌ "cloudctl not found in PATH"

**Error**: `cloudctl not found at /path/to/cloudctl`

**Causes**:
- cloudctl is not installed
- cloudctl is not in PATH
- CLOUDCTL_PATH environment variable points to wrong location

**Solutions**:

1. **Install cloudctl**:
   ```bash
   pip install cloudctl
   ```

2. **Check installation**:
   ```bash
   which cloudctl
   cloudctl --version
   ```

3. **Set explicit path**:
   ```python
   from skills.cloudctl import SkillConfig, CloudctlSkill
   
   config = SkillConfig(cloudctl_path="/usr/local/bin/cloudctl")
   skill = CloudctlSkill(config)
   ```

4. **Or via environment**:
   ```bash
   export CLOUDCTL_PATH="/usr/local/bin/cloudctl"
   ```

#### ❌ "No module named 'skills.cloudctl'"

**Error**: `ModuleNotFoundError: No module named 'skills.cloudctl'`

**Causes**:
- CloudctlSkill not installed
- Wrong Python environment

**Solutions**:

1. **Install from local repo**:
   ```bash
   cd /path/to/claude-skills
   pip install -e .
   ```

2. **Check Python version** (requires 3.12+):
   ```bash
   python --version
   ```

3. **Verify installation**:
   ```bash
   python -c "from skills.cloudctl import CloudctlSkill; print('OK')"
   ```

---

### Authentication Issues

#### ❌ "Failed to authenticate to AWS"

**Error**: `Failed to authenticate with organization`

**Causes**:
- AWS SSO URL misconfigured
- Browser OAuth failed or timed out
- Session expired

**Solutions**:

1. **Check SSO configuration**:
   ```bash
   cloudctl list
   # Check SSO URL is correct
   ```

2. **Manual re-authentication**:
   ```bash
   cloudctl login myorg
   # Follow browser OAuth flow
   ```

3. **Clear cached credentials**:
   ```bash
   rm -rf ~/.aws/sso/cache/
   cloudctl cache-clear
   cloudctl login myorg
   ```

4. **Check AWS configuration**:
   ```bash
   cat ~/.aws/config
   # Verify sso_start_url is correct
   ```

#### ❌ "GCP: cannot prompt during non-interactive execution"

**Error**: `cannot prompt during non-interactive execution`

**Causes**:
- Running in non-interactive environment (headless, SSH, etc.)
- `gcloud auth login` requires browser interaction

**Solutions**:

1. **In interactive terminal**, run manually:
   ```bash
   gcloud auth login
   gcloud auth application-default login
   cloudctl login gcp-terrorgems
   ```

2. **In CI/CD environment**, use service account:
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account-key.json"
   cloudctl login gcp-terrorgems
   ```

3. **For Claude automation**, ensure browser can pop up:
   ```python
   from skills.cloudctl import CloudctlSkill
   
   skill = CloudctlSkill()
   # Browser will open for OAuth flow
   result = await skill.login("gcp-terrorgems")
   ```

#### ❌ "Azure: No subscriptions found"

**Error**: `No subscriptions found in account`

**Causes**:
- User account has no Azure subscriptions
- Wrong tenant selected
- Insufficient permissions

**Solutions**:

1. **Check subscriptions**:
   ```bash
   az account list
   ```

2. **Set active subscription**:
   ```bash
   az account set --subscription "subscription-id"
   ```

3. **Re-authenticate**:
   ```bash
   az login --tenant "tenant-id"
   cloudctl login azure-org
   ```

---

### Context Switching Issues

#### ❌ "Organization 'X' not found"

**Error**: `Organization 'myorg' not found`

**Causes**:
- Organization name is incorrect
- Organization is disabled
- Organization not configured in cloudctl

**Solutions**:

1. **List configured organizations**:
   ```bash
   cloudctl org list
   ```

2. **Check spelling exactly matches**:
   ```python
   skill = CloudctlSkill()
   orgs = await skill.list_organizations()
   print(orgs)  # Check exact names
   ```

3. **Add organization if missing**:
   ```bash
   cloudctl org add myorg --provider aws ...
   ```

#### ❌ "Context switch validation failed"

**Error**: `Context switch validation failed`

**Causes**:
- Switch succeeded but credentials expired immediately after
- Access to new context was revoked
- Network issue after switch

**Solutions**:

1. **Refresh credentials**:
   ```bash
   cloudctl login myorg
   cloudctl switch myorg
   ```

2. **Verify you have access**:
   ```bash
   cloudctl env myorg
   # Should show current context without errors
   ```

3. **Try again with retries**:
   ```python
   from skills.cloudctl import SkillConfig, CloudctlSkill
   
   config = SkillConfig(max_retries=5)  # Increase retries
   skill = CloudctlSkill(config)
   result = await skill.switch_context("myorg")
   ```

#### ❌ "Failed to switch context"

**Error**: `Context switch failed: [error details]`

**Causes**:
- Invalid account ID or role
- cloudctl v4.0.0 requires interactive account/role selection
- Access denied to resource

**Solutions**:

1. **Use interactive selection**:
   ```bash
   cloudctl switch myorg
   # Select account and role interactively
   ```

2. **Check available accounts**:
   ```python
   skill = CloudctlSkill()
   accounts = await skill.list_accounts("myorg")
   print(accounts)  # Check available IDs
   ```

3. **Verify you have access**:
   ```bash
   cloudctl verify myorg
   ```

---

### Token & Credential Issues

#### ❌ "Token expired"

**Error**: `Token expired, attempting to refresh...`

**Causes**:
- Token lifetime exceeded (typically 1 hour for AWS, 1 hour for GCP)
- Credentials not refreshed after expiry

**Solutions** (usually automatic):

1. **Automatic refresh** — skill handles this automatically:
   ```python
   # Skill detects expiry and refreshes automatically
   context = await skill.get_context()
   # Transparent refresh happens in background
   ```

2. **Manual refresh if needed**:
   ```python
   skill = CloudctlSkill()
   result = await skill.login("myorg")
   if result.success:
       context = await skill.get_context()
   ```

3. **Check token status**:
   ```python
   status = await skill.get_token_status("myorg")
   print(f"Token valid: {status.valid}")
   print(f"Expires in: {status.expires_in_seconds}s")
   ```

#### ❌ "Invalid or missing credentials"

**Error**: `Invalid or missing credentials`

**Causes**:
- Never authenticated
- Credentials were revoked
- Wrong environment or account

**Solutions**:

1. **Authenticate first**:
   ```bash
   cloudctl login myorg
   ```

2. **Verify credentials exist**:
   ```python
   is_valid = await skill.verify_credentials("myorg")
   if not is_valid:
       # Need to login
       result = await skill.login("myorg")
   ```

3. **Check credential location**:
   - AWS: `~/.aws/credentials`, `~/.aws/config`
   - GCP: `~/.config/gcloud/`, Application Default Credentials
   - Azure: `~/.azure/`

4. **Use ensure_cloud_access** (recommended):
   ```python
   result = await skill.ensure_cloud_access("myorg")
   if result["success"]:
       print(f"Ready: {result['context']}")
   else:
       print(f"Error: {result['error']}")
       print(f"Fix: {result['fix']}")
   ```

---

### Timeout Issues

#### ❌ "Command timed out"

**Error**: `Command timed out after 30 seconds`

**Causes**:
- Network latency
- cloudctl performing heavy operation
- Unresponsive cloud provider API
- Default timeout too short

**Solutions**:

1. **Increase timeout**:
   ```python
   from skills.cloudctl import SkillConfig, CloudctlSkill
   
   config = SkillConfig(timeout_seconds=60)  # 60 seconds
   skill = CloudctlSkill(config)
   ```

2. **Or via environment**:
   ```bash
   export CLOUDCTL_TIMEOUT="60"
   ```

3. **Or in config file** (`.cloudctl.yaml`):
   ```yaml
   cloudctl:
     timeout_seconds: 60
   ```

4. **Verify network connectivity**:
   ```bash
   ping cloud.provider.com
   ```

5. **Check cloud provider status**:
   - AWS: https://status.aws.amazon.com
   - GCP: https://status.cloud.google.com
   - Azure: https://status.azure.com

---

### Health Check & Diagnostics

#### ❌ "Health check failed"

**Solutions**:

1. **Run health check directly**:
   ```python
   skill = CloudctlSkill()
   health = await skill.health_check()
   print(health)
   # Shows detailed issues
   ```

2. **Run cloudctl doctor**:
   ```bash
   cloudctl doctor
   # Shows diagnostic output
   ```

3. **Check cloudctl installation**:
   ```bash
   cloudctl --version
   cloudctl org list
   cloudctl env
   ```

4. **Review issues from health check**:
   ```python
   health = await skill.health_check()
   for issue in health.issues:
       print(f"Issue: {issue}")
   for warning in health.warnings:
       print(f"Warning: {warning}")
   ```

---

### Multi-Cloud Issues

#### ❌ "Switching between AWS and GCP fails"

**Error**: Context switches to wrong cloud or fails

**Causes**:
- Credentials for one provider expired
- Organization names confused
- Token refresh failed for target provider

**Solutions**:

1. **Check all credentials first**:
   ```python
   skill = CloudctlSkill()
   creds = await skill.check_all_credentials()
   print(creds)
   # Shows status of all orgs
   ```

2. **Explicit provider check**:
   ```python
   # Before switching
   context = await skill.get_context()
   print(f"Currently in: {context.provider}:{context.organization}")
   
   # After switching
   result = await skill.switch_context("gcp-terrorgems")
   new_context = await skill.get_context()
   print(f"Switched to: {new_context.provider}:{new_context.organization}")
   ```

3. **Use ensure_cloud_access for safety**:
   ```python
   # Guarantees you can access the target
   result = await skill.ensure_cloud_access("gcp-terrorgems")
   if result["success"]:
       print(f"Safe to operate in: {result['context']}")
   ```

4. **Re-authenticate if needed**:
   ```python
   # Refresh both
   await skill.login("aws-org")
   await skill.login("gcp-terrorgems")
   ```

---

### Configuration Issues

#### ❌ "Invalid configuration"

**Error**: `ValueError: Timeout must be between 1 and 300 seconds`

**Causes**:
- Invalid value in `.cloudctl.yaml`
- Invalid environment variable

**Solutions**:

1. **Check `.cloudctl.yaml` syntax**:
   ```bash
   # Validate YAML syntax
   python -c "import yaml; yaml.safe_load(open('.cloudctl.yaml'))"
   ```

2. **Example valid config**:
   ```yaml
   cloudctl:
     timeout_seconds: 30    # Between 1-300
     max_retries: 3         # Between 0-10
     verify_context_after_switch: true
     enable_audit_logging: true
     dry_run: false
   ```

3. **Reset to defaults**:
   ```bash
   rm .cloudctl.yaml
   # CloudctlSkill will use defaults
   ```

4. **Check environment variables**:
   ```bash
   echo $CLOUDCTL_TIMEOUT    # Should be numeric
   echo $CLOUDCTL_RETRIES    # Should be numeric
   ```

---

### Performance Issues

#### ❌ "Operations are slow"

**Solutions**:

1. **Enable context caching** (enabled by default):
   ```python
   config = SkillConfig()
   # Context is cached automatically
   # Repeated calls reuse cache
   ```

2. **Reduce health check frequency**:
   ```python
   # Don't call health_check() repeatedly
   # Call once at startup, cache result
   health = await skill.health_check()
   ```

3. **Use connection pooling** (if using requests):
   ```bash
   # Ensure HTTP connection reuse
   # Most libraries handle this automatically
   ```

4. **Check network latency**:
   ```bash
   time cloudctl env myorg
   # Baseline cloudctl performance
   ```

---

### Logging & Debugging

#### Enable Detailed Logging

```python
from skills.cloudctl import CloudctlSkill
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

skill = CloudctlSkill()
# Now see detailed logs
```

#### Check Audit Log

```bash
# View today's operations
cat ~/.config/cloudctl/audit/operations_$(date +%Y%m%d).jsonl

# Pretty-print JSON
cat ~/.config/cloudctl/audit/operations_20260426.jsonl | python -m json.tool

# Search for failures
grep '"success": false' ~/.config/cloudctl/audit/operations_20260426.jsonl
```

#### Get Operation Log from Skill

```python
skill = CloudctlSkill()
# ... perform operations ...

# Get in-memory log
logs = skill.get_operation_log()
for log in logs:
    print(f"{log.timestamp}: {log.operation} ({log.result.status})")
```

---

### Getting Help

If you encounter an issue not covered here:

1. **Check the documentation**:
   - README.md — Features and quick start
   - ARCHITECTURE.md — Design and internals
   - This file — Common issues

2. **Enable debug logging**:
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Run health check**:
   ```python
   health = await skill.health_check()
   print(health)  # Shows all issues and warnings
   ```

4. **Check audit log**:
   ```bash
   tail ~/.config/cloudctl/audit/operations_*.jsonl
   ```

5. **Test cloudctl directly**:
   ```bash
   cloudctl doctor
   cloudctl env
   cloudctl org list
   ```

---

**Last Updated**: 2026-04-26
**Version**: 1.2.0
