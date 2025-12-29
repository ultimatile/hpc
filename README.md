# hpc

An automation CLI tool for HPC workflow.

## Installation

```bash
uv sync
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

Submits a job to Slurm.

```bash
hpc submit "python train.py"
hpc submit "python train.py --epochs 100"
```

### `hpc status`

Checks the status of a submitted job.

```bash
hpc status 12345678
```

## Configuration

Edit `hpc.toml`:

```toml
[cluster]
host = "myhpc"                    # SSH host (from ~/.ssh/config)
workdir = "/scratch/user/proj"    # Remote working directory

[env]
modules = ["gcc/12.2.0", "cuda/12.2"]  # Modules to load
conda_env = "myenv"                     # Conda environment (optional)

[slurm]
partition = "gpu"      # Slurm partition
time = "02:00:00"      # Time limit
mem = "32G"            # Memory
gpus = 1               # Number of GPUs (optional)
```

## Requirements

- Python 3.11+
- SSH access to HPC cluster (key-based authentication recommended)
- rsync
- Slurm on the remote cluster

## Development

```bash
make test      # run tests
make lint      # run linter
make check     # run all checks
```
