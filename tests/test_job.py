"""Job manager tests"""

from unittest.mock import patch, MagicMock
from pathlib import Path

import pytest

from hpc.job import JobManager, JobStatus
from hpc.ssh import SSHManager
from hpc.config import HpcConfig, ClusterConfig, EnvConfig, SlurmConfig


@pytest.fixture
def mock_ssh_manager():
    return MagicMock(spec=SSHManager)


@pytest.fixture
def sample_config():
    return HpcConfig(
        cluster=ClusterConfig(host="myhpc", workdir="/scratch/user/proj"),
        env=EnvConfig(modules=["gcc/12.2.0"]),
        slurm=SlurmConfig(options={"partition": "gpu", "time": "02:00:00", "mem": "32G", "gpus": 1}),
    )


class TestJobStatus:
    def test_job_status_values(self):
        assert JobStatus.PENDING.value == "PENDING"
        assert JobStatus.RUNNING.value == "RUNNING"
        assert JobStatus.COMPLETED.value == "COMPLETED"
        assert JobStatus.FAILED.value == "FAILED"


class TestJobManagerInit:
    def test_init_with_ssh_and_config(self, mock_ssh_manager, sample_config):
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        assert manager.ssh_manager == mock_ssh_manager
        assert manager.config == sample_config


class TestJobManagerSubmit:
    def test_submit_job_returns_job_id(self, mock_ssh_manager, sample_config):
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        mock_ssh_manager.run_command.return_value = MagicMock(stdout="12345678\n")

        job_id = manager.submit_job("python train.py")
        assert job_id == "12345678"

    def test_submit_job_uses_sbatch_parsable(self, mock_ssh_manager, sample_config):
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        mock_ssh_manager.run_command.return_value = MagicMock(stdout="12345678\n")

        manager.submit_job("python train.py")
        call_args = mock_ssh_manager.run_command.call_args[0][0]
        assert "sbatch" in call_args
        assert "--parsable" in call_args


class TestJobManagerStatus:
    def test_get_job_status_completed(self, mock_ssh_manager, sample_config):
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        mock_ssh_manager.run_command.return_value = MagicMock(stdout="COMPLETED\n")

        status = manager.get_job_status("12345678")
        assert status == JobStatus.COMPLETED

    def test_get_job_status_running(self, mock_ssh_manager, sample_config):
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        mock_ssh_manager.run_command.return_value = MagicMock(stdout="RUNNING\n")

        status = manager.get_job_status("12345678")
        assert status == JobStatus.RUNNING

    def test_get_job_status_uses_sacct(self, mock_ssh_manager, sample_config):
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        mock_ssh_manager.run_command.return_value = MagicMock(stdout="COMPLETED\n")

        manager.get_job_status("12345678")
        call_args = mock_ssh_manager.run_command.call_args[0][0]
        assert "sacct" in call_args
        assert "12345678" in call_args
        assert "--noheader" in call_args


class TestJobManagerTemplate:
    def test_render_slurm_script(self, mock_ssh_manager, sample_config):
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        from hpc.run import RunConfig
        run = RunConfig(run_id="test_run", cmd="python train.py", status="pending")
        script = manager._render_slurm_script(run)

        assert "#!/bin/bash" in script
        assert "#SBATCH --partition=gpu" in script
        assert "#SBATCH --time=02:00:00" in script
        assert "#SBATCH --mem=32G" in script
        assert "#SBATCH --job-name=test_run" in script
        assert "python train.py" in script
