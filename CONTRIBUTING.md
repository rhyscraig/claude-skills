# Contributing to Claude Skills

Thanks for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

Be respectful, inclusive, and professional in all interactions.

## Getting Started

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-skills.git
cd claude-skills

# Install in development mode
make install

# Or with poetry
make bootstrap
```

### Running Tests

```bash
# Run all tests
make test

# Run with coverage
make coverage

# Run specific test file
pytest tests/test_models.py

# Run by marker
pytest -m unit
pytest -m security
```

### Code Quality

```bash
# Check code quality
make lint

# Auto-fix formatting
make format

# Run security checks
make security
```

## Contribution Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/awesome-feature
   ```

2. **Make your changes**
   - Write clear, documented code
   - Add tests for new functionality
   - Update documentation as needed

3. **Ensure tests pass**
   ```bash
   make check
   ```

4. **Commit with clear message**
   ```bash
   git commit -am "Add awesome feature

   - Describe what changed
   - Explain why this change
   - Reference any related issues"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/awesome-feature
   ```

6. **Create Pull Request**
   - Describe your changes
   - Reference any related issues
   - Ensure CI passes

## Code Standards

### Python Style

- **Line length:** 120 characters (Black)
- **Imports:** Sorted (Ruff)
- **Type hints:** Required throughout
- **Docstrings:** Google-style, for all public functions

### Example

```python
def switch_context(
    self,
    organization: str,
    account_id: Optional[str] = None,
    role: Optional[str] = None,
) -> CommandResult:
    """Switch cloud context to specified organization/account/role.

    Args:
        organization: Organization name
        account_id: AWS account ID or GCP project ID
        role: IAM role or GCP role

    Returns:
        CommandResult with switch operation status

    Raises:
        ValueError: If organization is empty
    """
```

### Testing

- Minimum **85% coverage** for committed code
- Test both happy path and error cases
- Use appropriate markers: `@pytest.mark.unit`, `@pytest.mark.security`
- Mock external dependencies

### Security

- No hardcoded credentials
- Validate all inputs using Pydantic
- Use subprocess isolation (no shell=True)
- Proper error handling without information leakage

## PR Review Process

1. **Automated checks must pass**
   - Tests (431/431)
   - Coverage (85%+)
   - Linting (ruff, black, mypy)
   - Security (bandit, checkov)

2. **Code review**
   - At least one maintainer approval
   - Address feedback constructively
   - Request re-review after changes

3. **Merge**
   - Use "Squash and merge" for cleaner history
   - Include clear commit message

## Releasing

Releases follow [Semantic Versioning](https://semver.org/):

- **MAJOR:** Breaking changes
- **MINOR:** New features (backward compatible)
- **PATCH:** Bug fixes

Steps:
1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create git tag: `git tag v1.2.3`
4. Push tag: `git push origin v1.2.3`
5. GitHub Actions creates release automatically

## Questions?

- Open an issue for bugs
- Start a discussion for questions
- Email security@craighoad.com for security issues

## License

By contributing, you agree your contributions are licensed under the MIT License.

---

Happy contributing! 🎉
