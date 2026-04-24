"""Tests for dashboard port, start_server, and dashboard CLI orchestration."""

from __future__ import annotations

import argparse
from unittest.mock import ANY, patch

from money4band.api.server import find_dashboard_port

# ===========================================================================
# find_dashboard_port
# ===========================================================================


class TestFindDashboardPort:
    def test_returns_preferred_when_free(self):
        with patch("money4band.network.networker.is_port_in_use", return_value=False):
            assert find_dashboard_port(8088) == 8088

    def test_falls_back_when_preferred_occupied(self):
        with (
            patch(
                "money4band.network.networker.is_port_in_use",
                side_effect=lambda p: p == 8088,
            ),
            patch(
                "money4band.network.networker.find_next_available_port",
                return_value=8089,
            ),
        ):
            assert find_dashboard_port(8088) == 8089

    def test_custom_preferred_port(self):
        with patch("money4band.network.networker.is_port_in_use", return_value=False):
            assert find_dashboard_port(9000) == 9000


# ===========================================================================
# start_server — always checks port availability
# ===========================================================================


class TestStartServer:
    """start_server always resolves port and starts uvicorn."""

    def test_uses_preferred_port_when_free(self):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server._mount_frontend"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("uvicorn.run") as mock_run,
        ):
            from money4band.api.server import start_server

            start_server(port=8088)
            mock_run.assert_called_once()
            assert mock_run.call_args.kwargs["port"] == 8088

    def test_falls_back_to_next_port_when_occupied(self):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server._mount_frontend"),
            patch("money4band.api.server.find_dashboard_port", return_value=9999),
            patch("uvicorn.run") as mock_run,
        ):
            from money4band.api.server import start_server

            start_server(port=8088)
            mock_run.assert_called_once()
            assert mock_run.call_args.kwargs["port"] == 9999

    def test_binds_to_specified_host(self):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server._mount_frontend"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("uvicorn.run") as mock_run,
        ):
            from money4band.api.server import start_server

            start_server(host="0.0.0.0", port=8088)
            mock_run.assert_called_once()
            assert mock_run.call_args.kwargs["host"] == "0.0.0.0"

    def test_sets_exposed_flag_for_non_loopback(self):
        import money4band.api.server as api

        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server._mount_frontend"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("uvicorn.run"),
        ):
            api.start_server(host="0.0.0.0", port=8088)
            assert api.is_exposed() is True

    def test_exposed_false_for_localhost(self):
        import money4band.api.server as api

        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server._mount_frontend"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("uvicorn.run"),
        ):
            api.start_server(host="127.0.0.1", port=8088)
            assert api.is_exposed() is False

    def test_auto_generates_key_when_exposed_without_key(self):
        import money4band.api.server as api

        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server._mount_frontend"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("money4band.api.server.ensure_api_key", return_value=""),
            patch(
                "money4band.api.server.regenerate_api_key",
                return_value="new-key-123",
            ) as mock_regen,
            patch("uvicorn.run"),
        ):
            api.start_server(host="0.0.0.0", port=8088)
            mock_regen.assert_called_once()


# ===========================================================================
# dashboard_cli.run_dashboard_command
# ===========================================================================


