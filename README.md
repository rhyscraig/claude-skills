# Claude Skills — Enterprise Cloud Operations

A best-practice repository of Claude AI skills for autonomous cloud operations. Currently includes the **cloudctl** skill for managing multi-cloud contexts across AWS, Azure, and GCP.

## Features

### cloudctl Skill

The cloudctl skill enables Claude to autonomously manage your cloud infrastructure contexts:

- **Context Switching:** Switch between AWS accounts, GCP projects, Azure subscriptions seamlessly
- **Authentication:** Trigger credential refresh across cloud providers
- **Environment Verification:** Automatically verify you're in the correct account/role before risky operations
- **Multi-Cloud Support:** Single interface for AWS, Azure, and GCP operations
- **Audit Logging:** Complete audit trail of all operations performed
- **Dry-Run Mode:** Test operations without execution
- **Retry Logic:** Automatic retry on transient failures

### Example Usage

```python
from skills.cloudctl import CloudctlSkill

skill = CloudctlSkill()

# Switch to production account
await skill.switch_context(
    organization="prod",
    account_id="123456789",
    role="terraform"
)

# Verify credentials are valid
is_valid = await skill.verify_credentials("prod")

# Execute arbitrary cloudctl command
result = await skill.execute_command(["status"])
```

## Installation

### Prerequisites

- Python 3.12 or later
- cloudctl v4.0.0 or later (`pip install cloudctl`)

### Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/claude-skills.git
cd claude-skills

# Install in development mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=skills --cov-report=html

# Run specific test markers
pytest -m unit
pytest -m integration
pytest -m security
```

### Code Quality

```bash
# Run linting
ruff check skills tests

# Format code
black skills tests

# Type checking
mypy skills

# Security scanning
bandit -r skills

# All checks
make lint
```

### Building

```bash
# Build distribution
poetry build

# Check build artifacts
twine check dist/*
```

## Configuration

Configure the cloudctl skill via `SkillConfig`:

```python
from skills.cloudctl import CloudctlSkill
from skills.cloudctl.models import SkillConfig

config = SkillConfig(
    cloudctl_path="cloudctl",          # Path to cloudctl binary
    timeout_seconds=30,                 # Command timeout
    max_retries=3,                      # Retry attempts
    verify_context_after_switch=True,  # Verify after context switch
    enable_audit_logging=True,         # Enable audit trail
    dry_run=False,                     # Dry-run mode
)

skill = CloudctlSkill(config=config)
```

### Environment Variables

Control behavior via environment variables:

```bash
export CLOUDCTL_PATH="/usr/local/bin/cloudctl"
export CLOUDCTL_TIMEOUT="60"
export CLOUDCTL_RETRIES="5"
export CLOUDCTL_VERIFY="true"
export CLOUDCTL_AUDIT="true"
export CLOUDCTL_DRY_RUN="false"
```

## Architecture

### Core Components

- **`skill.py`**: Main CloudctlSkill class for autonomous operations
- **`models.py`**: Data models with Pydantic validation
  - `CloudContext`: Current cloud context state
  - `CommandResult`: Command execution result
  - `SkillConfig`: Configuration with validation
  - `OperationLog`: Audit trail entry

### Design Principles

1. **Security First**
   - Subprocess isolation with explicit argument passing
   - No shell interpretation of arguments
   - Command injection prevention

2. **Observability**
   - Complete audit logging to `~/.config/cloudctl/audit/`
   - Operation tracking in-memory and on-disk
   - Rich console output with status indicators

3. **Reliability**
   - Automatic retry logic for transient failures
   - Timeout protection
   - Graceful error handling

4. **Type Safety**
   - Full type hints throughout
   - Pydantic validation for all models
   - MyPy strict mode enforcement

## Testing

### Test Coverage

Current coverage: **85%+**

Test categories:

- **Unit Tests:** Model validation, skill methods
- **Integration Tests:** Actual cloudctl command execution
- **Security Tests:** Command injection, environment variable handling

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_skill.py

# Run by marker
pytest -m "unit or security"

# Generate coverage report
pytest --cov=skills --cov-report=term-missing
```

## Security

### Threat Model

The skill is designed to:

1. **Prevent command injection** via subprocess argument isolation
2. **Audit all operations** to detect unauthorized access
3. **Validate all inputs** using Pydantic models
4. **Timeout long-running commands** to prevent DoS
5. **Control environment variables** to prevent leakage

### Security Scanning

```bash
# Bandit (security issues)
bandit -r skills

# Checkov (cloud misconfigurations)
checkov -d skills

# Pip-audit (dependencies)
pip-audit
```

## Project Structure

```
claude-skills/
├── skills/
│   └── cloudctl/              # cloudctl skill
│       ├── __init__.py        # Public API
│       ├── skill.py           # Main skill class
│       └── models.py          # Data models
├── tests/
│   ├── test_models.py         # Model tests
│   ├── test_skill.py          # Skill tests
│   └── conftest.py            # Pytest configuration
├── docs/
│   ├── ARCHITECTURE.md        # Architecture guide
│   ├── SECURITY.md            # Security documentation
│   └── EXAMPLES.md            # Usage examples
├── pyproject.toml             # Project metadata
├── README.md                  # This file
├── Makefile                   # Development tasks
└── .github/
    └── workflows/
        └── ci.yaml            # CI/CD pipeline
```

## Contributing

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/awesome`
3. **Write tests** for your changes
4. **Ensure tests pass**: `pytest`
5. **Check code quality**: `make lint`
6. **Commit with clear message**: `git commit -am "Add awesome feature"`
7. **Push to branch**: `git push origin feature/awesome`
8. **Create Pull Request** with description

### Code Style

- **Python**: PEP 8 via Black (line length 120)
- **Imports**: Sorted via Ruff
- **Types**: Full type hints, MyPy strict mode
- **Tests**: Pytest with ~85% coverage

## License

MIT License — see [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/claude-skills/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/claude-skills/discussions)
- **Security**: Report to security@craighoad.com

## Changelog

### v1.0.0 (2026-04-25)

**Initial Release**

- ✅ cloudctl skill with full AWS/GCP/Azure support
- ✅ Comprehensive audit logging
- ✅ Retry logic and timeout protection
- ✅ Full test coverage (85%+)
- ✅ Security scanning integrated
- ✅ Type hints throughout

---

**Built with ❤️ for autonomous cloud operations**
