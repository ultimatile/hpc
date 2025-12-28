"""SSH manager tests"""

import subprocess
from unittest.mock import patch, MagicMock

import pytest

from hpc.ssh import SSHManager, SSHError


class TestSSHManagerInit:
    def test_init_with_host(self):
        manager = SSHManager(host="myhpc")
        assert manager.host == "myhpc"

    def test_init_with_user(self):
        manager = SSHManager(host="myhpc", user="testuser")
        assert manager.user == "testuser"


class TestSSHManagerConnection:
    def test_test_connection_success(self):
        manager = SSHManager(host="myhpc")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert manager.test_connection() is True

    def test_test_connection_failure(self):
        manager = SSHManager(host="myhpc")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert manager.test_connection() is False


class TestSSHManagerRunCommand:
    def test_run_command_success(self):
        manager = SSHManager(host="myhpc")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr="",
            )
            result = manager.run_command("echo hello")
            assert result.returncode == 0
            assert result.stdout == "output"

    def test_run_command_with_quiet_option(self):
        manager = SSHManager(host="myhpc")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            manager.run_command("echo hello")
            call_args = mock_run.call_args[0][0]
            assert "-q" in call_args

    def test_run_command_failure_raises(self):
        manager = SSHManager(host="myhpc")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="Connection refused",
            )
            with pytest.raises(SSHError):
                manager.run_command("echo hello")

    def test_run_command_captures_stderr(self):
        manager = SSHManager(host="myhpc")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="output",
                stderr="warning message",
            )
            result = manager.run_command("some_cmd")
            assert result.stderr == "warning message"


class TestSSHManagerControlMaster:
    def test_control_master_options_included(self):
        manager = SSHManager(host="myhpc", use_control_master=True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            manager.run_command("echo hello")
            call_args = mock_run.call_args[0][0]
            args_str = " ".join(call_args)
            assert "ControlMaster" in args_str
            assert "ControlPath" in args_str
