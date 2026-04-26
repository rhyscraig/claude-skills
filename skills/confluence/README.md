# Confluence Documentation Skill

Production-grade skill for generating and managing Confluence documentation with enterprise-level features.

## Features

- **Three-Level Configuration**: Central defaults + local repo overrides + runtime parameters
- **Jira Integration**: Auto-link related issues, detect undocumented APIs, create gap tasks
- **8 Document Templates**: API, Architecture, Runbook, ADR, Feature, Infrastructure, Troubleshooting, Custom
- **Code Analysis**: Extract APIs, architecture, dependencies from multiple languages
- **Safety Guardrails**: Dry-run mode, approval gates, permission validation, metadata validation
- **Comprehensive Testing**: 71 tests passing

## Quick Start

### Central Configuration

Create `confluence.config.yaml`:

```yaml
confluence:
  instance_url: "https://company.atlassian.net"
  space_key: "ENG"

documentation:
  template: "api"
  metadata:
    owner: "platform-team"

jira:
  enabled: true
  default_project: "ENGR"
```

### Local Repository Configuration

Create `.confluence.yaml` in repo root:

```yaml
documentation:
  space_key: "SERVICES"
  metadata:
    owner: "payments-team"

jira:
  default_project: "PAYMENTS"
```

### Usage

```python
from skills.confluence import ConfluenceSkill

skill = ConfluenceSkill(config_path="confluence.config.yaml")
result = skill.document(repo_path=".", service_name="api", title="API Docs")
```

## Config Merging

Central → Local → Runtime (later overrides earlier)

## Jira Integration

- Auto-link related issues to documentation
- Detect undocumented APIs
- Create tasks for gaps

## Test Coverage

All 71 tests passing with 100% core coverage.

## Production Ready

✅ Pydantic v2 validation
✅ Three-level config merging
✅ Jira Cloud API v2 with error handling
✅ Safety guardrails (dry-run, approval, validation)
✅ Rate limiting and retries
✅ Comprehensive logging

Version: 1.1.0
