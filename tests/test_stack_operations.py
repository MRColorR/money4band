"""Tests for money4band.docker.start and money4band.docker.stop."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import yaml

# ---------------------------------------------------------------------------
# fn_startStack helpers
# ---------------------------------------------------------------------------


class TestGetDeviceNameFromEnv:
    def test_extracts_device_name(self, tmp_path: Path) -> None:
        from money4band.docker.start import get_device_name_from_env

        env = tmp_path / ".env"
        env.write_text("OTHER=x\nDEVICE_NAME=mybox\nMORE=y\n")
        assert get_device_name_from_env(str(env)) == "mybox"

    def test_missing_device_name(self, tmp_path: Path) -> None:
        from money4band.docker.start import get_device_name_from_env

        env = tmp_path / ".env"
        env.write_text("OTHER=x\n")
        result = get_device_name_from_env(str(env))
        assert result is None or result == ""


class TestExtractAppNamesFromCompose:
    def test_extracts_services(self, tmp_path: Path) -> None:
        from money4band.docker.start import _extract_app_names_from_compose

        compose = tmp_path / "docker-compose.yaml"
        data = {"services": {"earnapp": {"image": "x"}, "honeygain": {"image": "y"}}}
        compose.write_text(yaml.dump(data))
        result = _extract_app_names_from_compose(str(compose))
        assert sorted(result) == ["earnapp", "honeygain"]

    def test_empty_services_returns_infra_fallback(self, tmp_path: Path) -> None:
        """When services dict is empty, falls back to infra names."""
        from money4band.docker.start import _extract_app_names_from_compose

        compose = tmp_path / "docker-compose.yaml"
        compose.write_text(yaml.dump({"services": {}}))
        result = _extract_app_names_from_compose(str(compose))
        # Fallback: watchtower, m4bwebdashboard, tun2socks
        assert "watchtower" in result

    def test_missing_file_returns_infra_fallback(self, tmp_path: Path) -> None:
        from money4band.docker.start import _extract_app_names_from_compose

        result = _extract_app_names_from_compose(str(tmp_path / "nope.yaml"))
        assert "watchtower" in result


class TestValidateEnvFiles:
    def test_unique_names_returns_true(self, tmp_path: Path) -> None:
        from money4band.docker.start import validate_env_files

        env = tmp_path / ".env"
        env.write_text("DEVICE_NAME=main_box\n")
        instances = tmp_path / "instances"
        instances.mkdir()
        (instances / "inst1").mkdir()
        (instances / "inst1" / ".env").write_text("DEVICE_NAME=proxy_box\n")
        assert validate_env_files(str(env), str(instances)) is True

    def test_duplicate_names_returns_false(self, tmp_path: Path) -> None:
        from money4band.docker.start import validate_env_files

        env = tmp_path / ".env"
        env.write_text("DEVICE_NAME=same_name\n")
        instances = tmp_path / "instances"
        instances.mkdir()
        (instances / "inst1").mkdir()
        (instances / "inst1" / ".env").write_text("DEVICE_NAME=same_name\n")
        assert validate_env_files(str(env), str(instances)) is False

    def test_missing_env_still_returns_true(self, tmp_path: Path) -> None:
        """No files = no duplicates = True."""
        from money4band.docker.start import validate_env_files

        assert (
            validate_env_files(str(tmp_path / ".env"), str(tmp_path / "nope")) is True
        )


class TestGetContainerNamesFromEnv:
    def test_extracts_names(self, tmp_path: Path) -> None:
        from money4band.docker.start import get_container_names_from_env

        env = tmp_path / ".env"
        env.write_text(
            "COMPOSE_PROJECT_NAME=m4b\n"
            "EARNAPP_CONTAINER_NAME=m4b-earnapp\n"
            "HONEYGAIN_CONTAINER_NAME=m4b-honeygain\n"
            "OTHER=val\n"
        )
        result = get_container_names_from_env(str(env))
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# fn_startStack.start_stack — fully mocked
# ---------------------------------------------------------------------------


class TestStartStack:
    @patch("money4band.docker.start.input", return_value="")
    @patch("money4band.docker.start.run_docker_command", return_value=0)
    @patch("money4band.docker.start.show_spinner")
    @patch("money4band.docker.start._notify_event")
    def test_success(self, _notify, _spinner, mock_run, _input, tmp_path: Path) -> None:
        from money4band.docker.start import start_stack

        compose = tmp_path / "docker-compose.yaml"
        compose.write_text(yaml.dump({"services": {"app": {"image": "x"}}}))
        env = tmp_path / ".env"
        env.write_text("COMPOSE_PROJECT_NAME=test\n")
        result = start_stack(str(compose), str(env), "test", skip_questions=True)
        assert result is True

    @patch("money4band.docker.start.input", return_value="")
    @patch("money4band.docker.start.run_docker_command", return_value=1)
    @patch("money4band.docker.start.show_spinner")
    @patch("money4band.docker.start._notify_event")
    def test_failure(self, _notify, _spinner, mock_run, _input, tmp_path: Path) -> None:
        from money4band.docker.start import start_stack

        compose = tmp_path / "docker-compose.yaml"
        compose.write_text(yaml.dump({"services": {"app": {"image": "x"}}}))
        env = tmp_path / ".env"
        env.write_text("COMPOSE_PROJECT_NAME=test\n")
        result = start_stack(str(compose), str(env), "test", skip_questions=True)
        assert result is False


# ---------------------------------------------------------------------------
# fn_stopStack
# ---------------------------------------------------------------------------


class TestStopStack:
    @patch("money4band.docker.stop.input", return_value="")
    @patch("money4band.docker.stop.run_docker_command", return_value=0)
    @patch("money4band.docker.stop.show_spinner")
    @patch("money4band.docker.stop._notify_event")
    def test_success(self, _notify, _spinner, mock_run, _input, tmp_path: Path) -> None:
        from money4band.docker.stop import stop_stack

        compose = tmp_path / "docker-compose.yaml"
        compose.write_text(yaml.dump({"services": {}}))
        result = stop_stack(str(compose), "test", skip_questions=True)
        assert result is True

    @patch("money4band.docker.stop.input", return_value="")
    @patch("money4band.docker.stop.run_docker_command", return_value=1)
    @patch("money4band.docker.stop.show_spinner")
    @patch("money4band.docker.stop._notify_event")
    def test_failure(self, _notify, _spinner, mock_run, _input, tmp_path: Path) -> None:
        from money4band.docker.stop import stop_stack

        compose = tmp_path / "docker-compose.yaml"
        compose.write_text(yaml.dump({"services": {}}))
        result = stop_stack(str(compose), "test", skip_questions=True)
        assert result is False


class TestStopAllStacks:
    @patch("money4band.docker.stop.input", return_value="")
    @patch("money4band.docker.stop.stop_stack", return_value=True)
    def test_stops_main_and_instances(self, mock_stop, _input, tmp_path: Path) -> None:
        from money4band.docker.stop import stop_all_stacks

        compose = tmp_path / "docker-compose.yaml"
        compose.write_text(yaml.dump({"services": {}}))
        instances = tmp_path / "instances"
        instances.mkdir()
        inst1 = instances / "inst1"
        inst1.mkdir()
        (inst1 / "docker-compose.yaml").write_text(yaml.dump({"services": {}}))
        stop_all_stacks(str(compose), "main", str(instances), skip_questions=True)
        assert mock_stop.call_count >= 1
