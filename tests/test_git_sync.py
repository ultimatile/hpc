"""Git sync tests"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from hpc.sync import SyncManager, SyncResult
from hpc.ssh import SSHManager
from hpc.config import HpcConfig, ClusterConfig, EnvConfig, SlurmConfig


@pytest.fixture
def mock_ssh_manager():
    return MagicMock(spec=SSHManager)


@pytest.fixture
def sample_config():
    return HpcConfig(
        cluster=ClusterConfig(host="myhpc", workdir="/scratch/user/proj"),
        env=EnvConfig(),
        slurm=SlurmConfig(partition="gpu", time="02:00:00", mem="32G"),
    )


@pytest.fixture
def git_repo(temp_dir):
    """Create a temporary git repository"""
    import os
    env = os.environ.copy()
    env["GIT_DIR"] = str(temp_dir / ".git")
    env["GIT_WORK_TREE"] = str(temp_dir)
    env["GIT_AUTHOR_NAME"] = "Test"
    env["GIT_AUTHOR_EMAIL"] = "test@test.com"
    env["GIT_COMMITTER_NAME"] = "Test"
    env["GIT_COMMITTER_EMAIL"] = "test@test.com"

    subprocess.run(["git", "init"], env=env, capture_output=True)
    (temp_dir / "test.py").write_text("print('hello')")
    subprocess.run(["git", "add", "."], env=env, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        env=env,
        capture_output=True,
    )
    return temp_dir


class TestGitStatus:
    def test_get_git_commit(self, mock_ssh_manager, sample_config, git_repo):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        commit = manager.get_git_commit(git_repo)
        assert commit is not None
        assert len(commit) == 40  # full SHA

    def test_get_git_commit_short(self, mock_ssh_manager, sample_config, git_repo):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        commit = manager.get_git_commit(git_repo, short=True)
        assert commit is not None
        assert len(commit) == 7

    def test_has_uncommitted_changes_clean(self, mock_ssh_manager, sample_config, git_repo):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        assert manager.has_uncommitted_changes(git_repo) is False

    def test_has_uncommitted_changes_dirty(self, mock_ssh_manager, sample_config, git_repo):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        (git_repo / "test.py").write_text("print('modified')")
        assert manager.has_uncommitted_changes(git_repo) is True

    def test_not_git_repo(self, mock_ssh_manager, sample_config):
        import tempfile
        with tempfile.TemporaryDirectory(dir="/tmp") as tmpdir:
            manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
            commit = manager.get_git_commit(Path(tmpdir))
            assert commit is None
