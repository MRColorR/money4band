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

_APP_CFG = {"supported-apps": {"active": True, "entries": []}}

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
                "image": "nickfedor/watchtower:1.14",
                "environment": ["WATCHTOWER_SCOPE=${M4B_WATCHTOWER_SCOPE}"],
                "labels": ["com.centurylinklabs.watchtower.enable=true"],
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
                "restart": "always",
            },
            "proxy_enabled": {
                "container_name": "${DEVICE_NAME}_watchtower",
                "image": "nickfedor/watchtower:1.14",
                "environment": ["WATCHTOWER_SCOPE=${M4B_WATCHTOWER_SCOPE}"],
                "labels": ["com.centurylinklabs.watchtower.enable=true"],
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
                "restart": "always",
            },
        },
        "m4b_dashboard_service": {
            "container_name": "${DEVICE_NAME}_m4b_dashboard",
            "image": "nginx:1.28-alpine-slim",
            "restart": "always",
        },
        "proxy_service": {
            "container_name": "${DEVICE_NAME}_proxy",
            "image": "xjasonlyu/tun2socks:v2.6.0",
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

    def test_watchtower_scope_enforced_on_old_user_config(self):
        """Scope env vars and label are injected even when old user-config lacks them."""
        import copy

        # Simulate an older user-config whose watchtower service has no scope entries
        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["compose_config_common"]["watchtower_service"]["proxy_disabled"] = {
            "container_name": "${DEVICE_NAME}_watchtower",
            "image": "nickfedor/watchtower:1.14",
            # intentionally missing WATCHTOWER_SCOPE env and scope label
            "environment": ["WATCHTOWER_CLEANUP=true"],
            "labels": ["com.centurylinklabs.watchtower.enable=true"],
            "volumes": ["/var/run/docker.sock:/var/run/docker.sock"],
            "restart": "always",
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            compose_path = f.name
        try:
            assemble_docker_compose(
                _M4B_CFG, _APP_CFG, user_cfg, compose_path, is_main_instance=True
            )
            with open(compose_path) as f:
                doc = yaml.safe_load(f) or {}
        finally:
            if os.path.exists(compose_path):
                os.unlink(compose_path)

        wt = doc.get("services", {}).get("watchtower", {})
        env = wt.get("environment", [])
        labels = wt.get("labels", [])

        self.assertTrue(
            any("WATCHTOWER_SCOPE" in e for e in env),
            "WATCHTOWER_SCOPE must be enforced in watchtower environment",
        )
        self.assertTrue(
            any("WATCHTOWER_LABEL_ENABLE" in e for e in env),
            "WATCHTOWER_LABEL_ENABLE must be enforced in watchtower environment",
        )
        self.assertTrue(
            any("watchtower.scope" in lbl for lbl in labels),
            "scope label must be enforced on watchtower service",
        )


class TestContainerSecurityHardening(unittest.TestCase):
    """Verify no-new-privileges is injected on non-privileged services."""

    def _compose_with_proxy(self, proxy_privileged: bool) -> dict:
        import copy

        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["proxies"]["enabled"] = True
        if proxy_privileged:
            user_cfg["compose_config_common"]["proxy_service"]["privileged"] = True

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

    def test_nonprivileged_services_get_no_new_privileges(self):
        doc = self._compose_with_proxy(proxy_privileged=False)
        wt = doc["services"]["watchtower"]
        self.assertEqual(wt.get("security_opt"), ["no-new-privileges:true"])

    def test_privileged_service_skips_no_new_privileges(self):
        doc = self._compose_with_proxy(proxy_privileged=True)
        proxy = doc["services"]["proxy"]
        self.assertNotIn("security_opt", proxy)

    def test_watchtower_read_only(self):
        doc = self._compose_with_proxy(proxy_privileged=False)
        wt = doc["services"]["watchtower"]
        self.assertTrue(wt.get("read_only"))


class TestNotificationEnvStripping(unittest.TestCase):
    """KI-032: WATCHTOWER_NOTIFICATION_URL stripped when notifications disabled."""

    def _compose_notify(self, notifications_enabled: bool) -> dict:
        import copy

        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["notifications"]["enabled"] = notifications_enabled
        # Add notification URL env to watchtower template
        wt = user_cfg["compose_config_common"]["watchtower_service"]["proxy_disabled"]
        wt["environment"].append(
            "WATCHTOWER_NOTIFICATION_URL=${WATCHTOWER_NOTIFICATION_URL}"
        )

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

    def test_notification_env_stripped_when_disabled(self):
        doc = self._compose_notify(notifications_enabled=False)
        wt_env = doc["services"]["watchtower"].get("environment", [])
        self.assertFalse(
            any("WATCHTOWER_NOTIFICATION_URL" in e for e in wt_env),
            "WATCHTOWER_NOTIFICATION_URL should be stripped when notifications disabled",
        )

    def test_notification_env_kept_when_enabled(self):
        doc = self._compose_notify(notifications_enabled=True)
        wt_env = doc["services"]["watchtower"].get("environment", [])
        self.assertTrue(
            any("WATCHTOWER_NOTIFICATION_URL" in e for e in wt_env),
            "WATCHTOWER_NOTIFICATION_URL should be kept when notifications enabled",
        )


class TestDashboardHardening(unittest.TestCase):
    """Verify nginx dashboard gets read_only + tmpfs."""

    def test_dashboard_read_only_with_tmpfs(self):
        import copy

        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["m4b_dashboard"]["enabled"] = True

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            compose_path = f.name
        try:
            assemble_docker_compose(
                _M4B_CFG, _APP_CFG, user_cfg, compose_path, is_main_instance=True
            )
            with open(compose_path) as f:
                doc = yaml.safe_load(f) or {}
        finally:
            if os.path.exists(compose_path):
                os.unlink(compose_path)

        dash = doc["services"]["m4bwebdashboard"]
        self.assertTrue(dash.get("read_only"))
        self.assertIn("/var/cache/nginx", dash.get("tmpfs", []))
        self.assertIn("/run", dash.get("tmpfs", []))


class TestDockerProfiles(unittest.TestCase):
    """Verify Docker Compose profiles are injected on infrastructure services."""

    def _generate_compose(self, proxy_enabled=False, dashboard_enabled=True):
        import copy

        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["m4b_dashboard"]["enabled"] = dashboard_enabled
        user_cfg["proxies"]["enabled"] = proxy_enabled

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

    def test_watchtower_has_monitoring_profile(self):
        doc = self._generate_compose()
        wt = doc["services"]["watchtower"]
        self.assertEqual(wt.get("profiles"), ["monitoring"])

    def test_dashboard_has_dashboard_profile(self):
        doc = self._generate_compose(dashboard_enabled=True)
        dash = doc["services"]["m4bwebdashboard"]
        self.assertEqual(dash.get("profiles"), ["dashboard"])

    def test_proxy_has_proxy_profile(self):
        doc = self._generate_compose(proxy_enabled=True)
        proxy = doc["services"]["proxy"]
        self.assertEqual(proxy.get("profiles"), ["proxy"])

    def test_regular_app_has_no_profile(self):
        doc = self._generate_compose()
        # Find any enabled app that's not infrastructure
        for svc_name, svc in doc["services"].items():
            if svc_name not in ("watchtower", "m4bwebdashboard", "proxy"):
                self.assertNotIn("profiles", svc,
                    f"{svc_name} should not have profiles")


class TestHealthchecks(unittest.TestCase):
    """Verify healthchecks are injected on infrastructure services."""

    def _compose_with_services(self, proxy=False, dashboard=True):
        import copy

        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["m4b_dashboard"]["enabled"] = dashboard
        user_cfg["proxies"]["enabled"] = proxy

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

    def test_dashboard_has_healthcheck(self):
        doc = self._compose_with_services(dashboard=True)
        dash = doc["services"]["m4bwebdashboard"]
        hc = dash.get("healthcheck", {})
        self.assertIn("test", hc)
        self.assertTrue(any("wget" in str(t) for t in hc["test"]))

    def test_proxy_has_healthcheck(self):
        doc = self._compose_with_services(proxy=True)
        proxy = doc["services"]["proxy"]
        hc = proxy.get("healthcheck", {})
        self.assertIn("test", hc)
        self.assertTrue(any("tun0" in str(t) for t in hc["test"]))

    def test_proxy_healthcheck_has_start_period(self):
        doc = self._compose_with_services(proxy=True)
        hc = doc["services"]["proxy"]["healthcheck"]
        self.assertIn("start_period", hc)

    def test_watchtower_has_no_healthcheck(self):
        doc = self._compose_with_services()
        wt = doc["services"]["watchtower"]
        self.assertNotIn("healthcheck", wt)


class TestAppHealthchecks(unittest.TestCase):
    """Verify that healthcheck definitions in compose_config flow through to output."""

    _HC_APP = {
        "name": "HCAPP",
        "dashboard": "http://example.com",
        "link": "http://example.com",
        "compose_config": {
            "container_name": "${DEVICE_NAME}_hcapp",
            "image": "example/hcapp:latest",
            "restart": "always",
            "labels": [
                "com.centurylinklabs.watchtower.enable=true",
                "com.centurylinklabs.watchtower.scope=${M4B_WATCHTOWER_SCOPE}",
            ],
            "healthcheck": {
                "test": ["CMD-SHELL", "pgrep -f hcapp || exit 1"],
                "interval": "120s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "60s",
            },
        },
    }

    _HTTP_HC_APP = {
        "name": "HTTPAPP",
        "dashboard": "http://example.com",
        "link": "http://example.com",
        "compose_config": {
            "container_name": "${DEVICE_NAME}_httpapp",
            "image": "example/httpapp:latest",
            "restart": "always",
            "labels": [
                "com.centurylinklabs.watchtower.enable=true",
                "com.centurylinklabs.watchtower.scope=${M4B_WATCHTOWER_SCOPE}",
            ],
            "healthcheck": {
                "test": [
                    "CMD-SHELL",
                    "wget -q --spider http://127.0.0.1:8080/health || exit 1",
                ],
                "interval": "60s",
                "timeout": "10s",
                "retries": 3,
                "start_period": "30s",
            },
        },
    }

    def _compose_with_app(self, app_entry):
        import copy
        from unittest.mock import patch

        app_name = app_entry["name"].lower()
        app_cfg = {"supported-apps": {"active": True, "entries": [app_entry]}}
        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["apps"] = {app_name: {"enabled": True}}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            compose_path = f.name
        try:
            with patch("utils.compose_builder.check_img_arch_support", return_value=True):
                assemble_docker_compose(
                    _M4B_CFG, app_cfg, user_cfg, compose_path, is_main_instance=True
                )
            with open(compose_path) as f:
                return yaml.safe_load(f) or {}
        finally:
            if os.path.exists(compose_path):
                os.unlink(compose_path)

    def test_pgrep_healthcheck_preserved(self):
        doc = self._compose_with_app(self._HC_APP)
        svc = doc["services"]["hcapp"]
        hc = svc.get("healthcheck", {})
        self.assertIn("test", hc)
        self.assertEqual(hc["test"], ["CMD-SHELL", "pgrep -f hcapp || exit 1"])
        self.assertEqual(hc["interval"], "120s")
        self.assertEqual(hc["retries"], 3)
        self.assertEqual(hc["start_period"], "60s")

    def test_http_healthcheck_preserved(self):
        doc = self._compose_with_app(self._HTTP_HC_APP)
        svc = doc["services"]["httpapp"]
        hc = svc.get("healthcheck", {})
        self.assertIn("test", hc)
        self.assertTrue(any("wget" in str(t) for t in hc["test"]))
        self.assertEqual(hc["interval"], "60s")
        self.assertEqual(hc["start_period"], "30s")


class TestProxyDependsOn(unittest.TestCase):
    """Apps using proxy network_mode get depends_on with service_healthy condition."""

    _PROXY_APP = {
        "name": "TESTAPP",
        "dashboard": "http://example.com",
        "link": "http://example.com",
        "compose_config": {
            "container_name": "${DEVICE_NAME}_testapp",
            "image": "example/testapp:latest",
            "restart": "always",
            "labels": [
                "com.centurylinklabs.watchtower.enable=true",
                "com.centurylinklabs.watchtower.scope=${M4B_WATCHTOWER_SCOPE}",
            ],
        },
        "compose_config_proxy": {
            "network_mode": "service:proxy",
            "hostname": None,
        },
    }

    def _compose_proxy_app(self, proxy_enabled=True):
        import copy
        from unittest.mock import patch

        app_cfg = {"supported-apps": {"active": True, "entries": [self._PROXY_APP]}}
        user_cfg = copy.deepcopy(_USER_CFG_BASE)
        user_cfg["proxies"]["enabled"] = proxy_enabled
        user_cfg["apps"] = {"testapp": {"enabled": True}}

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".yaml") as f:
            compose_path = f.name
        try:
            with patch("utils.compose_builder.check_img_arch_support", return_value=True):
                assemble_docker_compose(
                    _M4B_CFG, app_cfg, user_cfg, compose_path, is_main_instance=True
                )
            with open(compose_path) as f:
                return yaml.safe_load(f) or {}
        finally:
            if os.path.exists(compose_path):
                os.unlink(compose_path)

    def test_app_depends_on_proxy_healthy(self):
        doc = self._compose_proxy_app(proxy_enabled=True)
        app_svc = doc["services"]["testapp"]
        depends = app_svc.get("depends_on", {})
        self.assertIn("proxy", depends)
        self.assertEqual(depends["proxy"].get("condition"), "service_healthy")

    def test_app_has_no_depends_on_without_proxy(self):
        doc = self._compose_proxy_app(proxy_enabled=False)
        app_svc = doc["services"]["testapp"]
        self.assertNotIn("depends_on", app_svc)


if __name__ == "__main__":
    unittest.main()
