"""Tests for config_viewer"""

import json
import subprocess
from unittest.mock import patch

from money4band.core.viewer import _mask_dict, _mask_value, edit_config, view_masked


class TestMaskValue:
    def test_short_string_fully_masked(self):
        assert _mask_value("ab") == "****"
        assert _mask_value("abcd") == "****"

    def test_longer_string_preserves_ends(self):
        assert _mask_value("hello@world.com") == "he****om"

    def test_uuid_masked(self):
        result = _mask_value("550e8400-e29b-41d4-a716-446655440000")
        assert result.startswith("55")
        assert result.endswith("00")
        assert "****" in result


class TestMaskDict:
    def test_masks_string_credential_values(self):
        data = {"apps": {"honeygain": {"email": "user@example.com", "enabled": True}}}
        masked = _mask_dict(data)
        assert masked["apps"]["honeygain"]["email"] == "us****om"
        assert masked["apps"]["honeygain"]["enabled"] is True

    def test_preserves_safe_keys(self):
        data = {"name": "my-device", "category": "supported"}
        masked = _mask_dict(data)
        assert masked["name"] == "my-device"
        assert masked["category"] == "supported"

    def test_preserves_non_string_values(self):
        data = {"port": 8080, "enabled": False, "tags": ["a", "b"]}
        masked = _mask_dict(data)
        assert masked["port"] == 8080
        assert masked["enabled"] is False
        assert masked["tags"] == ["a", "b"]

    def test_nested_dict_masked(self):
        data = {"apps": {"app1": {"token": "secret-token-value"}}}
        masked = _mask_dict(data)
        assert "****" in masked["apps"]["app1"]["token"]


class TestViewMasked:
    def test_missing_file(self, capsys):
        view_masked("/nonexistent/path.json")
        captured = capsys.readouterr()
        assert "Config not found" in captured.out

    def test_displays_masked_config(self, tmp_path, capsys):
        cfg = {"apps": {"honeygain": {"email": "test@example.com", "enabled": True}}}
        config_file = tmp_path / "user-config.json"
        config_file.write_text(json.dumps(cfg))

        with patch("money4band.core.viewer.load_json_config", return_value=cfg):
            view_masked(str(config_file))

        captured = capsys.readouterr()
        assert "credentials masked" in captured.out
        assert "te****om" in captured.out
        assert "test@example.com" not in captured.out


class TestEditConfig:
    def test_missing_file(self, capsys):
        edit_config("/nonexistent/path.json")
        captured = capsys.readouterr()
        assert "Config not found" in captured.out

    def test_editor_failure_leaves_config_unchanged(self, tmp_path, capsys):
        cfg = {"apps": {"honeygain": {"email": "test@example.com"}}}
        config_file = tmp_path / "user-config.json"
        config_file.write_text(json.dumps(cfg))

        with (
            patch("money4band.core.viewer.load_json_config", return_value=cfg),
            patch(
                "money4band.core.viewer.subprocess.run",
                return_value=subprocess.CompletedProcess(args=[], returncode=1),
            ),
        ):
            edit_config(str(config_file))

        captured = capsys.readouterr()
        assert "error" in captured.out.lower()
        # Original config should be unchanged
        assert json.loads(config_file.read_text()) == cfg

    def test_successful_edit_writes_back(self, tmp_path, capsys):
        cfg = {"apps": {"honeygain": {"email": "old@example.com"}}}
        edited = {"apps": {"honeygain": {"email": "new@example.com"}}}
        config_file = tmp_path / "user-config.json"
        config_file.write_text(json.dumps(cfg))

        def fake_editor(cmd):
            """Simulate editor modifying the temp file."""
            tmp_file = cmd[1]
            with open(tmp_file, "w") as f:
                json.dump(edited, f)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with (
            patch("money4band.core.viewer.load_json_config", return_value=cfg),
            patch("money4band.core.viewer.subprocess.run", side_effect=fake_editor),
            patch("money4band.core.dumper.write_json") as mock_write,
            patch("money4band.core.viewer.ensure_config_encrypted"),
        ):
            edit_config(str(config_file))

        captured = capsys.readouterr()
        assert "updated and encrypted" in captured.out.lower()
        mock_write.assert_called_once_with(edited, str(config_file))

    def test_invalid_json_after_edit(self, tmp_path, capsys):
        cfg = {"key": "value"}
        config_file = tmp_path / "user-config.json"
        config_file.write_text(json.dumps(cfg))

        def corrupt_editor(cmd):
            tmp_file = cmd[1]
            with open(tmp_file, "w") as f:
                f.write("{not valid json")
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with (
            patch("money4band.core.viewer.load_json_config", return_value=cfg),
            patch("money4band.core.viewer.subprocess.run", side_effect=corrupt_editor),
        ):
            edit_config(str(config_file))

        captured = capsys.readouterr()
        assert "Invalid JSON" in captured.out

    def test_multiword_editor_is_shlex_split(self, tmp_path):
        """P1-4: multi-word ``$EDITOR`` (e.g. ``code --wait``) must split into argv.

        Before the fix, ``subprocess.run([editor, tmp_path])`` treated the
        whole string ``"code --wait"`` as argv[0], causing FileNotFoundError.
        """
        cfg = {"k": "v"}
        config_file = tmp_path / "user-config.json"
        config_file.write_text(json.dumps(cfg))

        captured_argv: list[list[str]] = []

        def capture_argv(cmd, *args, **kwargs):
            captured_argv.append(list(cmd))
            # Touch the temp file with valid JSON so downstream parsing succeeds.
            tmp_file = cmd[-1]
            with open(tmp_file, "w") as f:
                json.dump(cfg, f)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with (
            patch("money4band.core.viewer.load_json_config", return_value=cfg),
            patch("money4band.core.viewer._get_editor", return_value="code --wait"),
            patch("money4band.core.viewer.subprocess.run", side_effect=capture_argv),
            patch("money4band.core.dumper.write_json"),
            patch("money4band.core.viewer.ensure_config_encrypted"),
        ):
            edit_config(str(config_file))

        assert len(captured_argv) == 1
        argv = captured_argv[0]
        assert argv[0] == "code"
        assert argv[1] == "--wait"
        assert argv[2].endswith(".json")  # tmp_path appended as last arg

    def test_quoted_editor_path_with_spaces_preserved(self, tmp_path):
        """Editor path with quoted spaces survives shlex.split as a single token."""
        cfg = {"k": "v"}
        config_file = tmp_path / "user-config.json"
        config_file.write_text(json.dumps(cfg))

        captured_argv: list[list[str]] = []

        def capture_argv(cmd, *args, **kwargs):
            captured_argv.append(list(cmd))
            with open(cmd[-1], "w") as f:
                json.dump(cfg, f)
            return subprocess.CompletedProcess(args=cmd, returncode=0)

        with (
            patch("money4band.core.viewer.load_json_config", return_value=cfg),
            patch(
                "money4band.core.viewer._get_editor",
                return_value='"C:/Program Files/My Editor/ed.exe" --flag',
            ),
            patch("money4band.core.viewer.subprocess.run", side_effect=capture_argv),
            patch("money4band.core.dumper.write_json"),
            patch("money4band.core.viewer.ensure_config_encrypted"),
        ):
            edit_config(str(config_file))

        argv = captured_argv[0]
        assert argv[0] == "C:/Program Files/My Editor/ed.exe"
        assert argv[1] == "--flag"
