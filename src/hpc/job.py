"""Slurm job management"""

from enum import Enum

from jinja2 import Template

from .config import HpcConfig
from .ssh import SSHManager


class JobStatus(Enum):
    """Slurm job status"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --partition={{ partition }}
#SBATCH --time={{ time }}
#SBATCH --mem={{ mem }}
{% if gpus %}#SBATCH --gpus={{ gpus }}
{% endif %}
{{ cmd }}
"""


class JobManager:
    """Slurm job submission and monitoring"""

    def __init__(self, ssh_manager: SSHManager, config: HpcConfig):
        self.ssh_manager = ssh_manager
        self.config = config

    def _render_slurm_script(self, cmd: str) -> str:
        """Render Slurm job script from template"""
        template = Template(SLURM_TEMPLATE)
        return template.render(
            partition=self.config.slurm.partition,
            time=self.config.slurm.time,
            mem=self.config.slurm.mem,
            gpus=self.config.slurm.gpus,
            cmd=cmd,
        )

    def submit_job(self, cmd: str) -> str:
        """Submit job to Slurm and return job ID"""
        script = self._render_slurm_script(cmd)
        # Write script and submit with sbatch --parsable
        submit_cmd = f"echo '{script}' | sbatch --parsable"
        result = self.ssh_manager.run_command(submit_cmd)
        return result.stdout.strip()

    def get_job_status(self, job_id: str) -> JobStatus:
        """Get job status using sacct"""
        cmd = f"sacct -j {job_id} --format=State --noheader | head -1"
        result = self.ssh_manager.run_command(cmd)
        status_str = result.stdout.strip()

        status_map = {
            "PENDING": JobStatus.PENDING,
            "RUNNING": JobStatus.RUNNING,
            "COMPLETED": JobStatus.COMPLETED,
            "FAILED": JobStatus.FAILED,
            "CANCELLED": JobStatus.CANCELLED,
            "TIMEOUT": JobStatus.TIMEOUT,
        }
        return status_map.get(status_str, JobStatus.FAILED)
