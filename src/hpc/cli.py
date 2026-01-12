"""CLI command definitions"""

import os
import shutil
from pathlib import Path
from typing import Optional

import typer
from typing_extensions import Annotated

from .main import app
from .config import ConfigManager
from .ssh import SSHManager
from .sync import SyncManager
from .job import JobManager
from .run import RunManager

# Global config path
_config_path: Path = Path("hpc.toml")


def get_config_path() -> Path:
    return _config_path


@app.callback()
def main(
    config: Annotated[
        Optional[Path], typer.Option("--config", "-c", help="Config file path")
    ] = None,
):
    """HPC workflow automation tool"""
    global _config_path
    if config:
        _config_path = config
    elif env_config := os.environ.get("HPC_CONFIG"):
        _config_path = Path(env_config)


def _get_user_config_path() -> Path:
    """Get user config path from XDG_CONFIG_HOME/hpc/config.toml"""
    xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    return Path(xdg_config) / "hpc" / "config.toml"


@app.command()
def init():
    """Initialize HPC project configuration"""
    config_path = get_config_path()
    if config_path.exists():
        print(f"Config file already exists: {config_path}")
        return

    user_config = _get_user_config_path()
    if user_config.exists():
        shutil.copy(user_config, config_path)
        print(f"Copied from {user_config}: {config_path}")
    else:
        manager = ConfigManager()
        manager.generate_template(config_path)
        print(f"Created config file: {config_path}")


@app.command()
def sync(
    apply: bool = False,
    push: bool = typer.Option(False, "--push", help="Only push local to remote"),
    pull: bool = typer.Option(False, "--pull", help="Only pull remote to local"),
):
    """Sync files bidirectionally with remote HPC cluster (push then pull)"""
    config_path = get_config_path()
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        print("Run 'hpc init' first to create a config file.")
        raise typer.Exit(1)

    if push and pull:
        print("Error: cannot use --push and --pull together")
        raise typer.Exit(1)

    manager = ConfigManager()
    config = manager.load_config(config_path)

    ssh = SSHManager(host=config.cluster.host)
    sync_manager = SyncManager(ssh_manager=ssh, config=config)

    dry_run = not apply
    local_path = Path.cwd()

    # Default: bidirectional (push then pull)
    do_push = not pull
    do_pull = not push

    if do_push:
        print("==> Push (local → remote)")
        sync_manager.sync_push(local_path=local_path, dry_run=dry_run)
    if do_pull:
        print("==> Pull (remote → local)")
        sync_manager.sync_pull(local_path=local_path, dry_run=dry_run)

    if dry_run:
        print("Dry run completed. Use --apply to sync files.")
    else:
        print("Sync completed.")


@app.command()
def submit(
    cmd: str = typer.Argument(None),
    script: Path = typer.Option(
        None, "--script", "-s", help="Shell script file to submit"
    ),
    wait: bool = typer.Option(False, "--wait", "-w", help="Wait for job completion"),
):
    """Submit a job to Slurm"""
    config_path = get_config_path()
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        raise typer.Exit(1)

    if not cmd and not script:
        print("Error: provide a command or --script")
        raise typer.Exit(1)

    if script:
        if not script.exists():
            print(f"Script not found: {script}")
            raise typer.Exit(1)
        cmd = script.read_text()

    manager = ConfigManager()
    config = manager.load_config(config_path)

    # Get git commit if in a git repo
    ssh = SSHManager(host=config.cluster.host)
    sync_manager = SyncManager(ssh_manager=ssh, config=config)
    git_commit = sync_manager.get_git_commit(Path.cwd(), short=True)

    if sync_manager.has_uncommitted_changes(Path.cwd()):
        print("Warning: uncommitted changes detected")

    runs_dir = Path(".hpc/runs")
    run_manager = RunManager(config=config, runs_dir=runs_dir)
    run = run_manager.create_run(cmd, git_commit=git_commit)

    job_manager = JobManager(ssh_manager=ssh, config=config)

    job_id = job_manager.submit_run(run)
    run.job_id = job_id
    run.status = "submitted"
    run_manager.save_run_meta(run)

    print(f"Submitted run: {run.run_id}")
    print(f"Job ID: {job_id}")
    if git_commit:
        print(f"Git commit: {git_commit}")

    if wait:
        print("Waiting for job completion...")
        status = job_manager.wait_for_job(job_id, adaptive=True)
        run.status = status.value.lower()
        run_manager.save_run_meta(run)
        print(f"Job finished: {status.value}")


