"""Configuration management"""

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


class SlurmConfig(BaseModel):
    """Slurm job configuration"""

    partition: str
    time: str
    mem: str
    gpus: Optional[int] = None


class HpcConfig(BaseModel):
    """Combined HPC configuration"""

    cluster: ClusterConfig
    env: EnvConfig
    slurm: SlurmConfig


class ConfigManager:
    """TOML configuration file manager"""

    def load_config(self, path: Path) -> HpcConfig:
        """Load configuration from TOML file"""
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path}")

        with open(path, "rb") as f:
            data = tomllib.load(f)

        return HpcConfig(
            cluster=ClusterConfig(**data["cluster"]),
            env=EnvConfig(**data.get("env", {})),
            slurm=SlurmConfig(**data["slurm"]),
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
                "conda_env": "myenv",
            },
            "slurm": {
                "partition": "gpu",
                "time": "02:00:00",
                "mem": "32G",
                "gpus": 1,
            },
        }
        with open(path, "wb") as f:
            tomli_w.dump(template, f)