class TestRunDashboardCommand:
    """Tests for the extracted dashboard CLI orchestration."""

    def test_foreground_delegates_to_start_server(self):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("money4band.api.server.start_server") as mock_start,
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk", return_value="k"
            ),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base")
            mock_start.assert_called_once_with(host="127.0.0.1", port=8088)

    def test_background_spawns_process(self):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk", return_value="k"
            ),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
            patch(
                "money4band.dashboard.setup.spawn_dashboard_background",
                return_value=12345,
            ) as mock_spawn,
            patch("money4band.network.networker.is_port_in_use", return_value=True),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", background=True)
            mock_spawn.assert_called_once()

    def test_port_fallback_prints_warning(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=8089),
            patch("money4band.api.server.start_server"),
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk", return_value="k"
            ),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", preferred_port=8088)
            captured = capsys.readouterr()
            assert "8088" in captured.out
            assert "8089" in captured.out

    def test_custom_port_used(self):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=9090),
            patch("money4band.api.server.start_server") as mock_start,
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk", return_value="k"
            ),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", preferred_port=9090)
            mock_start.assert_called_once_with(host="127.0.0.1", port=9090)

    def test_stop_kills_running_process(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=42),
            patch("money4band.dashboard.setup.remove_dashboard_pid"),
            patch("os.kill") as mock_kill,
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", stop=True)
            mock_kill.assert_called_once()
            assert "stopped" in capsys.readouterr().out.lower()

    def test_stop_no_running_dashboard(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", stop=True)
            assert "No running Dashboard" in capsys.readouterr().out

    def test_status_shows_running(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=99),
            patch(
                "money4band.core.loader.load_json_config",
                return_value={"m4b_dashboard": {"enabled": True, "port": 8088}},
            ),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", status_check=True)
            out = capsys.readouterr().out.lower()
            assert "running" in out
            assert "auto-start" in out

    def test_status_shows_not_running(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
            patch(
                "money4band.core.loader.load_json_config",
                return_value={"m4b_dashboard": {"enabled": False, "port": 8088}},
            ),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", status_check=True)
            out = capsys.readouterr().out.lower()
            assert "stopped" in out
            assert "auto-start" in out

    def test_show_key_prints_key(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk",
                return_value="secret-key-abc",
            ),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", show_key=True)
            assert "secret-key-abc" in capsys.readouterr().out

    def test_show_key_no_key(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.dashboard.setup.ensure_api_key_on_disk", return_value=""),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", show_key=True)
            assert "No API key" in capsys.readouterr().out

    def test_regenerate_key_prints_new(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch(
                "money4band.dashboard.setup.regenerate_api_key_on_disk",
                return_value="brand-new-key",
            ),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", regenerate_key=True)
            assert "brand-new-key" in capsys.readouterr().out

    def test_exposed_auto_generates_key_when_missing(self, capsys):
        """When host is non-loopback and no key exists, key is auto-generated."""
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("money4band.api.server.start_server"),
            patch("money4band.dashboard.setup.ensure_api_key_on_disk", return_value=""),
            patch(
                "money4band.dashboard.setup.regenerate_api_key_on_disk",
                return_value="auto-gen-key",
            ) as mock_regen,
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", host="0.0.0.0")
            mock_regen.assert_called_once()
            out = capsys.readouterr().out
            assert "generating" in out.lower()

    def test_exposed_shows_security_warning(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("money4band.api.server.start_server"),
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk",
                return_value="my-key",
            ),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", host="0.0.0.0")
            out = capsys.readouterr().out
            assert "WARNING" in out
            assert "Bearer" in out

    def test_localhost_no_security_warning(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("money4band.api.server.start_server"),
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk",
                return_value="my-key",
            ),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", host="127.0.0.1")
            out = capsys.readouterr().out
            assert "WARNING" not in out

    def test_background_already_running_refuses(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk", return_value="k"
            ),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=999),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base", background=True)
            out = capsys.readouterr().out
            assert "already running" in out.lower()

    def test_startup_prints_urls(self, capsys):
        with (
            patch("money4band.api.server.configure"),
            patch("money4band.api.server.find_dashboard_port", return_value=8088),
            patch("money4band.api.server.start_server"),
            patch(
                "money4band.dashboard.setup.ensure_api_key_on_disk",
                return_value="my-key",
            ),
            patch("money4band.dashboard.setup.read_dashboard_pid", return_value=None),
        ):
            from money4band.dashboard.cli import run_dashboard_command

            run_dashboard_command("config", "base")
            out = capsys.readouterr().out
            assert "http://localhost:8088/" in out
            assert "/api/docs" in out
            assert "/api/status" in out
            assert "my-key" in out


# ===========================================================================
# _cmd_dashboard (thin main.py wrapper)
# ===========================================================================


class TestCmdDashboard:
    """Verify main._cmd_dashboard delegates to run_dashboard_command."""

    def test_bare_dashboard_shows_help(self, capsys):
        """Bare `m4b dashboard` should print usage, not start the server."""
        from main import _cmd_dashboard

        args = argparse.Namespace(
            config_dir="config",
            dashboard_action=None,
        )
        _cmd_dashboard(args)
        out = capsys.readouterr().out
        assert "Commands:" in out
        assert "start" in out

    def test_start_delegates_to_dashboard_cli(self):
        with patch("money4band.dashboard.cli.run_dashboard_command") as mock_run:
            from main import _cmd_dashboard

            args = argparse.Namespace(
                config_dir="config",
                dashboard_action="start",
                port=8088,
                host="127.0.0.1",
                background=False,
            )
            _cmd_dashboard(args)
            mock_run.assert_called_once_with(
                config_dir="config",
                base_dir=ANY,
                host="127.0.0.1",
                preferred_port=8088,
                background=False,
            )

    def test_stop_delegates_to_dashboard_cli(self):
        with patch("money4band.dashboard.cli.run_dashboard_command") as mock_run:
            from main import _cmd_dashboard

            args = argparse.Namespace(
                config_dir="config",
                dashboard_action="stop",
            )
            _cmd_dashboard(args)
            mock_run.assert_called_once_with(
                config_dir="config",
                base_dir=ANY,
                stop=True,
            )

    def test_status_delegates_to_dashboard_cli(self):
        with patch("money4band.dashboard.cli.run_dashboard_command") as mock_run:
            from main import _cmd_dashboard

            args = argparse.Namespace(
                config_dir="config",
                dashboard_action="status",
            )
            _cmd_dashboard(args)
            mock_run.assert_called_once_with(
                config_dir="config",
                base_dir=ANY,
                status_check=True,
            )
