# Security Policy

## Overview

Claude Skills is a **production-grade framework** for building skills with inherent security controls. This document details:
- Security architecture and principles
- Safe credential handling patterns
- Secret prevention and detection
- Contributor security guidelines
- Incident response

## Security Principles

### 1. Secrets Never in Source Code

**Rule**: No credentials, API tokens, or sensitive data in any committed file.

**Why**: Git history is permanent. Once committed, a secret must be assumed compromised.

**Pattern**:
```python
# ❌ WRONG - Secret in code
api_token = "sk-1234567890abcdef"
jira_api = JiraAPI(token=api_token)

# ✅ CORRECT - Secret from environment
import os
api_token = os.environ.get("JIRA_API_TOKEN")
if not api_token:
    raise ValueError("JIRA_API_TOKEN not set")
jira_api = JiraAPI(token=api_token)
```

### 2. Configuration Externalized

**Rule**: All configuration must be external to source code.

**Pattern**:
- **Master Config**: `~/.claude/{skill}/config.json` (not in repo)
- **Repo Config**: `.claude/claude.json` (no secrets, just project keys)
- **Environment**: `$VAR_NAME` for all credentials
- **Examples**: `.env.example` with placeholder values only

```json
// ✅ .env.example (safe to commit)
{
  "JIRA_API_TOKEN": "sk_test_PLACEHOLDER_NEVER_USE",
  "GITHUB_TOKEN": "ghp_PLACEHOLDER_NEVER_USE"
}

// ❌ .env (never commit)
{
  "JIRA_API_TOKEN": "sk_1234567890abcdef",
  "GITHUB_TOKEN": "ghp_xyz789..."
}
```

### 3. Dependency on Environment

**Rule**: Code must require environment variables for all external service authentication.

```python
class JiraAPI:
    def __init__(self, cloud_id: str, token: Optional[str] = None):
        self.cloud_id = cloud_id
        # Always use environment variable if not explicitly provided
        self.token = token or os.environ.get("JIRA_API_TOKEN")
        if not self.token:
            raise ValueError(
                "JIRA_API_TOKEN not found. Set via: "
                "export JIRA_API_TOKEN=your_token"
            )
```

### 4. No Hardcoded URLs with Credentials

**Rule**: URLs must never contain authentication parameters.

```python
# ❌ WRONG - Token in URL
url = f"https://api.example.com/endpoint?token={api_token}"

# ✅ CORRECT - Token in header
headers = {"Authorization": f"Bearer {api_token}"}
response = requests.get(url, headers=headers)
```

### 5. Validation and Sanitization

**Rule**: All user input must be validated. Error messages must never leak internal state.

```python
# ❌ WRONG - Leaks internal details
try:
    result = api.call(user_input)
except Exception as e:
    print(f"Error: {e}")  # Might contain API key or internal path

# ✅ CORRECT - Safe error message
try:
    result = api.call(user_input)
except Exception as e:
    logger.error(f"API call failed: {e}", exc_info=True)  # Log with details
    print("❌ API call failed. Check logs for details.")  # User-safe message
```

## Secret Prevention Strategy

### Automated Detection (Git Hooks)

This repo uses **pre-commit framework** to detect secrets before they reach GitHub.

**Installation** (for contributors):
```bash
pip install pre-commit
pre-commit install
```

**What it catches**:
- AWS credentials (AKIA...)
- Private keys (-----BEGIN RSA...)
- Tokens and API keys
- Common credential patterns

**Running manually**:
```bash
pre-commit run --all-files
```

### GitHub Secret Scanning

This repository has **GitHub secret scanning enabled**. If you accidentally commit a real secret:

