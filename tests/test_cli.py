"""CLI command tests"""

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
