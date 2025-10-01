import unittest
from unittest.mock import patch, call
import os
from utils.cls import cls


class TestClsFunction(unittest.TestCase):
    @patch("os.system")
    @patch("utils.cls.logging.info")
    @patch("utils.cls.logging.error")
    def test_cls_success(self, mock_logging_error, mock_logging_info, mock_os_system):
        """
        Test that the cls function clears the console and logs the success message.
        """
        # Set up the os.system mock to return 0 (success)
        mock_os_system.return_value = 0

        cls()

        mock_os_system.assert_called_once_with("cls" if os.name == "nt" else "clear")
        mock_logging_info.assert_called_once_with("Console cleared successfully")
        mock_logging_error.assert_not_called()

    @patch("os.system", side_effect=Exception("Mocked error"))
    @patch("utils.cls.logging.info")
    @patch("utils.cls.logging.error")
    def test_cls_failure(self, mock_logging_error, mock_logging_info, mock_os_system):
        """
        Test that the cls function handles exceptions and logs the error message.
        """
        with self.assertRaises(Exception) as context:
            cls()

        mock_os_system.assert_called_once_with("cls" if os.name == "nt" else "clear")
        mock_logging_info.assert_not_called()
        mock_logging_error.assert_called_once_with(
            "Error clearing console: Mocked error"
        )
        self.assertEqual(str(context.exception), "Mocked error")


if __name__ == "__main__":
    unittest.main()
