"""Tests for money4band.ui.banner - shared banner & nickname helpers."""

from __future__ import annotations

from unittest.mock import patch

from money4band.ui.banner import ensure_nickname, get_system_username, print_banner

# ---------------------------------------------------------------------------
# get_system_username
# ---------------------------------------------------------------------------


class TestGetSystemUsername:
    @patch("money4band.ui.banner.getpass.getuser", return_value="alice")
    def test_returns_os_username(self, _mock) -> None:
        assert get_system_username() == "alice"

    @patch("money4band.ui.banner.getpass.getuser", side_effect=OSError("no tty"))
    def test_falls_back_to_user_on_error(self, _mock) -> None:
        assert get_system_username() == "user"


# ---------------------------------------------------------------------------
# ensure_nickname
# ---------------------------------------------------------------------------


class TestEnsureNickname:
    """Verify ensure_nickname resolves and mutates the config dict."""

    @patch("money4band.ui.banner.get_system_username", return_value="bob")
    def test_replaces_placeholder(self, _mock) -> None:
        cfg = {"user": {"Nickname": "yourNickname"}}
        result = ensure_nickname(cfg)
        assert result == "bob"
        assert cfg["user"]["Nickname"] == "bob"

    @patch("money4band.ui.banner.get_system_username", return_value="bob")
    def test_replaces_empty_nickname(self, _mock) -> None:
        cfg = {"user": {"Nickname": ""}}
        result = ensure_nickname(cfg)
        assert result == "bob"
        assert cfg["user"]["Nickname"] == "bob"

    @patch("money4band.ui.banner.get_system_username", return_value="bob")
    def test_replaces_your_prefix_case_insensitive(self, _mock) -> None:
        cfg = {"user": {"Nickname": "YourName123"}}
        assert ensure_nickname(cfg) == "bob"

    def test_keeps_existing_real_nickname(self) -> None:
        cfg = {"user": {"Nickname": "mattia"}}
        result = ensure_nickname(cfg)
        assert result == "mattia"
        assert cfg["user"]["Nickname"] == "mattia"

    @patch("money4band.ui.banner.get_system_username", return_value="bob")
    def test_creates_user_section_if_missing(self, _mock) -> None:
        cfg: dict = {}
        result = ensure_nickname(cfg)
        assert result == "bob"
        assert cfg["user"]["Nickname"] == "bob"

    @patch("money4band.ui.banner.get_system_username", return_value="bob")
    def test_creates_nickname_key_if_missing(self, _mock) -> None:
        cfg = {"user": {}}
        result = ensure_nickname(cfg)
        assert result == "bob"

    def test_does_not_mutate_when_nick_is_real(self) -> None:
        """Config dict should be untouched when nickname is already set."""
        cfg = {"user": {"Nickname": "alice", "email": "a@b.com"}}
        original_email = cfg["user"]["email"]
        ensure_nickname(cfg)
        assert cfg["user"]["email"] == original_email

    @patch("money4band.ui.banner.get_system_username", return_value="user")
    def test_fallback_username_used_when_getuser_fails(self, _mock) -> None:
        cfg = {"user": {"Nickname": ""}}
        assert ensure_nickname(cfg) == "user"


# ---------------------------------------------------------------------------
# print_banner
# ---------------------------------------------------------------------------


class TestPrintBanner:
    """Verify print_banner output for various parameter combinations."""

    _M4B_CFG = {
        "project": {
            "project_version": "5.0.0",
            "ds_project_server_url": "https://discord.gg/test",
        }
    }

    def test_basic_banner(self, capsys) -> None:
        print_banner(self._M4B_CFG)
        out = capsys.readouterr().out
        assert "MONEY4BAND v5.0.0" in out
        assert "discord.gg/test" in out
        assert "Hello" not in out

    def test_banner_with_nickname(self, capsys) -> None:
        print_banner(self._M4B_CFG, nickname="mattia")
        out = capsys.readouterr().out
        assert "Hello, " in out
        assert "mattia" in out

    def test_banner_with_greeting(self, capsys) -> None:
        print_banner(self._M4B_CFG, greeting="Welcome aboard!")
        out = capsys.readouterr().out
        assert "Welcome aboard!" in out
        assert "Hello" not in out  # no nickname -> no hello line

    def test_banner_with_nickname_and_greeting(self, capsys) -> None:
        print_banner(self._M4B_CFG, nickname="alice", greeting="Setup Wizard")
        out = capsys.readouterr().out
        assert "alice" in out
        assert "Setup Wizard" in out
        # nickname line comes before greeting
        hello_pos = out.index("alice")
        greeting_pos = out.index("Setup Wizard")
        assert hello_pos < greeting_pos

    def test_missing_project_section(self, capsys) -> None:
        print_banner({})
        out = capsys.readouterr().out
        assert "MONEY4BAND v?" in out

    def test_no_discord_url_line_when_missing(self, capsys) -> None:
        cfg = {"project": {"project_version": "1.0.0"}}
        print_banner(cfg)
        out = capsys.readouterr().out
        assert "Join our Discord community" not in out
        assert "MONEY4BAND v1.0.0" in out

    def test_donation_message_always_shown(self, capsys) -> None:
        print_banner(self._M4B_CFG)
        out = capsys.readouterr().out
        assert "Support the M4B development" in out
