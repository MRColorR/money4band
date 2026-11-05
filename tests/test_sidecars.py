"""Tests for auto-claim sidecar containers."""

import json
import os
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Fixtures - minimal configs that satisfy compose_builder / app_configurator
# ---------------------------------------------------------------------------

_HONEYGAIN_APP = {
    "name": "HONEYGAIN",
    "dashboard": "https://dashboard.honeygain.com/",
    "referrals": [{"url": "https://r.honeygain.me/X", "contributor": "MRColorR"}],
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
}


_HONEYGAIN_POT_ADDON = {
    "name": "HONEYGAIN_POT",
    "parent_id": "HONEYGAIN",
    "description": "Auto-claims daily Lucky Pot reward (~2x revenue)",
    "credentials_shared": True,
    "profile": "service",
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
}

_NO_SERVICE_APP = {
    "name": "TRAFFMONETIZER",
    "dashboard": "https://app.traffmonetizer.com/dashboard",
    "referrals": [
        {"url": "https://traffmonetizer.com/?aff=1", "contributor": "MRColorR"}
    ],
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


def _app_config(*apps, addons=None):
    return {
        "supported": {"active": True, "entries": list(apps)},
        "addons": list(addons or []),
    }


def _m4b_config():
    return {
        "project": {"name": "money4band"},
        "system": {"default_docker_platform": "linux/amd64", "sleep_time": 0},
        "network": {"driver": "bridge", "subnet": "172.106.0.0", "netmask": "16"},
        "watchtower": {"scope": "money4band"},
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
# compose_builder - sidecar service generation
# ---------------------------------------------------------------------------


class TestSidecarComposeGeneration:
    """Verify compose_builder emits sidecar services correctly."""

    @mock.patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @mock.patch(
        "money4band.docker.compose_builder.get_compatible_tag", return_value=None
    )
    def test_sidecar_added_when_service_enabled(self, _tag, _arch, tmp_path):
        from money4band.docker.compose_builder import assemble_docker_compose

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
        assemble_docker_compose(
            _m4b_config(),
            _app_config(_HONEYGAIN_APP, addons=[_HONEYGAIN_POT_ADDON]),
            user,
            out,
        )

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        assert "honeygain" in compose["services"]
        assert "honeygain-pot" in compose["services"]
        pot = compose["services"]["honeygain-pot"]
        assert pot["image"] == "ghcr.io/xterna/honeygain-pot:latest"
        assert "EMAIL=${HONEYGAIN_EMAIL}" in pot["environment"]
        assert pot["restart"] == "always"

    @mock.patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @mock.patch(
        "money4band.docker.compose_builder.get_compatible_tag", return_value=None
    )
    def test_sidecar_not_added_when_service_disabled(self, _tag, _arch, tmp_path):
        from money4band.docker.compose_builder import assemble_docker_compose

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
        assemble_docker_compose(
            _m4b_config(),
            _app_config(_HONEYGAIN_APP, addons=[_HONEYGAIN_POT_ADDON]),
            user,
            out,
        )

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        assert "honeygain" in compose["services"]
        assert "honeygain-pot" not in compose["services"]

    @mock.patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @mock.patch(
        "money4band.docker.compose_builder.get_compatible_tag", return_value=None
    )
    def test_sidecar_not_added_when_no_service_field(self, _tag, _arch, tmp_path):
        from money4band.docker.compose_builder import assemble_docker_compose

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

    @mock.patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @mock.patch(
        "money4band.docker.compose_builder.get_compatible_tag", return_value=None
    )
    def test_sidecar_inherits_platform_from_parent(self, _tag, _arch, tmp_path):
        from money4band.docker.compose_builder import assemble_docker_compose

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
        assemble_docker_compose(
            m4b, _app_config(_HONEYGAIN_APP, addons=[_HONEYGAIN_POT_ADDON]), user, out
        )

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        pot = compose["services"]["honeygain-pot"]
        assert pot.get("platform") == "linux/arm64"

    @mock.patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @mock.patch(
        "money4band.docker.compose_builder.get_compatible_tag", return_value=None
    )
    def test_sidecar_has_security_opt(self, _tag, _arch, tmp_path):
        from money4band.docker.compose_builder import assemble_docker_compose

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
        assemble_docker_compose(
            _m4b_config(),
            _app_config(_HONEYGAIN_APP, addons=[_HONEYGAIN_POT_ADDON]),
            user,
            out,
        )

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        pot = compose["services"]["honeygain-pot"]
        assert "no-new-privileges:true" in pot.get("security_opt", [])

    @mock.patch(
        "money4band.docker.compose_builder.check_img_arch_support", return_value=True
    )
    @mock.patch(
        "money4band.docker.compose_builder.get_compatible_tag", return_value=None
    )
    def test_sidecar_default_service_enabled_missing(self, _tag, _arch, tmp_path):
        """When user-config has no service_enabled key, sidecar is NOT added."""
        from money4band.docker.compose_builder import assemble_docker_compose

        user = _user_config(
            {
                "honeygain": {"enabled": True, "email": "a@b.c", "password": "pw"},
            }
        )
        out = str(tmp_path / "docker-compose.yaml")
        assemble_docker_compose(
            _m4b_config(),
            _app_config(_HONEYGAIN_APP, addons=[_HONEYGAIN_POT_ADDON]),
            user,
            out,
        )

        import yaml

        with open(out) as f:
            compose = yaml.safe_load(f)
        assert "honeygain-pot" not in compose["services"]


# ---------------------------------------------------------------------------
# app_configurator - sidecar prompt during setup
# ---------------------------------------------------------------------------


class TestSidecarSetupPrompt:
    """Verify sidecar prompt is shown during app configuration."""

    def test_sidecar_prompt_shown_for_app_with_service(self):
        from money4band.apps.configurator import _configure_apps

        user_config = _user_config()
        user_config["apps"]["honeygain"] = {"enabled": False}

        # Simulate: enable app -> enter email -> enter password -> enable sidecar
        with mock.patch(
            "money4band.apps.configurator.ask_question_yn", side_effect=[True, True]
        ):
            with mock.patch(
                "money4band.apps.configurator.ask_email", return_value="a@b.c"
            ):
                with mock.patch(
                    "money4band.apps.configurator.ask_string", return_value="pw"
                ):
                    with mock.patch("money4band.apps.configurator.cls"):
                        with mock.patch("builtins.input"):
                            _configure_apps(
                                user_config,
                                [_HONEYGAIN_APP],
                                _m4b_config(),
                                app_config=_app_config(
                                    _HONEYGAIN_APP, addons=[_HONEYGAIN_POT_ADDON]
                                ),
                            )

        assert user_config["apps"]["honeygain"]["service_enabled"] is True

    def test_sidecar_prompt_decline(self):
        from money4band.apps.configurator import _configure_apps

        user_config = _user_config()
        user_config["apps"]["honeygain"] = {"enabled": False}

        with mock.patch(
            "money4band.apps.configurator.ask_question_yn", side_effect=[True, False]
        ):
            with mock.patch(
                "money4band.apps.configurator.ask_email", return_value="a@b.c"
            ):
                with mock.patch(
                    "money4band.apps.configurator.ask_string", return_value="pw"
                ):
                    with mock.patch("money4band.apps.configurator.cls"):
                        with mock.patch("builtins.input"):
                            _configure_apps(
                                user_config,
                                [_HONEYGAIN_APP],
                                _m4b_config(),
                                app_config=_app_config(
                                    _HONEYGAIN_APP, addons=[_HONEYGAIN_POT_ADDON]
                                ),
                            )

        assert user_config["apps"]["honeygain"]["service_enabled"] is False

    def test_no_sidecar_prompt_for_app_without_service(self):
        from money4band.apps.configurator import _configure_apps

        user_config = _user_config()
        user_config["apps"]["traffmonetizer"] = {"enabled": False}

        # Only 1 yn call: enable app (no sidecar prompt)
        with mock.patch(
            "money4band.apps.configurator.ask_question_yn", side_effect=[True]
        ) as mock_yn:
            with mock.patch(
                "money4band.apps.configurator.ask_string", return_value="tok"
            ):
                with mock.patch("money4band.apps.configurator.cls"):
                    with mock.patch("builtins.input"):
                        _configure_apps(user_config, [_NO_SERVICE_APP], _m4b_config())

        assert mock_yn.call_count == 1
        assert "service_enabled" not in user_config["apps"]["traffmonetizer"]


# ---------------------------------------------------------------------------
# Catalog structural tests
# ---------------------------------------------------------------------------


class TestAppConfigServiceDefinitions:
    """Verify addon entries in the catalog are well-formed.

    The core Money4Band catalog ships no ToS-violating auto-claim addons
    (Honeygain/PacketShare pots live in the opt-in community catalog).
    These tests validate the *shape* of any addons that remain; the
    parent-specific assertions live in the community catalog repo.
    """

    @pytest.fixture()
    def app_config(self):
        from money4band.core.loader import load_app_config_with_overlays

        config_path = os.path.join(
            os.path.dirname(__file__), os.pardir, "config", "m4b-config.json"
        )
        return load_app_config_with_overlays(config_path)

    def test_addon_compose_config_has_required_keys(self, app_config):
        required = {"container_name", "image", "environment", "restart", "labels"}
        for addon in app_config.get("addons", []):
            cc = addon["compose_config"]
            missing = required - set(cc.keys())
            assert not missing, f"{addon['name']} addon missing keys: {missing}"

    def test_every_addon_has_parent_id(self, app_config):
        for addon in app_config.get("addons", []):
            assert addon.get("parent_id"), (
                f"{addon['name']} addon must declare parent_id"
            )

    def test_apps_without_addon_have_no_match(self, app_config):
        from money4band.apps.addons import get_addons_for

        parents_with_addons = {a["parent_id"] for a in app_config.get("addons", [])}
        for app in app_config["supported"]["entries"]:
            if app["name"] not in parents_with_addons:
                assert not get_addons_for(app["name"], app_config)


# ---------------------------------------------------------------------------
# user-config template tests
# ---------------------------------------------------------------------------


class TestUserConfigTemplate:
    """Verify per-bundle user_config_template carries service_enabled."""

    @pytest.fixture()
    def app_config(self):
        from money4band.core.loader import load_app_config_with_overlays

        config_path = os.path.join(
            os.path.dirname(__file__), os.pardir, "config", "m4b-config.json"
        )
        return load_app_config_with_overlays(config_path)

    @pytest.fixture()
    def app_entries(self, app_config):
        """Flatten {lower_name: entry} across all catalog categories."""
        entries: dict[str, dict] = {}
        for cat in ("supported", "newcomers", "deprecated"):
            for entry in app_config.get(cat, {}).get("entries", []):
                entries[entry["name"].lower()] = entry
        return entries

    def _template_for(self, app_entries, name: str) -> dict:
        entry = app_entries[name]
        tpl = entry.get("user_config_template")
        assert isinstance(tpl, dict), f"{entry['name']} is missing user_config_template"
        return tpl

    def test_honeygain_template_has_service_enabled(self, app_entries):
        assert self._template_for(app_entries, "honeygain")["service_enabled"] is False

    def test_packetshare_template_has_service_enabled(self, app_entries):
        assert (
            self._template_for(app_entries, "packetshare")["service_enabled"] is False
        )

    def test_bearshare_template_has_service_enabled(self, app_entries):
        assert self._template_for(app_entries, "bearshare")["service_enabled"] is False

    def test_other_apps_no_service_enabled(self, app_entries):
        sidecar_apps = {"honeygain", "packetshare", "bearshare"}
        for name, entry in app_entries.items():
            tpl = entry.get("user_config_template", {})
            if name not in sidecar_apps:
                assert "service_enabled" not in tpl, (
                    f"{name} should not have service_enabled"
                )

    def test_root_template_has_no_per_app_block(self):
        """template/user-config.json must not duplicate per-app knowledge."""
        tpl_path = os.path.join(
            os.path.dirname(__file__), os.pardir, "template", "user-config.json"
        )
        with open(tpl_path) as f:
            template = json.load(f)
        assert template["apps"] == {}, (
            "template/user-config.json must have apps: {} - "
            "per-app slices are declared in each catalog bundle."
        )
