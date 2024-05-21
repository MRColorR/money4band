import unittest
from unittest.mock import patch, MagicMock
import logging
import sys
from io import StringIO
from utils.fn_show_links import fn_show_links
import re

class TestFnShowLinks(unittest.TestCase):
    @patch('utils.fn_show_links.print')
    @patch('utils.fn_show_links.cls')
    @patch('utils.fn_show_links.input', create=True)
    def test_fn_show_links(self, mock_input, mock_cls, mock_print):
        """
        Test fn_show_links function.
        """
        # Mock input to avoid waiting for user input
        mock_input.return_value = ""

        # Prepare app_config sample data
        app_config = {
            "apps": [
                {
                    "name": "EARNAPP",
                    "dashboard": "https://earnapp.com/dashboard",
                    "link": "https://earnapp.com/i/3zulx7k",
                    "image": "fazalfarhan01/earnapp",
                    "flags": {
                        "--uuid": {
                            "length": 32
                        }
                    },
                    "claimURLBase": "To claim your node, after starting it, go to the app's dashboard and then visit the following link: https://earnapp.com/r/sdk-node-"
                },
                {
                    "name": "HONEYGAIN",
                    "dashboard": "https://dashboard.honeygain.com/",
                    "link": "https://r.honeygain.me/MINDL15721",
                    "image": "honeygain/honeygain",
                    "flags": {
                        "--email": {},
                        "--password": {}
                    }
                },
                {
                    "name": "GRASS",
                    "dashboard": "https://app.getgrass.io/dashboard",
                    "link": "https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f",
                    "image": "mrcolorrain/grass",
                    "flags": {
                        "--email": {},
                        "--password": {}
                    }
                }
            ],
            "extra-apps": [
                {
                    "name": "MYSTNODE",
                    "dashboard": "https://mystnodes.com/nodes",
                    "link": "https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9",
                    "image": "mysteriumnetwork/myst",
                    "flags": {
                        "--manual": {
                            "instructions": "Log into your device's mystnode local webdashboard, navigate to the Myst Node page and follow the onscreen instruction to complete the setup.\n\nDisclaimer: If you want to further optimize UPnP and port forwarding, consider setting manually 'network: host' for mystnode in your Docker compose. This may improve mystnode performance, but do this only if you know what you are doing and you are aware of potential security implications."
                        }
                    }
                }
            ],
            "removed-apps": []
        }

        # Capture the output
        captured_output = StringIO()
        sys.stdout = captured_output

        # Call the function
        fn_show_links(app_config)

        # Restore stdout
        sys.stdout = sys.__stdout__

        # Remove ANSI escape codes from the output
        output = captured_output.getvalue()
        ansi_escape = re.compile(r'\x1b\[([0-9;]*m)')
        clean_output = ansi_escape.sub('', output)

        # Collect printed lines from mock_print
        printed_lines = [call.args[0] for call in mock_print.call_args_list]
        printed_output = '\n'.join(printed_lines)

        # Remove ANSI escape codes from printed output
        clean_printed_output = ansi_escape.sub('', printed_output)

        # Assertions to check if the output contains the expected strings
        self.assertIn("Use CTRL+Click to open links or copy them:", clean_printed_output)
        self.assertIn("---APPS---", clean_printed_output)
        self.assertIn("EARNAPP: https://earnapp.com/i/3zulx7k", clean_printed_output)
        self.assertIn("HONEYGAIN: https://r.honeygain.me/MINDL15721", clean_printed_output)
        self.assertIn("GRASS: https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f", clean_printed_output)
        self.assertIn("---EXTRA-APPS---", clean_printed_output)
        self.assertIn("MYSTNODE: https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9", clean_printed_output)

    @patch('utils.fn_show_links.logging.error')
    def test_fn_show_links_exception(self, mock_logging_error):
        """
        Test fn_show_links function exception handling.
        """
        # Prepare app_config sample data that will raise an exception
        app_config = None

        with self.assertRaises(Exception):
            fn_show_links(app_config)

        mock_logging_error.assert_called_once_with("An error occurred in fn_show_links: 'NoneType' object has no attribute 'items'")

if __name__ == '__main__':
    unittest.main()
