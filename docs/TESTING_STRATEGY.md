# Testing Strategy for Claude Skills

> Pragmatic testing approach that catches real bugs while remaining maintainable.

## Philosophy

**Test Behavior, Not Implementation**

Good tests:
- ✅ Test what the user cares about (configuration loads correctly)
- ✅ Test edge cases (invalid config, missing files, env overrides)
- ✅ Test error conditions (what happens when external service fails?)
- ❌ Don't test internal implementation details
- ❌ Don't mock more than necessary
- ❌ Don't test third-party libraries

## Test Structure

### 1. Configuration Tests

```python
# tests/test_config.py
def test_config_loads_defaults():
    """Configuration loads and returns defaults."""
    config = MyConfig("my-skill", validate=False)
    defaults = config.load_defaults()
    assert defaults["api"]["url"] == "https://api.example.com"

def test_config_validates_schema():
    """Invalid configuration fails validation."""
    class BadConfig(MyConfig):
        def load_defaults(self):
            return {}  # Missing required fields
    
    config = BadConfig("my-skill")
    with pytest.raises(ConfigError):
        config.load()

def test_config_hierarchy():
    """Configuration hierarchy: defaults → master → repo → env."""
    # Setup master config
    # Setup repo config
    # Set environment variable
    
    config = loader.load()
    
    # Verify hierarchy applied
    assert config["app"]["name"] == "my-app"  # From repo
    assert config["api"]["url"] == "https://api-env.example.com"  # From env
```

### 2. Guardrails Tests

```python
# tests/test_guardrails.py
def test_action_allowed_without_confirmation():
    """Non-gated actions are allowed."""
    guardrails = MyGuardrails({})
    assert guardrails.can_perform("list") is True

def test_action_blocked_without_confirmation():
    """Gated actions require confirmation."""
    guardrails = MyGuardrails({})
    assert guardrails.can_perform("delete") is False

def test_confirmation_grants_permission():
    """User confirmation allows action."""
    guardrails = MyGuardrails({})
    confirmed = guardrails.confirm_action(
        "delete",
        user_input=lambda: True
    )
    assert confirmed is True

def test_rate_limit_enforcement():
    """Rate limits are enforced."""
    guardrails = MyGuardrails({})
    
    # Perform action up to limit
    for i in range(10):
        guardrails.confirm_action("delete", user_input=lambda: True)
    
    # Exceeding limit raises error
    with pytest.raises(GuardrailViolation):
        guardrails.confirm_action("delete", user_input=lambda: True)
```

### 3. CLI Tests

```python
# tests/test_cli.py
def test_cli_routes_commands():
    """CLI properly routes to command handlers."""
    cli = MyCLI()
    assert "list" in cli.commands
    assert "create" in cli.commands

def test_cli_shows_help():
    """Help text displays."""
    cli = MyCLI()
    result = cli.main(["--help"])
    assert result == 0

def test_cli_shows_version():
    """Version displays."""
    cli = MyCLI()
    result = cli.main(["--version"])
    assert result == 0

def test_cli_error_handling():
    """Unknown commands return error."""
    cli = MyCLI()
    result = cli.main(["unknown-command"])
    assert result == 1
```

## Test Fixtures

### Common Fixtures

```python
# tests/conftest.py

@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Temporary home directory for config tests."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    return home

@pytest.fixture
def temp_repo(tmp_path, monkeypatch):
    """Temporary repo directory."""
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    return repo

@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment for each test."""
    for key in list(os.environ.keys()):
        if key.startswith("TEST_"):
            monkeypatch.delenv(key, raising=False)
    return monkeypatch
```

### Usage

```python
def test_config_with_fixtures(temp_home, temp_repo):
    """Test configuration with temporary directories."""
    # Create master config in temp_home
    config_dir = temp_home / ".claude" / "my-skill"
    config_dir.mkdir(parents=True)
    
    # Create repo config in temp_repo
    claude_dir = temp_repo / ".claude"
    claude_dir.mkdir()
    
    # Load and test
    config = loader.load()
    assert config["app"]["name"] == "my-app"
```

## Test Coverage

### Target: >90% Coverage

```bash
# Generate coverage report
pytest tests/ --cov=src --cov-report=html

# View report
open htmlcov/index.html
```

### What to Cover

**Always test:**
- ✅ Happy path (normal operation)
- ✅ Error conditions (missing files, invalid input)
- ✅ Edge cases (empty arrays, null values)
- ✅ Configuration hierarchy
- ✅ Validation logic
- ✅ Permission gates

