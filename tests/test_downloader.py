import unittest
from unittest.mock import MagicMock, mock_open, patch

import httpx

from money4band.network.downloader import download_file


class TestDownloadFile(unittest.TestCase):
    @patch("money4band.network.downloader.get_client")
    def test_download_file_success(self, mock_get_client):
        """Test successful download of a file."""
        mock_response = MagicMock()
        mock_response.iter_bytes = lambda chunk_size: iter([b"test data"])
        mock_response.raise_for_status = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_client = MagicMock()
        mock_client.stream.return_value = mock_response
        mock_get_client.return_value = mock_client

        with patch("builtins.open", mock_open()) as mocked_file:
            download_file("http://example.com/testfile", "/tmp/testfile")
            mocked_file.assert_called_once_with("/tmp/testfile", "wb")
            mocked_file().write.assert_called_once_with(b"test data")

        # Verify stream was called with timeout
        mock_client.stream.assert_called_once()
        _, kwargs = mock_client.stream.call_args
        self.assertIn("timeout", kwargs)
        self.assertGreaterEqual(kwargs["timeout"], 15)

    @patch("money4band.network.downloader.logger.error")
    @patch("money4band.network.downloader.get_client")
    def test_download_file_failure(self, mock_get_client, mock_logging_error):
        """Test download failure due to an HTTP error."""
        mock_client = MagicMock()
        mock_client.stream.side_effect = httpx.HTTPError("Error")
        mock_get_client.return_value = mock_client

        with self.assertRaises(httpx.HTTPError):
            download_file("http://example.com/testfile", "/tmp/testfile")

        mock_logging_error.assert_called_once()


if __name__ == "__main__":
    unittest.main()
