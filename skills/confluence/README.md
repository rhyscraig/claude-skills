# Confluence Documentation Skill

A center-of-excellence Confluence skill that generates, updates, and maintains technical documentation from code repositories. Emphasizes safety, quality gates, and intelligent document management.

## Features

### Core Capabilities
- **Smart Document Management**: Detects existing docs, merges changes intelligently, prevents duplicates
- **Code Analysis**: Scans repositories to extract APIs, architecture, dependencies, code examples
- **Multi-Template System**: Architecture docs, API specs, runbooks, ADRs, troubleshooting guides
- **Quality Gates**: Link validation, metadata checks, permission verification, content analysis
- **Safety First**: Dry-run mode, interactive confirmation, audit trails, backup support

### Quality Assurance
- Zero duplicate documents (detection by title, hash, and ID)
- Link validation (internal references and external URLs)
- Metadata enforcement (owner, audience, purpose, version)
- Confluence permission checks before writes
- Accessibility validation for embedded content
- Content complexity analysis and warnings

### Configuration-Driven
- YAML-based configuration per documentation initiative
- Flexible merge strategies (append, replace, interactive)
- Template selection and customization
- Repo patterns and scan rules
- Audience and metadata defaults

### Advanced Features
- Scheduled updates (hook integration for automatic refreshes)
- Diagram generation (architecture, code structure)
- Related documents linking and cross-references
- Change tracking with audit comments
- Deprecation warnings for stale docs
- Integration with GitHub, Linear, Jira for cross-linking

## Usage

```python
from skills.confluence import ConfluenceSkill

skill = ConfluenceSkill(config_path="confluence.config.yaml")

result = skill.document(
    task="Document the payment service API",
    repos=["backend/payment-service"],
    doc_type="api",
    space_key="ENG",
    parent_page_title="APIs"
)
```

## Configuration

See `config.example.yaml` for a complete example. Key sections:

```yaml
confluence:
  instance_url: "https://company.atlassian.net"
  space_key: "ENG"
  
documentation:
  template: "api"
  parent_page: "APIs"
  merge_strategy: "interactive"  # append, replace, or interactive
  
code_analysis:
  repos:
    - pattern: "backend/**"
      include_patterns: ["*.py", "*.go"]
  extract:
    - apis
    - architecture
    - dependencies
    
guardrails:
  require_approval: true
  dry_run_by_default: true
  validate_links: true
  check_permissions: true
```

## Configuration Schema

Full schema validation is performed against `config.schema.json`.

## Safety & Guardrails

1. **Dry-Run Mode (Default)**: Preview changes without writing
2. **Interactive Confirmation**: User approval for overwrites
3. **Permission Checks**: Validates write access to space/pages
4. **Backup Support**: Creates audit trail of all changes
5. **Rate Limiting**: Respects Confluence API limits
6. **Fail-Safe Defaults**: Conservative behavior, opt-in for aggressive actions

## Testing

```bash
# Run all tests with coverage
make test

# Run specific test suite
pytest tests/test_doc_generators.py -v

# Run with mock Confluence (no API calls)
pytest tests/ -m "not integration"
```

## Architecture

- `skill.py`: Main entry point and orchestration
- `models.py`: Data structures and validation
- `confluence_client.py`: Confluence API wrapper with rate limiting
- `code_scanner.py`: Repository analysis and extraction
- `doc_generators.py`: Template-based documentation generation
- `guardrails.py`: Validation, safety checks, and quality gates
- `validators.py`: Input validation and normalization

## Best Practices

1. Always use dry-run mode first (`dry_run=True`)
2. Review changes before applying (`interactive=True`)
3. Start with a small space for testing before production
4. Use configuration files (don't hardcode values)
5. Enable link validation for documentation quality
6. Run permission checks before writing
7. Use audit trails for compliance

## Known Limitations

- Does not support Confluence Cloud API v3 macros in embedded code
- Diagram generation requires additional tooling (Mermaid/Kroki integration)
- Rate limiting: 100 writes/minute to Confluence

## Development

See `docs/ARCHITECTURE.md` for implementation details and extension points.
