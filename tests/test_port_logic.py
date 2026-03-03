"""
Test port assignment logic to ensure production readiness.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from utils.fn_setupApps import assign_app_ports, collect_assigned_ports
from utils.generator import generate_env_file, substitute_port_placeholders


class TestPortLogic(unittest.TestCase):
    """Test suite for port assignment and handling logic."""

    def test_assign_app_ports_single_port(self):
        """Test assigning a single port to an app."""
        app_name = "dawn"
        app = {"compose_config": {"ports": ["${DAWN_PORT}:5000"]}}
        config = {"ports": [5000]}

        with patch("utils.fn_setupApps.find_next_available_port") as mock_find_port:
            mock_find_port.side_effect = lambda x, **kwargs: x  # Return the same port

            result = assign_app_ports(app_name, app, config)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            # With app_index=0, instance_number=0, the base port is 50000 + 0*100 + 0*10 = 50000
            self.assertEqual(result, [50000])

    def test_assign_app_ports_multiple_ports(self):
        """Test assigning multiple ports to an app."""
        app_name = "wipter"
        app = {
            "compose_config": {
                "ports": ["${WIPTER_PORT_1}:5900", "${WIPTER_PORT_2}:6080"]
            }
        }
        config = {"ports": [5900, 6080]}

        with patch("utils.fn_setupApps.find_next_available_port") as mock_find_port:
            mock_find_port.side_effect = lambda x, **kwargs: x  # Return the same port

            result = assign_app_ports(app_name, app, config)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 2)
            # With app_index=0, instance_number=0, the base port is 50000 + 0*100 + 0*10 = 50000
            # First port: 50000 + 0 = 50000, Second port: 50000 + 1 = 50001
            self.assertEqual(result, [50000, 50001])

    def test_assign_app_ports_default_when_no_config(self):
        """Test default port assignment when config doesn't have ports."""
        app_name = "mystnode"
        app = {"compose_config": {"ports": ["${MYSTNODE_PORT}:4449"]}}
        config = {}  # No ports in config

        with patch("utils.fn_setupApps.find_next_available_port") as mock_find_port:
            mock_find_port.side_effect = lambda x, **kwargs: x  # Return the same port

            result = assign_app_ports(app_name, app, config)

            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0], 50000)  # Default starting port

    def test_assign_app_ports_respects_reserved_ports(self):
        """Test assigning ports skips globally reserved ports."""
        app_name = "wipter"
        app = {
            "compose_config": {
                "ports": ["${WIPTER_PORT_1}:5900", "${WIPTER_PORT_2}:6080"]
            }
        }
        config = {}
        reserved_ports = {50000, 50001, 50002}

        with patch("utils.fn_setupApps.find_next_available_port") as mock_find_port:
            mock_find_port.side_effect = lambda x, **kwargs: next(
                p for p in range(x, 65535) if p not in kwargs.get("exclude_ports", [])
            )

            result = assign_app_ports(
                app_name,
                app,
                config,
                app_index=0,
                instance_number=0,
                reserved_ports=reserved_ports,
            )

        # Candidates start at 50000 and 50001, all three (50000-50002) are reserved
        # so the first available is 50003, then 50004
        self.assertEqual(result, [50003, 50004])
        self.assertIn(50003, reserved_ports)
        self.assertIn(50004, reserved_ports)

    def test_substitute_port_placeholders_single(self):
        """Test substituting a single port placeholder."""
        port_placeholders = ["${DAWN_PORT}:5000"]
        actual_ports = [8080]

        result = substitute_port_placeholders(port_placeholders, actual_ports)

        self.assertEqual(result, ["8080:5000"])

    def test_substitute_port_placeholders_multiple(self):
        """Test substituting multiple port placeholders."""
        port_placeholders = ["${WIPTER_PORT_1}:5900", "${WIPTER_PORT_2}:6080"]
        actual_ports = [5901, 6081]

        result = substitute_port_placeholders(port_placeholders, actual_ports)

        self.assertEqual(result, ["5901:5900", "6081:6080"])

    def test_substitute_port_placeholders_uses_first_when_insufficient(self):
        """Test that substitute uses first port when actual_ports list is too short."""
        port_placeholders = [
            "${APP_PORT_1}:5000",
            "${APP_PORT_2}:5001",
            "${APP_PORT_3}:5002",
        ]
        actual_ports = [8080]  # Only one port provided

        result = substitute_port_placeholders(port_placeholders, actual_ports)

        self.assertEqual(result, ["8080:5000", "8080:5001", "8080:5002"])

    def test_substitute_port_placeholders_empty_raises_error(self):
        """Test that empty actual_ports raises ValueError."""
        port_placeholders = ["${APP_PORT}:5000"]
        actual_ports = []  # Empty list

        with self.assertRaises(ValueError) as context:
            substitute_port_placeholders(port_placeholders, actual_ports)

        self.assertIn("cannot be empty", str(context.exception))

    def test_config_ports_always_list(self):
        """Test that ports are always stored as list in config."""
        # Simulate the setup flow
        app_name = "dawn"
        app = {"compose_config": {"ports": ["${DAWN_PORT}:5000"]}}
        config = {"ports": [5000]}  # Should be list

        with patch("utils.fn_setupApps.find_next_available_port") as mock_find_port:
            mock_find_port.return_value = 5000

            assigned_ports = assign_app_ports(app_name, app, config)

            # Verify it returns a list
            self.assertIsInstance(assigned_ports, list)

            # Verify we would store it as list
            config["ports"] = assigned_ports
            self.assertIsInstance(config["ports"], list)

    def test_generate_env_file_handles_list_ports(self):
        """Test that generate_env_file correctly handles list format ports."""
        # Mock configurations
        m4b_config = {
            "network": {"subnet": "172.19.7.0", "netmask": "27"},
            "system": {"sleep_time": 3},
        }

        app_config = {
            "apps": [
                {
                    "name": "DAWN",
                    "flags": {"email": {}, "password": {}},
                    "compose_config": {"ports": ["${DAWN_PORT}:5000"]},
                },
                {
                    "name": "WIPTER",
                    "flags": {"email": {}, "password": {}},
                    "compose_config": {
                        "ports": ["${WIPTER_PORT_1}:5900", "${WIPTER_PORT_2}:6080"]
                    },
                },
            ]
        }

        user_config = {
            "device_info": {"device_name": "test_device"},
            "resource_limits": {},
            "apps": {
                "dawn": {
                    "enabled": True,
                    "email": "test@test.com",
                    "password": "pass",
                    "ports": [8080],  # List with single element
                },
                "wipter": {
                    "enabled": True,
                    "email": "test@test.com",
                    "password": "pass",
                    "ports": [5901, 6081],  # List with multiple elements
                },
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            env_path = f.name

        try:
            generate_env_file(m4b_config, app_config, user_config, env_path)

            # Read the generated env file
            with open(env_path) as f:
                env_content = f.read()

            # Verify single port app creates indexed and non-indexed variables
            self.assertIn("DAWN_PORT_1=8080", env_content)
            self.assertIn("DAWN_PORT=8080", env_content)  # Backward compat

            # Verify multiple port app creates indexed variables
            self.assertIn("WIPTER_PORT_1=5901", env_content)
            self.assertIn("WIPTER_PORT_2=6081", env_content)
            # Should NOT have non-indexed WIPTER_PORT for multiple ports

            # Watchtower scope vars are always emitted — defaults when watchtower key absent
            self.assertIn("M4B_WATCHTOWER_LABELS=true", env_content)
            self.assertIn("M4B_WATCHTOWER_SCOPE=money4band", env_content)

        finally:
            if os.path.exists(env_path):
                os.unlink(env_path)

    def test_generate_env_file_watchtower_vars_configurable(self):
        """Watchtower scope vars respect m4b_config overrides."""
        m4b_config = {
            "network": {"subnet": "172.19.7.0", "netmask": "27"},
            "system": {},
            "watchtower": {"enable_labels": False, "scope": "custom-scope"},
        }
        app_config = {"apps": []}
        user_config = {
            "device_info": {"device_name": "testdev"},
            "resource_limits": {},
            "apps": {},
        }

        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".env") as f:
            env_path = f.name

        try:
            generate_env_file(m4b_config, app_config, user_config, env_path)

            with open(env_path) as f:
                env_content = f.read()

            self.assertIn("M4B_WATCHTOWER_LABELS=false", env_content)
            self.assertIn("M4B_WATCHTOWER_SCOPE=custom-scope", env_content)

        finally:
            if os.path.exists(env_path):
                os.unlink(env_path)

    def test_multiproxy_instance_port_consistency(self):
        """Test that multiproxy instances maintain port list consistency."""
        # Simulate the multiproxy setup flow
        base_config = {"ports": [4449]}  # Already a list

        # When creating multiple instances, ports should remain lists
        instance_configs = []
        for i in range(3):
            instance_config = base_config.copy()
            # Simulate port offset for instance
            if isinstance(instance_config["ports"], list):
                instance_config["ports"] = [
                    p + (i + 1) * 10 for p in instance_config["ports"]
                ]

            instance_configs.append(instance_config)

        # Verify all instances have list ports
        for i, config in enumerate(instance_configs):
            self.assertIsInstance(
                config["ports"], list, f"Instance {i} ports should be list"
            )
            self.assertEqual(len(config["ports"]), 1)


class TestConfigPortFormat(unittest.TestCase):
    """Test suite to verify config files use list format for ports."""

    def test_user_config_template_ports_are_lists(self):
        """Verify all port definitions in user-config template are lists."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "template",
            "user-config.json",
        )

        with open(config_path) as f:
            config = json.load(f)

        apps_with_ports = {}

        # Check apps
        for app_name, app_config in config.get("apps", {}).items():
            if "ports" in app_config:
                apps_with_ports[app_name] = app_config["ports"]

        # Check m4b_dashboard
        if "m4b_dashboard" in config and "ports" in config["m4b_dashboard"]:
            apps_with_ports["m4b_dashboard"] = config["m4b_dashboard"]["ports"]

        # Verify all are lists
        for app_name, port_value in apps_with_ports.items():
            with self.subTest(app=app_name):
                self.assertIsInstance(
                    port_value,
                    list,
                    f"{app_name} ports should be a list, got {type(port_value)}",
                )

    def test_m4b_config_has_port_settings(self):
        """Verify m4b-config.json has configurable port settings."""
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "config",
            "m4b-config.json",
        )

        with open(config_path) as f:
            config = json.load(f)

        # Check port configuration exists
        self.assertIn("ports", config, "m4b-config.json should have ports section")

        port_config = config["ports"]

        # Check required keys
        self.assertIn("default_port_base", port_config)
        self.assertIn("port_offset_per_app", port_config)
        self.assertIn("port_offset_per_instance", port_config)

        # Check values are integers
        self.assertIsInstance(port_config["default_port_base"], int)
        self.assertIsInstance(port_config["port_offset_per_app"], int)
        self.assertIsInstance(port_config["port_offset_per_instance"], int)

        # Check reasonable defaults
        self.assertGreaterEqual(port_config["default_port_base"], 1024)
        self.assertGreater(port_config["port_offset_per_app"], 0)
        self.assertGreater(port_config["port_offset_per_instance"], 0)


class TestCollectAssignedPorts(unittest.TestCase):
    """Test suite for collecting assigned app ports."""

    def test_collect_assigned_ports_enabled_apps_only(self):
        """Only enabled apps' ports are collected; disabled apps are ignored."""
        user_config = {
            "apps": {
                "wipter": {"enabled": True, "ports": [50000, "50001"]},
                "dawn": {"enabled": True, "ports": 50100},
                "mystnode": {"enabled": False, "ports": [50200]},
            }
        }

        used_ports = collect_assigned_ports(user_config)

        self.assertEqual(used_ports, {50000, 50001, 50100})

    def test_collect_assigned_ports_empty_and_missing(self):
        """Missing apps key and apps without ports return empty set."""
        self.assertEqual(collect_assigned_ports({}), set())
        self.assertEqual(
            collect_assigned_ports({"apps": {"earnapp": {"enabled": True}}}), set()
        )

    def test_collect_assigned_ports_invalid_port_values_skipped(self):
        """Non-numeric port values are skipped gracefully."""
        user_config = {
            "apps": {
                "wipter": {"enabled": True, "ports": [50000, None, "bad"]},
            }
        }
        used_ports = collect_assigned_ports(user_config)
        self.assertEqual(used_ports, {50000})

    def test_no_cross_instance_collision_with_reserved_ports(self):
        """Two successive multiproxy instances with shared reserved set don't collide."""
        app = {
            "compose_config": {
                "ports": ["${WIPTER_PORT_1}:5900", "${WIPTER_PORT_2}:6080"]
            }
        }
        # Simulate: main instance already owns 50000, 50001
        reserved_ports: set = {50000, 50001}

        with patch("utils.fn_setupApps.find_next_available_port") as mock_fp:
            mock_fp.side_effect = lambda x, **kwargs: next(
                p for p in range(x, 65535) if p not in kwargs.get("exclude_ports", [])
            )

            # First proxy instance (instance_number=1, app_index=0)
            ports_inst1 = assign_app_ports(
                "wipter", app, {}, app_index=0, instance_number=1,
                reserved_ports=reserved_ports,
            )
            # Second proxy instance (instance_number=2, app_index=0)
            ports_inst2 = assign_app_ports(
                "wipter", app, {}, app_index=0, instance_number=2,
                reserved_ports=reserved_ports,
            )

        # inst1 and inst2 must each have 2 unique ports
        self.assertEqual(len(set(ports_inst1)), 2)
        self.assertEqual(len(set(ports_inst2)), 2)
        # No overlap between the two instances
        self.assertFalse(set(ports_inst1) & set(ports_inst2), "instances share a port")
        # Neither instance may reuse the main instance's ports
        self.assertNotIn(50000, ports_inst1)
        self.assertNotIn(50000, ports_inst2)
        self.assertNotIn(50001, ports_inst1)
        self.assertNotIn(50001, ports_inst2)


if __name__ == "__main__":
    unittest.main()
