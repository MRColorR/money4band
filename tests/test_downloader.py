import unittest
from unittest.mock import MagicMock, mock_open, patch

import requests

from utils.downloader import download_file


class TestDownloadFile(unittest.TestCase):
    @patch("utils.downloader.get_session")
    def test_download_file_success(self, mock_get_session):
        """Test successful download of a file."""
        mock_response = MagicMock()
        mock_response.iter_content = lambda chunk_size: [b"test data"]
        mock_response.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.get.return_value = mock_response
        mock_get_session.return_value = mock_session

        with patch("builtins.open", mock_open()) as mocked_file:
            download_file("http://example.com/testfile", "/tmp/testfile")
            mocked_file.assert_called_once_with("/tmp/testfile", "wb")
            mocked_file().write.assert_called_once_with(b"test data")

        # Verify timeout was passed
        _, kwargs = mock_session.get.call_args
        self.assertIn("timeout", kwargs)
        self.assertGreaterEqual(kwargs["timeout"], 15)

    @patch("utils.downloader.logging.error")
    @patch("utils.downloader.get_session")
    def test_download_file_failure(self, mock_get_session, mock_logging_error):
        """Test download failure due to a request exception."""
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.RequestException("Error")
        mock_get_session.return_value = mock_session

        with self.assertRaises(requests.RequestException):
            download_file("http://example.com/testfile", "/tmp/testfile")

        mock_logging_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
