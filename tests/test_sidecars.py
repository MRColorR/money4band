"""Tests for auto-claim sidecar containers."""

import json
import os
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Fixtures — minimal configs that satisfy compose_builder / app_configurator
# ---------------------------------------------------------------------------

_HONEYGAIN_APP = {
    "name": "HONEYGAIN",
    "dashboard": "https://dashboard.honeygain.com/",
    "link": "https://r.honeygain.me/X",
    "compose_config": {
        "container_name": "${DEVICE_NAME}_honeygain",
        "hostname": "${DEVICE_NAME}_honeygain",
        "image": "honeygain/honeygain:latest",
        "environment": ["HONEYGAIN_DUMMY=''"],
        "labels": [
            "com.centurylinklabs.watchtower.enable=true",
            "com.centurylinklabs.watchtower.scope=${M4B_WATCHTOWER_SCOPE}",
        ],
        "command": [
            "-tou-accept",
            "-email",
            "${HONEYGAIN_EMAIL}",
            "-pass",
            "${HONEYGAIN_PASSWORD}",
            "-device",
            "${DEVICE_NAME}",
        ],
        "restart": "always",
        "cpus": "${APP_CPU_LIMIT_MEDIUM}",
        "mem_reservation": "${APP_MEM_RESERV_MEDIUM}",
        "mem_limit": "${APP_MEM_LIMIT_MEDIUM}",
        "logging": {
            "driver": "json-file",
            "options": {"max-size": "10m", "max-file": "3"},
        },
    },
    "compose_config_proxy": {"network_mode": "service:proxy", "hostname": None},
    "flags": {"email": {}, "password": {}},
    "install_limit": 10,
    "service": {
        "name": "honeygain-pot",
        "description": "Auto-claims daily Lucky Pot reward (~2x revenue)",
        "credentials_shared": True,
        "compose_config": {
            "container_name": "${DEVICE_NAME}_honeygain-pot",
            "hostname": "${DEVICE_NAME}_honeygain-pot",
            "image": "ghcr.io/xterna/honeygain-pot:latest",
            "environment": [
                "EMAIL=${HONEYGAIN_EMAIL}",
                "PASSWORD=${HONEYGAIN_PASSWORD}",
            ],
            "labels": [
                "com.centurylinklabs.watchtower.enable=true",
                "com.centurylinklabs.watchtower.scope=${M4B_WATCHTOWER_SCOPE}",
            ],
            "dns": ["1.1.1.1", "8.8.8.8"],
            "restart": "always",
            "cpus": "${APP_CPU_LIMIT_LITTLE}",
            "mem_reservation": "${APP_MEM_RESERV_LITTLE}",
            "mem_limit": "${APP_MEM_LIMIT_LITTLE}",
            "logging": {
                "driver": "json-file",
                "options": {"max-size": "10m", "max-file": "3"},
            },
        },
    },
}

_NO_SERVICE_APP = {
    "name": "TRAFFMONETIZER",
    "dashboard": "https://app.traffmonetizer.com/dashboard",
    "link": "https://traffmonetizer.com/?aff=1",
    "compose_config": {
        "container_name": "${DEVICE_NAME}_traffmonetizer",
        "hostname": "${DEVICE_NAME}_traffmonetizer",
        "image": "traffmonetizer/cli_v2:latest",
        "environment": ["TRAFFMONETIZER_DUMMY=''"],
        "labels": [],
        "command": ["start", "accept", "--token", "${TRAFFMONETIZER_TOKEN}"],
        "restart": "always",
        "cpus": "${APP_CPU_LIMIT_LITTLE}",
        "mem_reservation": "${APP_MEM_RESERV_LITTLE}",
        "mem_limit": "${APP_MEM_LIMIT_LITTLE}",
        "logging": {
            "driver": "json-file",
            "options": {"max-size": "10m", "max-file": "3"},
        },
    },
    "compose_config_proxy": {"network_mode": "service:proxy", "hostname": None},
    "flags": {"token": {}},
    "install_limit": -1,
}


def _app_config(*apps):
    return {"supported-apps": {"active": True, "entries": list(apps)}}


def _m4b_config():
    return {
        "project": {"name": "money4band"},
        "system": {"default_docker_platform": "linux/amd64", "sleep_time": 0},
        "network": {"driver": "bridge", "subnet": "172.106.0.0", "netmask": "16"},
        "watchtower": {"enable_labels": True, "scope": "money4band"},
    }


