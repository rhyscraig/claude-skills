# Contributing to Claude Skills Platform

Thank you for contributing! This is a production-grade framework, so we maintain high standards for code quality, security, and testing.

## Before You Start

1. Read [SECURITY.md](SECURITY.md) — understand our secret handling practices
2. Review [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — understand the design
3. Check existing [issues](https://github.com/rhyscraig/claude-skills/issues) — avoid duplicate work

## Development Setup

### 1. Clone & Install

```bash
git clone https://github.com/rhyscraig/claude-skills.git
cd claude-skills
make install
```

### 2. Verify Setup

```bash
make check  # Runs all quality checks
```

## Making Changes

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Use descriptive branch names:
- `feature/add-cli-base-class` ✅ Good
- `fix/config-validation-bug` ✅ Good
- `docs/update-readme` ✅ Good
- `f1` ❌ Not descriptive

### 2. Write Code with Tests

Every feature must have tests.

```python
# ✅ Good: Tests validate behavior
def test_config_merges_hierarchy():
    """Verify configuration hierarchy: defaults → master → repo → env."""
    config = loader.load()
    assert config["app"]["debug"] is True  # From master
    assert config["app"]["name"] == "my-app"  # From repo

# ❌ Bad: No test coverage
def _internal_helper():
    # Untested helper function
    pass
```

### 3. Run Quality Checks

Before committing:

```bash
make format      # Auto-format code
make lint        # Check for issues
make typecheck   # Verify type hints
make test        # Run all tests
```

Or run all at once:

```bash
make check       # Format + lint + typecheck + test
```

### 4. Never Commit Secrets

**CRITICAL**: Never commit secrets, API keys, or credentials.

```bash
# ❌ WRONG - Never do this
echo "JIRA_API_TOKEN=sk_1234567890abcdef" >> .env
git add .env

# ✅ CORRECT - Use environment variables only
touch .env
git check-ignore .env  # Verify it's ignored

# ✅ CORRECT - Commit example with placeholders
cat > .env.example << 'EOF'
JIRA_API_TOKEN=sk_PLACEHOLDER_NEVER_USE_THIS
EOF
git add .env.example
```

Before every commit, run pre-commit hooks:

```bash
pre-commit run --all-files
```

## Code Standards

### Style & Formatting

```bash
# Format with Black (line length 100)
black src/ tests/
```

### Linting

```bash
# Check with Ruff
ruff check src/ tests/ --fix
```

Ruff rules enforced:
- `E` — PEP 8 errors
- `F` — Unused imports, undefined names
- `W` — PEP 8 warnings
- `I` — Import sorting
- `N` — Naming conventions

### Type Hints

All public functions must have type hints:

```python
# ✅ Good
def load_config(
    skill_name: str, 
    validate: bool = True
) -> Dict[str, Any]:
    """Load configuration from hierarchy."""
    pass

# ❌ Bad
def load_config(skill_name, validate=True):
    pass
```

Type check with mypy:

```bash
mypy src/ --strict --ignore-missing-imports
```

### Documentation

All public classes and functions need docstrings:

```python
class BaseConfigLoader(ABC):
    """Abstract base class for configuration management.
    
    Implements configuration hierarchy:
    1. Built-in defaults
    2. Master config (~/.claude/{skill}/config.json)
    3. Repo config (.claude/claude.json)
    4. Environment variable overrides
    """

    def load(self) -> Dict[str, Any]:
        """Load configuration from all sources.
        
        Returns:
            Merged configuration dict
            
        Raises:
            ConfigError: If validation fails
        """
        pass
```

## Testing

### Coverage Requirements

- Aim for >90% code coverage
- Test both success and failure paths
- Test configuration hierarchy
- Test guardrails and safety features

### Test Structure

```python
# ✅ Good test structure
class TestConfigLoader:
    """Tests for config loading."""
    
    def test_loads_defaults(self):
        """Verify defaults load without error."""
        loader = ConfigLoader("test")
        config = loader.load()
        assert config["app"]["name"] == "test-app"
    
    def test_merges_master_config(self, tmp_path):
        """Verify master config overrides defaults."""
        # Setup
        master = {"app": {"debug": True}}
        # Execute
        loader.load()
        # Assert
        assert loader.config["app"]["debug"] is True
    
    def test_validation_fails_invalid_schema(self):
        """Verify invalid config raises error."""
        with pytest.raises(ConfigError):
            loader.load()
```

### Run Tests

```bash
# All tests
pytest tests/

# With coverage
pytest tests/ --cov=src --cov-report=html

# Specific test
pytest tests/test_base_config.py::TestConfigLoader::test_loads_defaults -v
```

## Security Checklist

Before submitting PR:

- [ ] No `.env` files with real credentials
- [ ] No API keys or tokens in code
- [ ] No hardcoded passwords or secrets
- [ ] All external service calls use environment variables
- [ ] Error messages don't leak internal state or credentials
- [ ] Configuration examples use placeholder values
- [ ] Pre-commit hooks pass: `pre-commit run --all-files`
- [ ] Tests verify no secrets in logs or output

See [SECURITY.md](SECURITY.md) for complete security guidelines.

## Pull Request Process

### 1. Before Opening PR

- [ ] All tests pass: `make test`
- [ ] All checks pass: `make check`
- [ ] Code is formatted: `black src/ tests/`
- [ ] No secrets committed
- [ ] Docstrings added for new functions
- [ ] Tests written for new code (>90% coverage)

### 2. Create Pull Request

Title format:
```
[type] description

Types: feat, fix, docs, refactor, test, chore
```

Examples:
- `[feat] Add CLI base class for skill development`
- `[fix] Fix config validation for nested properties`
- `[docs] Update SKILL_TEMPLATE with new patterns`
- `[test] Add comprehensive guardrails tests`

### 3. PR Description

Include:
- What the PR does
- Why it's needed
- How to test it
- Any breaking changes

```markdown
## What

Add `BaseSkillCLI` abstract class for command routing.

## Why

Standardizes CLI development across all skills. Reduces boilerplate.

## How to Test

1. `make test` — all tests pass
2. `make check` — all quality checks pass
3. Review example usage in docs/SKILL_TEMPLATE.md

## Breaking Changes

None.
```

### 4. Code Review

Reviewers will check:
- Does it follow code standards?
- Are there sufficient tests?
- Is documentation clear?
- Are there security issues?
- Does it fit the architecture?

### 5. Merge

Once approved and CI passes, the PR will be merged.

## Common Issues

### "pre-commit: command not found"

Install pre-commit:
```bash
pip install pre-commit
pre-commit install
```

### "import not found"

Verify dependencies are installed:
```bash
pip install -e ".[dev]"
```

### Tests fail locally but pass in CI

Make sure you're using the same Python version:
```bash
python --version  # Should be 3.8+
```

## Questions?

1. Check existing [issues](https://github.com/rhyscraig/claude-skills/issues)
2. Review [SECURITY.md](SECURITY.md), [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md), or [docs/SKILL_TEMPLATE.md](docs/SKILL_TEMPLATE.md)
3. Open a [discussion](https://github.com/rhyscraig/claude-skills/discussions)

## Code of Conduct

Be respectful, inclusive, and constructive. We value all contributions.

---

Thanks for making Claude Skills Platform better! 🎉
