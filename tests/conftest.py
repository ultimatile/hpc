"""Pytest configuration and fixtures for hpc tests"""

import tempfile
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner():
    """Typer CLI runner for testing commands"""
    return CliRunner()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture(autouse=True)
def reset_config_path():
    """Reset global config path before each test"""
    from hpc import cli

    cli._config_path = Path("hpc.toml")
    yield
    cli._config_path = Path("hpc.toml")
