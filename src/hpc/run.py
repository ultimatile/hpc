"""Run management - tracking job executions"""

import hashlib
import tomllib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import tomli_w

from .config import HpcConfig


@dataclass
class RunConfig:
    """Configuration and metadata for a single run"""

    run_id: str
    cmd: str
    status: str
    job_id: Optional[str] = None
    git_commit: Optional[str] = None
    created_at: Optional[str] = None
    slurm_time: Optional[str] = None
    slurm_mem: Optional[str] = None
    slurm_partition: Optional[str] = None


class RunManager:
    """Manages run lifecycle and metadata"""

    def __init__(self, config: HpcConfig, runs_dir: Path):
        self.config = config
        self.runs_dir = runs_dir
        self.runs_dir.mkdir(parents=True, exist_ok=True)

    def _generate_run_id(self) -> str:
        """Generate unique run ID: YYYY-MM-DD_HHMMSS_<hash>"""
        import uuid
        now = datetime.now()
        timestamp = now.strftime("%Y-%m-%d_%H%M%S")
        short_hash = uuid.uuid4().hex[:6]
        return f"{timestamp}_{short_hash}"

    def create_run(self, cmd: str) -> RunConfig:
        """Create a new run with generated ID"""
        run_id = self._generate_run_id()
        run_dir = self.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        return RunConfig(
            run_id=run_id,
            cmd=cmd,
            status="pending",
            created_at=datetime.now().isoformat(),
            slurm_time=self.config.slurm.time,
            slurm_mem=self.config.slurm.mem,
            slurm_partition=self.config.slurm.partition,
        )

    def save_run_meta(self, run: RunConfig) -> None:
        """Save run metadata to TOML file"""
        run_dir = self.runs_dir / run.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        meta_path = run_dir / "meta.toml"

        data = {k: v for k, v in asdict(run).items() if v is not None}
        with open(meta_path, "wb") as f:
            tomli_w.dump(data, f)

    def load_run_meta(self, run_id: str) -> RunConfig:
        """Load run metadata from TOML file"""
        meta_path = self.runs_dir / run_id / "meta.toml"
        with open(meta_path, "rb") as f:
            data = tomllib.load(f)
        return RunConfig(**data)

    def list_runs(self) -> list[RunConfig]:
        """List all runs"""
        runs = []
        for run_dir in self.runs_dir.iterdir():
            if run_dir.is_dir():
                meta_path = run_dir / "meta.toml"
                if meta_path.exists():
                    runs.append(self.load_run_meta(run_dir.name))
        return runs
