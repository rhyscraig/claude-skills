"""Pytest configuration and fixtures."""

import os
import sys
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir(tmp_path):
    """Create temporary directory for tests."""
    return tmp_path


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment."""
    os.environ["CLOUDCTL_DRY_RUN"] = "false"
    os.environ["CLOUDCTL_TIMEOUT"] = "5"
    os.environ["CLOUDCTL_AUDIT"] = "false"
    yield


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: unit tests")
    config.addinivalue_line("markers", "integration: integration tests (requires cloudctl)")
    config.addinivalue_line("markers", "security: security-related tests")
    config.addinivalue_line("markers", "slow: slow tests")