**Don't need to test:**
- ❌ Third-party library behavior (pytest, requests, etc.)
- ❌ Python built-ins (str, dict, list)
- ❌ Simple getters/setters with no logic

## Mocking Strategy

### Rule: Mock External Dependencies, Not Your Code

```python
# ✅ GOOD - Mock external API
def test_api_call(monkeypatch, mock_api_response):
    mock_api_response({"id": 1, "name": "Item"})
    
    api = MyAPI("https://api.example.com", "key")
    item = api.get_item(1)
    
    assert item["name"] == "Item"

# ❌ BAD - Mocking your own code
def test_config_loading(monkeypatch):
    monkeypatch.setattr(
        MyConfig,
        "load_defaults",
        lambda: {"mocked": True}
    )
    # This defeats the purpose of testing!
```

### Mocking External Services

```python
# Mock HTTP requests
@pytest.fixture
def mock_requests(monkeypatch):
    class MockResponse:
        def __init__(self, json_data):
            self.json_data = json_data
        
        def json(self):
            return self.json_data
        
        def raise_for_status(self):
            pass
    
    def mock_get(*args, **kwargs):
        return MockResponse({"items": []})
    
    monkeypatch.setattr(requests, "get", mock_get)

# Use in tests
def test_list_items(mock_requests):
    api = MyAPI("https://api.example.com", "key")
    items = api.list_items()
    assert items == []
```

## Security Testing

### Test Secret Handling

```python
# tests/test_security.py
def test_config_never_logs_secrets(caplog):
    """Verify secrets are never logged."""
    config = MyConfig("my-skill")
    config.load()
    
    # Check logs don't contain any API keys
    assert "sk_" not in caplog.text
    assert "APIKEY" not in caplog.text

def test_env_var_required_not_defaulted():
    """Verify API keys come from environment, not defaults."""
    config = MyConfig("my-skill")
    
    # Without env var set
    os.environ.pop("MY_SKILL_API_KEY", None)
    
    with pytest.raises(ValueError):
        config.load()

def test_error_messages_dont_leak_secrets():
    """Verify error messages are user-safe."""
    try:
        api = MyAPI("https://api.example.com", "real_key_12345")
        api.call_external_service()
    except Exception as e:
        # Should never contain actual key
        assert "real_key_12345" not in str(e)
```

## Integration Tests

### Test Full Workflows

```python
# tests/integration/test_e2e.py
def test_create_and_list_items():
    """End-to-end: create item and verify it appears in list."""
    # Setup config
    config = MyConfig("my-skill")
    config.load()
    
    # Create item
    api = MyAPI(config["api"]["url"], config["api"]["key"])
    created = api.create_item("My Project", "New Item")
    
    # List items
    items = api.list_items("My Project")
    
    # Verify created item in list
    assert any(item["id"] == created["id"] for item in items)
```

## Running Tests

### All Tests

```bash
pytest tests/
```

### Specific Test File

```bash
pytest tests/test_config.py
```

### Specific Test

```bash
pytest tests/test_config.py::TestConfigLoader::test_loads_defaults
```

### With Verbose Output

```bash
pytest tests/ -v
```

### With Coverage

```bash
pytest tests/ --cov=src --cov-report=html
```

### Run Only Security Tests

```bash
pytest tests/ -m security
```

## Continuous Integration

GitHub Actions runs tests on every push and PR:

1. **Test on multiple Python versions** (3.8 - 3.12)
2. **Check code quality** (black, ruff, mypy)
3. **Run security checks** (bandit, detect-secrets)
4. **Generate coverage report**

See `.github/workflows/test.yml` for configuration.

## Test Maintenance

### Keep Tests Updated When Code Changes

```python
# ❌ When you change behavior, update tests
def load_config(skip_validation: bool = False):
    # Changed from validate=True
    pass

# ✅ Update corresponding tests
def test_can_skip_validation():
    config = MyConfig("my-skill", skip_validation=True)
    # ... test behavior
```

### Delete Tests That No Longer Make Sense

```python
# If you remove a feature, remove its tests too
# ❌ Don't keep dead tests "just in case"
```

### Refactor Tests Like Code

Tests are code too. Keep them clean:
- Extract common setup to fixtures
- Use descriptive names
- Remove duplication
- Update comments

---

**Remember**: Good tests catch bugs, prevent regressions, and document behavior. Invest in testing.
