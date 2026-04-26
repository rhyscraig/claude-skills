"""Tests for base configuration loader.

Demonstrates pragmatic testing patterns for config management:
- Testing configuration hierarchy (defaults → master → repo → env)
- Validation and error handling
- Environment variable overrides
- Secret prevention
"""

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import pytest

from src.base_config import BaseConfigLoader, ConfigError


class TestConfig(BaseConfigLoader):
    """Test implementation of BaseConfigLoader."""

    def schema(self) -> Dict[str, Any]:
        """Return schema for testing."""
        return {
            "type": "object",
            "properties": {
                "app": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "debug": {"type": "boolean"},
                    },
                    "required": ["name"],
                },
                "api": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string"},
                        "url": {"type": "string"},
                    },
                },
            },
            "required": ["app"],
        }

    def load_defaults(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "app": {
                "name": "test-app",
                "debug": False,
            },
            "api": {
                "key": "${API_KEY}",
                "url": "https://api.example.com",
            },
        }


class TestBaseConfigLoader:
    """Test suite for base configuration loader."""

    def test_load_defaults(self):
        """Test loading default configuration."""
        config_loader = TestConfig("test")
        config = config_loader.load()

        assert config["app"]["name"] == "test-app"
        assert config["app"]["debug"] is False
        assert config["api"]["url"] == "https://api.example.com"

    def test_load_master_config(self, tmp_path, monkeypatch):
        """Test loading master configuration."""
        # Create fake master config
        home = tmp_path / "home"
        home.mkdir()
        config_dir = home / ".claude" / "test"
        config_dir.mkdir(parents=True)

        master_config = {
            "app": {"debug": True},
            "api": {"url": "https://api-prod.example.com"},
        }

        with open(config_dir / "config.json", "w") as f:
            json.dump(master_config, f)

        # Mock home directory
        monkeypatch.setattr("pathlib.Path.home", lambda: home)

        # Load config
        config_loader = TestConfig("test")
        config = config_loader.load()

        # Master config should override defaults
        assert config["app"]["debug"] is True
        assert config["api"]["url"] == "https://api-prod.example.com"
        assert config["app"]["name"] == "test-app"  # From defaults

    def test_load_repo_config(self, tmp_path, monkeypatch):
        """Test loading repo-specific configuration."""
        # Create repo config
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        claude_dir = repo_dir / ".claude"
        claude_dir.mkdir()

        repo_config = {
            "app": {"name": "my-project"},
        }

        with open(claude_dir / "claude.json", "w") as f:
            json.dump(repo_config, f)

        # Change to repo directory
        monkeypatch.chdir(repo_dir)

        # Load config
        config_loader = TestConfig("test")
        config = config_loader.load()

        # Repo config should override defaults
        assert config["app"]["name"] == "my-project"

    def test_config_hierarchy(self, tmp_path, monkeypatch):
        """Test full configuration hierarchy (defaults → master → repo → env)."""
        # Create master config
        home = tmp_path / "home"
        home.mkdir()
        config_dir = home / ".claude" / "test"
        config_dir.mkdir(parents=True)

        master_config = {
            "app": {"debug": True},
        }

        with open(config_dir / "config.json", "w") as f:
            json.dump(master_config, f)

        # Create repo config
        repo_dir = tmp_path / "repo"
        repo_dir.mkdir()
        claude_dir = repo_dir / ".claude"
        claude_dir.mkdir()

        repo_config = {
            "app": {"name": "my-project"},
        }

        with open(claude_dir / "claude.json", "w") as f:
            json.dump(repo_config, f)

        # Mock home and change to repo
        monkeypatch.setattr("pathlib.Path.home", lambda: home)
        monkeypatch.chdir(repo_dir)

        # Set env override
        monkeypatch.setenv("TEST_API_URL", "https://api-env.example.com")

        # Load config
        config_loader = TestConfig("test")
        config = config_loader.load()

        # Check hierarchy applied correctly
        assert config["app"]["name"] == "my-project"  # From repo
        assert config["app"]["debug"] is True  # From master
        assert config["api"]["url"] == "https://api-env.example.com"  # From env

    def test_validation_passes(self):
        """Test configuration passes validation."""
        config_loader = TestConfig("test")
        config = config_loader.load()

        # Should not raise
        assert config["app"]["name"] == "test-app"

    def test_validation_fails_missing_required(self):
        """Test validation fails with missing required field."""

        class BadConfig(TestConfig):
            def load_defaults(self) -> Dict[str, Any]:
                return {
                    "api": {"key": "test"},  # Missing required "app"
                }

        config_loader = BadConfig("test")

        with pytest.raises(ConfigError) as exc_info:
            config_loader.load()

        assert "validation failed" in str(exc_info.value).lower()

    def test_validation_fails_wrong_type(self):
        """Test validation fails with wrong field type."""

        class BadConfig(TestConfig):
            def load_defaults(self) -> Dict[str, Any]:
                return {
                    "app": {
                        "name": "test",
                        "debug": "yes",  # Should be boolean, not string
                    },
                }

        config_loader = BadConfig("test")

        with pytest.raises(ConfigError) as exc_info:
            config_loader.load()

        assert "validation failed" in str(exc_info.value).lower()

    def test_deep_merge(self):
        """Test deep merging of configuration dicts."""
        config_loader = TestConfig("test")

        base = {
            "a": {"b": 1, "c": 2},
            "x": "test",
        }

        overrides = {
            "a": {"b": 99},
            "y": "new",
        }

        result = config_loader._deep_merge(base, overrides)

        assert result["a"]["b"] == 99  # Overridden
        assert result["a"]["c"] == 2  # Preserved from base
        assert result["x"] == "test"  # Preserved from base
        assert result["y"] == "new"  # Added from overrides

    def test_invalid_json_raises_error(self, tmp_path, monkeypatch):
        """Test that invalid JSON raises ConfigError."""
        home = tmp_path / "home"
        home.mkdir()
        config_dir = home / ".claude" / "test"
        config_dir.mkdir(parents=True)

        # Write invalid JSON
        with open(config_dir / "config.json", "w") as f:
            f.write("{invalid json}")

        monkeypatch.setattr("pathlib.Path.home", lambda: home)

        config_loader = TestConfig("test")

        with pytest.raises(ConfigError) as exc_info:
            config_loader.load()

        assert "JSON" in str(exc_info.value)

    def test_config_caching(self):
        """Test that configuration is cached after first load."""
        config_loader = TestConfig("test")

        config1 = config_loader.load()
        config2 = config_loader.load()

        # Should be same object (cached)
        assert config1 is config2

    def test_config_reset(self):
        """Test resetting configuration cache."""
        config_loader = TestConfig("test")

        config1 = config_loader.load()
        config_loader.reset()
        config2 = config_loader.load()

        # Should be different objects (cache cleared)
        assert config1 is not config2
        # But same content
        assert config1 == config2

    def test_show_returns_json_string(self):
        """Test show() returns pretty-printed JSON."""
        config_loader = TestConfig("test")
        output = config_loader.show()

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed["app"]["name"] == "test-app"

    def test_no_secrets_in_config(self):
        """Test that environment variable placeholders are not secrets."""
        config_loader = TestConfig("test")
        config = config_loader.load()

        # ${API_KEY} placeholder should not leak actual key
        assert config["api"]["key"] == "${API_KEY}"
