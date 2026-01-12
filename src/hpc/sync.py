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
    dry_run: bool


class SyncManager:
    """rsync-based file synchronization manager"""

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
            result = subprocess.run(cmd, cwd=path, capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def has_uncommitted_changes(self, path: Path) -> bool:
        """Check if there are uncommitted changes"""
        try:
            git_dir = path / ".git"
            if not git_dir.exists():
                return False

            result = subprocess.run(
                [
                    "git",
                    "--git-dir",
                    str(git_dir),
                    "--work-tree",
                    str(path),
                    "status",
                    "--porcelain",
                ],
                capture_output=True,
                text=True,
            )
            return len(result.stdout.strip()) > 0
        except Exception:
            return False

    def _build_rsync_command(
        self, local_path: Path, dry_run: bool, reverse: bool = False
    ) -> list[str]:
        """Build rsync command with options"""
        cmd = ["rsync", "-avz", "-e", "ssh -q"]

        if dry_run:
            cmd.append("--dry-run")

        # Common ignore patterns
        for pattern in self.config.sync.ignore:
            cmd.extend(["--exclude", pattern])

        # Direction-specific ignore patterns
        if reverse:
            for pattern in self.config.sync.ignore_pull:
                cmd.extend(["--exclude", pattern])
        else:
            for pattern in self.config.sync.ignore_push:
                cmd.extend(["--exclude", pattern])

        remote = f"{self.config.cluster.host}:{self.config.cluster.workdir}"
        local = str(local_path) + "/"

        if reverse:
            cmd.extend([remote + "/", local])
        else:
            cmd.extend([local, remote])

        return cmd

    def remote_dir_exists(self) -> bool:
        """Check if remote workdir exists"""
        try:
            self.ssh_manager.run_command("test", ["-d", self.config.cluster.workdir])
            return True
        except Exception:
            return False

    def sync_push(self, local_path: Path, dry_run: bool = True) -> SyncResult:
        """Sync local files to remote HPC cluster"""
        cmd = self._build_rsync_command(local_path, dry_run, reverse=False)
        result = subprocess.run(cmd)
        return SyncResult(success=result.returncode == 0, dry_run=dry_run)

    def sync_pull(self, local_path: Path, dry_run: bool = True) -> SyncResult:
        """Sync remote files to local"""
        cmd = self._build_rsync_command(local_path, dry_run, reverse=True)
        result = subprocess.run(cmd)
        return SyncResult(success=result.returncode == 0, dry_run=dry_run)

    def sync_inputs(self, local_path: Path, dry_run: bool = True) -> SyncResult:
        """Sync local files to remote HPC cluster (alias for sync_push)"""
        return self.sync_push(local_path, dry_run)
