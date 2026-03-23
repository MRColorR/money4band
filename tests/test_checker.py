import unittest
from unittest.mock import MagicMock, patch

import requests

import money4band.http_client as http_client_mod
from money4band.checker import (
    check_img_arch_support,
    fetch_docker_tags,
    get_compatible_tag,
)
from money4band.http_client import configure, get_session

# Realistic Docker Hub API response fragments for testing
DOCKERHUB_TAGS_RESPONSE = {
    "results": [
        {
            "name": "latest",
            "images": [
                {"architecture": "amd64", "os": "linux"},
                {"architecture": "arm64", "os": "linux"},
            ],
        },
        {
            "name": "lite",
            "images": [
                {"architecture": "amd64", "os": "linux"},
            ],
        },
    ]
}

GHCR_TAGS_RESPONSE = {"tags": ["latest", "v1.0", "v2.0"]}


class TestConfigure(unittest.TestCase):
    def tearDown(self):
        # Reset module globals after each test
        configure({
            "system": {
                "registry_request_timeout": 15,
                "registry_max_retries": 3,
            }
        })

    def test_configure_overrides_defaults(self):
        configure({
            "system": {
                "registry_request_timeout": 30,
                "registry_max_retries": 5,
            }
        })
        self.assertEqual(http_client_mod.REQUEST_TIMEOUT, 30)
        self.assertEqual(http_client_mod.MAX_RETRIES, 5)

    def test_configure_keeps_defaults_when_keys_missing(self):
        configure({"system": {}})
        self.assertEqual(http_client_mod.REQUEST_TIMEOUT, 15)
        self.assertEqual(http_client_mod.MAX_RETRIES, 3)

    def test_configure_handles_empty_config(self):
        configure({})
        self.assertEqual(http_client_mod.REQUEST_TIMEOUT, 15)
        self.assertEqual(http_client_mod.MAX_RETRIES, 3)


class TestGetSession(unittest.TestCase):
    def test_session_has_retry_adapter(self):
        session = get_session()
        adapter = session.get_adapter("https://example.com")
        self.assertEqual(adapter.max_retries.total, 3)
        self.assertIn(429, adapter.max_retries.status_forcelist)
        self.assertIn(503, adapter.max_retries.status_forcelist)

    def test_session_respects_configured_retries(self):
        configure({"system": {"registry_max_retries": 7}})
        session = get_session()
        adapter = session.get_adapter("https://example.com")
        self.assertEqual(adapter.max_retries.total, 7)
        # Reset
        configure({"system": {"registry_max_retries": 3}})


class TestFetchDockerTags(unittest.TestCase):
    @patch("money4band.checker.get_session")
    def test_dockerhub_success(self, mock_get_session):
        mock_resp = MagicMock()
        mock_resp.json.return_value = DOCKERHUB_TAGS_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_get_session.return_value = mock_session

        result = fetch_docker_tags("honeygain/honeygain")

        mock_session.get.assert_called_once()
        call_url = mock_session.get.call_args[0][0]
        self.assertIn("registry.hub.docker.com", call_url)
        self.assertIn("honeygain/honeygain", call_url)
        self.assertEqual(result, DOCKERHUB_TAGS_RESPONSE)

    @patch("money4band.checker.get_session")
    def test_ghcr_success(self, mock_get_session):
        mock_resp = MagicMock()
        mock_resp.json.return_value = GHCR_TAGS_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_get_session.return_value = mock_session

        result = fetch_docker_tags("ghcr.io/techroy23/docker-wipter")

        call_url = mock_session.get.call_args[0][0]
        self.assertIn("ghcr.io", call_url)
        # GHCR response is normalized to Docker Hub-like structure
        self.assertIn("results", result)
        tag_names = [t["name"] for t in result["results"]]
        self.assertEqual(tag_names, ["latest", "v1.0", "v2.0"])

    @patch("money4band.checker.get_session")
    def test_connection_error_returns_none(self, mock_get_session):
        """KI-003 core fix: network failure must return None, not crash."""
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.ConnectionError("DNS resolution failed")
        mock_get_session.return_value = mock_session

        result = fetch_docker_tags("honeygain/honeygain")
        self.assertIsNone(result)

    @patch("money4band.checker.get_session")
    def test_timeout_returns_none(self, mock_get_session):
        mock_session = MagicMock()
        mock_session.get.side_effect = requests.Timeout("Read timed out")
        mock_get_session.return_value = mock_session

        result = fetch_docker_tags("honeygain/honeygain")
        self.assertIsNone(result)

    @patch("money4band.checker.get_session")
    def test_http_error_returns_none(self, mock_get_session):
        mock_session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        mock_session.get.return_value = mock_resp
        mock_get_session.return_value = mock_session

        result = fetch_docker_tags("nonexistent/image")
        self.assertIsNone(result)

    @patch("money4band.checker.get_session")
    def test_timeout_kwarg_is_passed(self, mock_get_session):
        """Verify session.get() is called with the configured timeout."""
        mock_resp = MagicMock()
        mock_resp.json.return_value = DOCKERHUB_TAGS_RESPONSE
        mock_resp.raise_for_status.return_value = None
        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_get_session.return_value = mock_session

        fetch_docker_tags("owner/image")

        _, kwargs = mock_session.get.call_args
        self.assertIn("timeout", kwargs)
        self.assertEqual(kwargs["timeout"], 15)


