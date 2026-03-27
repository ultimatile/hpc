"""Job manager tests"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from hpc.job import JobManager, JobStatus
from hpc.ssh import SSHManager
from hpc.config import HpcConfig, ClusterConfig, EnvConfig, SlurmConfig, PjmConfig


@pytest.fixture
def mock_ssh_manager():
    return MagicMock(spec=SSHManager)


@pytest.fixture
def sample_config():
    return HpcConfig(
        cluster=ClusterConfig(host="myhpc", workdir="/scratch/user/proj"),
        env=EnvConfig(modules=["gcc/12.2.0"]),
        slurm=SlurmConfig(
            options={"partition": "gpu", "time": "02:00:00", "mem": "32G", "gpus": 1}
        ),
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
        call_args = mock_ssh_manager.run_command.call_args
        assert call_args.args[0] == "sbatch"
        assert "--parsable" in call_args.args[1]

    def test_submit_job_includes_pjm_submit_options(self, mock_ssh_manager):
        config = HpcConfig(
            cluster=ClusterConfig(
                host="myhpc", workdir="/scratch/user/proj", scheduler="pjm"
            ),
            env=EnvConfig(),
            pjm=PjmConfig(
                options=[["-L", "node=12"]],
                submit_options=["--no-check-directory"],
            ),
        )
        manager = JobManager(ssh_manager=mock_ssh_manager, config=config)
        mock_ssh_manager.run_command.return_value = MagicMock(
            stdout="[INFO] PJM 0000 pjsub Job 12345678 submitted.\n"
        )

        manager.submit_job("python train.py")
        call_args = mock_ssh_manager.run_command.call_args
        assert call_args.args[0] == "pjsub"
        assert "--no-check-directory" in call_args.args[1]

    def test_submit_job_includes_slurm_submit_options(self, mock_ssh_manager):
        config = HpcConfig(
            cluster=ClusterConfig(host="myhpc", workdir="/scratch/user/proj"),
            env=EnvConfig(),
            slurm=SlurmConfig(
                options={"partition": "gpu"},
                submit_options=["--export=ALL"],
            ),
        )
        manager = JobManager(ssh_manager=mock_ssh_manager, config=config)
        mock_ssh_manager.run_command.return_value = MagicMock(stdout="12345678\n")

        manager.submit_job("python train.py")
        call_args = mock_ssh_manager.run_command.call_args
        assert call_args.args[0] == "sbatch"
        assert "--parsable" in call_args.args[1]
        assert "--export=ALL" in call_args.args[1]

    def test_submit_run_includes_pjm_submit_options(self, mock_ssh_manager):
        config = HpcConfig(
            cluster=ClusterConfig(
                host="myhpc", workdir="/scratch/user/proj", scheduler="pjm"
            ),
            env=EnvConfig(),
            pjm=PjmConfig(
                options=[["-L", "node=12"]],
                submit_options=["--no-check-directory"],
            ),
        )
        manager = JobManager(ssh_manager=mock_ssh_manager, config=config)
        mock_ssh_manager.run_command.return_value = MagicMock(
            stdout="[INFO] PJM 0000 pjsub Job 12345678 submitted.\n"
        )
        from hpc.run import RunConfig

        run = RunConfig(run_id="test_run", cmd="python train.py", status="pending")
        manager.submit_run(run)

        # Last run_command call is the submit
        call_args = mock_ssh_manager.run_command.call_args
        assert call_args.args[0] == "pjsub"
        assert "--no-check-directory" in call_args.args[1]

    def test_submit_run_includes_slurm_submit_options(self, mock_ssh_manager):
        config = HpcConfig(
            cluster=ClusterConfig(host="myhpc", workdir="/scratch/user/proj"),
            env=EnvConfig(),
            slurm=SlurmConfig(
                options={"partition": "gpu"},
                submit_options=["--export=ALL"],
            ),
        )
        manager = JobManager(ssh_manager=mock_ssh_manager, config=config)
        mock_ssh_manager.run_command.return_value = MagicMock(stdout="12345678\n")
        from hpc.run import RunConfig

        run = RunConfig(run_id="test_run", cmd="python train.py", status="pending")
        manager.submit_run(run)

        call_args = mock_ssh_manager.run_command.call_args
        assert call_args.args[0] == "sbatch"
        assert "--parsable" in call_args.args[1]
        assert "--export=ALL" in call_args.args[1]


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
        call_args = mock_ssh_manager.run_command.call_args
        assert call_args.args[0] == "sacct"
        assert "12345678" in call_args.args[1]
        assert "--noheader" in call_args.args[1]


class TestJobManagerTemplate:
    def test_render_job_script(self, mock_ssh_manager, sample_config):
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        from hpc.run import RunConfig

        run = RunConfig(run_id="test_run", cmd="python train.py", status="pending")
        script = manager._render_job_script(run)

        assert "#!/bin/bash" in script
        assert "#SBATCH --partition=gpu" in script
        assert "#SBATCH --time=02:00:00" in script
        assert "#SBATCH --mem=32G" in script
        assert "#SBATCH --job-name=test_run" in script
        assert "python train.py" in script

    def test_render_job_script_default_cwd(self, mock_ssh_manager, sample_config):
        """Default cwd_relative=Path('.') uses workdir as job working directory"""
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        from hpc.run import RunConfig

        run = RunConfig(run_id="test_run", cmd="echo hi", status="pending")
        script = manager._render_job_script(run)
        assert "cd /scratch/user/proj" in script

    def test_render_job_script_with_subdirectory(self, mock_ssh_manager, sample_config):
        """cwd_relative appends subdirectory to workdir for job cd"""
        manager = JobManager(ssh_manager=mock_ssh_manager, config=sample_config)
        from hpc.run import RunConfig

        run = RunConfig(run_id="test_run", cmd="echo hi", status="pending")
        script = manager._render_job_script(run, cwd_relative=Path("runs/bench1"))
        assert "cd /scratch/user/proj/runs/bench1" in script
        # Output paths still use base workdir
        assert "--output=/scratch/user/proj/.hpc/runs/test_run" in script