@app.command()
def status(id: str = typer.Argument(None)):
    """Check job status (accepts run_id or job_id)"""
    config_path = get_config_path()
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        raise typer.Exit(1)

    if not id:
        print("Please specify a run_id or job_id")
        raise typer.Exit(1)

    manager = ConfigManager()
    config = manager.load_config(config_path)

    runs_dir = Path(".hpc/runs")
    run_manager = RunManager(config=config, runs_dir=runs_dir)

    # Try as run_id first, then as job_id
    try:
        run = run_manager.load_run_meta(id)
        job_id = run.job_id
    except FileNotFoundError:
        run = run_manager.find_run_by_job_id(id)
        job_id = id

    if run and not job_id:
        print(f"Run {run.run_id} has no job ID")
        raise typer.Exit(1)

    if not job_id:
        print(f"Run not found: {id}")
        raise typer.Exit(1)

    ssh = SSHManager(host=config.cluster.host)
    job_manager = JobManager(ssh_manager=ssh, config=config)

    job_status = job_manager.get_job_status(job_id)
    print(f"Job {job_id}: {job_status.value}")


@app.command(name="list")
def list_runs():
    """List all runs"""
    config_path = get_config_path()
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        raise typer.Exit(1)

    manager = ConfigManager()
    config = manager.load_config(config_path)

    runs_dir = Path(".hpc/runs")
    run_manager = RunManager(config=config, runs_dir=runs_dir)
    runs = run_manager.list_runs()

    if not runs:
        print("No runs found.")
        return

    for run in runs:
        job_info = f" (job: {run.job_id})" if run.job_id else ""
        print(f"{run.run_id}: {run.status}{job_info} - {run.cmd}")


@app.command(name="job-output")
def job_output(id: str):
    """Show Slurm job output (accepts run_id or job_id)"""
    config_path = get_config_path()
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        raise typer.Exit(1)

    manager = ConfigManager()
    config = manager.load_config(config_path)

    runs_dir = Path(".hpc/runs")
    run_manager = RunManager(config=config, runs_dir=runs_dir)

    # Try as run_id first, then as job_id
    try:
        run = run_manager.load_run_meta(id)
    except FileNotFoundError:
        run = run_manager.find_run_by_job_id(id)

    if not run:
        print(f"Run not found: {id}")
        raise typer.Exit(1)

    if not run.job_id:
        print(f"Run {run.run_id} has no job ID")
        raise typer.Exit(1)

    ssh = SSHManager(host=config.cluster.host)
    job_manager = JobManager(ssh_manager=ssh, config=config)

    output = job_manager.get_job_output(run.run_id, run.job_id)
    print(output, end="")


@app.command()
def wait(id: str):
    """Wait for a run to complete (accepts run_id or job_id)"""
    config_path = get_config_path()
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        raise typer.Exit(1)

    manager = ConfigManager()
    config = manager.load_config(config_path)

    runs_dir = Path(".hpc/runs")
    run_manager = RunManager(config=config, runs_dir=runs_dir)

    # Try as run_id first, then as job_id
    try:
        run = run_manager.load_run_meta(id)
    except FileNotFoundError:
        run = run_manager.find_run_by_job_id(id)

    if not run:
        print(f"Run not found: {id}")
        raise typer.Exit(1)

    if not run.job_id:
        print(f"Run {run.run_id} has no job ID")
        raise typer.Exit(1)

    ssh = SSHManager(host=config.cluster.host)
    job_manager = JobManager(ssh_manager=ssh, config=config)

    print(f"Waiting for job {run.job_id}...")
    status = job_manager.wait_for_job(run.job_id, adaptive=True)
    run.status = status.value.lower()
    run_manager.save_run_meta(run)
    print(f"Job finished: {status.value}")
