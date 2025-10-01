import unittest
from unittest.mock import patch
from utils.prompt_helper import ask_email, ask_string, ask_question_yn, ask_uuid


class TestPromptHelper(unittest.TestCase):
    @patch("builtins.input", return_value="test@example.com")
    def test_ask_email_valid(self, mock_input):
        self.assertEqual(ask_email("Enter email:"), "test@example.com")

    @patch("builtins.input", side_effect=["", "test@example.com"])
    def test_ask_email_empty_then_valid(self, mock_input):
        self.assertEqual(ask_email("Enter email:"), "test@example.com")

    @patch("builtins.input", return_value="")
    def test_ask_string_empty_allowed(self, mock_input):
        self.assertEqual(ask_string("Enter string:", empty_allowed=True), "")

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


if __name__ == "__main__":
    unittest.main()
