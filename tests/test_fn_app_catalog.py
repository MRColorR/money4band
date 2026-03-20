import re
import unittest
from unittest.mock import patch

from utils.fn_app_catalog import fn_app_catalog


class TestFnAppCatalog(unittest.TestCase):
    @patch("utils.fn_app_catalog.print")
    @patch("utils.fn_app_catalog.cls")
    @patch("utils.fn_app_catalog.input", create=True)
    def test_fn_app_catalog(self, mock_input, mock_cls, mock_print):
        """
        Test fn_app_catalog shows active and inactive categories.
        """
        # Mock input to avoid waiting for user input
        mock_input.return_value = ""

        # Prepare app_config sample data with active + removed categories
        app_config = {
            "supported-apps": {"active": True, "entries": [
                {
                    "name": "EARNAPP",
                    "dashboard": "https://earnapp.com/dashboard",
                    "link": "https://earnapp.com/i/3zulx7k",
                    "image": "fazalfarhan01/earnapp",
                    "flags": {"--uuid": {"length": 32}},
                    "claimURLBase": "To claim your node, after starting it, go to the app's dashboard and then visit the following link: https://earnapp.com/r/sdk-node-",
                },
                {
                    "name": "HONEYGAIN",
                    "dashboard": "https://dashboard.honeygain.com/",
                    "link": "https://r.honeygain.me/MINDL15721",
                    "image": "honeygain/honeygain",
                    "flags": {"--email": {}, "--password": {}},
                },
                {
                    "name": "MYSTNODE",
                    "manual_onboard": True,
                    "dashboard": "https://mystnodes.com/nodes",
                    "link": "https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9",
                    "image": "mysteriumnetwork/myst",
                    "flags": {
                        "--manual": {
                            "instructions": "Log into your device's mystnode local webdashboard..."
                        }
                    },
                },
            ]},
            "deprecated-apps": {"active": False, "entries": [
                {
                    "name": "GRASS",
                    "removal_reason": "Docker image unavailability",
                    "dashboard": "https://app.getgrass.io/dashboard",
                    "link": "https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f",
                    "image": "mrcolorrain/grass",
                    "flags": {"--email": {}, "--password": {}},
                },
            ]},
        }

        # Call the function
        fn_app_catalog(app_config)

        # Collect printed lines from mock_print
        printed_lines = [
            call.args[0] if call.args else ""
            for call in mock_print.call_args_list
        ]
        printed_output = "\n".join(printed_lines)

        # Remove ANSI escape codes from printed output
        ansi_escape = re.compile(r"\x1b\[([0-9;]*m)")
        clean_printed_output = ansi_escape.sub("", printed_output)

        # Active category assertions
        self.assertIn("--- SUPPORTED-APPS [ACTIVE] ---", clean_printed_output)
        self.assertIn("EARNAPP: https://earnapp.com/i/3zulx7k", clean_printed_output)
        self.assertIn(
            "HONEYGAIN: https://r.honeygain.me/MINDL15721", clean_printed_output
        )
        self.assertIn(
            "MYSTNODE: https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9",
            clean_printed_output,
        )

        # Removed category assertions — header + removal reason
        self.assertIn("--- DEPRECATED-APPS [INACTIVE] ---", clean_printed_output)
        self.assertIn(
            "GRASS: https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f",
            clean_printed_output,
        )
        self.assertIn("(Docker image unavailability)", clean_printed_output)

    @patch("utils.fn_app_catalog.logging.error")
    def test_fn_app_catalog_exception(self, mock_logging_error):
        """
        Test fn_app_catalog exception handling.
        """
        # Prepare app_config sample data that will raise an exception
        app_config = None

        with self.assertRaises(Exception):
            fn_app_catalog(app_config)

        mock_logging_error.assert_called_once_with(
            "An error occurred in fn_app_catalog: 'NoneType' object has no attribute 'items'"
        )


if __name__ == "__main__":
    unittest.main()
