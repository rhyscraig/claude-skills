# Claude Skills Platform

> Production-grade framework for building Claude skills with reusable patterns, safety guardrails, configuration management, and enterprise-grade architecture.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)
![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)

## What is This?

Claude Skills Platform is a **foundation for building production-grade AI automation tools**. Instead of rebuilding configuration, safety, and CLI patterns for each skill, inherit from our proven architecture and focus on your core logic.

**Not a CLI tool.** A framework. Built to be extended.

## Design Principles

✅ **Security First** — No secrets in code. Environment variables + validation.  
✅ **Configuration Hierarchy** — Master config + repo overrides + environment.  
✅ **Safety by Default** — Confirmation gates, audit logging, rate limiting.  
✅ **Type Safe** — Full type hints, dataclass models, validation.  
✅ **Testable Architecture** — Dependency injection, mockable dependencies.  
✅ **Pragmatic Testing** — Real-world test patterns, >90% coverage.  
✅ **Modern Python** — 3.8+, dataclasses, pathlib, logging.  

## Features

### 🔒 Security & Configuration
- **Bulletproof secrets handling** — No API keys in code, config files, or history
- **Configuration hierarchy** — `~/.claude/{skill}/config.json` + `.claude/claude.json` + environment
- **Environment validation** — Required variables checked at startup
- **Audit logging** — All sensitive operations recorded
- **Pre-commit hooks** — Automatic secret detection before GitHub

### 🛡️ Safety & Guardrails
- **Confirmation gates** — Required approval for sensitive operations
- **Rate limiting** — Prevent runaway bulk operations
- **Permission enforcement** — Role-based action control
- **Audit trails** — Complete action history with context
- **Error safety** — User-friendly messages, never leak internals

### 🏗️ Clean Architecture
- **Layered design** — CLI → Config → Guardrails → API → Models
- **Dependency injection** — Explicit dependencies, no global state
- **Separation of concerns** — Config, validation, routing, business logic isolated
- **Consistent patterns** — Every command follows same structure
- **Testable by design** — Mockable dependencies, pure functions

### 📚 Comprehensive Documentation
- **SKILL_TEMPLATE.md** — Step-by-step guide for building new skills
- **SECURITY.md** — Best practices for handling secrets safely
- **TESTING_STRATEGY.md** — Pragmatic testing patterns with examples
- **Example code** — Real patterns from jira-skill v2.0.0

## Quick Start: Build Your First Skill

### 1. Install Framework

```bash
pip install -e /path/to/claude-skills
```

### 2. Create Skill Structure

```bash
mkdir my-skill
cd my-skill
python -m pip install requests jsonschema typing-extensions
```

### 3. Inherit Base Classes

```python
# my_skill/config.py
from src.base_config import BaseConfigLoader

class MySkillConfig(BaseConfigLoader):
    def schema(self):
        return {
            "type": "object",
            "properties": {
                "api": {"type": "object", ...}
            }
        }
    
    def load_defaults(self):
        return {
            "api": {
                "url": "https://api.example.com",
                "key": os.environ.get("MY_SKILL_API_KEY")
            }
        }

# my_skill/cli.py
from src.base_cli import BaseSkillCLI

class MySkillCLI(BaseSkillCLI):
    def skill_name(self):
        return "my-skill"
    
    def skill_version(self):
        return "1.0.0"
    
    def register_commands(self):
        self.register_command("do-thing", self.cmd_do_thing, "Do a thing")
    
    def cmd_do_thing(self, args):
        config = self.config_loader.load()
        # Your logic here
        return 0
```

### 4. Run Your Skill

```bash
# Register CLI
pip install -e .

# Test it
my-skill --version
my-skill --help
my-skill do-thing
```

See [SKILL_TEMPLATE.md](docs/SKILL_TEMPLATE.md) for complete walkthrough.

## Example: Jira Skill

