"""CLI command definitions"""

from pathlib import Path

import typer

from .main import app
from .config import ConfigManager
from .ssh import SSHManager
from .sync import SyncManager
from .job import JobManager
from .run import RunManager


@app.command()
def init():
    """Initialize HPC project configuration"""
    config_path = Path("hpc.toml")
    if config_path.exists():
        print(f"Config file already exists: {config_path}")
        return
    manager = ConfigManager()
    manager.generate_template(config_path)
    print(f"Created config file: {config_path}")


@app.command()
def sync(apply: bool = False):
    """Sync files to remote HPC cluster"""
    config_path = Path("hpc.toml")
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        print("Run 'hpc init' first to create a config file.")
        raise typer.Exit(1)

    manager = ConfigManager()
    config = manager.load_config(config_path)

    ssh = SSHManager(host=config.cluster.host)
    sync_manager = SyncManager(ssh_manager=ssh, config=config)

    dry_run = not apply
    result = sync_manager.sync_inputs(local_path=Path.cwd(), dry_run=dry_run)

    if dry_run:
        print("Dry run completed. Use --apply to sync files.")
    else:
        print(f"Sync completed: {result.files_synced} files synced.")


@app.command()
def submit(cmd: str):
    """Submit a job to Slurm"""
    config_path = Path("hpc.toml")
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        raise typer.Exit(1)

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


@app.command()
def status(job_id: str = typer.Argument(None)):
    """Check job status"""
    config_path = Path("hpc.toml")
    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        raise typer.Exit(1)

    if not job_id:
        print("Please specify a job ID")
        raise typer.Exit(1)

    manager = ConfigManager()
    config = manager.load_config(config_path)

    ssh = SSHManager(host=config.cluster.host)
    job_manager = JobManager(ssh_manager=ssh, config=config)

    job_status = job_manager.get_job_status(job_id)
    print(f"Job {job_id}: {job_status.value}")


@app.command()
def list():
    """List all runs"""
    config_path = Path("hpc.toml")
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
