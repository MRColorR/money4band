"""Tests for CLI subcommand parsing, dispatch, and handler correctness.

These tests verify:
- Parser construction and subcommand routing
- That each handler passes the *correct config paths* (not just "was called")
- Auto-backup is triggered on destructive commands and NOT on non-destructive ones
- Edge cases: unknown subcommands, malformed flags, empty argv
- get_active_profiles logic with various partial/mangled configs
"""

import argparse
import os
import sys
import types

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_main(monkeypatch, tmp_path):
    """Ensure main module can be imported without side-effects."""
    monkeypatch.setattr("os.chdir", lambda _: None)
    monkeypatch.setattr("main.BASE_DIR", str(tmp_path))


def _make_args(tmp_path, command=None, extra_argv=None):
    """Build parsed args from argv, pointing --config-dir at tmp_path."""
    from main import _build_parser

    argv = ["--config-dir", str(tmp_path)]
    if extra_argv:
        argv.extend(extra_argv)
    if command:
        argv.append(command)
    return _build_parser().parse_args(argv)


def _capture_module_call(monkeypatch, module_path):
    """Replace a module with a fake that records call arguments.

    Returns the ``captured`` dict — after the handler runs,
    ``captured["args"]`` holds the positional args tuple.
    """
    captured: dict = {}
    fake = types.ModuleType(module_path)
    fake.main = lambda *a, **kw: captured.update(args=a, kwargs=kw)
    monkeypatch.setitem(sys.modules, module_path, fake)
    return captured


# ---------------------------------------------------------------------------
# Parser construction
# ---------------------------------------------------------------------------

class TestBuildParser:

    def test_all_subcommands_present(self):
        from main import _build_parser

        parser = _build_parser()
        sub_action = next(
            a for a in parser._subparsers._group_actions
            if isinstance(a, argparse._SubParsersAction)
        )
        expected = {
            "setup", "start", "stop", "status",
            "generate", "links", "reset", "proxy",
            "backup", "restore", "update", "config",
            "limit", "ip", "info", "dns",
        }
        assert set(sub_action.choices.keys()) == expected

    def test_no_subcommand_gives_none(self):
        from main import _build_parser

        assert _build_parser().parse_args([]).command is None

    def test_global_flags_propagate_through_subcommand(self):
        from main import _build_parser

        args = _build_parser().parse_args(
            ["--log-level", "DEBUG", "--config-dir", "/tmp/x", "stop"]
        )
        assert args.log_level == "DEBUG"
        assert args.config_dir == "/tmp/x"
        assert args.command == "stop"

    def test_unknown_subcommand_raises(self):
        from main import _build_parser

        with pytest.raises(SystemExit):
            _build_parser().parse_args(["nonexistent"])


# ---------------------------------------------------------------------------
# Dispatch table integrity
# ---------------------------------------------------------------------------

class TestDispatchTable:

    def test_dispatch_keys_match_parser_subcommands(self):
        """Every subcommand in the parser has a matching dispatch entry and vice-versa."""
        from main import _SUBCOMMAND_DISPATCH, _build_parser

        parser = _build_parser()
        sub_action = next(
            a for a in parser._subparsers._group_actions
            if isinstance(a, argparse._SubParsersAction)
        )
        assert set(_SUBCOMMAND_DISPATCH.keys()) == set(sub_action.choices.keys())


# ---------------------------------------------------------------------------
# _resolve_paths — verify custom config dir + filenames propagate
# ---------------------------------------------------------------------------

class TestResolvePaths:

    def test_default_filenames(self, tmp_path):
        from main import _resolve_paths

        args = _make_args(tmp_path)
        m4b, apps, user = _resolve_paths(args)
        assert os.path.basename(m4b) == "m4b-config.json"
        assert os.path.basename(apps) == "app-config.json"
        assert os.path.basename(user) == "user-config.json"
        # All must share the same directory
        assert os.path.dirname(m4b) == os.path.dirname(apps) == os.path.dirname(user)

    def test_custom_config_dir_reflected(self, tmp_path):
        from main import _resolve_paths

        custom = tmp_path / "my_cfg"
        args = _make_args(tmp_path, extra_argv=["--config-dir", str(custom)])
        m4b, _, _ = _resolve_paths(args)
        assert os.path.dirname(m4b) == str(custom)


# ---------------------------------------------------------------------------
# Handler argument correctness — the core regression tests
# Each handler must pass the right config paths in the right order.
# ---------------------------------------------------------------------------

