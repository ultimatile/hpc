"""Config manager tests"""

import pytest
from pathlib import Path

from hpc.config import (
    ClusterConfig,
    EnvConfig,
    SlurmConfig,
    HpcConfig,
    ConfigManager,
)


class TestClusterConfig:
    def test_cluster_config_required_fields(self):
        config = ClusterConfig(host="myhpc", workdir="/scratch/user/proj")
        assert config.host == "myhpc"
        assert config.workdir == "/scratch/user/proj"

    def test_cluster_config_missing_host_raises(self):
        with pytest.raises(Exception):
            ClusterConfig(workdir="/scratch/user/proj")


class TestEnvConfig:
    def test_env_config_with_setup(self):
        config = EnvConfig(setup=[{"module": "gcc/12.2.0"}, {"spack": "cuda@12"}])
        assert len(config.setup) == 2

    def test_env_config_with_string_command(self):
        config = EnvConfig(setup=["my_setup"])
        assert config.setup == ["my_setup"]

    def test_env_config_defaults(self):
        config = EnvConfig()
        assert config.setup == []

    def test_env_config_rejects_shell_special(self):
        config = EnvConfig(setup=[{"module": "gcc; rm -rf ~"}])
        with pytest.raises(Exception):
            config.get_setup_commands()


class TestSlurmConfig:
    def test_slurm_config_default_options(self):
        config = SlurmConfig()
        assert config.options == {}

    def test_slurm_config_with_options(self):
        config = SlurmConfig(
            options={"partition": "gpu", "time": "02:00:00", "gpus": 1}
        )
        assert config.options["partition"] == "gpu"
        assert config.options["gpus"] == 1


class TestHpcConfig:
    def test_hpc_config_combines_all(self):
        config = HpcConfig(
            cluster=ClusterConfig(host="myhpc", workdir="/scratch/user/proj"),
            env=EnvConfig(setup=[{"module": "gcc/12.2.0"}]),
            slurm=SlurmConfig(options={"partition": "gpu"}),
        )
        assert config.cluster.host == "myhpc"
        assert config.slurm.options["partition"] == "gpu"


class TestConfigManager:
    def test_load_config_from_toml(self, temp_dir):
        config_path = temp_dir / "hpc.toml"
        config_path.write_text("""
[cluster]
host = "myhpc"
workdir = "/scratch/user/proj"

[env]
setup = [
    { module = "gcc/12.2.0" },
    { spack = "cuda@12" },
]

[slurm.options]
partition = "gpu"
time = "02:00:00"
mem = "32G"
gpus = 1
""")
        manager = ConfigManager()
        config = manager.load_config(config_path)

        assert config.cluster.host == "myhpc"
        assert config.cluster.workdir == "/scratch/user/proj"
        assert len(config.env.setup) == 2
        assert config.slurm.options["partition"] == "gpu"
        assert config.slurm.options["time"] == "02:00:00"
        assert config.slurm.options["mem"] == "32G"
        assert config.slurm.options["gpus"] == 1

    def test_load_config_file_not_found(self):
        manager = ConfigManager()
        with pytest.raises(FileNotFoundError):
            manager.load_config(Path("/nonexistent/hpc.toml"))

    def test_load_config_invalid_toml(self, temp_dir):
        config_path = temp_dir / "hpc.toml"
        config_path.write_text("invalid toml [[[")
        manager = ConfigManager()
        with pytest.raises(Exception):
            manager.load_config(config_path)

    def test_generate_template(self, temp_dir):
        manager = ConfigManager()
        config_path = temp_dir / "hpc.toml"
        manager.generate_template(config_path)

        assert config_path.exists()
        content = config_path.read_text()
        assert "[cluster]" in content
        assert "[env]" in content
        assert "[slurm.options]" in content
