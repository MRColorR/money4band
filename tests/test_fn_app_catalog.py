import io
import json
import os
import re
import unittest
from unittest.mock import patch

from money4band.apps.catalog import (
    _display_catalog,
    _manage_categories,
    fn_app_catalog,
)


def _strip_ansi(text: str) -> str:
    return re.compile(r"\x1b\[([0-9;]*m)").sub("", text)


def _collect_output(mock_print) -> str:
    lines = [call.args[0] if call.args else "" for call in mock_print.call_args_list]
    return _strip_ansi("\n".join(lines))


class TestFnAppCatalog(unittest.TestCase):
    _APP_CONFIG = {
        "supported-apps": {
            "active": True,
            "entries": [
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
            ],
        },
        "deprecated-apps": {
            "active": False,
            "entries": [
                {
                    "name": "GRASS",
                    "removal_reason": "Docker image unavailability",
                    "dashboard": "https://app.getgrass.io/dashboard",
                    "link": "https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f",
                    "compose_layer": "residential",
                },
            ],
        },
    }

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((200, 24)),
    )
    @patch("money4band.apps.catalog.sys")
    @patch("money4band.apps.catalog.print")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_wide_terminal_single_line_with_links(
        self, mock_input, mock_cls, mock_print, mock_sys, _mock_term
    ):
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

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((80, 24)),
    )
    @patch("money4band.apps.catalog.sys")
    @patch("money4band.apps.catalog.print")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_compact_mode_link_on_own_line(
        self, mock_input, mock_cls, mock_print, mock_sys, _mock_term
    ):
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

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((80, 24)),
    )
    @patch("money4band.apps.catalog.sys")
    @patch("money4band.apps.catalog.print")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_deprecated_apps_show_links_and_reason(
        self, mock_input, mock_cls, mock_print, mock_sys, _mock_term
    ):
        """Deprecated apps show referral link + removal reason (same format as supported)."""
        mock_input.return_value = ""
        mock_sys.stdout.reconfigure = lambda **kw: None

        fn_app_catalog(self._APP_CONFIG)
        out = _collect_output(mock_print)

        self.assertIn("GRASS", out)
        self.assertIn(
            "https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f", out
        )
        self.assertIn(">> Docker image unavailability", out)

    @patch("money4band.apps.catalog.logger.error")
    def test_fn_app_catalog_exception(self, mock_logging_error):
        """Test fn_app_catalog exception handling."""
        app_config = None
        with self.assertRaises((TypeError, AttributeError)):
            fn_app_catalog(app_config)
        mock_logging_error.assert_called_once()

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((200, 24)),
    )
    @patch("money4band.apps.catalog.sys")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_fn_app_catalog_returns_false_on_back(
        self, mock_input, mock_cls, mock_sys, _mock_term
    ):
        mock_input.return_value = "b"
        mock_sys.stdout.reconfigure = lambda **kw: None
        result = fn_app_catalog(self._APP_CONFIG)
        self.assertFalse(result)

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((200, 24)),
    )
    @patch("money4band.apps.catalog.sys")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_fn_app_catalog_returns_true_on_manage(
        self, mock_input, mock_cls, mock_sys, _mock_term
    ):
        # First call returns 'm' for manage, second call returns '' (back from manage)
        mock_input.side_effect = ["m", "b"]
        mock_sys.stdout.reconfigure = lambda **kw: None
        result = fn_app_catalog(self._APP_CONFIG)
        self.assertTrue(result)


