"""Tests for money4band.apps.configurator - credential collection and app setup."""

from __future__ import annotations

from unittest.mock import patch

from money4band.apps.configurator import (
    configure_apikey,
    configure_apps,
    configure_cid,
    configure_code,
    configure_email,
    configure_manual,
    configure_password,
    configure_token,
    configure_userid,
    configure_uuid,
    flag_function_mapper,
)


class TestConfigureEmail:
    """Prompt stores user-supplied email in config dict."""

    @patch("money4band.apps.configurator.ask_email", return_value="user@test.com")
    def test_stores_email(self, _ask):
        app = {"name": "EARNAPP"}
        config: dict = {}
        configure_email(app, {}, config)
        assert config["email"] == "user@test.com"


class TestConfigurePassword:
    """Prompt stores user-supplied password in config dict."""

    @patch("money4band.apps.configurator.ask_string", return_value="s3cret")
    def test_stores_password(self, _ask):
        config: dict = {}
        configure_password({"name": "EARNAPP"}, {}, config)
        assert config["password"] == "s3cret"


class TestConfigureApikey:
    """Prompt stores user-supplied API key."""

    @patch("money4band.apps.configurator.ask_string", return_value="key123")
    def test_stores_apikey(self, _ask):
        config: dict = {}
        configure_apikey({"name": "GRASS"}, {}, config)
        assert config["apikey"] == "key123"


class TestConfigureUserid:
    """Prompt stores user-supplied user ID."""

    @patch("money4band.apps.configurator.ask_string", return_value="uid456")
    def test_stores_userid(self, _ask):
        config: dict = {}
        configure_userid({"name": "APP"}, {}, config)
        assert config["userid"] == "uid456"


class TestConfigureCid:
    """Prompt stores user-supplied CID."""

    @patch("money4band.apps.configurator.ask_string", return_value="6aTk")
    def test_stores_cid(self, _ask):
        config: dict = {}
        configure_cid({"name": "PACKETSTREAM"}, {}, config)
        assert config["cid"] == "6aTk"


class TestConfigureCode:
    """Prompt stores user-supplied code."""

    @patch("money4band.apps.configurator.ask_string", return_value="mycode")
    def test_stores_code(self, _ask):
        config: dict = {}
        configure_code({"name": "APP"}, {}, config)
        assert config["code"] == "mycode"


class TestConfigureToken:
    """Prompt stores user-supplied token."""

    @patch("money4band.apps.configurator.ask_string", return_value="tok123")
    def test_stores_token(self, _ask):
        config: dict = {}
        configure_token({"name": "APP"}, {}, config)
        assert config["token"] == "tok123"


class TestConfigureManual:
    """Shows manual instructions when provided, errors when missing."""

    @patch("builtins.input", return_value="")
    def test_shows_instructions(self, _inp, capsys):
        config: dict = {}
        configure_manual({"name": "APP"}, {"instructions": "Do X then Y"}, config)
        out = capsys.readouterr().out
        assert "Do X then Y" in out
        assert "manual configuration" in out.lower()

    def test_missing_instructions_prints_error(self, capsys):
        config: dict = {}
        configure_manual({"name": "APP"}, {}, config)
        out = capsys.readouterr().out
        assert "Error" in out


class TestConfigureUuid:
    """UUID generation branch: auto-generate when user declines import."""

    @patch("money4band.apps.configurator.ask_question_yn", return_value=False)
    @patch(
        "money4band.apps.configurator.generate_uuid",
        return_value="abcd1234abcd1234abcd1234abcd1234",
    )
    def test_auto_generates_uuid(self, _gen, _ask):
        config: dict = {}
        flag_config = {"length": 32}
        configure_uuid({"name": "EARNAPP"}, flag_config, config)
        assert config["uuid"] == "abcd1234abcd1234abcd1234abcd1234"

    @patch("money4band.apps.configurator.ask_question_yn", return_value=True)
    @patch(
        "money4band.apps.configurator.ask_uuid",
        return_value="1234567890abcdef1234567890abcdef",
    )
    def test_imports_existing_uuid(self, _ask_uuid, _ask_yn):
        config: dict = {}
        flag_config = {"length": 32}
        configure_uuid({"name": "EARNAPP"}, flag_config, config)
        assert config["uuid"] == "1234567890abcdef1234567890abcdef"

    def test_missing_length_returns_early(self, capsys):
        config: dict = {}
        configure_uuid({"name": "APP"}, {}, config)
        assert "uuid" not in config

    def test_invalid_length_returns_early(self, capsys):
        config: dict = {}
        configure_uuid({"name": "APP"}, {"length": -1}, config)
        assert "uuid" not in config

    @patch("money4band.apps.configurator.ask_question_yn", return_value=False)
    @patch("money4band.apps.configurator.generate_uuid", return_value="abcd1234")
    def test_prefix_prepended(self, _gen, _ask):
        config: dict = {}
        flag_config = {"length": 8, "prefix": "sdk-node-"}
        configure_uuid({"name": "EARNAPP"}, flag_config, config)
        assert config["uuid"] == "sdk-node-abcd1234"

    @patch("money4band.apps.configurator.ask_question_yn", return_value=False)
    @patch("money4band.apps.configurator.generate_uuid", return_value="abcd")
    @patch("builtins.input", return_value="")
    def test_claim_url_written(self, _inp, _gen, _ask, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        config: dict = {}
        flag_config = {"length": 4, "claimURLBase": "https://claim.example.com/"}
        configure_uuid({"name": "TESTAPP"}, flag_config, config)
        claim_file = tmp_path / "claim_instructions_testapp.txt"
        assert claim_file.exists()
        assert "abcd" in claim_file.read_text()


class TestFlagFunctionMapper:
    """All flag names map to callable handlers."""

    def test_all_flags_are_callable(self):
        for name, func in flag_function_mapper.items():
            assert callable(func), f"{name} is not callable"

    def test_expected_keys_present(self):
        expected = {
            "email",
            "password",
            "apikey",
            "userid",
            "uuid",
            "cid",
            "code",
            "token",
            "manual",
        }
        assert expected == set(flag_function_mapper.keys())


class TestConfigureApps:
    """Integration: configure_apps iterates categories and calls _configure_apps."""

    @patch(
        "money4band.apps.configurator.get_active_app_categories",
        return_value=["supported"],
    )
    @patch("money4band.apps.configurator.get_category_entries", return_value=[])
    @patch("money4band.apps.configurator.cls")
    def test_empty_category_leaves_apps_unchanged(self, _cls, _entries, _cats):
        user_config = {"apps": {}}
        configure_apps(user_config, {}, {})
        assert user_config["apps"] == {}
