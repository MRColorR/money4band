"""Tests for scripts/migrate_to_v5.py — v4→v5 config migration."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Ensure scripts/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from migrate_to_v5 import (
    backup_file,
    build_app_flag_map,
    build_v5_config,
    map_env_to_apps,
    merge_v4_user_config,
    migrate,
    parse_env_file,
    validate_config,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def env_file(tmp_path: Path) -> Path:
    content = (
        "# Comment line\n"
        "DEVICE_NAME=mybox\n"
        "OS_TYPE=Linux\n"
        "DETECTED_ARCHITECTURE=amd64\n"
        "DETECTED_DOCKER_ARCH=amd64\n"
        "HONEYGAIN_EMAIL=test@example.com\n"
        'HONEYGAIN_PASSWORD="secret123"\n'
        "EARNAPP_UUID=sdk-node-abc123\n"
        "PACKETSTREAM_CID=1234\n"
        "M4B_DASHBOARD_PORT=8081\n"
        "STACK_PROXY_ENABLED=False\n"
    )
    p = tmp_path / ".env"
    p.write_text(content, encoding="utf-8")
    return p


@pytest.fixture()
def sample_flag_map() -> dict[str, list[str]]:
    return {
        "earnapp": ["uuid"],
        "honeygain": ["email", "password", "service_enabled"],
        "packetstream": ["cid"],
        "traffmonetizer": ["token"],
    }


@pytest.fixture()
def sample_app_config() -> dict:
    return {
        "supported-apps": {
            "active": True,
            "entries": [
                {"name": "EARNAPP", "flags": {"uuid": "sdk-node-..."}},
                {
                    "name": "HONEYGAIN",
                    "flags": {
                        "email": "...",
                        "password": "...",
                        "service_enabled": False,
                    },
                },
                {"name": "PACKETSTREAM", "flags": {"cid": "..."}},
            ],
        },
        "deprecated-apps": {
            "active": False,
            "entries": [
                {"name": "WIPTER", "flags": {"email": "...", "password": "..."}},
            ],
        },
    }


@pytest.fixture()
def sample_template() -> dict:
    return {
        "user": {"Nickname": "yourNickname", "email": "your@mail.com"},
        "device_info": {
            "device_name": "yourDeviceName",
            "os_type": "Linux",
            "detected_architecture": "amd64",
            "detected_docker_arch": "amd64",
        },
        "apps": {
            "earnapp": {"enabled": False, "uuid": "sdk-node-yourEARNAPPDeviceUUID"},
            "honeygain": {
                "enabled": False,
                "email": "yourHONEYGAINMail",
                "password": "yourHONEYGAINPw",
            },
            "packetstream": {"enabled": False, "cid": "yourPACKETSTREAMCID"},
        },
        "m4b_dashboard": {"enabled": True, "port": 8088},
        "proxies": {"enabled": False, "url": ""},
    }


# ---------------------------------------------------------------------------
# parse_env_file
# ---------------------------------------------------------------------------


class TestParseEnvFile:
    def test_basic_parsing(self, env_file: Path) -> None:
        result = parse_env_file(env_file)
        assert result["DEVICE_NAME"] == "mybox"
        assert result["HONEYGAIN_EMAIL"] == "test@example.com"
        assert result["EARNAPP_UUID"] == "sdk-node-abc123"

    def test_strips_quotes(self, env_file: Path) -> None:
        result = parse_env_file(env_file)
        assert result["HONEYGAIN_PASSWORD"] == "secret123"

    def test_skips_comments(self, env_file: Path) -> None:
        result = parse_env_file(env_file)
        assert not any(k.startswith("#") for k in result)

    def test_empty_file(self, tmp_path: Path) -> None:
        p = tmp_path / ".env"
        p.write_text("", encoding="utf-8")
        assert parse_env_file(p) == {}

    def test_only_comments(self, tmp_path: Path) -> None:
        p = tmp_path / ".env"
        p.write_text("# just a comment\n# another\n", encoding="utf-8")
        assert parse_env_file(p) == {}

    def test_empty_value(self, tmp_path: Path) -> None:
        p = tmp_path / ".env"
        p.write_text("KEY=\n", encoding="utf-8")
        result = parse_env_file(p)
        assert result["KEY"] == ""


# ---------------------------------------------------------------------------
# build_app_flag_map
# ---------------------------------------------------------------------------


class TestBuildAppFlagMap:
    def test_extracts_flags(self, sample_app_config: dict) -> None:
        result = build_app_flag_map(sample_app_config)
        assert "earnapp" in result
        assert result["earnapp"] == ["uuid"]
        assert set(result["honeygain"]) == {"email", "password", "service_enabled"}

    def test_includes_deprecated(self, sample_app_config: dict) -> None:
        result = build_app_flag_map(sample_app_config)
        assert "wipter" in result

    def test_empty_config(self) -> None:
        assert build_app_flag_map({}) == {}


# ---------------------------------------------------------------------------
# map_env_to_apps
# ---------------------------------------------------------------------------


class TestMapEnvToApps:
    def test_maps_credentials(self, sample_flag_map: dict) -> None:
        env = {
            "EARNAPP_UUID": "sdk-node-real123",
            "HONEYGAIN_EMAIL": "a@b.com",
            "HONEYGAIN_PASSWORD": "pw",
        }
        result = map_env_to_apps(env, sample_flag_map)
        assert result["earnapp"]["uuid"] == "sdk-node-real123"
        assert result["earnapp"]["enabled"] is True
        assert result["honeygain"]["email"] == "a@b.com"

    def test_skips_placeholder_values(self, sample_flag_map: dict) -> None:
        env = {"EARNAPP_UUID": "yourEARNAPPDeviceUUID"}
        result = map_env_to_apps(env, sample_flag_map)
        assert "uuid" not in result["earnapp"]
        # No real creds → not enabled
        assert "enabled" not in result["earnapp"]

    def test_missing_app_gets_empty_entry(self, sample_flag_map: dict) -> None:
        result = map_env_to_apps({}, sample_flag_map)
        assert result["earnapp"] == {}
        assert result["traffmonetizer"] == {}


# ---------------------------------------------------------------------------
# build_v5_config
# ---------------------------------------------------------------------------


class TestBuildV5Config:
    def test_merges_device_info(
        self, sample_template: dict, sample_flag_map: dict
    ) -> None:
        env = {"DEVICE_NAME": "mybox", "OS_TYPE": "Linux"}
        config = build_v5_config(sample_template, env, sample_flag_map, None)
        assert config["device_info"]["device_name"] == "mybox"

    def test_merges_app_creds(
        self, sample_template: dict, sample_flag_map: dict
    ) -> None:
        env = {"EARNAPP_UUID": "sdk-node-real"}
        config = build_v5_config(sample_template, env, sample_flag_map, None)
        assert config["apps"]["earnapp"]["uuid"] == "sdk-node-real"
        assert config["apps"]["earnapp"]["enabled"] is True

    def test_dashboard_port(self, sample_template: dict, sample_flag_map: dict) -> None:
        env = {"M4B_DASHBOARD_PORT": "9090"}
        config = build_v5_config(sample_template, env, sample_flag_map, None)
        assert config["m4b_dashboard"]["port"] == 9090

    def test_proxy_settings(self, sample_template: dict, sample_flag_map: dict) -> None:
        env = {
            "STACK_PROXY_ENABLED": "true",
            "STACK_PROXY_URL": "socks5://1.2.3.4:1080",
        }
        config = build_v5_config(sample_template, env, sample_flag_map, None)
        assert config["proxies"]["enabled"] is True
        assert config["proxies"]["url"] == "socks5://1.2.3.4:1080"

    def test_does_not_mutate_template(
        self, sample_template: dict, sample_flag_map: dict
    ) -> None:
        import copy

        original = copy.deepcopy(sample_template)
        build_v5_config(sample_template, {"DEVICE_NAME": "x"}, sample_flag_map, None)
        assert sample_template == original

    def test_merges_v4_user_config(
        self, sample_template: dict, sample_flag_map: dict
    ) -> None:
        v4 = {
            "apps": {"earnapp": {"enabled": True, "custom_field": "extra"}},
            "user": {"Nickname": "Bob"},
        }
        config = build_v5_config(sample_template, {}, sample_flag_map, v4)
        # v4 fields that don't exist in template get merged
        assert config["apps"]["earnapp"]["custom_field"] == "extra"
        assert config["user"]["Nickname"] == "Bob"


# ---------------------------------------------------------------------------
# merge_v4_user_config
# ---------------------------------------------------------------------------


class TestMergeV4UserConfig:
    def test_merges_app_fields(self) -> None:
        v5: dict = {"apps": {"earnapp": {"enabled": False}}}
        v4 = {"apps": {"earnapp": {"enabled": True, "uuid": "v4-uuid"}}}
        merge_v4_user_config(v5, v4)
        assert v5["apps"]["earnapp"]["uuid"] == "v4-uuid"
        # enabled already existed in v5 — should NOT be overwritten
        assert v5["apps"]["earnapp"]["enabled"] is False

    def test_adds_new_apps(self) -> None:
        v5: dict = {"apps": {}}
        v4 = {"apps": {"newapp": {"enabled": True, "token": "abc"}}}
        merge_v4_user_config(v5, v4)
        assert v5["apps"]["newapp"]["token"] == "abc"


# ---------------------------------------------------------------------------
# validate_config
# ---------------------------------------------------------------------------


class TestValidateConfig:
    def test_no_warnings_when_ok(self) -> None:
        config = {
            "apps": {"earnapp": {"enabled": True}},
            "device_info": {"device_name": "realbox"},
        }
        assert validate_config(config) == []

    def test_warns_no_apps_enabled(self) -> None:
        config = {
            "apps": {"earnapp": {"enabled": False}},
            "device_info": {"device_name": "x"},
        }
        warnings = validate_config(config)
        assert any("No apps" in w for w in warnings)

    def test_warns_placeholder_device(self) -> None:
        config = {
            "apps": {"a": {"enabled": True}},
            "device_info": {"device_name": "yourDeviceName"},
        }
        warnings = validate_config(config)
        assert any("placeholder" in w for w in warnings)


# ---------------------------------------------------------------------------
# backup_file
# ---------------------------------------------------------------------------


class TestBackupFile:
    def test_creates_bak(self, tmp_path: Path) -> None:
        f = tmp_path / "test.json"
        f.write_text("hello")
        bak = backup_file(f)
        assert bak is not None
        assert bak.exists()
        assert bak.read_text() == "hello"
        assert bak.suffix == ".bak"

    def test_increments_on_collision(self, tmp_path: Path) -> None:
        f = tmp_path / "test.json"
        f.write_text("v1")
        (tmp_path / "test.json.bak").write_text("existing")
        bak = backup_file(f)
        assert bak is not None
        assert "bak1" in bak.name

    def test_returns_none_for_missing(self, tmp_path: Path) -> None:
        assert backup_file(tmp_path / "nope.json") is None


# ---------------------------------------------------------------------------
# Integration: migrate()
# ---------------------------------------------------------------------------


class TestMigrate:
    def _setup_project(self, tmp_path: Path) -> Path:
        """Create a minimal v4 project layout."""
        root = tmp_path / "m4b"
        root.mkdir()
        # template
        (root / "template").mkdir()
        template = {
            "user": {"Nickname": "yourNickname"},
            "device_info": {
                "device_name": "yourDeviceName",
                "os_type": "Linux",
                "detected_architecture": "amd64",
                "detected_docker_arch": "amd64",
            },
            "apps": {
                "earnapp": {"enabled": False, "uuid": "yourEARNAPPDeviceUUID"},
                "honeygain": {"enabled": False, "email": "...", "password": "..."},
            },
            "m4b_dashboard": {"enabled": True, "port": 8088},
            "proxies": {"enabled": False, "url": ""},
        }
        (root / "template" / "user-config.json").write_text(
            json.dumps(template), encoding="utf-8"
        )
        # app-config
        (root / "config").mkdir()
        app_config = {
            "supported-apps": {
                "active": True,
                "entries": [
                    {"name": "EARNAPP", "flags": {"uuid": "..."}},
                    {"name": "HONEYGAIN", "flags": {"email": "...", "password": "..."}},
                ],
            },
        }
        (root / "config" / "app-config.json").write_text(
            json.dumps(app_config), encoding="utf-8"
        )
        # .env (v4 format)
        env_content = (
            "DEVICE_NAME=testbox\n"
            "OS_TYPE=Linux\n"
            "DETECTED_ARCHITECTURE=amd64\n"
            "DETECTED_DOCKER_ARCH=amd64\n"
            "EARNAPP_UUID=sdk-node-real123\n"
            "HONEYGAIN_EMAIL=test@test.com\n"
            "HONEYGAIN_PASSWORD=pass123\n"
            "M4B_DASHBOARD_PORT=8081\n"
        )
        (root / ".env").write_text(env_content, encoding="utf-8")
        return root

    def test_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        root = self._setup_project(tmp_path)
        result = migrate(str(root), dry_run=True)
        assert result is True
        output = capsys.readouterr().out
        assert "DRY RUN" in output
        # Originals should NOT have .bak
        assert not (root / ".env.bak").exists()

    def test_full_migration(self, tmp_path: Path) -> None:
        root = self._setup_project(tmp_path)
        result = migrate(str(root))
        assert result is True
        # .bak created
        assert (root / ".env.bak").exists()
        # user-config written
        uc_path = root / "config" / "user-config.json"
        assert uc_path.exists()
        content = uc_path.read_text(encoding="utf-8")
        # In test env, crypto may encrypt or leave plaintext — both are valid
        if not content.startswith("M4B_ENCRYPTED:"):
            config = json.loads(content)
            assert config["apps"]["earnapp"]["uuid"] == "sdk-node-real123"
            assert config["apps"]["earnapp"]["enabled"] is True
            assert config["device_info"]["device_name"] == "testbox"

    def test_already_encrypted_skips(self, tmp_path: Path) -> None:
        root = self._setup_project(tmp_path)
        # Write encrypted marker to user-config
        (root / "config" / "user-config.json").write_text(
            "M4B_ENCRYPTED:fakeciphertext"
        )
        result = migrate(str(root))
        assert result is True
        # No .bak created
        assert not (root / ".env.bak").exists()

    def test_missing_template_fails(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        result = migrate(str(root))
        assert result is False

    def test_no_env_still_works(self, tmp_path: Path) -> None:
        root = self._setup_project(tmp_path)
        (root / ".env").unlink()
        result = migrate(str(root), dry_run=True)
        assert result is True
