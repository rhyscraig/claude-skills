"""Pytest configuration and fixtures for Claude Skills tests.

Provides common fixtures and setup for all tests.
"""

import os
import sys
import tempfile
from pathlib import Path

import pytest


# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Temporary home directory for testing config loading.

    Usage:
        def test_config(temp_home):
            config_dir = temp_home / ".claude" / "my-skill"
            config_dir.mkdir(parents=True)
            # Write config file
            # Test config loading
    """
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr("pathlib.Path.home", lambda: home)
    return home


@pytest.fixture
def temp_repo(tmp_path, monkeypatch):
    """Temporary repository directory for testing repo-level config.

    Usage:
        def test_repo_config(temp_repo):
            repo_dir = temp_repo
            claude_dir = repo_dir / ".claude"
            claude_dir.mkdir()
            # Write repo config
            # Change to repo
            monkeypatch.chdir(repo_dir)
            # Test config loading
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    monkeypatch.chdir(repo)
    return repo


@pytest.fixture
def clean_env(monkeypatch):
    """Clean environment variables for testing.

    Usage:
        def test_env_override(clean_env):
            monkeypatch.setenv("MY_VAR", "value")
            # Test with clean environment
    """
    # Clear test-related env vars
    for key in list(os.environ.keys()):
        if key.startswith("TEST_") or key.startswith("MY_SKILL_"):
            monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.fixture
def mock_api_response(monkeypatch):
    """Mock external API responses.

    Usage:
        def test_api_call(mock_api_response):
            mock_api_response({
                "items": [{"id": 1, "name": "Item 1"}]
            })
            # Test API client
    """
    def _mock(response_data):
        import requests
        from unittest.mock import Mock, patch

        mock_response = Mock()
        mock_response.json.return_value = response_data
        mock_response.raise_for_status.return_value = None

        monkeypatch.setattr(
            requests.Session,
            "post",
            return_value=mock_response
        )
        monkeypatch.setattr(
            requests.Session,
            "get",
            return_value=mock_response
        )

        return mock_response

    return _mock


# Configuration for pytest
def pytest_configure(config):
    """Configure pytest."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "security: mark test as testing security features"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
