"""Tests for farewell and exit in fn_bye.py."""

import unittest
from unittest.mock import patch

from money4band.fn_bye import fn_bye


class TestFnBye(unittest.TestCase):
    @patch("money4band.fn_bye.sys.exit")
    @patch("money4band.fn_bye.time.sleep")
    @patch("money4band.fn_bye.cls")
    def test_fn_bye_exits(self, _cls, _sleep, mock_exit):
        config = {
            "system": {"sleep_time": 0},
            "farewell_messages": ["Goodbye!"],
        }
        fn_bye(config)
        mock_exit.assert_called_once_with(0)

    @patch("money4band.fn_bye.sys.exit")
    @patch("money4band.fn_bye.time.sleep")
    @patch("money4band.fn_bye.cls")
    def test_fn_bye_uses_sleep_time(self, _cls, mock_sleep, mock_exit):
        config = {"system": {"sleep_time": 5}}
        fn_bye(config)
        mock_sleep.assert_called_once_with(5)

    @patch("money4band.fn_bye.sys.exit")
    @patch("money4band.fn_bye.time.sleep")
    @patch("money4band.fn_bye.cls")
    def test_fn_bye_default_config(self, _cls, mock_sleep, mock_exit):
        """Uses defaults when config is minimal."""
        fn_bye({})
        mock_exit.assert_called_once_with(0)
        mock_sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
