"""Configuration management"""

import shlex
import sys
import tomllib
from pathlib import Path
from typing import Literal

import tomli_w
from pydantic import BaseModel

# str: command without args, dict: {cmd: args}
SetupItem = str | dict[str, str | list[str]]

SHELL_SPECIAL = set(";|&`$<>\\'\"\n ")


def _validate_arg(arg: str) -> None:
    if bad := SHELL_SPECIAL & set(arg):
        raise ValueError(f"Shell special characters not allowed: {bad}")


def build_setup_commands(setup: list[SetupItem]) -> list[str]:
    """Build shell commands from setup items"""
    cmds = []
    for item in setup:
        if isinstance(item, str):
            _validate_arg(item)
            cmds.append(shlex.quote(item))
        else:
            cmd, args = next(iter(item.items()))
            _validate_arg(cmd)
            args_list = [args] if isinstance(args, str) else args
            args_list = [a for a in args_list if a]
            for a in args_list:
                _validate_arg(a)
            quoted_args = " ".join(shlex.quote(a) for a in args_list)
            if cmd == "module":
                cmds.append(f"module load {quoted_args}")
            elif cmd == "spack":
                cmds.append(f"spack load {quoted_args}")
            else:
                parts = [shlex.quote(cmd)] + [shlex.quote(a) for a in args_list]
                cmds.append(" ".join(parts))
    return cmds


class ClusterConfig(BaseModel):
    """Cluster connection configuration"""

    host: str
    workdir: str


class EnvConfig(BaseModel):
    """Environment configuration"""

    modules: list[str] = []
    spack: list[str] = []
    setup: list[SetupItem] = []

    def get_setup_commands(self) -> list[str]:
        """Build commands: modules → spack → setup"""
        items: list[SetupItem] = []
        for m in self.modules:
            items.append({"module": m})
        for s in self.spack:
            items.append({"spack": s})
        items.extend(self.setup)
        return build_setup_commands(items)


class SyncConfig(BaseModel):
    """Sync configuration"""

    ignore: list[str] = []
    ignore_push: list[str] = []
    ignore_pull: list[str] = []
    compare: Literal["checksum", "timestamp"] = "checksum"


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
