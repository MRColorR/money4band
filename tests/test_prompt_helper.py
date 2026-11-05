import unittest
from unittest.mock import patch

from money4band.ui.prompt import (
    ask_email,
    ask_question_num,
    ask_question_yn,
    ask_string,
    ask_uuid,
)


class TestPromptHelper(unittest.TestCase):
    @patch("builtins.input", return_value="test@example.com")
    def test_ask_email_valid(self, mock_input):
        self.assertEqual(ask_email("Enter email:"), "test@example.com")

    @patch("builtins.input", side_effect=["", "test@example.com"])
    def test_ask_email_empty_then_valid(self, mock_input):
        self.assertEqual(ask_email("Enter email:"), "test@example.com")

    @patch("builtins.input", return_value="")
    def test_ask_string_returns_default_when_empty(self, mock_input):
        """When input is empty and a default is provided, the default is returned."""
        self.assertEqual(ask_string("Enter string:", default="fallback"), "fallback")

    @patch("builtins.input", return_value="non-empty string")
    def test_ask_string_not_empty(self, mock_input):
        self.assertEqual(ask_string("Enter string:"), "non-empty string")

    @patch("builtins.input", return_value="y")
    def test_ask_question_yn_yes(self, mock_input):
        self.assertTrue(ask_question_yn("Continue?"))

    @patch("builtins.input", return_value="n")
    def test_ask_question_yn_no(self, mock_input):
        self.assertFalse(ask_question_yn("Continue?"))

    @patch("builtins.input", return_value="abcd1234abcd1234abcd1234abcd1234")
    def test_ask_uuid_valid(self, mock_input):
        self.assertEqual(
            ask_uuid("Enter UUID:", 32), "abcd1234abcd1234abcd1234abcd1234"
        )

    @patch("builtins.input", side_effect=["", "abcd1234abcd1234abcd1234abcd1234"])
    def test_ask_uuid_empty_then_valid(self, mock_input):
        self.assertEqual(
            ask_uuid("Enter UUID:", 32), "abcd1234abcd1234abcd1234abcd1234"
        )

    # ------------------------------------------------------------------
    # ask_question_num
    # ------------------------------------------------------------------

    @patch("builtins.input", return_value="9090")
    def test_ask_question_num_valid(self, mock_input):
        self.assertEqual(ask_question_num("Port:"), 9090)

    @patch("builtins.input", return_value="")
    def test_ask_question_num_default(self, mock_input):
        self.assertEqual(ask_question_num("Port:", default=8088), 8088)

    @patch("builtins.input", side_effect=["abc", "1234"])
    def test_ask_question_num_invalid_then_valid(self, mock_input):
        self.assertEqual(ask_question_num("Port:"), 1234)

    @patch("builtins.input", side_effect=["100", "2000"])
    def test_ask_question_num_below_min(self, mock_input):
        self.assertEqual(ask_question_num("Port:", min_val=1024), 2000)

    @patch("builtins.input", side_effect=["70000", "50000"])
    def test_ask_question_num_above_max(self, mock_input):
        self.assertEqual(ask_question_num("Port:", max_val=65535), 50000)


if __name__ == "__main__":
    unittest.main()
