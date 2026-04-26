# Confluence Skill Architecture

## Overview

The Confluence Documentation Skill is a center-of-excellence implementation for intelligent document management, generation, and maintenance in Confluence. It emphasizes safety, quality, and prevention of duplicate documentation.

## Design Principles

1. **Safety First**: Dry-run mode by default, explicit approval gates, comprehensive validation
2. **Configuration-Driven**: All behavior controlled via YAML config, not hardcoded
3. **Quality Gates**: Validation at every step, guardrails prevent mistakes
4. **Smart Merging**: Detects existing docs, intelligent merge strategies, prevents duplicates
5. **Code-Aware**: Analyzes repositories to extract relevant information
6. **Template System**: Different documentation types with domain-specific generators
7. **Audit Trail**: Full tracking of all changes, who made them, when

## Architecture Layers

### 1. Configuration Layer (`models.py`)
- **SkillConfig**: Main configuration container
- **ConfluenceConfig**: Confluence instance settings
- **DocumentationConfig**: Doc generation settings
- **CodeAnalysisConfig**: Code scanning rules
- **GuardrailsConfig**: Safety and validation rules
- **DocumentMetadata**: Per-document metadata

Validation is performed via Pydantic models with JSON schema support.

### 2. API Layer (`confluence_client.py`)
- **ConfluenceClient**: Thin wrapper around Confluence Cloud API v2
- Features:
  - Rate limiting (token bucket algorithm)
  - Automatic retries for transient failures
  - Session caching for performance
  - Permission checking before operations
  - Page/link existence validation

### 3. Code Analysis Layer (`code_scanner.py`)
- **CodeScanner**: Analyzes repositories to extract documentation-relevant info
- Extraction types:
  - **APIs**: REST endpoints, routes, methods
  - **Architecture**: File structure, module organization
  - **Dependencies**: Package/dependency manifests
  - **Classes**: Class definitions and methods (Python)
  - **Functions**: Function definitions (Python)
  - **Config**: Configuration files
  - **Errors**: Error/exception definitions
  - **Examples**: Code examples

- Language support: Python, TypeScript/JavaScript, Go
- Uses AST parsing for accuracy, regex for cross-language matching

### 4. Document Generation Layer (`doc_generators.py`)
- **DocGenerator** (abstract base class)
- Concrete implementations:
  - **APIDocGenerator**: For API specifications
  - **ArchitectureDocGenerator**: For architecture/design docs
  - **RunbookDocGenerator**: For operational procedures
  - **ADRDocGenerator**: For architecture decision records
  - **FeatureDocGenerator**: For feature specifications
  - **InfrastructureDocGenerator**: For infrastructure docs
  - **TroubleshootingDocGenerator**: For troubleshooting guides
  - **CustomDocGenerator**: For custom/untyped docs

- All generators:
  - Produce Confluence storage format HTML
  - Include metadata sections automatically
  - Support extracted code information
  - Follow template best practices

### 5. Validation Layer (`guardrails.py`)
- **GuardailValidator**: Comprehensive validation engine
  - Metadata validation (required fields, deprecated terms)
  - Content validation (size, links, formatting)
  - Link validation (anchors, external URLs)
  - Accessibility checks

- **ApprovalGate**: Manages user approval for changes
  - Configurable requirement for approval
  - Interactive and non-interactive modes
  - Caching of approvals

### 6. Orchestration Layer (`skill.py`)
- **ConfluenceSkill**: Main entry point
  - Coordinates all components
  - Manages workflow: scan → validate → generate → check → write
  - Handles error cases gracefully
  - Produces detailed result summaries
  - Maintains operation logs

## Workflow

