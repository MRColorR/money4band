"""Tests for money4band.fn_stopStack — stack stop logic."""

from __future__ import annotations

from unittest.mock import patch

from money4band.fn_stopStack import stop_all_stacks, stop_stack


class TestStopStack:
    @patch("money4band.fn_stopStack._notify_event")
    @patch("money4band.fn_stopStack.run_docker_command", return_value=0)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value="m4b")
    @patch("money4band.fn_stopStack.show_spinner")
    @patch("money4band.fn_stopStack.is_user_root", return_value=True)
    def test_successful_stop(self, _root, _spin, _proj, mock_run, _notify) -> None:
        result = stop_stack(
            compose_file="docker-compose.yaml",
            instance_name="money4band",
            skip_questions=True,
        )
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert "down" in cmd

    @patch("money4band.fn_stopStack._notify_event")
    @patch("money4band.fn_stopStack.run_docker_command", return_value=1)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value="m4b")
    @patch("money4band.fn_stopStack.show_spinner")
    @patch("money4band.fn_stopStack.is_user_root", return_value=True)
    def test_failed_stop_returns_false(
        self, _root, _spin, _proj, mock_run, _notify
    ) -> None:
        result = stop_stack(
            compose_file="docker-compose.yaml",
            skip_questions=True,
        )
        assert result is False

    @patch("money4band.fn_stopStack.ask_question_yn", return_value=False)
    @patch("builtins.input", return_value="")
    def test_user_cancels(self, _inp, _ask) -> None:
        result = stop_stack(
            compose_file="docker-compose.yaml",
            skip_questions=False,
        )
        assert result is False

    @patch("money4band.fn_stopStack._notify_event")
    @patch(
        "money4band.fn_stopStack.run_docker_command", side_effect=RuntimeError("fail")
    )
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value=None)
    @patch("money4band.fn_stopStack.show_spinner")
    @patch("money4band.fn_stopStack.is_user_root", return_value=True)
    @patch("builtins.input", return_value="")
    def test_exception_returns_false(
        self, _inp, _root, _spin, _proj, _run, _notify
    ) -> None:
        result = stop_stack(
            compose_file="docker-compose.yaml",
            skip_questions=True,
        )
        assert result is False

    @patch("money4band.fn_stopStack._notify_event")
    @patch("money4band.fn_stopStack.run_docker_command", return_value=0)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value="m4b")
    @patch("money4band.fn_stopStack.show_spinner")
    @patch("money4band.fn_stopStack.is_user_root", return_value=True)
    def test_multi_compose_files(self, _root, _spin, _proj, mock_run, _notify) -> None:
        result = stop_stack(
            compose_file=["compose.yml", "compose.service.yml"],
            skip_questions=True,
        )
        assert result is True
        cmd = mock_run.call_args[0][0]
        assert cmd.count("-f") == 2

    @patch("money4band.fn_stopStack._notify_event")
    @patch("money4band.fn_stopStack.run_docker_command", return_value=0)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value="m4b")
    @patch("money4band.fn_stopStack.show_spinner")
    @patch("money4band.fn_stopStack.is_user_root", return_value=True)
    def test_includes_all_profiles(
        self, _root, _spin, _proj, mock_run, _notify
    ) -> None:
        stop_stack(compose_file="compose.yml", skip_questions=True)
        cmd = mock_run.call_args[0][0]
        # Should include monitoring and proxy profiles (dashboard is no
        # longer a Docker service — it runs as a standalone FastAPI process).
        profile_indices = [i for i, c in enumerate(cmd) if c == "--profile"]
        profiles = [cmd[i + 1] for i in profile_indices]
        assert "monitoring" in profiles
        assert "dashboard" not in profiles
        assert "proxy" in profiles


class TestStopAllStacks:
    @patch("money4band.fn_stopStack.stop_stack", return_value=True)
    @patch("money4band.fn_stopStack.is_user_in_docker_group", return_value=True)
    @patch("builtins.input", return_value="")
    def test_stops_main_stack(self, _inp, _group, mock_stop):
        stop_all_stacks(
            main_compose_file="compose.yml",
            skip_questions=True,
        )
        mock_stop.assert_called()

    @patch("money4band.fn_stopStack.stop_stack", return_value=True)
    @patch("money4band.fn_stopStack.is_user_in_docker_group", return_value=True)
    @patch("builtins.input", return_value="")
    def test_stops_proxy_instances(self, _inp, _group, mock_stop, tmp_path):
        inst_dir = tmp_path / "instances" / "inst1"
        inst_dir.mkdir(parents=True)
        (inst_dir / "docker-compose.yaml").write_text("version: '3'\nservices: {}\n")

        stop_all_stacks(
            main_compose_file="compose.yml",
            instances_dir=str(tmp_path / "instances"),
            skip_questions=True,
        )
        # Main + 1 instance = at least 2 calls
        assert mock_stop.call_count >= 2

    @patch("money4band.fn_stopStack.ask_question_yn", return_value=False)
    @patch("builtins.input", return_value="")
    def test_user_cancels(self, _inp, _ask):
        stop_all_stacks(skip_questions=False)
        # Should return without error

    @patch("money4band.fn_stopStack.stop_stack")
    @patch("money4band.fn_stopStack.is_user_in_docker_group", return_value=True)
    @patch("builtins.input", return_value="")
    def test_instance_failure_continues(self, _inp, _group, mock_stop, tmp_path):
        """Even if an instance fails to stop, the finally block runs."""
        # First call (main) succeeds, subsequent calls raise
        mock_stop.side_effect = [True, RuntimeError("fail")]

        inst_dir = tmp_path / "instances" / "inst1"
        inst_dir.mkdir(parents=True)
        (inst_dir / "docker-compose.yaml").write_text("version: '3'\nservices: {}\n")

        # Should not raise
        stop_all_stacks(
            main_compose_file="compose.yml",
            instances_dir=str(tmp_path / "instances"),
            skip_questions=True,
        )


