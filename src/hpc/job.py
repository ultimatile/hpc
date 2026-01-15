"""Job management for HPC schedulers"""

from jinja2 import Template

from .config import HpcConfig
from .ssh import SSHManager
from .run import RunConfig
from .scheduler import JobStatus, get_scheduler


def _resolve_home_path(ssh_manager, path: str) -> str:
    """Resolve ~ to actual home directory path via SSH"""
    if path.startswith("~/") or path == "~":
        result = ssh_manager.run_command("printenv", ["HOME"])
        home_dir = result.stdout.strip()
        if path == "~":
            return home_dir
        else:
            return path.replace("~", home_dir, 1)
    return path


JOB_TEMPLATE = """#!/bin/bash
{% for directive in directives %}
{{ directive }}
{% endfor %}
{{ scheduler.directive_prefix().split()[0] }} --output={{ workdir }}/.hpc/runs/{{ run_id }}/job-%j.out
{{ scheduler.directive_prefix().split()[0] }} --error={{ workdir }}/.hpc/runs/{{ run_id }}/job-%j.err

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
    """Job submission and monitoring"""

    def __init__(self, ssh_manager: SSHManager, config: HpcConfig):
        self.ssh_manager = ssh_manager
        self.config = config
        self.scheduler = get_scheduler(config.cluster.scheduler)

    def _build_directives(self, options: dict, job_name: str | None = None) -> list[str]:
        """Build scheduler directives from options"""
        prefix = self.scheduler.directive_prefix()
        directives = []
        opts = options.copy()
        if job_name and "job_name" not in opts and "job-name" not in opts:
            opts["job_name"] = job_name
        for key, value in opts.items():
            directives.append(f"{prefix} --{key.replace('_', '-')}={value}")
        return directives

    def _render_job_script(self, run: RunConfig) -> str:
        """Render job script from template"""
        template = Template(JOB_TEMPLATE)
        workdir = _resolve_home_path(self.ssh_manager, self.config.cluster.workdir)
        directives = self._build_directives(self.config.slurm.options, run.run_id)
        return template.render(
            run_id=run.run_id,
            directives=directives,
            scheduler=self.scheduler,
            workdir=workdir,
            modules=self.config.env.modules,
            conda_env=self.config.env.conda_env,
            cmd=run.cmd,
        )

    def submit_run(self, run: RunConfig) -> str:
        """Submit run and return job ID"""
        script = self._render_job_script(run)

        workdir = _resolve_home_path(self.ssh_manager, self.config.cluster.workdir)
        run_dir = f"{workdir}/.hpc/runs/{run.run_id}"
        self.ssh_manager.run_command("mkdir", ["-p", run_dir])

        script_path = f"{run_dir}/job.sh"
        self.ssh_manager.run_command("tee", [script_path], input_text=script)

        cmd = self.scheduler.submit_cmd()
        result = self.ssh_manager.run_command(cmd[0], cmd[1:] + [script_path])
        return self.scheduler.parse_job_id(result.stdout)

    def submit_job(self, cmd: str) -> str:
        """Legacy: Submit job without run tracking"""
        template = Template(JOB_TEMPLATE)
        workdir = _resolve_home_path(self.ssh_manager, self.config.cluster.workdir)
        directives = self._build_directives(self.config.slurm.options, "job")

        script = template.render(
            run_id="job",
            directives=directives,
            scheduler=self.scheduler,
            workdir=workdir,
            modules=self.config.env.modules,
            conda_env=self.config.env.conda_env,
            cmd=cmd,
        )
        submit_cmd = self.scheduler.submit_cmd()
        result = self.ssh_manager.run_command(submit_cmd[0], submit_cmd[1:], input_text=script)
        return self.scheduler.parse_job_id(result.stdout)

    def get_job_status(self, job_id: str) -> JobStatus:
        """Get job status"""
        cmd = self.scheduler.status_cmd(job_id)
        result = self.ssh_manager.run_command(cmd[0], cmd[1:])
        return self.scheduler.parse_status(result.stdout)

    def get_job_output(self, run_id: str, job_id: str, error: bool = False) -> str:
        """Get job output file contents"""
        from .ssh import SSHError

        workdir = _resolve_home_path(self.ssh_manager, self.config.cluster.workdir)
        ext = "err" if error else "out"
        output_path = f"{workdir}/.hpc/runs/{run_id}/job-{job_id}.{ext}"

        try:
            result = self.ssh_manager.run_command("cat", [output_path])
            return result.stdout
        except SSHError:
            status = self.get_job_status(job_id)
            if status in (JobStatus.PENDING, JobStatus.RUNNING):
                return f"Job {job_id} is {status.value}. Output file not yet available.\n"
            raise

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
