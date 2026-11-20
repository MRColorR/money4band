import io
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
        "supported": {
            "active": True,
            "entries": [
                {
                    "name": "EARNAPP",
                    "dashboard": "https://earnapp.com/dashboard",
                    "referrals": [
                        {
                            "url": "https://earnapp.com/i/3zulx7k",
                            "contributor": "MRColorR",
                        }
                    ],
                    "profile": "residential",
                },
                {
                    "name": "HONEYGAIN",
                    "_source": "community",
                    "dashboard": "https://dashboard.honeygain.com/",
                    "referrals": [
                        {
                            "url": "https://r.honeygain.me/MINDL15721",
                            "contributor": "MRColorR",
                        }
                    ],
                    "profile": "residential",
                },
                {
                    "name": "MYSTNODE",
                    "manual_onboard": True,
                    "dashboard": "https://mystnodes.com/nodes",
                    "referrals": [
                        {
                            "url": "https://mystnodes.co/?referral_code=Tc7RaS7Fm12K3Xun6mlU9q9hbnjojjl9aRBW8ZA9",
                            "contributor": "MRColorR",
                        }
                    ],
                    "profile": "universal",
                },
            ],
        },
        "deprecated": {
            "active": False,
            "entries": [
                {
                    "name": "GRASS",
                    "additional_details": "Docker image unavailability",
                    "dashboard": "https://app.getgrass.io/dashboard",
                    "referrals": [
                        {
                            "url": "https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f",
                            "contributor": "MRColorR",
                        }
                    ],
                    "profile": "residential",
                },
            ],
        },
    }

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((200, 24)),
    )
    @patch("money4band.apps.catalog.print")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_wide_terminal_single_line_with_links(
        self, mock_input, mock_cls, mock_print, _mock_term
    ):
        """Wide terminal shows Name, Link, Layer, Payout on a single line."""
        mock_input.return_value = ""

        fn_app_catalog(self._APP_CONFIG)
        out = _collect_output(mock_print)

        # Category headers
        self.assertIn("--- SUPPORTED [ACTIVE] ---", out)
        self.assertIn("--- DEPRECATED [INACTIVE] ---", out)

        # All four column headers present (wide = single-line mode)
        self.assertIn("Name", out)
        self.assertIn("Link", out)
        self.assertIn("Layer", out)
        self.assertIn("Payout", out)
        self.assertIn("Source", out)
        self.assertRegex(out, r"HONEYGAIN\s+community")
        self.assertRegex(out, r"EARNAPP\s+builtin")

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
    @patch("money4band.apps.catalog.print")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_compact_mode_link_on_own_line(
        self, mock_input, mock_cls, mock_print, _mock_term
    ):
        """Narrow terminal uses compact mode: link on its own indented line."""
        mock_input.return_value = ""

        fn_app_catalog(self._APP_CONFIG)
        out = _collect_output(mock_print)

        # Compact header shows Name, Layer, Payout (no Link column)
        self.assertIn("Name", out)
        self.assertIn("Layer", out)
        self.assertIn("Payout", out)
        self.assertIn("Source", out)
        self.assertRegex(out, r"HONEYGAIN\s+community")

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
    @patch("money4band.apps.catalog.print")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_deprecated_apps_keep_links_without_inline_notes(
        self, mock_input, mock_cls, mock_print, _mock_term
    ):
        """Archived entries remain visible; long notes belong to the detail view."""
        mock_input.return_value = ""

        fn_app_catalog(self._APP_CONFIG)
        out = _collect_output(mock_print)

        self.assertIn("GRASS", out)
        self.assertIn(
            "https://app.getgrass.io/register/?referralCode=qyvJmxgNUhcLo2f", out
        )
        self.assertNotIn("Docker image unavailability", out)
        self.assertIn("App details", out)

    @patch("money4band.apps.info.show_app_detail")
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", side_effect=["i", "grass", ""], create=True)
    def test_details_are_accessible_from_interactive_menu(self, _input, _cls, detail):
        self.assertTrue(fn_app_catalog(self._APP_CONFIG))
        detail.assert_called_once_with(self._APP_CONFIG, "grass")

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
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_fn_app_catalog_returns_false_on_back(
        self, mock_input, mock_cls, _mock_term
    ):
        mock_input.return_value = "b"
        result = fn_app_catalog(self._APP_CONFIG)
        self.assertFalse(result)

    @patch(
        "money4band.apps.catalog.shutil.get_terminal_size",
        return_value=os.terminal_size((200, 24)),
    )
    @patch("money4band.apps.catalog.cls")
    @patch("money4band.apps.catalog.input", create=True)
    def test_fn_app_catalog_returns_true_on_manage(
        self, mock_input, mock_cls, _mock_term
    ):
        # First call returns 'm' for manage, second call returns '' (back from manage)
        mock_input.side_effect = ["m", "b"]
        result = fn_app_catalog(self._APP_CONFIG)
        self.assertTrue(result)


class TestManageCategories(unittest.TestCase):
    _APP_CONFIG = {
        "supported": {
            "active": True,
            "entries": [
                {"name": "APP1", "link": "", "profile": "residential"},
            ],
        },
        "deprecated": {
            "active": False,
            "entries": [
                {"name": "APP2", "link": "", "profile": "universal"},
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
        from pathlib import Path

        from money4band.core.catalog_overrides import load_user_overrides
        from money4band.core.catalog_store import default_envelope, write_envelope

        cfg = copy.deepcopy(self._APP_CONFIG)
        with tempfile.TemporaryDirectory() as folder:
            cfg_path = str(Path(folder) / "m4b-config.json")
            envelope = default_envelope()
            first_key = list(cfg.keys())[0]
            envelope["categories"][first_key] = {"active": True}
            write_envelope(envelope, cfg_path)
            shipped = Path(cfg_path).read_bytes()

            _manage_categories(cfg, cfg_path)
            assert Path(cfg_path).read_bytes() == shipped
            overrides = load_user_overrides(Path(folder) / "user-config.json")
            assert overrides["categories"][first_key]["active"] is False

    @patch("money4band.apps.catalog.input", create=True, return_value="xyz")
    def test_invalid_input(self, _inp, capsys=None):
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        _manage_categories(cfg, None)  # Should not crash


class TestDisplayCatalog(unittest.TestCase):
    _APP_CONFIG = {
        "supported": {
            "active": True,
            "entries": [
                {
                    "name": "TESTAPP",
                    "referrals": [
                        {"url": "https://example.com", "contributor": "MRColorR"}
                    ],
                    "profile": "residential",
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
        "supported": {
            "active": True,
            "entries": [
                {"name": "A1", "link": "", "profile": "residential"},
            ],
        },
        "deprecated": {
            "active": False,
            "entries": [
                {"name": "A2", "link": "", "profile": "universal"},
            ],
        },
    }

    @patch("money4band.apps.catalog.input", create=True, return_value="99")
    def test_out_of_range_selection_warns(self, _inp):
        """Selecting a number beyond category count should print 'Invalid'."""
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        _manage_categories(cfg, None)
        # Should not crash, active states unchanged
        self.assertTrue(cfg["supported"]["active"])

    @patch("money4band.apps.catalog.input", create=True, return_value="")
    def test_empty_input_returns(self, _inp):
        import copy

        cfg = copy.deepcopy(self._APP_CONFIG)
        _manage_categories(cfg, None)
        # No change
        self.assertTrue(cfg["supported"]["active"])

    def test_empty_config_shows_no_categories(self):
        """No categories found -> prints message and returns."""
        _manage_categories({}, None)  # should not crash


if __name__ == "__main__":
    unittest.main()
