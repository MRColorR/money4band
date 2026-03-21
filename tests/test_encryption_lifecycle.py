"""Tests for credential encryption lifecycle (atexit/signal hooks)."""

import json
import os
import signal
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestRegisterEncryptionHooks:

    def test_registers_atexit_and_sigterm(self):
        # Import fresh to reset module state
        import main

        main._encrypt_on_exit_paths.clear()

        with (
            patch("main.atexit.register") as mock_atexit,
            patch("main.signal.signal") as mock_signal,
        ):
            main.register_encryption_hooks("/tmp/test-config.json")

        mock_atexit.assert_called_once()
        mock_signal.assert_called_once_with(signal.SIGTERM, main._sigterm_handler)
        assert "/tmp/test-config.json" in main._encrypt_on_exit_paths

        # Cleanup
        main._encrypt_on_exit_paths.clear()

    def test_idempotent_registration(self):
        import main

        main._encrypt_on_exit_paths.clear()

        with (
            patch("main.atexit.register") as mock_atexit,
            patch("main.signal.signal"),
        ):
            main.register_encryption_hooks("/tmp/test-config.json")
            main.register_encryption_hooks("/tmp/test-config.json")

        # Should only register once
        mock_atexit.assert_called_once()
        assert main._encrypt_on_exit_paths.count("/tmp/test-config.json") == 1

        main._encrypt_on_exit_paths.clear()


class TestEncryptOnExit:

    def test_encrypts_all_registered_paths(self):
        import main

        main._encrypt_on_exit_paths.clear()
        main._encrypt_on_exit_paths.extend(["/path/a.json", "/path/b.json"])

        with patch("main.ensure_config_encrypted") as mock_enc:
            main._encrypt_on_exit()

        assert mock_enc.call_count == 2
        mock_enc.assert_any_call("/path/a.json")
        mock_enc.assert_any_call("/path/b.json")

        main._encrypt_on_exit_paths.clear()

    def test_best_effort_continues_on_error(self):
        import main

        main._encrypt_on_exit_paths.clear()
        main._encrypt_on_exit_paths.extend(["/path/a.json", "/path/b.json"])

        with patch(
            "main.ensure_config_encrypted",
            side_effect=[OSError("fail"), None],
        ) as mock_enc:
            main._encrypt_on_exit()  # Should NOT raise

        assert mock_enc.call_count == 2

        main._encrypt_on_exit_paths.clear()


class TestSigtermHandler:

    def test_encrypts_and_exits(self):
        import main

        main._encrypt_on_exit_paths.clear()
        main._encrypt_on_exit_paths.append("/path/config.json")

        with (
            patch("main.ensure_config_encrypted") as mock_enc,
            pytest.raises(SystemExit) as exc_info,
        ):
            main._sigterm_handler(signal.SIGTERM, None)

        mock_enc.assert_called_once_with("/path/config.json")
        assert exc_info.value.code == 128 + signal.SIGTERM

        main._encrypt_on_exit_paths.clear()


class TestCmdConfig:

    def test_view_dispatches_to_viewer(self, tmp_path):
        import main

        args = MagicMock()
        args.config_dir = str(tmp_path)
        args.config_m4b_file = "m4b-config.json"
        args.config_app_file = "app-config.json"
        args.config_usr_file = "user-config.json"
        args.config_action = "view"

        expected = os.path.join(str(tmp_path), "user-config.json")

        with patch("utils.config_viewer.view_masked") as mock_view:
            main._cmd_config(args)

        mock_view.assert_called_once_with(expected)

    def test_edit_dispatches_to_editor(self, tmp_path):
        import main

        main._encrypt_on_exit_paths.clear()

        args = MagicMock()
        args.config_dir = str(tmp_path)
        args.config_m4b_file = "m4b-config.json"
        args.config_app_file = "app-config.json"
        args.config_usr_file = "user-config.json"
        args.config_action = "edit"

        expected = os.path.join(str(tmp_path), "user-config.json")

        with (
            patch("utils.config_viewer.edit_config") as mock_edit,
            patch("main.atexit.register"),
            patch("main.signal.signal"),
        ):
            main._cmd_config(args)

        mock_edit.assert_called_once_with(expected)

        main._encrypt_on_exit_paths.clear()

    def test_no_action_prints_usage(self, capsys):
        import main

        args = MagicMock()
        args.config_dir = "/tmp/config"
        args.config_m4b_file = "m4b-config.json"
        args.config_app_file = "app-config.json"
        args.config_usr_file = "user-config.json"
        args.config_action = None

        main._cmd_config(args)

        captured = capsys.readouterr()
        assert "config {view,edit}" in captured.out
