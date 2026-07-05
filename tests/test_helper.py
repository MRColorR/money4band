"""Tests for money4band.docker.helper - utility functions."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from money4band.docker.helper import (
    check_required_files,
    get_compose_project_name,
    is_user_root,
    run_docker_command,
    show_spinner,
)


class TestGetComposeProjectName:
    def test_reads_from_env(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("OTHER=val\nCOMPOSE_PROJECT_NAME=my_project\nMORE=x\n")
        assert get_compose_project_name(str(env)) == "my_project"

    def test_missing_key_returns_none(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("OTHER=val\n")
        assert get_compose_project_name(str(env)) is None

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert get_compose_project_name(str(tmp_path / "nope.env")) is None

    def test_compose_file_path_converted(self, tmp_path: Path) -> None:
        """If a docker-compose.yaml path is given, it's converted to .env."""
        env = tmp_path / ".env"
        env.write_text("COMPOSE_PROJECT_NAME=proj\n")
        result = get_compose_project_name(str(tmp_path / "docker-compose.yaml"))
        assert result == "proj"


class TestRunDockerCommand:
    @patch("money4band.docker.helper.subprocess")
    def test_success_returns_zero(self, mock_sp) -> None:
        mock_sp.run.return_value = MagicMock(returncode=0)
        assert run_docker_command(["docker", "ps"]) == 0

    @patch("money4band.docker.helper.subprocess")
    def test_failure_returns_nonzero(self, mock_sp) -> None:
        mock_sp.run.return_value = MagicMock(returncode=1)
        assert run_docker_command(["docker", "compose", "up"]) == 1

    @patch("money4band.docker.helper.subprocess")
    def test_command_passed_through(self, mock_sp) -> None:
        mock_sp.run.return_value = MagicMock(returncode=0)
        run_docker_command(["docker", "compose", "-f", "test.yml", "up"])
        call_args = mock_sp.run.call_args
        assert "docker" in call_args[0][0]


class TestCheckRequiredFiles:
    def test_all_exist(self, tmp_path: Path) -> None:
        f1 = tmp_path / "a.txt"
        f2 = tmp_path / "b.txt"
        f1.write_text("x")
        f2.write_text("y")
        assert check_required_files([str(f1), str(f2)], "Error", "Hint") == []

    def test_missing_files_returned(self, tmp_path: Path) -> None:
        f1 = tmp_path / "exists.txt"
        f1.write_text("x")
        result = check_required_files(
            [str(f1), str(tmp_path / "missing.txt")], "Error", "Hint"
        )
        assert len(result) == 1

    def test_all_missing(self, tmp_path: Path) -> None:
        result = check_required_files(
            [str(tmp_path / "a"), str(tmp_path / "b")], "Error", "Hint"
        )
        assert len(result) == 2


class TestIsUserRoot:
    @patch("platform.system", return_value="Windows")
    def test_windows_not_root(self, _mock) -> None:
        assert is_user_root() is False

    @patch("platform.system", return_value="Darwin")
    def test_macos_not_root(self, _mock) -> None:
        assert is_user_root() is False


