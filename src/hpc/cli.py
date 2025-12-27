"""CLI command definitions"""

from pathlib import Path

from .main import app
from .config import ConfigManager


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
    pass


@app.command()
def submit(cmd: str):
    """Submit a job to Slurm"""
    pass


@app.command()
def status(run_id: str = None):
    """Check job status"""
    pass
