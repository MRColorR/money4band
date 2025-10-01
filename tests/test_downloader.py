import unittest
from unittest.mock import patch, mock_open, MagicMock
import requests
from utils.downloader import download_file


class TestDownloadFile(unittest.TestCase):
    @patch("utils.downloader.requests.get")
    def test_download_file_success(self, mock_get):
        """
        Test successful download of a file.
        """
        # Mock the response
        mock_response = MagicMock()
        mock_response.iter_content = lambda chunk_size: [b"test data"]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        # Mock the open function
        with patch("builtins.open", mock_open()) as mocked_file:
            download_file("http://example.com/testfile", "/tmp/testfile")
            mocked_file.assert_called_once_with("/tmp/testfile", "wb")
            mocked_file().write.assert_called_once_with(b"test data")

    @patch("utils.downloader.logging.error")
    @patch("utils.downloader.requests.get")
    def test_download_file_failure(self, mock_get, mock_logging_error):
        """
        Test download failure due to a request exception.
        """
        # Mock the response to raise an exception
        mock_get.side_effect = requests.RequestException("Error")

        with self.assertRaises(requests.RequestException):
            download_file("http://example.com/testfile", "/tmp/testfile")

        mock_logging_error.assert_called_once_with(
            "An error occurred while downloading the file from http://example.com/testfile: Error"
        )


if __name__ == "__main__":
    unittest.main()