def _user_config(apps_override=None):
    base = {
        "device_info": {"device_name": "test", "detected_docker_arch": "amd64"},
        "apps": {},
        "m4b_dashboard": {"enabled": False},
        "watchtower": {"enabled": False},
        "proxies": {"enabled": False},
        "notifications": {"enabled": False},
        "compose_config_common": {
            "network": {"driver": "bridge", "subnet": "172.106.0.0", "netmask": "16"},
        },
        "resource_limits": {
            "app_cpu_limit_little": 0.5,
            "app_cpu_limit_medium": 1,
            "app_mem_reserv_little": "64m",
            "app_mem_limit_little": "128m",
            "app_mem_reserv_medium": "128m",
            "app_mem_limit_medium": "256m",
        },
    }
    if apps_override:
        base["apps"] = apps_override
    return base


# ---------------------------------------------------------------------------
# compose_builder — sidecar service generation
# ---------------------------------------------------------------------------


class TestSidecarComposeGeneration:
    """Verify compose_builder emits sidecar services correctly."""

    @mock.patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @mock.patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    def test_sidecar_added_when_service_enabled(self, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        user = _user_config(
            {
                "honeygain": {
                    "enabled": True,
                    "email": "a@b.c",
                    "password": "pw",
                    "service_enabled": True,
                },
            }
        )
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(_m4b_config(), _app_config(_HONEYGAIN_APP), user, out)

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        assert "honeygain" in compose["services"]
        assert "honeygain-pot" in compose["services"]
        pot = compose["services"]["honeygain-pot"]
        assert pot["image"] == "ghcr.io/xterna/honeygain-pot:latest"
        assert "EMAIL=${HONEYGAIN_EMAIL}" in pot["environment"]
        assert pot["restart"] == "always"

    @mock.patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @mock.patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    def test_sidecar_not_added_when_service_disabled(self, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        user = _user_config(
            {
                "honeygain": {
                    "enabled": True,
                    "email": "a@b.c",
                    "password": "pw",
                    "service_enabled": False,
                },
            }
        )
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(_m4b_config(), _app_config(_HONEYGAIN_APP), user, out)

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        assert "honeygain" in compose["services"]
        assert "honeygain-pot" not in compose["services"]

    @mock.patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @mock.patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    def test_sidecar_not_added_when_no_service_field(self, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        user = _user_config(
            {
                "traffmonetizer": {"enabled": True, "token": "tok123"},
            }
        )
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(_m4b_config(), _app_config(_NO_SERVICE_APP), user, out)

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        assert "traffmonetizer" in compose["services"]
        # No sidecar for traffmonetizer
        assert len([k for k in compose["services"] if "pot" in k]) == 0

    @mock.patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @mock.patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    def test_sidecar_inherits_platform_from_parent(self, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        user = _user_config(
            {
                "honeygain": {
                    "enabled": True,
                    "email": "a@b.c",
                    "password": "pw",
                    "service_enabled": True,
                    "docker_platform": "linux/arm64",
                },
            }
        )
        m4b = _m4b_config()
        m4b["system"]["default_docker_platform"] = "linux/arm64"
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(m4b, _app_config(_HONEYGAIN_APP), user, out)

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        pot = compose["services"]["honeygain-pot"]
        assert pot.get("platform") == "linux/arm64"

    @mock.patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @mock.patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    def test_sidecar_has_security_opt(self, _tag, _arch, tmp_path):
        from money4band.compose_builder import assemble_docker_compose

        user = _user_config(
            {
                "honeygain": {
                    "enabled": True,
                    "email": "a@b.c",
                    "password": "pw",
                    "service_enabled": True,
                },
            }
        )
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(_m4b_config(), _app_config(_HONEYGAIN_APP), user, out)

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        pot = compose["services"]["honeygain-pot"]
        assert "no-new-privileges:true" in pot.get("security_opt", [])

    @mock.patch("money4band.compose_builder.check_img_arch_support", return_value=True)
    @mock.patch("money4band.compose_builder.get_compatible_tag", return_value=None)
    def test_sidecar_default_service_enabled_missing(self, _tag, _arch, tmp_path):
        """When user-config has no service_enabled key, sidecar is NOT added."""
        from money4band.compose_builder import assemble_docker_compose

        user = _user_config(
            {
                "honeygain": {"enabled": True, "email": "a@b.c", "password": "pw"},
            }
        )
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(_m4b_config(), _app_config(_HONEYGAIN_APP), user, out)

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        assert "honeygain-pot" not in compose["services"]


# ---------------------------------------------------------------------------
# app_configurator — sidecar prompt during setup
# ---------------------------------------------------------------------------


class TestSidecarSetupPrompt:
    """Verify sidecar prompt is shown during app configuration."""

    def test_sidecar_prompt_shown_for_app_with_service(self):
        from money4band.app_configurator import _configure_apps

        user_config = _user_config()
        user_config["apps"]["honeygain"] = {"enabled": False}

        # Simulate: enable app → enter email → enter password → enable sidecar
        with mock.patch(
            "money4band.app_configurator.ask_question_yn", side_effect=[True, True]
        ):
            with mock.patch(
                "money4band.app_configurator.ask_email", return_value="a@b.c"
            ):
                with mock.patch(
                    "money4band.app_configurator.ask_string", return_value="pw"
                ):
                    with mock.patch("money4band.app_configurator.cls"):
                        with mock.patch("builtins.input"):
                            _configure_apps(
                                user_config, [_HONEYGAIN_APP], _m4b_config()
                            )

        assert user_config["apps"]["honeygain"]["service_enabled"] is True

    def test_sidecar_prompt_decline(self):
        from money4band.app_configurator import _configure_apps

        user_config = _user_config()
        user_config["apps"]["honeygain"] = {"enabled": False}

        with mock.patch(
            "money4band.app_configurator.ask_question_yn", side_effect=[True, False]
        ):
            with mock.patch(
                "money4band.app_configurator.ask_email", return_value="a@b.c"
            ):
                with mock.patch(
                    "money4band.app_configurator.ask_string", return_value="pw"
                ):
                    with mock.patch("money4band.app_configurator.cls"):
                        with mock.patch("builtins.input"):
                            _configure_apps(
                                user_config, [_HONEYGAIN_APP], _m4b_config()
                            )

        assert user_config["apps"]["honeygain"]["service_enabled"] is False

    def test_no_sidecar_prompt_for_app_without_service(self):
        from money4band.app_configurator import _configure_apps

        user_config = _user_config()
        user_config["apps"]["traffmonetizer"] = {"enabled": False}

        # Only 1 yn call: enable app (no sidecar prompt)
        with mock.patch(
            "money4band.app_configurator.ask_question_yn", side_effect=[True]
        ) as mock_yn:
            with mock.patch(
                "money4band.app_configurator.ask_string", return_value="tok"
            ):
                with mock.patch("money4band.app_configurator.cls"):
                    with mock.patch("builtins.input"):
                        _configure_apps(user_config, [_NO_SERVICE_APP], _m4b_config())

        assert mock_yn.call_count == 1
        assert "service_enabled" not in user_config["apps"]["traffmonetizer"]


# ---------------------------------------------------------------------------
# app-config.json structural tests
# ---------------------------------------------------------------------------


class TestAppConfigServiceDefinitions:
    """Verify app-config.json service entries are well-formed."""

    @pytest.fixture()
    def app_config(self):
        config_path = os.path.join(
            os.path.dirname(__file__), os.pardir, "config", "app-config.json"
        )
        with open(config_path) as f:
            return json.load(f)

    def test_honeygain_has_service(self, app_config):
        hg = next(
            a
            for a in app_config["supported-apps"]["entries"]
            if a["name"] == "HONEYGAIN"
        )
        svc = hg["service"]
        assert svc["name"] == "honeygain-pot"
        assert "image" in svc["compose_config"]
        assert svc["credentials_shared"] is True

    def test_packetshare_has_service(self, app_config):
        ps = next(
            a
            for a in app_config["supported-apps"]["entries"]
            if a["name"] == "PACKETSHARE"
        )
        svc = ps["service"]
        assert svc["name"] == "packetshare-pot"
        assert "image" in svc["compose_config"]
        assert svc["credentials_shared"] is True

    def test_service_compose_config_has_required_keys(self, app_config):
        required = {"container_name", "image", "environment", "restart", "labels"}
        for app in app_config["supported-apps"]["entries"]:
            svc = app.get("service")
            if svc:
                cc = svc["compose_config"]
                missing = required - set(cc.keys())
                assert not missing, f"{app['name']} sidecar missing keys: {missing}"

    def test_apps_without_service_have_none(self, app_config):
        for app in app_config["supported-apps"]["entries"]:
            if app["name"] not in ("HONEYGAIN", "PACKETSHARE"):
                assert "service" not in app, f"{app['name']} should not have a service"


# ---------------------------------------------------------------------------
# user-config template tests
# ---------------------------------------------------------------------------


class TestUserConfigTemplate:
    """Verify user-config template includes service_enabled for sidecar apps."""

    @pytest.fixture()
    def template(self):
        tpl_path = os.path.join(
            os.path.dirname(__file__), os.pardir, "template", "user-config.json"
        )
        with open(tpl_path) as f:
            return json.load(f)

    def test_honeygain_template_has_service_enabled(self, template):
        assert template["apps"]["honeygain"]["service_enabled"] is False

    def test_packetshare_template_has_service_enabled(self, template):
        assert template["apps"]["packetshare"]["service_enabled"] is False

    def test_other_apps_no_service_enabled(self, template):
        for name, cfg in template["apps"].items():
            if name not in ("honeygain", "packetshare"):
                assert "service_enabled" not in cfg, (
                    f"{name} should not have service_enabled"
                )