The framework includes **[jira-skill](https://github.com/rhyscraig/jira-skill)** (v2.0.0) as a reference implementation:

- **28 commands** across 6 categories
- **Configuration hierarchy** with per-project overrides
- **Safety guardrails** with confirmation gates
- **Full test coverage** (unit + integration)
- **Production deployed**

See [jira-skill repository](https://github.com/rhyscraig/jira-skill) for complete example.

## Architecture at a Glance

```
┌─────────────────────────────────────┐
│          CLI Layer (BaseSkillCLI)   │  ← Your commands & routing
├─────────────────────────────────────┤
│    Config Layer (BaseConfigLoader)  │  ← Hierarchy + validation
├─────────────────────────────────────┤
│    Guardrails Layer (BaseGuardrails)│  ← Confirmation + audit
├─────────────────────────────────────┤
│         Your Business Logic         │  ← Your API client, parsers, etc
├─────────────────────────────────────┤
│   External Services (APIs, etc)     │  ← Jira, GitHub, Slack, etc
└─────────────────────────────────────┘
```

Each layer is **independently testable** with mocked dependencies.

## Security Architecture

### No Secrets in Code

```python
# ❌ WRONG
api_key = "sk_1234567890abcdef"

# ✅ CORRECT
api_key = os.environ["MY_SKILL_API_KEY"]
```

### Configuration Flow

```
Defaults (src/config.py)
    ↓
Master Config (~/.claude/{skill}/config.json)
    ↓
Repo Config (.claude/claude.json)
    ↓
Environment Variables
    ↓
Validated Config
```

No secrets at any stage. See [SECURITY.md](SECURITY.md) for complete guide.

## Testing Strategy

Pragmatic testing that catches real bugs:

```python
# Test configuration hierarchy
def test_config_hierarchy():
    """Verify config merges defaults → master → repo → env."""
    config = loader.load()
    assert config["app"]["debug"] is True  # From master
    assert config["app"]["name"] == "my-app"  # From repo
    assert config["api"]["url"] == "https://env.example.com"  # From env

# Test guardrails
def test_confirmation_required():
    """Verify sensitive actions require approval."""
    assert not guardrails.can_perform("delete")  # Blocked without confirmation
    confirmed = guardrails.confirm_action("delete", user_input=mock_yes)
    assert confirmed is True  # Approved after confirmation

# Test CLI integration
def test_cli_routes_commands():
    """Verify CLI properly routes to handlers."""
    result = cli.main(["do-thing", "--id", "123"])
    assert result == 0  # Success
```

See [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) for complete patterns.

## Project Structure

```
claude-skills/
├── src/
│   ├── base_config.py          # Configuration loader
│   ├── base_guardrails.py      # Safety enforcement
│   ├── base_cli.py             # CLI framework
│   └── __init__.py             # Exports
├── tests/
│   ├── test_base_config.py
│   ├── test_base_guardrails.py
│   ├── test_base_cli.py
│   └── conftest.py
├── docs/
│   ├── SKILL_TEMPLATE.md       # How to build a skill
│   ├── TESTING_STRATEGY.md     # Testing patterns
│   └── ARCHITECTURE.md         # Technical deep dive
├── .pre-commit-config.yaml     # Pre-commit hooks
├── Makefile                    # Common tasks
├── pyproject.toml              # Package metadata
├── SECURITY.md                 # Security best practices
├── CONTRIBUTING.md             # Contributing guide
└── README.md                   # This file
```

## Getting Started: Step by Step

### 1. Read the Docs

- **Quick understanding**: [ARCHITECTURE.md](docs/ARCHITECTURE.md) (10 min read)
- **Build your first skill**: [SKILL_TEMPLATE.md](docs/SKILL_TEMPLATE.md) (30 min)
- **Keep secrets safe**: [SECURITY.md](SECURITY.md) (15 min)

### 2. Study the Example

Clone and explore [jira-skill](https://github.com/rhyscraig/jira-skill):
- How config hierarchy works
- How guardrails enforce safety
- How tests are structured

### 3. Build Your Skill

Follow [SKILL_TEMPLATE.md](docs/SKILL_TEMPLATE.md) to create your first skill.

### 4. Deploy It

```bash
pip install -e /path/to/your-skill
your-skill --version
your-skill --help
```

## Development

### Setup

```bash
git clone https://github.com/rhyscraig/claude-skills.git
cd claude-skills
pip install -e ".[dev]"
make install
```

### Run Tests

```bash
# All tests
make test

# With coverage
make coverage

# Specific test
pytest tests/test_base_config.py -v
```

### Quality Checks

```bash
# Format code
make format

# Lint
make lint

# Type checking
make typecheck

# All checks
make check
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code standards (black, ruff, mypy)
- Pull request process
- Testing requirements
- Security guidelines

**TL;DR**: 
1. Fork & clone
2. `make install` to set up environment
3. Make your changes with tests
4. `make check` to verify code quality
5. Submit PR

## Security

See [SECURITY.md](SECURITY.md) for:
- Secret prevention strategies
- Configuration best practices
- Incident response procedures
- Testing for security issues

**Tl;DR**: Never commit secrets. Use environment variables. Pre-commit hooks catch mistakes.

## License

MIT License - see [LICENSE](LICENSE) for details.

```
Copyright 2026 Craig Hoad

Permission is hereby granted, free of charge, to any person obtaining a copy...
```

## Support

### Documentation

- 📖 [SKILL_TEMPLATE.md](docs/SKILL_TEMPLATE.md) — Build a skill from scratch
- 🏗️ [ARCHITECTURE.md](docs/ARCHITECTURE.md) — Technical deep dive
- 🔒 [SECURITY.md](SECURITY.md) — Safe credential handling
- ✅ [TESTING_STRATEGY.md](docs/TESTING_STRATEGY.md) — Test patterns
- 🤝 [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute

### Examples

- **[jira-skill](https://github.com/rhyscraig/jira-skill)** — Full reference implementation with 28 commands

### Questions?

1. Check the docs first (they're comprehensive)
2. Search existing GitHub issues
3. Open a new issue with:
   - What you're trying to do
   - What failed
   - Relevant error messages (no secrets!)

---

**Made with ❤️ for Claude**

Built by [@craighoad](https://github.com/craighoad)  
Production-proven. Security-first. Ready to extend.
