import os
import tempfile
import unittest

import yaml

from utils.generator import (
    assemble_docker_compose,
    generate_device_name,
    generate_env_file,
    generate_uuid,
    validate_uuid,
)


class TestGeneratorFunctions(unittest.TestCase):
    def test_validate_uuid(self):
        valid_uuid = "1234567890abcdef1234567890abcdef"
        invalid_uuid = "12345"
        self.assertTrue(validate_uuid(valid_uuid, 32))
        self.assertFalse(validate_uuid(invalid_uuid, 32))

    def test_generate_uuid(self):
        uuid = generate_uuid(32)
        self.assertEqual(len(uuid), 32)

    def test_generate_device_name(self):
        adjectives = ["swift", "brave"]
        animals = ["panther", "eagle"]
        device_name = generate_device_name(adjectives, animals)
        self.assertIn(device_name.split("_")[0], adjectives)
        self.assertIn(device_name.split("_")[1], animals)


# ── Minimal configs shared by env-file and compose tests ─────────────────────

_M4B_CFG = {
    "project": {"project_version": "test"},
    "network": {"subnet": "172.19.0.0", "netmask": "24"},
    "system": {"default_docker_platform": "linux/amd64"},
    "watchtower": {"enable_labels": True, "scope": "money4band"},
}

_APP_CFG = {"apps": [], "extra-apps": []}

_USER_CFG_BASE = {
    "device_info": {"device_name": "testdev"},
    "resource_limits": {},
    "apps": {},
    "proxies": {"enabled": False, "url": "", "url_example": ""},
    "notifications": {"enabled": False, "url": ""},
    "m4b_dashboard": {"enabled": False},
    "watchtower": {"enabled": True},
    "compose_config_common": {
        "network": {
            "driver": "${NETWORK_DRIVER}",
            "subnet": "${NETWORK_SUBNET}",
            "netmask": "${NETWORK_NETMASK}",
        },
        "watchtower_service": {
            "proxy_disabled": {
                "container_name": "${DEVICE_NAME}_watchtower",
                "image": "nickfedor/watchtower:latest",
                "environment": ["WATCHTOWER_SCOPE=${M4B_WATCHTOWER_SCOPE}"],
                "labels": ["com.centurylinklabs.watchtower.enable=true"],
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
                "restart": "always",
            },
            "proxy_enabled": {
                "container_name": "${DEVICE_NAME}_watchtower",
                "image": "nickfedor/watchtower:latest",
                "environment": ["WATCHTOWER_SCOPE=${M4B_WATCHTOWER_SCOPE}"],
                "labels": ["com.centurylinklabs.watchtower.enable=true"],
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
                "restart": "always",
            },
        },
        "m4b_dashboard_service": {
            "container_name": "${DEVICE_NAME}_m4b_dashboard",
            "image": "nginx:alpine-slim",
            "restart": "always",
        },
        "proxy_service": {
            "container_name": "${DEVICE_NAME}_proxy",
            "image": "xjasonlyu/tun2socks",
            "restart": "always",
        },
    },
}


class TestGenerateEnvFileWatchtower(unittest.TestCase):
    """Verify M4B_WATCHTOWER_LABELS and M4B_WATCHTOWER_SCOPE are always emitted."""

    def _run(self, m4b_cfg, user_cfg=None):
        if user_cfg is None:
            user_cfg = _USER_CFG_BASE.copy()
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            env_path = f.name
        try:
            generate_env_file(m4b_cfg, _APP_CFG, user_cfg, env_path)
            return open(env_path).read()
        finally:
            if os.path.exists(env_path):
                os.unlink(env_path)

    def test_default_scope_emitted(self):
        """Default scope values from m4b-config appear in .env."""
        content = self._run(_M4B_CFG)
        self.assertIn("M4B_WATCHTOWER_LABELS=true", content)
        self.assertIn("M4B_WATCHTOWER_SCOPE=money4band", content)

    def test_custom_scope_emitted(self):
        """Custom scope/labels values from m4b-config appear in .env."""
        cfg = dict(
            _M4B_CFG, watchtower={"enable_labels": False, "scope": "custom-scope"}
        )
        content = self._run(cfg)
        self.assertIn("M4B_WATCHTOWER_LABELS=false", content)
        self.assertIn("M4B_WATCHTOWER_SCOPE=custom-scope", content)

    def test_missing_watchtower_key_uses_defaults(self):
        """When watchtower key is absent in m4b-config, hardcoded defaults kick in."""
        cfg = {k: v for k, v in _M4B_CFG.items() if k != "watchtower"}
        content = self._run(cfg)
        self.assertIn("M4B_WATCHTOWER_LABELS=true", content)
        self.assertIn("M4B_WATCHTOWER_SCOPE=money4band", content)


class TestAssembleDockerComposeWatchtower(unittest.TestCase):
    """Verify the watchtower.enabled toggle controls Watchtower service inclusion."""

    def _compose(self, watchtower_enabled: bool) -> dict:
        import copy

        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["watchtower"]["enabled"] = watchtower_enabled

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            compose_path = f.name
        try:
            assemble_docker_compose(
                _M4B_CFG, _APP_CFG, user_cfg, compose_path, is_main_instance=True
            )
            with open(compose_path) as f:
                return yaml.safe_load(f) or {}
        finally:
            if os.path.exists(compose_path):
                os.unlink(compose_path)

    def test_watchtower_service_included_when_enabled(self):
        """watchtower service is present in compose when watchtower.enabled is True."""
        doc = self._compose(watchtower_enabled=True)
        self.assertIn("watchtower", doc.get("services", {}))

    def test_watchtower_service_omitted_when_disabled(self):
        """watchtower service is absent from compose when watchtower.enabled is False."""
        doc = self._compose(watchtower_enabled=False)
        self.assertNotIn("watchtower", doc.get("services", {}))


if __name__ == "__main__":
    unittest.main()
