---
name: hpc
description: HPC cluster workflow automation - sync files to remote cluster, submit scheduler jobs (Slurm/PJM), and monitor job status. Use when working with hpc.toml, submitting HPC jobs, syncing to clusters, or checking job status.
allowed-tools: Bash(hpc:*)
---

# hpc CLI

HPC workflow automation tool for file sync and scheduler job management (Slurm/PJM).

## CLI Reference

```
!`hpc --skill`
```

## Getting Started

If `hpc.toml` does not exist in the project, run `hpc init` to create it, then ask the user to edit it with their cluster settings (host, workdir, scheduler, etc.) before proceeding.

## Typical Workflow

1. `hpc sync` - Sync files to remote cluster (`--dry-run` to preview)
2. `hpc submit "command"` or `hpc submit -s script.sh` - Submit a job
3. `hpc status <id>` - Check job status (accepts run_id or job_id)
4. `hpc job-output <id>` - View stdout (`-e` for stderr)
5. `hpc wait <id>` - Wait for completion

## Key Concepts

- **Project root**: hpc walks up from CWD to find `hpc.toml` (like git finds `.git`). All commands work from any subdirectory.
- **run_id vs job_id**: `hpc submit` returns both. Either can be used with `status`, `job-output`, `wait`.
- **Multi-setup runs**: Submit from subdirectories to set the job's remote working directory accordingly (e.g., `cd runs/setup-a && hpc submit "python main.py"` runs in `/remote/project/runs/setup-a`).
- **Config resolution**: `--config` / `-c` > `$HPC_CONFIG` > walk-up discovery > `./hpc.toml`
- **Sync scope**: `hpc sync` always syncs the entire project root, regardless of CWD.
