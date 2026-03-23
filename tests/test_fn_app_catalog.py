import os
import re
import unittest
from unittest.mock import patch

from money4band.fn_app_catalog import fn_app_catalog


def _strip_ansi(text: str) -> str:
    return re.compile(r"\x1b\[([0-9;]*m)").sub("", text)


def _collect_output(mock_print) -> str:
    lines = [call.args[0] if call.args else "" for call in mock_print.call_args_list]
    return _strip_ansi("\n".join(lines))


class TestFnAppCatalog(unittest.TestCase):

    _APP_CONFIG = {
        "supported-apps": {"active": True, "entries": [
            {
                "name": "EARNAPP",
                "dashboard": "https://earnapp.com/dashboard",
                "link": "https://earnapp.com/i/3zulx7k",
                "compose_layer": "residential",
            },
            {
                "name": "HONEYGAIN",
                "dashboard": "https://dashboard.honeygain.com/",
                "link": "https://r.honeygain.me/MINDL15721",
                "compose_layer": "residential",
            },
            {
                "name": "MYSTNODE",
                "manual_onboard": True,
                "dashboard": "https://mystnodes.com/nodes",
                "link": "https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9",
                "compose_layer": "universal",
            },
        ]},
        "deprecated-apps": {"active": False, "entries": [
            {
                "name": "GRASS",
                "removal_reason": "Docker image unavailability",
                "dashboard": "https://app.getgrass.io/dashboard",
                "link": "https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f",
                "compose_layer": "residential",
            },
        ]},
    }

    @patch("money4band.fn_app_catalog.shutil.get_terminal_size", return_value=os.terminal_size((200, 24)))
    @patch("money4band.fn_app_catalog.sys")
    @patch("money4band.fn_app_catalog.print")
    @patch("money4band.fn_app_catalog.cls")
    @patch("money4band.fn_app_catalog.input", create=True)
    def test_wide_terminal_single_line_with_links(self, mock_input, mock_cls, mock_print, mock_sys, _mock_term):
        """Wide terminal shows Name, Link, Layer, Payout on a single line."""
        mock_input.return_value = ""
        mock_sys.stdout.reconfigure = lambda **kw: None

        fn_app_catalog(self._APP_CONFIG)
        out = _collect_output(mock_print)

        # Category headers
        self.assertIn("--- SUPPORTED-APPS [ACTIVE] ---", out)
        self.assertIn("--- DEPRECATED-APPS [INACTIVE] ---", out)

        # All four column headers present (wide = single-line mode)
        self.assertIn("Name", out)
        self.assertIn("Link", out)
        self.assertIn("Layer", out)
        self.assertIn("Payout", out)

        # Full referral links present and never truncated
        self.assertIn("https://earnapp.com/i/3zulx7k", out)
        self.assertIn("https://r.honeygain.me/MINDL15721", out)
        self.assertIn(
            "https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9",
            out,
        )

        # Dashboard links NOT shown
        self.assertNotIn("Dashboard", out)
        self.assertNotIn("earnapp.com/dashboard", out)

    @patch("money4band.fn_app_catalog.shutil.get_terminal_size", return_value=os.terminal_size((80, 24)))
    @patch("money4band.fn_app_catalog.sys")
    @patch("money4band.fn_app_catalog.print")
    @patch("money4band.fn_app_catalog.cls")
    @patch("money4band.fn_app_catalog.input", create=True)
    def test_compact_mode_link_on_own_line(self, mock_input, mock_cls, mock_print, mock_sys, _mock_term):
        """Narrow terminal uses compact mode: link on its own indented line."""
        mock_input.return_value = ""
        mock_sys.stdout.reconfigure = lambda **kw: None

        fn_app_catalog(self._APP_CONFIG)
        out = _collect_output(mock_print)

        # Compact header shows Name, Layer, Payout (no Link column)
        self.assertIn("Name", out)
        self.assertIn("Layer", out)
        self.assertIn("Payout", out)

        # Full links still present with -> prefix
        self.assertIn("-> https://earnapp.com/i/3zulx7k", out)
        self.assertIn("-> https://r.honeygain.me/MINDL15721", out)
        self.assertIn(
            "-> https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9",
            out,
        )

    @patch("money4band.fn_app_catalog.shutil.get_terminal_size", return_value=os.terminal_size((80, 24)))
    @patch("money4band.fn_app_catalog.sys")
    @patch("money4band.fn_app_catalog.print")
    @patch("money4band.fn_app_catalog.cls")
    @patch("money4band.fn_app_catalog.input", create=True)
    def test_deprecated_apps_show_links_and_reason(self, mock_input, mock_cls, mock_print, mock_sys, _mock_term):
        """Deprecated apps show referral link + removal reason (same format as supported)."""
        mock_input.return_value = ""
        mock_sys.stdout.reconfigure = lambda **kw: None

        fn_app_catalog(self._APP_CONFIG)
        out = _collect_output(mock_print)

        self.assertIn("GRASS", out)
        self.assertIn("https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f", out)
        self.assertIn(">> Docker image unavailability", out)

    @patch("money4band.fn_app_catalog.logger.error")
    def test_fn_app_catalog_exception(self, mock_logging_error):
        """Test fn_app_catalog exception handling."""
        app_config = None
        with self.assertRaises(Exception):
            fn_app_catalog(app_config)
        mock_logging_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
