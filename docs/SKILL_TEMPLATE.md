# Building a Skill with Claude Skills Platform

> Complete step-by-step guide for building production-grade Claude skills using the framework.

## What You'll Learn

By the end of this guide, you'll have built a complete skill with:
- Configuration hierarchy (master + repo overrides)
- Safety guardrails with confirmation gates
- Full test coverage
- Production-ready CLI
- Security best practices

**Time**: ~30 minutes for basic skill, ~1-2 hours for production-grade

## Prerequisites

- Python 3.8+
- Basic familiarity with CLI tools
- Git

## Step 1: Create Skill Structure

### Create Project Directory

```bash
mkdir my-skill
cd my-skill
git init
pip install requests jsonschema typing-extensions pytest black ruff mypy
```

### Create Package Structure

```bash
mkdir src tests docs
touch src/__init__.py src/config.py src/cli.py src/api.py
touch tests/__init__.py tests/test_config.py tests/test_cli.py
touch pyproject.toml README.md SECURITY.md .gitignore
```

### Create .gitignore

Start with Claude Skills Platform's security-focused `.gitignore`:

```gitignore
# Python
__pycache__/
*.egg-info/
dist/
build/
.pytest_cache/

# Secrets (CRITICAL)
.env
.env.*
!.env.example
*.key
*.pem
secrets/

# IDE
.vscode/
.idea/
```

## Step 2: Design Configuration Schema

Your skill needs configuration. Define it clearly:

```python
# src/config.py
from src.base_config import BaseConfigLoader
from typing import Any, Dict
import os

class MySkillConfig(BaseConfigLoader):
    """Configuration for my-skill."""
    
    def schema(self) -> Dict[str, Any]:
        """Configuration schema."""
        return {
            "type": "object",
            "properties": {
                "api": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "format": "uri"},
                        "key": {"type": "string"},
                        "timeout": {"type": "integer", "minimum": 1}
                    },
                    "required": ["url", "key"]
                },
                "defaults": {
                    "type": "object",
                    "properties": {
                        "project": {"type": "string"},
                        "assignee": {"type": "string"}
                    }
                }
            },
            "required": ["api"]
        }
    
    def load_defaults(self) -> Dict[str, Any]:
        """Default configuration."""
        return {
            "api": {
                "url": "https://api.example.com",
                "key": "${MY_SKILL_API_KEY}",  # Placeholder
                "timeout": 30
            },
            "defaults": {
                "project": "DEFAULT",
                "assignee": None
            }
        }
```

### Create Example Config

Users will copy this to `~/.claude/my-skill/config.json` and fill with real values:

```json
{
  "api": {
    "url": "https://api.example.com",
    "key": "sk_YOUR_KEY_HERE",
    "timeout": 30
  },
  "defaults": {
    "project": "MY_PROJECT",
    "assignee": "alice@example.com"
  }
}
```

**Never commit this with real values!**

## Step 3: Create API Client

Encapsulate external service calls:

```python
# src/api.py
from typing import Any, Dict, Optional
import requests
from datetime import datetime

class MySkillAPI:
    """Client for external API."""
    
    def __init__(self, url: str, api_key: str, timeout: int = 30):
        """Initialize API client.
        
        Args:
            url: Base API URL
            api_key: API authentication key
            timeout: Request timeout in seconds
        """
        self.url = url
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {api_key}"
    
    def list_items(self, project: str) -> list[Dict[str, Any]]:
        """List items in a project."""
        resp = self.session.get(
            f"{self.url}/projects/{project}/items",
            timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()["items"]
    
    def create_item(
        self, 
        project: str, 
        name: str, 
        description: str
    ) -> Dict[str, Any]:
        """Create new item."""
        resp = self.session.post(
            f"{self.url}/projects/{project}/items",
            json={"name": name, "description": description},
            timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()
    
    def __del__(self):
        """Clean up session."""
        self.session.close()
```

## Step 4: Create CLI Commands

Commands follow a consistent pattern:

