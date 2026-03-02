import os
import unittest

from utils.loader import load_json_config


class TestAppConfigCommands(unittest.TestCase):
    def test_sensitive_commands_are_exec_form_lists(self):
        app_config_path = os.path.join("config", "app-config.json")
        app_config = load_json_config(app_config_path)
        apps_by_name = {app["name"]: app for app in app_config.get("apps", [])}

        honeygain_cmd = apps_by_name["HONEYGAIN"]["compose_config"].get("command")
        iproyal_cmd = apps_by_name["IPROYALPAWNS"]["compose_config"].get("command")
        traff_cmd = apps_by_name["TRAFFMONETIZER"]["compose_config"].get("command")

        self.assertIsInstance(honeygain_cmd, list)
        self.assertIsInstance(iproyal_cmd, list)
        self.assertIsInstance(traff_cmd, list)

        self.assertIn("${HONEYGAIN_PASSWORD}", honeygain_cmd)
        self.assertIn("-password=${IPROYALPAWNS_PASSWORD}", iproyal_cmd)
        self.assertIn("${TRAFFMONETIZER_TOKEN}", traff_cmd)


if __name__ == "__main__":
    unittest.main()
