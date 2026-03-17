"""CLI command tests"""

from unittest.mock import patch, MagicMock

from hpc.main import app
from hpc import cli  # noqa: F401 - register commands


def test_help(cli_runner):
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "HPC job execution support tool" in result.stdout


def test_init_command_exists(cli_runner):
    result = cli_runner.invoke(app, ["init", "--help"])
    assert result.exit_code == 0


def test_init_creates_config_file(cli_runner, temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)
    result = cli_runner.invoke(app, ["init"])
    assert result.exit_code == 0
    config_path = temp_dir / "hpc.toml"
    assert config_path.exists()
    content = config_path.read_text()
    assert "[cluster]" in content


def test_sync_command_exists(cli_runner):
    result = cli_runner.invoke(app, ["sync", "--help"])
    assert result.exit_code == 0


def test_sync_requires_config(cli_runner, temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)
    result = cli_runner.invoke(app, ["sync"])
    assert result.exit_code != 0
    assert "Config file not found" in result.stdout or "hpc.toml" in result.stdout


def test_submit_command_exists(cli_runner):
    result = cli_runner.invoke(app, ["submit", "--help"])
    assert result.exit_code == 0


def test_submit_requires_config(cli_runner, temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)
    result = cli_runner.invoke(app, ["submit", "python train.py"])
    assert result.exit_code != 0


def test_submit_requires_cmd_or_script(cli_runner, temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)
    (temp_dir / "hpc.toml").write_text("[cluster]\nhost = 'test'\nworkdir = '/tmp'")
    result = cli_runner.invoke(app, ["submit"])
    assert result.exit_code != 0
    assert "provide a command or --script" in result.stdout


def test_submit_script_not_found(cli_runner, temp_dir, monkeypatch):
    monkeypatch.chdir(temp_dir)
    (temp_dir / "hpc.toml").write_text("[cluster]\nhost = 'test'\nworkdir = '/tmp'")
    result = cli_runner.invoke(app, ["submit", "--script", "nonexistent.sh"])
    assert result.exit_code != 0
    assert "Script not found" in result.stdout


def test_status_command_exists(cli_runner):
    result = cli_runner.invoke(app, ["status", "--help"])
    assert result.exit_code == 0


def test_config_option(cli_runner, temp_dir, monkeypatch):
    """Test --config option loads specified config file"""
    monkeypatch.chdir(temp_dir)
    custom_config = temp_dir / "custom.toml"
    custom_config.write_text("[cluster]\nhost = 'test'\nworkdir = '/tmp'")
    result = cli_runner.invoke(app, ["--config", str(custom_config), "sync"])
    # Should not fail with "Config file not found" since custom.toml exists
    assert "Config file not found" not in result.stdout


def test_config_env_var(cli_runner, temp_dir, monkeypatch):
    """Test HPC_CONFIG environment variable"""
    monkeypatch.chdir(temp_dir)
    custom_config = temp_dir / "env.toml"
    custom_config.write_text("[cluster]\nhost = 'test'\nworkdir = '/tmp'")
    monkeypatch.setenv("HPC_CONFIG", str(custom_config))
    result = cli_runner.invoke(app, ["sync"])
    assert "Config file not found" not in result.stdout


def test_config_option_overrides_env(cli_runner, temp_dir, monkeypatch):
    """Test --config takes precedence over HPC_CONFIG"""
    monkeypatch.chdir(temp_dir)
    opt_config = temp_dir / "opt.toml"
    opt_config.write_text("[cluster]\nhost = 'test'\nworkdir = '/tmp'")
    monkeypatch.setenv("HPC_CONFIG", "nonexistent.toml")
    result = cli_runner.invoke(app, ["--config", str(opt_config), "sync"])
    assert "Config file not found" not in result.stdout


def test_walk_up_finds_config(cli_runner, temp_dir, monkeypatch):
    """Walk-up discovery finds hpc.toml in parent directory"""
    (temp_dir / "hpc.toml").write_text("[cluster]\nhost = 'test'\nworkdir = '/tmp'")
    child = temp_dir / "runs" / "bench1"
    child.mkdir(parents=True)
    monkeypatch.chdir(child)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = cli_runner.invoke(app, ["sync"])
        assert result.exit_code == 0
        assert "Config file not found" not in result.stdout


def test_sync_uses_project_root(cli_runner, temp_dir, monkeypatch):
    """sync uses project root (hpc.toml location) as local path, not CWD"""
    (temp_dir / "hpc.toml").write_text("[cluster]\nhost = 'test'\nworkdir = '/tmp'")
    child = temp_dir / "runs" / "bench1"
    child.mkdir(parents=True)
    monkeypatch.chdir(child)
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        cli_runner.invoke(app, ["sync"])
        # rsync should use project root, not the child directory
        call_args = mock_run.call_args[0][0]
        local_arg = [a for a in call_args if str(temp_dir.resolve()) in str(a)]
        assert local_arg
        # Should NOT contain the child subpath as the source
        assert not any(str(child) in str(a) for a in call_args)


def test_init_does_not_walk_up(cli_runner, temp_dir, monkeypatch):
    """init creates hpc.toml in CWD, does not walk up"""
    (temp_dir / "hpc.toml").write_text("[cluster]\nhost = 'test'\nworkdir = '/tmp'")
    child = temp_dir / "subdir"
    child.mkdir()
    monkeypatch.chdir(child)
    result = cli_runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert (child / "hpc.toml").exists()