class TestCheckImgArchSupport(unittest.TestCase):
    @patch("money4band.checker.fetch_docker_tags", return_value=DOCKERHUB_TAGS_RESPONSE)
    def test_arch_supported(self, _mock):
        result = check_img_arch_support("honeygain/honeygain", "latest", "linux/amd64")
        self.assertTrue(result)

    @patch("money4band.checker.fetch_docker_tags", return_value=DOCKERHUB_TAGS_RESPONSE)
    def test_arch_not_supported(self, _mock):
        # "lite" tag only has amd64
        result = check_img_arch_support("honeygain/honeygain", "lite", "linux/arm64")
        self.assertFalse(result)

    @patch("money4band.checker.fetch_docker_tags", return_value=DOCKERHUB_TAGS_RESPONSE)
    def test_tag_not_found(self, _mock):
        result = check_img_arch_support(
            "honeygain/honeygain", "nonexistent", "linux/amd64"
        )
        self.assertFalse(result)

    @patch("money4band.checker.fetch_docker_tags", return_value=None)
    def test_registry_unreachable_returns_none(self, _mock):
        # KI-003: registry down must NOT return False (disables apps)
        result = check_img_arch_support(
            "honeygain/honeygain", "latest", "linux/amd64"
        )
        self.assertIsNone(result)

    @patch("money4band.checker.time.sleep")  # Don't actually sleep in tests
    def test_ghcr_returns_none(self, _mock_sleep):
        """GHCR images return None (can't check arch without PAT)."""
        result = check_img_arch_support(
            "ghcr.io/techroy23/docker-wipter", "latest", "linux/amd64"
        )
        self.assertIsNone(result)

    @patch("money4band.checker.fetch_docker_tags", return_value=DOCKERHUB_TAGS_RESPONSE)
    def test_multi_arch_tag(self, _mock):
        """'latest' has both amd64 and arm64 — both should be detected."""
        self.assertTrue(
            check_img_arch_support("img", "latest", "linux/amd64")
        )
        self.assertTrue(
            check_img_arch_support("img", "latest", "linux/arm64")
        )


class TestGetCompatibleTag(unittest.TestCase):
    @patch("money4band.checker.fetch_docker_tags", return_value=DOCKERHUB_TAGS_RESPONSE)
    def test_finds_compatible_tag(self, _mock):
        # Both "latest" and "lite" support amd64
        result = get_compatible_tag("honeygain/honeygain", "linux/amd64")
        self.assertIn(result, ["latest", "lite"])

    @patch("money4band.checker.fetch_docker_tags", return_value=DOCKERHUB_TAGS_RESPONSE)
    @patch("money4band.checker.ensure_service")
    def test_no_compatible_tag_triggers_binfmt(self, mock_ensure, _mock_tags):
        # No tag supports "riscv64"
        result = get_compatible_tag("honeygain/honeygain", "linux/riscv64")
        self.assertIsNone(result)
        mock_ensure.assert_called_once()

    @patch("money4band.checker.fetch_docker_tags", return_value=None)
    def test_registry_unreachable_returns_none(self, _mock):
        result = get_compatible_tag("honeygain/honeygain", "linux/amd64")
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
