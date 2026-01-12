"""Configuration management"""

import sys
import tomllib
from pathlib import Path
from typing import Optional

import tomli_w
from pydantic import BaseModel


class ClusterConfig(BaseModel):
    """Cluster connection configuration"""

    host: str
    workdir: str


class EnvConfig(BaseModel):
    """Environment configuration"""

    modules: list[str] = []
    conda_env: Optional[str] = None


class SyncConfig(BaseModel):
    """Sync configuration"""

    ignore: list[str] = []
    ignore_push: list[str] = []
    ignore_pull: list[str] = []


class SlurmConfig(BaseModel):
    """Slurm job configuration"""

    options: dict[str, str | int] = {}


class HpcConfig(BaseModel):
    """Combined HPC configuration"""

    cluster: ClusterConfig
    env: EnvConfig
    sync: SyncConfig = SyncConfig()
    slurm: SlurmConfig


KNOWN_SECTIONS = {"cluster", "env", "sync", "slurm"}


class ConfigManager:
    """TOML configuration file manager"""

    def load_config(self, path: Path) -> HpcConfig:
        """Load configuration from TOML file"""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        unknown = set(data.keys()) - KNOWN_SECTIONS
        for section in sorted(unknown):
            print(
                f"\033[33mWarning: unknown section [{section}] in {path}\033[0m",
                file=sys.stderr,
            )

        return HpcConfig(
            cluster=ClusterConfig(**data["cluster"]),
            env=EnvConfig(**data.get("env", {})),
            sync=SyncConfig(**data.get("sync", {})),
            slurm=SlurmConfig(options=data.get("slurm", {}).get("options", {})),
        )

    def generate_template(self, path: Path) -> None:
        """Generate template configuration file"""
        template = {
            "cluster": {
                "host": "myhpc",
                "workdir": "/scratch/${USER}/myproj",
            },
            "env": {
                "modules": ["gcc/12.2.0", "cuda/12.2"],
            },
            "sync": {
                "ignore": ["hpc.toml", ".git"],
                "ignore_push": [".hpc"],
            },
            "slurm": {
                "options": {
                    "partition": "gpu",
                    "time": "02:00:00",
                    "mem": "32G",
                    "gpus": 1,
                    "account": "myaccount",
                }
            },
        }
        with open(path, "wb") as f:
            tomli_w.dump(template, f)
