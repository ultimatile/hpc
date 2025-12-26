"""CLI command definitions"""

from .main import app


@app.command()
def init():
    """Initialize HPC project configuration"""
    pass


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