class TestHandlerArguments:
    """Verify handlers forward the correct (apps, m4b, user) paths to downstream modules."""

    @pytest.fixture(autouse=True)
    def _noop_user_config(self, monkeypatch):
        monkeypatch.setattr("main._ensure_user_config", lambda *a, **kw: None)
        monkeypatch.setattr("main._auto_backup", lambda *a, **kw: None)
        monkeypatch.setattr("main._has_template_defaults", lambda *a, **kw: False)
        monkeypatch.setattr(
            "utils.helper.check_docker_ready", lambda *a, **kw: None
        )

    def test_setup_passes_apps_m4b_user_paths(self, monkeypatch, tmp_path):
        captured = _capture_module_call(monkeypatch, "utils.fn_setupApps")
        from main import _cmd_setup
        _cmd_setup(_make_args(tmp_path, "setup"))

        a, m, u = captured["args"]
        assert a.endswith("app-config.json")
        assert m.endswith("m4b-config.json")
        assert u.endswith("user-config.json")
        # The dir portion must match --config-dir
        assert str(tmp_path) in a

    def test_start_passes_apps_m4b_user_paths(self, monkeypatch, tmp_path):
        captured = _capture_module_call(monkeypatch, "utils.fn_startStack")
        from main import _cmd_start
        _cmd_start(_make_args(tmp_path, "start"))

        a, m, u = captured["args"]
        assert a.endswith("app-config.json")
        assert m.endswith("m4b-config.json")
        assert u.endswith("user-config.json")

    def test_stop_passes_apps_m4b_user_paths(self, monkeypatch, tmp_path):
        captured = _capture_module_call(monkeypatch, "utils.fn_stopStack")
        from main import _cmd_stop
        _cmd_stop(_make_args(tmp_path, "stop"))

        a, m, u = captured["args"]
        assert a.endswith("app-config.json")
        assert m.endswith("m4b-config.json")
        assert u.endswith("user-config.json")

    def test_generate_passes_apps_m4b_user_paths(self, monkeypatch, tmp_path):
        captured = _capture_module_call(monkeypatch, "utils.generator")
        from main import _cmd_generate
        _cmd_generate(_make_args(tmp_path, "generate"))

        a, m, u = captured["args"]
        assert a.endswith("app-config.json")
        assert m.endswith("m4b-config.json")
        assert u.endswith("user-config.json")

    def test_links_passes_apps_m4b_user_paths(self, monkeypatch, tmp_path):
        captured = _capture_module_call(monkeypatch, "utils.fn_app_catalog")
        from main import _cmd_links
        _cmd_links(_make_args(tmp_path, "links"))

        a, m, u = captured["args"]
        assert a.endswith("app-config.json")
        assert m.endswith("m4b-config.json")
        assert u.endswith("user-config.json")

    def test_proxy_passes_apps_m4b_user_paths(self, monkeypatch, tmp_path):
        captured = _capture_module_call(monkeypatch, "utils.fn_multiproxy_tools")
        from main import _cmd_proxy
        _cmd_proxy(_make_args(tmp_path, "proxy"))

        a, m, u = captured["args"]
        assert a.endswith("app-config.json")
        assert m.endswith("m4b-config.json")
        assert u.endswith("user-config.json")

    def test_status_no_compose_file_warns(self, monkeypatch, tmp_path, capsys):
        monkeypatch.setattr("main.BASE_DIR", str(tmp_path))
        from main import _cmd_status
        _cmd_status(_make_args(tmp_path, "status"))
        assert "No compose files found" in capsys.readouterr().out

    def test_update_passes_m4b_config_to_checker(self, monkeypatch, tmp_path):
        received = {}
        monkeypatch.setattr(
            "main.loader.load_json_config",
            lambda p: {"_loaded_from": p, "project": {"project_version": "5.0.0"}},
        )
        monkeypatch.setattr(
            "utils.updater.check_for_update",
            lambda cfg: (received.update(cfg=cfg), None)[1],
        )
        from main import _cmd_update
        _cmd_update(_make_args(tmp_path, "update"))
        assert received["cfg"]["_loaded_from"].endswith("m4b-config.json")


# ---------------------------------------------------------------------------
# Auto-backup: destructive commands (setup, generate, reset) must trigger it;
# non-destructive commands (start, stop, links) must NOT.
# ---------------------------------------------------------------------------

