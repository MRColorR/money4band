"""Tests for money4band.fn_startStack — stack start logic."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from money4band.fn_startStack import (
    _extract_app_names_from_compose,
    get_container_names_from_env,
    get_device_name_from_env,
    start_all_stacks,
    start_stack,
    validate_env_files,
)


class TestGetDeviceNameFromEnv:
    def test_reads_device_name(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("OTHER=val\nDEVICE_NAME=happy_cat\nMORE=x\n")
        assert get_device_name_from_env(str(env)) == "happy_cat"

    def test_missing_key_returns_none(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("OTHER=val\n")
        assert get_device_name_from_env(str(env)) is None

    def test_missing_file_returns_none(self, tmp_path: Path) -> None:
        assert get_device_name_from_env(str(tmp_path / "no.env")) is None

    def test_equals_in_value(self, tmp_path: Path) -> None:
        env = tmp_path / ".env"
        env.write_text("DEVICE_NAME=name=with=equals\n")
        assert get_device_name_from_env(str(env)) == "name=with=equals"


class TestStartStack:
    @patch("money4band.fn_startStack._notify_event")
    @patch("money4band.fn_startStack.run_docker_command", return_value=0)
    @patch("money4band.fn_startStack.get_compose_project_name", return_value="m4b")
    @patch("money4band.fn_startStack.show_spinner")
    @patch("money4band.fn_startStack.is_user_root", return_value=True)
    def test_successful_start(self, _root, _spin, _proj, mock_run, _notify) -> None:
        result = start_stack(
            compose_file="docker-compose.yaml",
            env_file=".env",
            instance_name="money4band",
            skip_questions=True,
        )
        assert result is True
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "up" in cmd
        assert "-d" in cmd

    @patch("money4band.fn_startStack._notify_event")
    @patch("money4band.fn_startStack.run_docker_command", return_value=1)
    @patch("money4band.fn_startStack.get_compose_project_name", return_value="m4b")
    @patch("money4band.fn_startStack.show_spinner")
    @patch("money4band.fn_startStack.is_user_root", return_value=True)
    @patch("builtins.input", return_value="")
    def test_failed_start_returns_false(
        self, _inp, _root, _spin, _proj, mock_run, _notify
    ) -> None:
        result = start_stack(
            compose_file="docker-compose.yaml",
            env_file=".env",
            skip_questions=True,
        )
        assert result is False

    @patch("money4band.fn_startStack.ask_question_yn", return_value=False)
    @patch("builtins.input", return_value="")
    def test_user_cancels(self, _inp, _ask) -> None:
        result = start_stack(
            compose_file="docker-compose.yaml",
            env_file=".env",
            skip_questions=False,
        )
        assert result is False

    @patch("money4band.fn_startStack._notify_event")
    @patch(
        "money4band.fn_startStack.run_docker_command",
        side_effect=RuntimeError("docker not found"),
    )
    @patch("money4band.fn_startStack.get_compose_project_name", return_value=None)
    @patch("money4band.fn_startStack.show_spinner")
    @patch("money4band.fn_startStack.is_user_root", return_value=True)
    @patch("builtins.input", return_value="")
    def test_exception_returns_false(
        self, _inp, _root, _spin, _proj, _run, _notify
    ) -> None:
        result = start_stack(
            compose_file="docker-compose.yaml",
            env_file=".env",
            skip_questions=True,
        )
        assert result is False

    @patch("money4band.fn_startStack._notify_event")
    @patch("money4band.fn_startStack.run_docker_command", return_value=0)
    @patch("money4band.fn_startStack.get_compose_project_name", return_value="m4b")
    @patch("money4band.fn_startStack.show_spinner")
    @patch("money4band.fn_startStack.is_user_root", return_value=True)
    def test_multi_compose_files(self, _root, _spin, _proj, mock_run, _notify) -> None:
        result = start_stack(
            compose_file=["compose.yml", "compose.service.yml"],
            env_file=".env",
            skip_questions=True,
        )
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert cmd.count("-f") == 2

    @patch("money4band.fn_startStack._notify_event")
    @patch("money4band.fn_startStack.run_docker_command", return_value=0)
    @patch("money4band.fn_startStack.get_compose_project_name", return_value="m4b")
    @patch("money4band.fn_startStack.show_spinner")
    @patch("money4band.fn_startStack.is_user_root", return_value=True)
    def test_passes_profiles(self, _root, _spin, _proj, mock_run, _notify) -> None:
        result = start_stack(
            compose_file="compose.yml",
            env_file=".env",
            skip_questions=True,
            profiles=("monitoring", "dashboard"),
        )
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "--profile" in cmd
        idx = cmd.index("--profile")
        assert cmd[idx + 1] == "monitoring"


class TestStartAllStacks:
    @patch("money4band.fn_startStack.generate_container_url_list")
    @patch("money4band.fn_startStack.start_stack", return_value=True)
    @patch("money4band.fn_startStack.is_user_in_docker_group", return_value=True)
    @patch("money4band.fn_startStack.ask_question_yn", return_value=True)
    @patch("subprocess.run")
    @patch("builtins.input", return_value="")
    @patch("time.sleep")
    def test_starts_main_stack(
        self, _sleep, _inp, mock_sub_run, _ask, _group, mock_start, _dashurls
    ):
        mock_sub_run.return_value = MagicMock(stdout="", returncode=0)

        start_all_stacks(
            main_compose_file="compose.yml",
            main_env_file=".env",
            skip_questions=True,
        )
        mock_start.assert_called()

    @patch("money4band.fn_startStack.generate_container_url_list")
    @patch("money4band.fn_startStack.start_stack", return_value=True)
    @patch("money4band.fn_startStack.is_user_in_docker_group", return_value=True)
    @patch("subprocess.run")
    @patch("builtins.input", return_value="")
    @patch("time.sleep")
    def test_starts_proxy_instances(
        self, _sleep, _inp, mock_sub_run, _group, mock_start, _dashurls, tmp_path
    ):
        mock_sub_run.return_value = MagicMock(stdout="", returncode=0)

        # Create instances dir with one instance
        inst_dir = tmp_path / "instances" / "inst1"
        inst_dir.mkdir(parents=True)
        (inst_dir / ".env").write_text("DEVICE_NAME=test1\n")
        (inst_dir / "docker-compose.yaml").write_text("version: '3'\nservices: {}\n")

        # Create main env
        main_env = tmp_path / ".env"
        main_env.write_text("DEVICE_NAME=main_dev\n")

        start_all_stacks(
            main_compose_file="compose.yml",
            main_env_file=str(main_env),
            instances_dir=str(tmp_path / "instances"),
            skip_questions=True,
        )
        # Main + 1 instance = at least 2 calls
        assert mock_start.call_count >= 2

    @patch("money4band.fn_startStack.ask_question_yn", return_value=False)
    @patch("builtins.input", return_value="")
    def test_user_cancels(self, _inp, _ask):
        start_all_stacks(skip_questions=False)
        # Should return without error


class TestGetContainerNamesFromEnv:
    def test_extracts_names(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("DEVICE_NAME=mydev\n")

        compose = tmp_path / "docker-compose.yaml"
        compose.write_text("version: '3'\nservices:\n  app1: {}\n  app2: {}\n")

        names = get_container_names_from_env(str(env))
        assert "mydev_app1" in names
        assert "mydev_app2" in names

    def test_missing_device_name(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text("OTHER=val\n")
        assert get_container_names_from_env(str(env)) == []


class TestExtractAppNamesFromCompose:
    def test_returns_service_names(self, tmp_path):
        compose = tmp_path / "docker-compose.yaml"
        compose.write_text("version: '3'\nservices:\n  web: {}\n  db: {}\n")
        names = _extract_app_names_from_compose(str(compose))
        assert "web" in names
        assert "db" in names

    def test_missing_file_returns_infra_fallback(self):
        names = _extract_app_names_from_compose("/nonexistent/compose.yaml")
        assert "watchtower" in names
        assert "tun2socks" in names
        assert "m4bwebdashboard" not in names

    def test_multi_file_merges_services(self, tmp_path):
        c1 = tmp_path / "a.yaml"
        c1.write_text("version: '3'\nservices:\n  alpha: {}\n")
        c2 = tmp_path / "b.yaml"
        c2.write_text("version: '3'\nservices:\n  beta: {}\n")
        names = _extract_app_names_from_compose([str(c1), str(c2)])
        assert "alpha" in names
        assert "beta" in names


class TestStartAllStacksForceClean:
    @patch("money4band.fn_startStack.generate_container_url_list")
    @patch("money4band.fn_startStack.start_stack", return_value=True)
    @patch("money4band.fn_startStack.is_user_in_docker_group", return_value=True)
    @patch("subprocess.run")
    @patch("builtins.input", return_value="")
    @patch("time.sleep")
    def test_force_clean_stops_containers_first(
        self, _sleep, _inp, mock_sub_run, _group, mock_start, _dashurls, tmp_path
    ):
        """force_clean=True should run 'docker ps -q' then 'docker stop' before starting."""
        main_env = tmp_path / ".env"
        main_env.write_text("DEVICE_NAME=dev1\n")

        # First ps call returns container IDs, second ps returns running names
        mock_sub_run.side_effect = [
            MagicMock(stdout="abc123\ndef456\n", returncode=0),  # docker ps -q
            MagicMock(returncode=0),  # docker stop abc123 def456
            MagicMock(stdout="", returncode=0),  # docker ps --format
        ]
        start_all_stacks(
            main_compose_file="compose.yml",
            main_env_file=str(main_env),
            skip_questions=True,
            force_clean=True,
        )
        # Verify docker stop was called with the container IDs
        stop_call = mock_sub_run.call_args_list[1]
        assert "stop" in stop_call[0][0]
        assert "abc123" in stop_call[0][0]


class TestStartAllStacksConflictDetection:
    @patch("money4band.fn_startStack.generate_container_url_list")
    @patch("money4band.fn_startStack.start_stack", return_value=True)
    @patch("money4band.fn_startStack.is_user_in_docker_group", return_value=True)
    @patch("subprocess.run")
    @patch("builtins.input", return_value="")
    @patch("time.sleep")
    def test_duplicate_device_names_detected(
        self,
        _sleep,
        _inp,
        mock_sub_run,
        _group,
        mock_start,
        _dashurls,
        tmp_path,
        capsys,
    ):
        """Two instances with the same DEVICE_NAME should trigger a conflict warning."""
        mock_sub_run.return_value = MagicMock(stdout="", returncode=0)

        main_env = tmp_path / ".env"
        main_env.write_text("DEVICE_NAME=same_name\n")
        (tmp_path / "docker-compose.yaml").write_text(
            "version: '3'\nservices:\n  app1: {}\n"
        )

        # Create an instance with the same device name
        inst = tmp_path / "instances" / "inst1"
        inst.mkdir(parents=True)
        (inst / ".env").write_text("DEVICE_NAME=same_name\n")
        (inst / "docker-compose.yaml").write_text(
            "version: '3'\nservices:\n  app1: {}\n"
        )

        start_all_stacks(
            main_compose_file="compose.yml",
            main_env_file=str(main_env),
            instances_dir=str(tmp_path / "instances"),
            skip_questions=True,
        )
        captured = capsys.readouterr()
        assert "Duplicate" in captured.out or "conflict" in captured.out.lower()


class TestStartAllStacksRunningContainerWarning:
    @patch("money4band.fn_startStack.generate_container_url_list")
    @patch("money4band.fn_startStack.start_stack", return_value=True)
    @patch("money4band.fn_startStack.is_user_in_docker_group", return_value=True)
    @patch("subprocess.run")
    @patch("builtins.input", return_value="")
    @patch("time.sleep")
    def test_warns_about_existing_containers(
        self,
        _sleep,
        _inp,
        mock_sub_run,
        _group,
        mock_start,
        _dashurls,
        tmp_path,
        capsys,
    ):
        """Running containers should produce a warning listing their names."""
        main_env = tmp_path / ".env"
        main_env.write_text("DEVICE_NAME=mydev\n")

        mock_sub_run.return_value = MagicMock(
            stdout="existing_container_1\nexisting_container_2\n", returncode=0
        )
        start_all_stacks(
            main_compose_file="compose.yml",
            main_env_file=str(main_env),
            skip_questions=True,
        )
        captured = capsys.readouterr()
        assert "existing_container_1" in captured.out
        assert "2 running containers" in captured.out


class TestStartStackMain:
    @patch("money4band.fn_startStack.start_all_stacks")
    @patch("money4band.fn_startStack.loader.load_json_config")
    @patch("money4band.compose_builder.get_compose_files", return_value=["compose.yml"])
    @patch("money4band.fn_startStack.cls")
    @patch("os.path.isfile", return_value=True)
    def test_main_delegates_to_start_all_stacks(
        self, _isfile, _cls, _get_cf, mock_load, mock_start_all
    ):
        from money4band.fn_startStack import main

        mock_load.side_effect = [
            {"project": {"compose_project_name": "m4b"}},  # m4b_config
            {"apps": {}},  # user_config
        ]
        with patch(
            "money4band.helper.get_active_profiles", return_value=["monitoring"]
        ):
            main("app.json", "m4b.json", "user.json")
        mock_start_all.assert_called_once()
        call_kwargs = mock_start_all.call_args
        assert call_kwargs[1].get("profiles") == (
            "monitoring",
        ) or "monitoring" in call_kwargs[1].get("profiles", ())

    @patch("money4band.fn_startStack.loader.load_json_config")
    @patch("money4band.compose_builder.get_compose_files", return_value=[])
    @patch("money4band.fn_startStack.cls")
    @patch("os.path.isfile", return_value=False)
    @patch("builtins.input", return_value="")
    def test_main_missing_files_warns(
        self, _inp, _isfile, _cls, _get_cf, mock_load, capsys
    ):
        from money4band.fn_startStack import main

        mock_load.return_value = {"project": {"compose_project_name": "m4b"}}
        main("app.json", "m4b.json", "user.json")
        captured = capsys.readouterr()
        assert "Cannot start" in captured.out or "missing" in captured.out.lower()

    def test_missing_file(self, tmp_path):
        assert get_container_names_from_env(str(tmp_path / "no.env")) == []


class TestValidateEnvFiles:
    def test_unique_names_pass(self, tmp_path):
        main_env = tmp_path / ".env"
        main_env.write_text("DEVICE_NAME=main_dev\n")

        inst_dir = tmp_path / "instances" / "inst1"
        inst_dir.mkdir(parents=True)
        (inst_dir / ".env").write_text("DEVICE_NAME=inst1_dev\n")

        assert validate_env_files(str(main_env), str(tmp_path / "instances")) is True

    def test_duplicate_names_fail(self, tmp_path):
        main_env = tmp_path / ".env"
        main_env.write_text("DEVICE_NAME=same_dev\n")

        inst_dir = tmp_path / "instances" / "inst1"
        inst_dir.mkdir(parents=True)
        (inst_dir / ".env").write_text("DEVICE_NAME=same_dev\n")

        assert validate_env_files(str(main_env), str(tmp_path / "instances")) is False