```python
# src/cli.py
from src.base_cli import BaseSkillCLI
from src.config import MySkillConfig
from src.guardrails import MySkillGuardrails
from src.api import MySkillAPI

class MySkillCLI(BaseSkillCLI):
    """CLI for my-skill."""
    
    def skill_name(self) -> str:
        return "my-skill"
    
    def skill_version(self) -> str:
        return "1.0.0"
    
    def get_config_loader(self):
        return MySkillConfig("my-skill")
    
    def get_guardrails(self):
        config = self.config_loader.load()
        return MySkillGuardrails(config.get("guardrails", {}))
    
    def register_commands(self):
        """Register all commands."""
        self.register_command("list", self.cmd_list, "List items")
        self.register_command("create", self.cmd_create, "Create item")
        self.register_command("config", self.cmd_config, "Show config")
    
    def cmd_list(self, args):
        """List items in project."""
        try:
            config = self.config_loader.load()
            api = MySkillAPI(
                url=config["api"]["url"],
                api_key=config["api"]["key"]
            )
            
            project = args[0] if args else config["defaults"]["project"]
            items = api.list_items(project)
            
            print(f"\n📋 Items in {project}:")
            for item in items:
                print(f"  • {item['name']}: {item['description']}")
            
            return 0
        
        except Exception as e:
            self.logger.exception("Error listing items")
            print(f"❌ Failed to list items: {e}")
            return 1
    
    def cmd_create(self, args):
        """Create new item."""
        if len(args) < 2:
            print("❌ Usage: my-skill create <project> <name> [description]")
            return 1
        
        try:
            config = self.config_loader.load()
            api = MySkillAPI(
                url=config["api"]["url"],
                api_key=config["api"]["key"]
            )
            
            project = args[0]
            name = args[1]
            description = args[2] if len(args) > 2 else ""
            
            # Require confirmation for creation
            def handler():
                result = api.create_item(project, name, description)
                print(f"✅ Created: {result['name']}")
            
            return 0 if self.run_with_confirmation("create", handler) else 1
        
        except Exception as e:
            self.logger.exception("Error creating item")
            print(f"❌ Failed to create item: {e}")
            return 1
    
    def cmd_config(self, args):
        """Show configuration."""
        print(self.config_loader.show())
        return 0

def main():
    """CLI entry point."""
    cli = MySkillCLI()
    return cli.main()

if __name__ == "__main__":
    sys.exit(main())
```

## Step 5: Create Guardrails

Define which actions need confirmation:

```python
# src/guardrails.py
from src.base_guardrails import BaseGuardrails
from typing import List, Dict

class MySkillGuardrails(BaseGuardrails):
    """Safety enforcement for my-skill."""
    
    def actions_requiring_confirmation(self) -> List[str]:
        """Actions requiring user confirmation."""
        return [
            "create",      # Creating items
            "delete",      # Deleting items
            "reassign",    # Reassigning ownership
        ]
    
    def get_rate_limits(self) -> Dict[str, int]:
        """Rate limits per run."""
        return {
            "create": 100,    # Max 100 creates per run
            "delete": 10,     # Max 10 deletes per run
            "reassign": 50,   # Max 50 reassignments per run
        }
```

## Step 6: Create Tests

Pragmatic tests that catch real bugs:

```python
# tests/test_config.py
import pytest
import json
import tempfile
from pathlib import Path
from src.config import MySkillConfig

def test_config_loads_defaults():
    """Verify default configuration loads."""
    config = MySkillConfig("my-skill", validate=False)
    defaults = config.load_defaults()
    
    assert defaults["api"]["url"] == "https://api.example.com"
    assert defaults["api"]["timeout"] == 30

def test_config_validates_schema():
    """Verify invalid config fails validation."""
    class BadConfig(MySkillConfig):
        def load_defaults(self):
            return {"api": {}}  # Missing required fields
    
    config = BadConfig("my-skill")
    with pytest.raises(Exception):  # ConfigError
        config.load()

def test_config_from_environment(monkeypatch):
    """Verify environment variables override config."""
    monkeypatch.setenv("MY_SKILL_API_URL", "https://custom.example.com")
    
    config = MySkillConfig("my-skill")
    loaded = config.load()
    
    assert loaded["api"]["url"] == "https://custom.example.com"

# tests/test_cli.py
import pytest
from src.cli import MySkillCLI
from unittest.mock import Mock, patch

def test_cli_routes_commands():
    """Verify CLI routes commands properly."""
    cli = MySkillCLI()
    
    assert "list" in cli.commands
    assert "create" in cli.commands
    assert "config" in cli.commands

def test_cli_shows_help():
    """Verify help text displays."""
    cli = MySkillCLI()
    result = cli.main(["--help"])
    
    assert result == 0

def test_cli_shows_version():
    """Verify version displays."""
    cli = MySkillCLI()
    result = cli.main(["--version"])
    
    assert result == 0
```

