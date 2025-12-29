"""File synchronization management"""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import HpcConfig
from .ssh import SSHManager


@dataclass
class SyncResult:
    """Result of sync operation"""

    success: bool
    files_synced: int
    dry_run: bool


class SyncManager:
    """rsync-based file synchronization manager"""

    DEFAULT_EXCLUDES = [".git", "__pycache__", "*.pyc", ".venv", "node_modules"]

    def __init__(self, ssh_manager: SSHManager, config: HpcConfig):
        self.ssh_manager = ssh_manager
        self.config = config

    def get_git_commit(self, path: Path, short: bool = False) -> Optional[str]:
        """Get current git commit hash"""
        try:
            # Check if path itself is a git repo
            git_dir = path / ".git"
            if not git_dir.exists():
                return None

            cmd = ["git", "rev-parse"]
            if short:
                cmd.append("--short")
            cmd.append("HEAD")
            result = subprocess.run(
                cmd, cwd=path, capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def has_uncommitted_changes(self, path: Path) -> bool:
        """Check if there are uncommitted changes"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=path,
                capture_output=True,
                text=True,
            )
            return len(result.stdout.strip()) > 0
        except Exception:
            return False

    def _build_rsync_command(
        self, local_path: Path, dry_run: bool
    ) -> list[str]:
        """Build rsync command with options"""
        cmd = ["rsync", "-avz"]

        if dry_run:
            cmd.append("--dry-run")

        for pattern in self.DEFAULT_EXCLUDES:
            cmd.extend(["--exclude", pattern])

        target = f"{self.config.cluster.host}:{self.config.cluster.workdir}"
        cmd.extend([str(local_path) + "/", target])

        return cmd

    def sync_inputs(self, local_path: Path, dry_run: bool = True) -> SyncResult:
        """Sync local files to remote HPC cluster"""
        cmd = self._build_rsync_command(local_path, dry_run)

        result = subprocess.run(cmd, capture_output=True, text=True)

        return SyncResult(
            success=result.returncode == 0,
            files_synced=0,  # TODO: parse rsync output
            dry_run=dry_run,
        )