class TestAutoBackup:

    def _run_handler(self, monkeypatch, tmp_path, handler_name, module_path=None):
        """Run a handler and return whether _auto_backup was invoked."""
        backup_called = {"yes": False}

        monkeypatch.setattr("main._ensure_user_config", lambda *a, **kw: None)
        monkeypatch.setattr(
            "main._auto_backup",
            lambda path: backup_called.update(yes=True, path=path),
        )
        if module_path:
            _capture_module_call(monkeypatch, module_path)

        import main
        handler = getattr(main, handler_name)
        handler(_make_args(tmp_path, handler_name.replace("_cmd_", "")))
        return backup_called

    def test_setup_triggers_auto_backup(self, monkeypatch, tmp_path):
        result = self._run_handler(monkeypatch, tmp_path, "_cmd_setup", "utils.fn_setupApps")
        assert result["yes"], "_auto_backup must be called before setup"
        assert result["path"].endswith("user-config.json")

    def test_generate_triggers_auto_backup(self, monkeypatch, tmp_path):
        result = self._run_handler(monkeypatch, tmp_path, "_cmd_generate", "utils.generator")
        assert result["yes"], "_auto_backup must be called before generate"

    def test_reset_triggers_auto_backup(self, monkeypatch, tmp_path):
        monkeypatch.setattr("main.reset_main", lambda **kw: None)
        result = self._run_handler(monkeypatch, tmp_path, "_cmd_reset")
        assert result["yes"], "_auto_backup must be called before reset"

    def test_start_does_not_trigger_auto_backup(self, monkeypatch, tmp_path):
        result = self._run_handler(monkeypatch, tmp_path, "_cmd_start", "utils.fn_startStack")
        assert not result["yes"], "start must NOT auto-backup"

    def test_stop_does_not_trigger_auto_backup(self, monkeypatch, tmp_path):
        result = self._run_handler(monkeypatch, tmp_path, "_cmd_stop", "utils.fn_stopStack")
        assert not result["yes"], "stop must NOT auto-backup"

    def test_links_does_not_trigger_auto_backup(self, monkeypatch, tmp_path):
        result = self._run_handler(monkeypatch, tmp_path, "_cmd_links", "utils.fn_app_catalog")
        assert not result["yes"], "links must NOT auto-backup"


# ---------------------------------------------------------------------------
# Main entry point dispatch
# ---------------------------------------------------------------------------

class TestMainDispatch:

    def test_no_args_dispatches_to_menu(self, monkeypatch):
        called = {}
        monkeypatch.setattr("sys.argv", ["m4b"])
        monkeypatch.setattr("main._cmd_menu", lambda a: called.update(yes=True))
        monkeypatch.setattr("main._setup_logging", lambda a: None)

        from main import main
        main()
        assert called.get("yes")

    def test_subcommand_dispatches_via_table(self, monkeypatch):
        called = {}
        monkeypatch.setattr("sys.argv", ["m4b", "stop"])
        monkeypatch.setattr("main._setup_logging", lambda a: None)
        monkeypatch.setitem(
            __import__("main")._SUBCOMMAND_DISPATCH,
            "stop",
            lambda a: called.update(yes=True, command=a.command),
        )
        from main import main
        main()
        assert called.get("yes")
        assert called["command"] == "stop"


# ---------------------------------------------------------------------------
# get_active_profiles — real logic, varied inputs
# ---------------------------------------------------------------------------

class TestGetActiveProfiles:

    def test_all_disabled(self):
        from utils.helper import get_active_profiles

        cfg = {
            "watchtower": {"enabled": False},
            "m4b_dashboard": {"enabled": False},
            "proxies": {"enabled": False},
        }
        assert get_active_profiles(cfg) == []

    def test_all_enabled(self):
        from utils.helper import get_active_profiles

        cfg = {
            "watchtower": {"enabled": True},
            "m4b_dashboard": {"enabled": True},
            "proxies": {"enabled": True},
        }
        assert get_active_profiles(cfg) == ["monitoring", "dashboard", "proxy"]

    def test_monitoring_only(self):
        from utils.helper import get_active_profiles

        cfg = {
            "watchtower": {"enabled": True},
            "m4b_dashboard": {"enabled": False},
            "proxies": {"enabled": False},
        }
        assert get_active_profiles(cfg) == ["monitoring"]

    def test_empty_config_defaults_watchtower_on(self):
        """Watchtower defaults to enabled when key is missing entirely."""
        from utils.helper import get_active_profiles

        assert get_active_profiles({}) == ["monitoring"]

    def test_partial_config_missing_nested_enabled_key(self):
        """A section present but missing 'enabled' falls back to default."""
        from utils.helper import get_active_profiles

        cfg = {"watchtower": {}, "m4b_dashboard": {}, "proxies": {}}
        # watchtower defaults to True, others default to False
        assert get_active_profiles(cfg) == ["monitoring"]

    def test_profile_order_is_stable(self):
        """Profiles always come out in monitoring → dashboard → proxy order."""
        from utils.helper import get_active_profiles

        cfg = {
            "proxies": {"enabled": True},
            "m4b_dashboard": {"enabled": True},
            "watchtower": {"enabled": True},
        }
        assert get_active_profiles(cfg) == ["monitoring", "dashboard", "proxy"]
