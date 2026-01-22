# hpc

An automation CLI tool for HPC workflow: source code and data sync and SLURM job management.

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

Submits a job to Slurm.
Returns both run_id (e.g., `20260109_1234`, hpc's local tracking ID) and job_id (Slurm's job ID, e.g., `12345678`).

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

Shows the output of a Slurm job.
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

[env]
modules = ["gcc/12.2.0", "cuda/12.2"]  # Modules to load (shorthand for module load)
spack = ["python@3.11"]                # Spack packages to load (shorthand for spack load)
setup = [                              # Additional setup commands
    {source = "/path/to/venv/bin/activate"},
    {export = ["VAR=value"]},          # {command = [args...]} format
    "some_cmd",                        # String: command without args
]

[sync]
ignore = ["hpc.toml", ".git"]  # Patterns to exclude from sync
compare = "checksum"           # File comparison: "checksum" (content-based, default) or "timestamp"

[slurm]
partition = "gpu"      # Slurm partition
time = "02:00:00"      # Time limit
mem = "32G"            # Memory
gpus = 1               # Number of GPUs (optional)
```

### Environment Setup

Commands are executed in this order: `modules` → `spack` → `setup`.

`modules` and `spack` are shorthand syntax:

- `modules = ["gcc/12.2.0"]` expands to `module load gcc/12.2.0`
- `spack = ["python@3.11"]` expands to `spack load python@3.11`

`setup` accepts:

- String: command without args (e.g., `"some_cmd"`)
- Dict: `{command = args}` format (e.g., `{export = ["VAR=value"]}` → `export VAR=value`)
- Special commands `module` and `spack` in dict format expand to `module load` / `spack load`

If you need a different execution order, put everything in `setup`:

```toml
[env]
setup = [
    {spack = "python@3.11"},
    {module = "gcc/12.2.0"},
    {source = "/path/to/venv/bin/activate"},
]
```

Shell special characters (`` ;|&`$<>\'"\n `` and space) are prohibited in arguments for security.

`$XDG_CONFIG_HOME/hpc/config.toml` (default: `~/.config/hpc/config.toml`) will be copied as `hpc.toml` if it exists when running `hpc init`.

## Requirements

- Python 3.11+
- SSH access to HPC cluster (key-based authentication recommended)
- rsync
- Slurm on the remote cluster

### rsync Note

rsync from https://rsync.samba.org/ is recommended over macOS's built-in openrsync. When using checksum-based comparison (`compare = "checksum"`, default), openrsync has a bug where files with sizes that are exact multiples of 64 bytes are always detected as changed, even when identical. This is due to a protocol 29 checksum boundary issue. Confirmed with macOS 15.7's openrsync (protocol version 29, rsync version 2.6.9 compatible). If concerned, use `[sync] compare = "timestamp"` instead.

On macOS, install rsync via Homebrew:

```bash
brew install rsync
```

## Development

```bash
make test      # run tests
make lint      # run linter
make check     # run all checks
```
