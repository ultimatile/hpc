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
def reset_env_config(monkeypatch):
    """Clear HPC_CONFIG env var before each test"""
    monkeypatch.delenv("HPC_CONFIG", raising=False)