## Step 7: Package It

Create `pyproject.toml`:

```toml
[project]
name = "my-skill"
version = "1.0.0"
description = "Production-grade skill for X"
readme = "README.md"
requires-python = ">=3.8"
license = {text = "MIT"}
authors = [{name = "Your Name", email = "you@example.com"}]

dependencies = [
    "requests>=2.31.0",
    "jsonschema>=4.20.0",
    "typing-extensions>=4.8.0;python_version<'3.10'",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-cov>=4.1.0",
    "black>=23.12.0",
    "ruff>=0.1.0",
    "mypy>=1.7.0",
]

[project.scripts]
my-skill = "src.cli:main"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

## Step 8: Install & Test

```bash
# Install skill locally
pip install -e .

# Verify CLI works
my-skill --version
my-skill --help

# Run tests
pytest tests/

# Check code quality
black src/ tests/
ruff check src/ tests/
mypy src/
```

## Step 9: Create Documentation

Create `README.md` for users:

```markdown
# my-skill

Production-grade CLI for X.

## Quick Start

```bash
pip install my-skill
export MY_SKILL_API_KEY=sk_your_key_here
my-skill config  # Verify setup
my-skill list MY_PROJECT
```

## Configuration

Create `~/.claude/my-skill/config.json`:

```json
{
  "api": {
    "url": "https://api.example.com",
    "key": "sk_YOUR_KEY",
    "timeout": 30
  }
}
```

## Commands

- `my-skill list PROJECT` — List items
- `my-skill create PROJECT NAME [DESCRIPTION]` — Create item
- `my-skill config` — Show configuration

See [docs/](docs/) for complete reference.
```

Create `SECURITY.md` explaining secret handling:

```markdown
# Security

## Never Commit Secrets

1. `.env` files are ignored by git
2. `config.json` with real keys is not committed
3. API keys come from environment variables only

## Configuration

```bash
# Create local config
mkdir -p ~/.claude/my-skill
cat > ~/.claude/my-skill/config.json << 'EOF'
{
  "api": {
    "url": "https://api.example.com",
    "key": "sk_YOUR_REAL_KEY"
  }
}
EOF

# Or use environment variable
export MY_SKILL_API_KEY=sk_your_key_here
```

## Running Safely

```bash
# Always verify config is loaded correctly
my-skill config

# Then use the skill
my-skill list MY_PROJECT
```
```

## Step 10: Deploy & Share

Push to GitHub:

```bash
git add .
git commit -m "Initial my-skill implementation"
git remote add origin https://github.com/yourusername/my-skill
git push -u origin main
```

Make README in GitHub attractive:
- Add badges (license, Python version, tests)
- Quick start examples
- Link to documentation
- Contributor guidelines

## Verification Checklist

Before calling your skill "done":

- [ ] Configuration hierarchy works (defaults → master → repo → env)
- [ ] All commands have confirmation gates for sensitive operations
- [ ] Tests pass (`pytest tests/`)
- [ ] Code quality passes (`make check`)
- [ ] Security policy document exists (SECURITY.md)
- [ ] No secrets in any committed files
- [ ] Pre-commit hooks configured
- [ ] Documentation is complete (README, API reference)
- [ ] Example configs use placeholder values
- [ ] Entry point registered in pyproject.toml
- [ ] CLI works: `my-skill --version && my-skill --help`

## Next Steps

1. **Add more commands** following the same pattern
2. **Add integration tests** with mocked external services
3. **Create Makefile** for common tasks
4. **Set up GitHub Actions** for CI/CD
5. **Write comprehensive user guide**

## Getting Help

- Review [jira-skill](https://github.com/rhyscraig/jira-skill) for complete example
- Check [SECURITY.md](../SECURITY.md) for safe credential patterns
- Read [TESTING_STRATEGY.md](TESTING_STRATEGY.md) for test patterns
- See [ARCHITECTURE.md](ARCHITECTURE.md) for design decisions

---

**Congratulations!** You've built a production-grade Claude skill. 🎉

Now go build amazing things.
