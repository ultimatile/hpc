"""Sync manager tests"""

from unittest.mock import patch, MagicMock
from pathlib import Path

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


class TestSyncResult:
    def test_sync_result_fields(self):
        result = SyncResult(success=True, files_synced=5, dry_run=False)
        assert result.success is True
        assert result.files_synced == 5
        assert result.dry_run is False


class TestSyncManagerInit:
    def test_init_with_ssh_and_config(self, mock_ssh_manager, sample_config):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        assert manager.ssh_manager == mock_ssh_manager
        assert manager.config == sample_config


class TestSyncManagerSyncInputs:
    def test_sync_inputs_dry_run(self, mock_ssh_manager, sample_config, temp_dir):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = manager.sync_inputs(local_path=temp_dir, dry_run=True)
            assert result.dry_run is True
            call_args = mock_run.call_args[0][0]
            assert "--dry-run" in call_args

    def test_sync_inputs_apply(self, mock_ssh_manager, sample_config, temp_dir):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            result = manager.sync_inputs(local_path=temp_dir, dry_run=False)
            assert result.dry_run is False
            call_args = mock_run.call_args[0][0]
            assert "--dry-run" not in call_args

    def test_sync_inputs_uses_rsync(self, mock_ssh_manager, sample_config, temp_dir):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            manager.sync_inputs(local_path=temp_dir, dry_run=True)
            call_args = mock_run.call_args[0][0]
            assert call_args[0] == "rsync"

    def test_sync_inputs_target_path(self, mock_ssh_manager, sample_config, temp_dir):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            manager.sync_inputs(local_path=temp_dir, dry_run=True)
            call_args = mock_run.call_args[0][0]
            args_str = " ".join(call_args)
            assert "myhpc:/scratch/user/proj" in args_str

    def test_sync_inputs_excludes_patterns(self, mock_ssh_manager, sample_config, temp_dir):
        manager = SyncManager(ssh_manager=mock_ssh_manager, config=sample_config)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            manager.sync_inputs(local_path=temp_dir, dry_run=True)
            call_args = mock_run.call_args[0][0]
            assert "--exclude" in call_args