class TestManageCategories(unittest.TestCase):
    _APP_CONFIG = {
        "supported-apps": {
            "active": True,
            "entries": [
                {"name": "APP1", "link": "", "compose_layer": "residential"},
            ],
        },
        "deprecated-apps": {
            "active": False,
            "entries": [
                {"name": "APP2", "link": "", "compose_layer": "universal"},
            ],
        },
    }

    @patch("money4band.apps.catalog.input", create=True, return_value="b")
    def test_back_exits(self, _inp):
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        _manage_categories(cfg, None)
        # No changes, should not crash

    @patch("money4band.apps.catalog.input", create=True, return_value="1")
    def test_toggle_category(self, _inp):
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        _manage_categories(cfg, None)
        # Category 1 was active, now should be False
        first_key = list(cfg.keys())[0]
        self.assertFalse(cfg[first_key]["active"])

    @patch("money4band.apps.catalog.input", create=True, return_value="1")
    def test_toggle_persists_to_file(self, _inp, tmp_path=None):
        import copy
        import tempfile

        cfg = copy.deepcopy(self._APP_CONFIG)
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            json.dump(cfg, f)
            cfg_path = f.name
        try:
            _manage_categories(cfg, cfg_path)
            saved = json.loads(open(cfg_path).read())
            first_key = list(saved.keys())[0]
            self.assertFalse(saved[first_key]["active"])
        finally:
            os.unlink(cfg_path)

    @patch("money4band.apps.catalog.input", create=True, return_value="xyz")
    def test_invalid_input(self, _inp, capsys=None):
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        _manage_categories(cfg, None)  # Should not crash


class TestDisplayCatalog(unittest.TestCase):
    _APP_CONFIG = {
        "supported-apps": {
            "active": True,
            "entries": [
                {
                    "name": "TESTAPP",
                    "link": "https://example.com",
                    "compose_layer": "residential",
                    "app_details": {"earnings": {"min_payout": "$5"}},
                },
            ],
        },
    }

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((200, 24)),
    )
    @patch("sys.stdout", new_callable=io.StringIO)
    def test_display_catalog_shows_app_names(self, mock_stdout, _mock_term):
        import copy

        _display_catalog(copy.deepcopy(self._APP_CONFIG))
        output = mock_stdout.getvalue()
        self.assertIn("TESTAPP", output)
        self.assertIn("residential", output)
        self.assertIn("$5", output)


class TestManageCategoriesEdgeCases(unittest.TestCase):
    _APP_CONFIG = {
        "supported-apps": {
            "active": True,
            "entries": [
                {"name": "A1", "link": "", "compose_layer": "residential"},
            ],
        },
        "deprecated-apps": {
            "active": False,
            "entries": [
                {"name": "A2", "link": "", "compose_layer": "universal"},
            ],
        },
    }

    @patch("money4band.apps.catalog.input", create=True, return_value="q")
    def test_quit_raises_system_exit(self, _inp):
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        with self.assertRaises(SystemExit):
            _manage_categories(cfg, None)

    @patch("money4band.apps.catalog.input", create=True, return_value="99")
    def test_out_of_range_selection_warns(self, _inp):
        """Selecting a number beyond category count should print 'Invalid'."""
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        _manage_categories(cfg, None)
        # Should not crash, active states unchanged
        self.assertTrue(cfg["supported-apps"]["active"])

    @patch("money4band.apps.catalog.input", create=True, return_value="")
    def test_empty_input_returns(self, _inp):
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        _manage_categories(cfg, None)
        # No change
        self.assertTrue(cfg["supported-apps"]["active"])

    def test_empty_config_shows_no_categories(self):
        """No categories found → prints message and returns."""
        _manage_categories({}, None)  # should not crash


class TestFnAppCatalogQuit(unittest.TestCase):
    _APP_CONFIG = {
        "supported-apps": {
            "active": True,
            "entries": [
                {"name": "X", "link": "", "compose_layer": "res"},
            ],
        },
    }

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((200, 24)),
    )
    @patch("money4band.apps.catalog.sys")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True, return_value="q")
    def test_q_raises_system_exit(self, _inp, _cls, mock_sys, _term):
        mock_sys.stdout.reconfigure = lambda **kw: None
        with self.assertRaises(SystemExit):
            fn_app_catalog(self._APP_CONFIG)


if __name__ == "__main__":
    unittest.main()