class TestGetComposeProjectNameParsing:
    """Whitespace stripping and empty-file handling for .env project name."""

    def test_trailing_whitespace_stripped(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("COMPOSE_PROJECT_NAME=money4band  \n")
        assert get_compose_project_name(str(env)) == "money4band"

    def test_empty_file_returns_none(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("")
        assert get_compose_project_name(str(env)) is None


class TestIsDockerDaemonRunning:
    @patch("money4band.docker.helper.subprocess")
    def test_running(self, mock_sp) -> None:
        from money4band.docker.helper import is_docker_daemon_running

        mock_sp.run.return_value = MagicMock(returncode=0)
        assert is_docker_daemon_running() is True

    @patch("money4band.docker.helper.subprocess")
    def test_not_running(self, mock_sp) -> None:
        from money4band.docker.helper import is_docker_daemon_running

        mock_sp.run.return_value = MagicMock(returncode=1)
        assert is_docker_daemon_running() is False

    @patch("money4band.docker.helper.subprocess")
    def test_docker_not_installed(self, mock_sp) -> None:
        from money4band.docker.helper import is_docker_daemon_running

        mock_sp.run.side_effect = FileNotFoundError
        assert is_docker_daemon_running() is False


class TestIsUserInDockerGroup:
    @patch("platform.system", return_value="Windows")
    def test_windows_always_true(self, _mock) -> None:
        from money4band.docker.helper import is_user_in_docker_group

        assert is_user_in_docker_group() is True

    @patch("platform.system", return_value="Linux")
    @patch("money4band.docker.helper.subprocess")
    @patch("money4band.docker.helper.getpass")
    def test_linux_in_group(self, mock_gp, mock_sp, _sys) -> None:
        from money4band.docker.helper import is_user_in_docker_group

        mock_gp.getuser.return_value = "user1"
        mock_sp.run.return_value = MagicMock(stdout="user1 : user1 docker sudo")
        assert is_user_in_docker_group() is True

    @patch("platform.system", return_value="Linux")
    @patch("money4band.docker.helper.subprocess")
    @patch("money4band.docker.helper.getpass")
    def test_linux_not_in_group(self, mock_gp, mock_sp, _sys) -> None:
        from money4band.docker.helper import is_user_in_docker_group

        mock_gp.getuser.return_value = "user1"
        mock_sp.run.return_value = MagicMock(stdout="user1 : user1 sudo")
        assert is_user_in_docker_group() is False


class TestIsMultiarchEmulationAvailable:
    @patch("money4band.docker.helper.subprocess")
    def test_detected_via_buildx(self, mock_sp) -> None:
        from money4band.docker.helper import is_multiarch_emulation_available

        mock_sp.run.return_value = MagicMock(
            returncode=0,
            stdout="Platforms: linux/amd64, linux/arm64, linux/arm/v7",
        )
        assert is_multiarch_emulation_available() is True

    @patch("money4band.docker.helper.subprocess")
    def test_single_arch_returns_false(self, mock_sp) -> None:
        from money4band.docker.helper import is_multiarch_emulation_available

        mock_sp.run.return_value = MagicMock(
            returncode=0, stdout="Platforms: linux/amd64"
        )
        with patch("os.path.isdir", return_value=False):
            assert is_multiarch_emulation_available() is False

    @patch("money4band.docker.helper.subprocess")
    def test_all_checks_fail_returns_false(self, mock_sp) -> None:
        from money4band.docker.helper import is_multiarch_emulation_available

        mock_sp.run.side_effect = Exception("no docker")
        with patch("os.path.isdir", return_value=False):
            assert is_multiarch_emulation_available() is False


class TestRunDockerCommandFailureAndSudo:
    """OSError wrapping and sudo prepending on Linux."""

    @patch("money4band.docker.helper.subprocess")
    def test_exception_raises_runtime_error(self, mock_sp) -> None:
        mock_sp.run.side_effect = OSError("not found")
        with pytest.raises(RuntimeError, match="Command failed"):
            run_docker_command(["docker", "info"])

    @patch("money4band.docker.helper.subprocess")
    @patch("platform.system", return_value="Linux")
    def test_sudo_prepended_on_linux(self, _sys, mock_sp) -> None:
        mock_sp.run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        run_docker_command(["docker", "ps"], use_sudo=True)
        cmd = mock_sp.run.call_args[0][0]
        assert cmd[0] == "sudo"


class TestShowSpinner:
    def test_stops_when_event_set(self) -> None:
        event = threading.Event()
        event.set()
        show_spinner("Testing...", event)


class TestCheckDockerReady:
    @patch("platform.system", return_value="Windows")
    @patch("money4band.docker.helper.is_docker_daemon_running", return_value=True)
    def test_passes_when_daemon_running(self, _daemon, _sys) -> None:
        from money4band.docker.helper import check_docker_ready

        check_docker_ready()

    @patch("platform.system", return_value="Windows")
    @patch("money4band.docker.helper.is_docker_daemon_running", return_value=False)
    def test_raises_when_daemon_not_running(self, _daemon, _sys) -> None:
        from money4band.docker.helper import check_docker_ready

        with pytest.raises(RuntimeError, match="not running"):
            check_docker_ready()

    @patch("platform.system", return_value="Linux")
    @patch("money4band.docker.helper.is_docker_daemon_running", return_value=True)
    @patch("money4band.docker.helper.is_user_root", return_value=True)
    def test_linux_root_passes(self, _root, _daemon, _sys) -> None:
        from money4band.docker.helper import check_docker_ready

        check_docker_ready()

    @patch("platform.system", return_value="Linux")
    @patch("money4band.docker.helper.is_docker_daemon_running", return_value=False)
    def test_linux_daemon_not_running(self, _daemon, _sys) -> None:
        from money4band.docker.helper import check_docker_ready

        with pytest.raises(RuntimeError):
            check_docker_ready()

    @patch("platform.system", return_value="Linux")
    @patch("money4band.docker.helper.is_docker_daemon_running", return_value=True)
    @patch("money4band.docker.helper.is_user_root", return_value=False)
    @patch("money4band.docker.helper.is_user_in_docker_group", return_value=False)
    @patch("money4band.docker.helper.create_docker_group_if_needed")
    def test_linux_not_in_group_fixes(
        self, mock_fix, _group, _root, _daemon, _sys
    ) -> None:
        from money4band.docker.helper import check_docker_ready

        check_docker_ready()
        mock_fix.assert_called_once()


class TestCreateDockerGroup:
    """Docker group creation and user addition on Linux."""

    @patch("platform.system", return_value="Windows")
    def test_skips_on_windows(self, _sys) -> None:
        from money4band.docker.helper import create_docker_group_if_needed

        create_docker_group_if_needed()  # No crash, no-op

    @patch("platform.system", return_value="Linux")
    @patch("money4band.docker.helper.getpass")
    @patch("money4band.docker.helper.subprocess")
    def test_creates_group_and_adds_user(self, mock_sp, mock_gp, _sys) -> None:
        from money4band.docker.helper import create_docker_group_if_needed

        mock_sp.run.side_effect = [
            MagicMock(returncode=1),  # getent group docker -> doesn't exist
            MagicMock(returncode=0),  # groupadd
            MagicMock(returncode=0),  # usermod
        ]
        mock_gp.getuser.return_value = "testuser"
        create_docker_group_if_needed()
        assert mock_sp.run.call_count == 3

    @patch("platform.system", return_value="Linux")
    @patch("money4band.docker.helper.getpass")
    @patch("money4band.docker.helper.subprocess")
    def test_existing_group_just_adds_user(self, mock_sp, mock_gp, _sys) -> None:
        from money4band.docker.helper import create_docker_group_if_needed

        mock_sp.run.side_effect = [
            MagicMock(returncode=0),  # getent -> group exists
            MagicMock(returncode=0),  # usermod
        ]
        mock_gp.getuser.return_value = "testuser"
        create_docker_group_if_needed()
        assert mock_sp.run.call_count == 2


class TestSetupService:
    """Systemd/sysvinit service setup on Linux."""

    @patch("platform.system", return_value="Linux")
    @patch("os.path.exists")
    @patch("money4band.docker.helper.subprocess")
    def test_systemd_already_active(self, mock_sp, mock_exists, _sys) -> None:
        from money4band.docker.helper import setup_service

        mock_exists.return_value = True
        mock_sp.run.return_value = MagicMock(stdout="active", returncode=0)
        setup_service("docker.binfmt", "/tmp/svc.service")
        # Only one call: systemctl is-active
        mock_sp.run.assert_called_once()

    @patch("platform.system", return_value="Linux")
    @patch("os.path.exists")
    @patch("money4band.docker.helper.subprocess")
    def test_systemd_install_and_start(self, mock_sp, mock_exists, _sys) -> None:
        from money4band.docker.helper import setup_service

        # is-active returns "inactive", /etc/systemd/system exists, service file doesn't yet
        mock_exists.side_effect = lambda p: p == "/etc/systemd/system"
        mock_sp.run.side_effect = [
            MagicMock(stdout="inactive"),  # systemctl is-active
            MagicMock(returncode=0),  # cp
            MagicMock(returncode=0),  # daemon-reload
            MagicMock(returncode=0),  # enable
            MagicMock(returncode=0),  # start
        ]
        setup_service("docker.binfmt", "/tmp/svc.service")
