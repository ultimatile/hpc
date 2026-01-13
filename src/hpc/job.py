"""Slurm job management"""

from enum import Enum

from jinja2 import Template

from .config import HpcConfig
from .ssh import SSHManager
from .run import RunConfig


def _resolve_home_path(ssh_manager, path: str) -> str:
    """Resolve ~ to actual home directory path via SSH"""
    if path.startswith("~/") or path == "~":
        # Get the actual home directory from remote system
        result = ssh_manager.run_command("printenv", ["HOME"])
        home_dir = result.stdout.strip()
        if path == "~":
            return home_dir
        else:
            return path.replace("~", home_dir, 1)
    return path


class JobStatus(Enum):
    """Slurm job status"""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"


SLURM_TEMPLATE = """#!/bin/bash
{% for key, value in slurm_options.items() %}
#SBATCH --{{ key.replace('_', '-') }}={{ value }}
{% endfor %}
#SBATCH --output={{ workdir }}/.hpc/runs/{{ run_id }}/slurm-%j.out
#SBATCH --error={{ workdir }}/.hpc/runs/{{ run_id }}/slurm-%j.err

cd {{ workdir }}

{% for module in modules %}
module load {{ module }}
{% endfor %}
{% if conda_env %}
conda activate {{ conda_env }}
{% endif %}

{{ cmd }}
"""


class JobManager:
    """Slurm job submission and monitoring"""

    def __init__(self, ssh_manager: SSHManager, config: HpcConfig):
        self.ssh_manager = ssh_manager
        self.config = config

    def _render_slurm_script(self, run: RunConfig) -> str:
        """Render Slurm job script from template"""
        template = Template(SLURM_TEMPLATE)

        # Add job-name if not specified
        slurm_options = self.config.slurm.options.copy()
        if "job_name" not in slurm_options and "job-name" not in slurm_options:
            slurm_options["job_name"] = run.run_id

        workdir = _resolve_home_path(self.ssh_manager, self.config.cluster.workdir)
        return template.render(
            run_id=run.run_id,
            slurm_options=slurm_options,
            workdir=workdir,
            modules=self.config.env.modules,
            conda_env=self.config.env.conda_env,
            cmd=run.cmd,
        )

    def submit_run(self, run: RunConfig) -> str:
        """Submit run to Slurm and return job ID"""
        script = self._render_slurm_script(run)

        # Create run directory on remote
        workdir = _resolve_home_path(self.ssh_manager, self.config.cluster.workdir)
        run_dir = f"{workdir}/.hpc/runs/{run.run_id}"
        self.ssh_manager.run_command("mkdir", ["-p", run_dir])

        # Write script to remote
        script_path = f"{run_dir}/job.sh"
        self.ssh_manager.run_command("tee", [script_path], input_text=script)

        # Submit with sbatch --parsable
        result = self.ssh_manager.run_command("sbatch", ["--parsable", script_path])
        return result.stdout.strip()

    def submit_job(self, cmd: str) -> str:
        """Legacy: Submit job without run tracking"""
        template = Template(SLURM_TEMPLATE)

        # Add job-name if not specified
        slurm_options = self.config.slurm.options.copy()
        if "job_name" not in slurm_options and "job-name" not in slurm_options:
            slurm_options["job_name"] = "job"

        script = template.render(
            run_id="job",
            slurm_options=slurm_options,
            workdir=_resolve_home_path(self.ssh_manager, self.config.cluster.workdir),
            modules=self.config.env.modules,
            conda_env=self.config.env.conda_env,
            cmd=cmd,
        )
        result = self.ssh_manager.run_command(
            "sbatch", ["--parsable"], input_text=script
        )
        return result.stdout.strip()

    def get_job_status(self, job_id: str) -> JobStatus:
        """Get job status using sacct"""
        result = self.ssh_manager.run_command(
            "sacct", ["-j", job_id, "--format=State", "--noheader"]
        )
        lines = result.stdout.strip().splitlines() if result.stdout else []
        status_str = lines[0].strip().rstrip("+") if lines else ""

        status_map = {
            "PENDING": JobStatus.PENDING,
            "RUNNING": JobStatus.RUNNING,
            "COMPLETED": JobStatus.COMPLETED,
            "FAILED": JobStatus.FAILED,
            "CANCELLED": JobStatus.CANCELLED,
            "TIMEOUT": JobStatus.TIMEOUT,
        }
        return status_map.get(status_str, JobStatus.FAILED)

    def get_job_output(self, run_id: str, job_id: str, error: bool = False) -> str:
        """Get job output file contents"""
        workdir = _resolve_home_path(self.ssh_manager, self.config.cluster.workdir)
        ext = "err" if error else "out"
        output_path = f"{workdir}/.hpc/runs/{run_id}/slurm-{job_id}.{ext}"

        result = self.ssh_manager.run_command("cat", [output_path])
        return result.stdout

    def wait_for_job(
        self,
        job_id: str,
        interval: float = 60,
        adaptive: bool = False,
        max_interval: float = 86400,
        growth_factor: float = 2.0,
    ) -> JobStatus:
        """Wait for job to complete, polling at interval

        Args:
            job_id: Slurm job ID
            interval: Initial polling interval in seconds
            adaptive: If True, increase interval geometrically
            max_interval: Maximum polling interval (default 1 hour)
            growth_factor: Multiplier for adaptive interval (default 2x)
        """
        import time

        current_interval = interval
        terminal_states = {
            JobStatus.COMPLETED,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
            JobStatus.TIMEOUT,
        }

        while True:
            status = self.get_job_status(job_id)
            if status in terminal_states:
                return status

            time.sleep(current_interval)

            if adaptive:
                current_interval = min(current_interval * growth_factor, max_interval)
