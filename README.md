# hpc

An automation CLI tool for HPC workflow: source code/data sync and scheduler job management (Slurm/PJM).

## Installation

```bash
# execute in this repo
uv tool install .
```

## Quick Start

```bash
# 1. Initialize project
hpc init

# 2. Edit configuration
vim hpc.toml

# 3. Sync files to cluster (dry-run first)
hpc sync
hpc sync --apply

# 4. Submit job
hpc submit "python train.py"

# 5. Check status
hpc status 12345678

# 6. View job output
hpc job-output 12345678
```

## Commands

### `hpc init`

Creates `hpc.toml` configuration file in the current directory.

```bash
hpc init
```

### `hpc sync`

Syncs local files to the remote HPC cluster using rsync.

```bash
hpc sync           # dry-run (shows what would be synced)
hpc sync --apply   # actual sync
```

### `hpc submit`

Submits a job to the configured scheduler.
Returns both run_id (e.g., `20260109_1234`, hpc's local tracking ID) and job_id (scheduler job ID, e.g., `12345678`).

```bash
hpc submit "python train.py"
hpc submit --script run.sh
hpc submit -s run.sh --wait
```

### `hpc status`

Checks the status of a submitted job.
Accepts either run_id or job_id.

```bash
hpc status 12345678
```

### `hpc job-output`

Shows the output of a submitted job.
Accepts either run_id or job_id.

```bash
hpc job-output 12345678
```

### `hpc wait`

Waits for a run to complete.
Accepts either run_id or job_id.

```bash
hpc wait 12345678
```

## Configuration

Edit `hpc.toml`:

```toml
[cluster]
host = "myhpc"                    # SSH host (from ~/.ssh/config)
workdir = "/scratch/user/proj"    # Remote working directory; all codes and data will be synced here
scheduler = "slurm"                # "slurm" (default) or "pjm"

[env]
modules = ["gcc/12.2.0", "cuda/12.2"]  # Modules to load
conda_env = "myenv"                    # Conda environment (optional, runs `conda activate myenv` before job)

[sync]
ignore = ["hpc.toml", ".git"]  # Patterns to exclude from sync

[slurm.options]
partition = "gpu"      # Example (Slurm): partition
time = "02:00:00"      # Example (Slurm): time limit
mem = "32G"            # Example (Slurm): memory
gpus = 1               # Example (Slurm): number of GPUs
```

Scheduler directive options are configured under `[slurm.options]` for both `slurm` and `pjm`.
When `scheduler = "pjm"`, set keys/values that match your PJM environment.

`$XDG_CONFIG_HOME/hpc/config.toml` (default: `~/.config/hpc/config.toml`) will be copied as `hpc.toml` if it exists when running `hpc init`.

## Requirements

- Python 3.11+
- SSH access to HPC cluster (key-based authentication recommended)
- rsync
- Slurm or PJM on the remote cluster

## Development

```bash
make test      # run tests
make lint      # run linter
make check     # run all checks
```
