"""CLI command definitions"""

from pathlib import Path

import typer

from .main import app
from .config import ConfigManager
from .ssh import SSHManager
from .sync import SyncManager


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
    pass


@app.command()
def status(run_id: str = None):
    """Check job status"""
    pass