```
1. Initialize ConfluenceSkill with SkillConfig
   ↓
2. Call skill.document(task, repos, doc_type, ...)
   ↓
3. Prepare configuration (merge overrides)
   ↓
4. Scan code repositories
   ├─ CodeScanner.scan_repos()
   └─ Extract APIs, architecture, dependencies, etc.
   ↓
5. Generate document metadata
   ├─ Title from task (auto-generated)
   ├─ Owner/audience from config
   └─ Status, labels, version
   ↓
6. Check for existing documents
   ├─ ConfluenceClient.find_page_by_title()
   └─ Handle merge strategy if exists
   ↓
7. Validate permissions
   ├─ ConfluenceClient.check_write_permission()
   └─ Early exit if no permission
   ↓
8. Generate document content
   ├─ Create appropriate DocGenerator
   ├─ Pass extracted info
   └─ Get storage format HTML
   ↓
9. Validate content
   ├─ GuardailValidator.validate_metadata()
   ├─ GuardailValidator.validate_content()
   └─ Collect errors and warnings
   ↓
10. Request approval (if configured)
    ├─ Show summary to user
    └─ Wait for explicit confirmation
    ↓
11. Write to Confluence
    ├─ Create or update page
    ├─ Apply labels
    ├─ Add audit comment
    └─ Return result
    ↓
12. Return DocumentGenerationResult
    ├─ Success flag
    ├─ Document ID and URL
    ├─ All errors and warnings
    └─ Duration and preview
```

## Safety Features

### Dry-Run Mode
- Default behavior: preview changes without writing
- Can be overridden per operation
- Shows what would happen without side effects

### Duplicate Prevention
- Page title-based detection
- Hash-based change detection
- Configurable merge strategies (append, replace, skip, interactive)
- Prevents accidental overwrites

### Permission Checks
- Validates write access to space before operating
- Handles 403 Forbidden gracefully
- Caches permission results

### Validation Gates
- Required metadata validation
- Content size limits with warnings
- Link validation (anchors, external URLs)
- Deprecated term detection
- Accessibility checks

### Approval Gates
- Can require explicit user approval before writing
- Interactive mode for merge strategy selection
- Approval caching to avoid repeated prompts

### Rate Limiting
- Token bucket implementation
- Prevents Confluence API throttling
- Configurable limits per minute

### Audit Trails
- Optional audit comments on pages
- Timestamp and metadata tracking
- Change history available
- Operation logs for debugging

## Extension Points

### Adding New Document Templates

1. Create new generator class extending `DocGenerator`
2. Implement `generate()` method
3. Add to `create_generator()` factory
4. Update `DocumentTemplate` enum
5. Add tests in `test_doc_generators.py`

Example:
```python
class MyDocGenerator(DocGenerator):
    def generate(self) -> str:
        parts = ["<h1>" + self.metadata.title + "</h1>"]
        # Generate content...
        return self._wrap_storage("\n".join(parts))
```

### Adding New Code Extraction Types

1. Add extraction type to `CodeAnalysisConfig.extract`
2. Implement `_extract_*()` method in `CodeScanner`
3. Return structured dict with type, details
4. Use in generators via `self.extracted_info`

### Adding New Integrations

1. Create integration config in `IntegrationConfig`
2. Add client/wrapper class
3. Call from appropriate location in `ConfluenceSkill`
4. Add configuration documentation

## Performance Considerations

- **Caching**: Page lookups cached per session
- **Rate Limiting**: Respects Confluence API limits
- **File Limits**: Configurable max files analyzed
- **Content Limits**: Warns for large documents
- **Batch Operations**: Update multiple pages efficiently

## Testing Strategy

- **Unit Tests**: Individual components (models, validators, generators)
- **Integration Tests**: ConfluenceClient with mocked API
- **Mock Fixtures**: Fixture-based testing with pytest
- **Configuration Tests**: Validation of config files
- **Error Scenarios**: Edge cases and failure modes

All tests run without hitting real Confluence instances (mocked API).

## Known Limitations

1. **Diagram Generation**: Requires additional tooling (Mermaid/Kroki)
2. **Macro Support**: Limited support for complex Confluence macros
3. **Legacy Cloud API**: Only supports v2 API (not v1)
4. **Rate Limits**: 100 writes/minute due to Confluence limits
5. **Concurrent Operations**: Not designed for concurrent access to same page