1. **Alert**: GitHub notifies maintainers immediately
2. **Prevention**: Secret is blocked from being pushed (if using GitHub's push protection)
3. **Remediation**: Secret must be revoked immediately

### .gitignore Strategy

The `.gitignore` file blocks:
- `.env*` files (environment variables)
- `*.key`, `*.pem` (private keys)
- `credentials.json`, `config.local.json` (config with secrets)
- Patterns matching `*secret*`, `*token*`, `*password*` (case variations)

**Test** your local setup:
```bash
# Verify .env is ignored
touch .env.test
git status  # Should NOT show .env.test
rm .env.test
```

## Credential Patterns by Service

### Jira API Token

**Storage**: Environment variable only
```bash
export JIRA_API_TOKEN="your_token_here"
```

**Usage in code**:
```python
class SkillConfig:
    @property
    def jira_api_token(self) -> str:
        token = os.environ.get("JIRA_API_TOKEN")
        if not token:
            raise ValueError("JIRA_API_TOKEN environment variable not set")
        return token
```

**Never in**:
- pyproject.toml
- Any Python file
- Config files committed to repo
- URLs or log output

### AWS Credentials

**Storage**: `~/.aws/credentials` (not in repo)
```ini
[default]
aws_access_key_id = AKIA...
aws_secret_access_key = ...
```

**Usage**: Let boto3 auto-discover from environment or ~/.aws/credentials

**Never in**:
- Environment variables in `.env` files
- Source code
- Configuration files
- Docker images (without proper secrets mounting)

### GitHub Token

**Storage**: Environment variable
```bash
export GITHUB_TOKEN="ghp_..."
```

**Usage**:
```python
import os
token = os.environ.get("GITHUB_TOKEN")
headers = {"Authorization": f"token {token}"}
```

## Contributing with Security

### Before Every Commit

1. **Review your changes**:
   ```bash
   git diff
   git diff --staged
   ```
   Look for any credentials, tokens, API keys, or sensitive data.

2. **Check .gitignore patterns**:
   ```bash
   # Test a secret file is ignored
   touch test.env
   git status  # Should NOT appear
   rm test.env
   ```

3. **Use pre-commit hooks**:
   ```bash
   pre-commit run --all-files
   ```

4. **Never commit**:
   - `.env` files
   - API tokens
   - Private keys
   - Local configuration with real values
   - Database credentials
   - Any string containing "secret", "token", "password" with real values

### Pull Request Checklist

- [ ] No `.env` files committed
- [ ] No API tokens in code
- [ ] No hardcoded credentials
- [ ] All secrets come from environment variables
- [ ] Config files have `.example` versions with placeholder values
- [ ] Error messages don't leak internal details
- [ ] Pre-commit hooks pass

### If You Accidentally Commit a Secret

1. **Stop**: Do NOT push to GitHub if possible
2. **Revert**: 
   ```bash
   git reset --soft HEAD~1
   git reset
   ```
3. **Remove**: Edit files to remove the secret
4. **Recommit**: Create a new clean commit
5. **Notify**: Tell maintainers if pushed (so they can rotate the credential)

## Configuration Examples

### Safe Config Pattern

**`.env.example`** (safe to commit):
```env
# Jira Configuration
JIRA_API_TOKEN=sk_test_NEVER_USE_THIS_PLACEHOLDER
JIRA_CLOUD_ID=your-instance.atlassian.net

# GitHub Configuration
GITHUB_TOKEN=ghp_NEVER_USE_THIS_PLACEHOLDER

# Optional: Local overrides
# Copy to .env and fill with real values (never commit .env)
```

**`src/config.py`** (safe):
```python
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class SkillConfig:
    """Configuration loaded from environment."""
    
    jira_api_token: str
    jira_cloud_id: str
    github_token: Optional[str] = None
    
    @classmethod
    def from_environment(cls) -> "SkillConfig":
        """Load configuration from environment variables."""
        jira_token = os.environ.get("JIRA_API_TOKEN")
        if not jira_token:
            raise ValueError(
                "JIRA_API_TOKEN not found. Set via: export JIRA_API_TOKEN=..."
            )
        
        return cls(
            jira_api_token=jira_token,
            jira_cloud_id=os.environ.get("JIRA_CLOUD_ID", ""),
            github_token=os.environ.get("GITHUB_TOKEN"),
        )
```

**`.claude/claude.json`** (safe to commit, project-specific):
```json
{
  "jira": {
    "cloudId": "darkmothcreative",
    "projectKey": "TG"
  }
}
```

## Incident Response

### If You Discover a Leaked Secret

1. **Notify immediately**: Contact repo maintainers
2. **Assess**: Determine scope (was it pushed? How long was it exposed?)
3. **Rotate**: If real credential was exposed, rotate/revoke it immediately
4. **Remediate**: Remove from Git history (requires force push and careful coordination)
5. **Prevent**: Ensure pre-commit hooks and .gitignore are in place

### Common Scenarios

**Scenario**: "I ran a test with my real token and committed it"
- **Fix**: Revert commit, remove token, rotate credential, recommit clean code
- **Prevention**: Use `.env.example` for tests, load from environment

**Scenario**: "I accidentally committed an `api_key = "..."` line"
- **Fix**: Remove line, create new commit, never force push to main
- **Prevention**: Code review catches hardcoded credentials

**Scenario**: "My local `.env` got committed"
- **Fix**: Remove from repo history (force push with caution), rotate any real credentials
- **Prevention**: Verify `.env` is in `.gitignore`, never bypass with `-f` flag

## Testing Security

### Unit Tests for Config

```python
# ✅ tests/test_config_security.py
def test_config_requires_env_variable():
    """Verify config fails without environment variable."""
    import os
    # Clear environment
    os.environ.pop("JIRA_API_TOKEN", None)
    
    # Should raise error
    with pytest.raises(ValueError, match="JIRA_API_TOKEN"):
        SkillConfig.from_environment()

def test_config_never_logs_token(caplog):
    """Verify token is never logged."""
    os.environ["JIRA_API_TOKEN"] = "sk_real_token_12345"
    config = SkillConfig.from_environment()
    
    # Check logs don't contain token
    assert "sk_real_token_12345" not in caplog.text
```

### Manual Security Checks

```bash
# Scan for common secret patterns
grep -r "api_key = " src/
grep -r "token = " src/
grep -r "password = " src/

# Verify .env is ignored
git check-ignore .env

# Test pre-commit hooks
pre-commit run --all-files
```

## References

- [OWASP: Secrets Management](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [Pre-commit Framework](https://pre-commit.com/)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [12 Factor App: Config](https://12factor.net/config)

## Questions?

If you have security concerns or questions about safe patterns:
1. Check this document first
2. Open an issue (without sharing secrets!)
3. Contact maintainers directly

---

**Last Updated**: 2026-04-26  
**Security Review**: Comprehensive  
**Status**: All systems secure