class TestStopStackProjectName:
    """Verify -p project_name flag is passed through to docker compose."""

    @patch("money4band.fn_stopStack.run_docker_command", return_value=0)
    @patch("money4band.fn_stopStack.is_user_root", return_value=True)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value="my-proj")
    def test_project_name_forwarded_to_compose(self, _proj, _root, mock_run) -> None:
        stop_stack("docker-compose.yaml", skip_questions=True)
        cmd = mock_run.call_args[0][0]
        # -p my-proj must appear in the command
        idx = cmd.index("-p")
        assert cmd[idx + 1] == "my-proj"

    @patch("money4band.fn_stopStack.run_docker_command", return_value=0)
    @patch("money4band.fn_stopStack.is_user_root", return_value=True)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value=None)
    def test_no_project_name_omits_p_flag(self, _proj, _root, mock_run) -> None:
        stop_stack("docker-compose.yaml", skip_questions=True)
        cmd = mock_run.call_args[0][0]
        assert "-p" not in cmd

    @patch("money4band.fn_stopStack.run_docker_command", return_value=0)
    @patch("money4band.fn_stopStack.is_user_root", return_value=True)
    @patch("money4band.fn_stopStack.get_compose_project_name", return_value=None)
    def test_all_profiles_activated(self, _proj, _root, mock_run) -> None:
        stop_stack("docker-compose.yaml", skip_questions=True)
        cmd = mock_run.call_args[0][0]
        for profile in ("monitoring", "proxy"):
            assert profile in cmd, f"profile {profile} missing from command"
        assert "dashboard" not in cmd, "dashboard profile should not be present"


class TestStopAllStacksInstances:
    """Test stop_all_stacks iterating over proxy instances."""

    @patch("money4band.fn_stopStack.stop_stack", return_value=True)
    @patch("money4band.fn_stopStack.is_user_in_docker_group", return_value=True)
    @patch("builtins.input", return_value="")
    def test_stops_each_instance(self, _inp, _group, mock_stop, tmp_path):
        """Each instance directory with a compose file should be stopped."""
        for name in ("inst1", "inst2"):
            d = tmp_path / "instances" / name
            d.mkdir(parents=True)
            (d / "docker-compose.yaml").write_text("version: '3'\nservices: {}\n")

        stop_all_stacks(
            main_compose_file="compose.yml",
            instances_dir=str(tmp_path / "instances"),
            skip_questions=True,
        )
        # Main + 2 instances = 3 calls
        assert mock_stop.call_count == 3

    @patch("money4band.fn_stopStack.stop_stack", return_value=True)
    @patch("money4band.fn_stopStack.is_user_in_docker_group", return_value=True)
    @patch("builtins.input", return_value="")
    def test_missing_instances_dir_logs_warning(self, _inp, _group, mock_stop, capsys):
        """When instances_dir doesn't exist, should log a warning and continue."""
        stop_all_stacks(
            main_compose_file="compose.yml",
            instances_dir="/nonexistent/dir",
            skip_questions=True,
        )
        # Only main stack should be stopped
        mock_stop.assert_called_once()


class TestStopStackMain:
    @patch("money4band.fn_stopStack.stop_all_stacks")
    @patch("money4band.fn_stopStack.loader.load_json_config")
    @patch("money4band.compose_builder.get_compose_files", return_value=["compose.yml"])
    @patch("money4band.fn_stopStack.cls")
    def test_main_delegates_to_stop_all(self, _cls, _get_cf, mock_load, mock_stop_all):
        from money4band.fn_stopStack import main

        mock_load.side_effect = [
            {"project": {"compose_project_name": "m4b"}},
            {"apps": {}},
        ]
        main("app.json", "m4b.json", "user.json")
        mock_stop_all.assert_called_once()

    @patch("money4band.fn_stopStack.loader.load_json_config")
    @patch("money4band.compose_builder.get_compose_files", return_value=[])
    @patch("money4band.fn_stopStack.check_required_files", return_value=True)
    @patch("money4band.fn_stopStack.cls")
    @patch("builtins.input", return_value="")
    def test_main_missing_compose_returns(
        self, _inp, _cls, mock_check, _get_cf, mock_load
    ):
        """When no compose files found, main() should return early after checking."""
        from money4band.fn_stopStack import main

        mock_load.side_effect = [
            {"project": {"compose_project_name": "m4b"}},
            {"apps": {}},
        ]
        main("app.json", "m4b.json", "user.json")
        # check_required_files should have been consulted
        mock_check.assert_called_once()
