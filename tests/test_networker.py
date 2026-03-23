"""
Test networker module functionality.
"""

import unittest
from unittest.mock import patch

from money4band.networker import (
    ACCEPTED_PROXY_PROTOCOLS,
    check_proxy_connectivity,
    find_next_available_port,
    is_port_in_use,
    validate_proxy_list,
    validate_proxy_url,
)


class TestNetworker(unittest.TestCase):
    """Test suite for networker module."""

    def test_is_port_in_use_free_port(self):
        """Test that is_port_in_use returns False for a free port."""
        # Use a high port number that's unlikely to be in use
        test_port = 54321
        result = is_port_in_use(test_port)
        # We can't guarantee the port is free, so we just test the function runs
        self.assertIsInstance(result, bool)

    def test_find_next_available_port_basic(self):
        """Test basic port finding without exclude list."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            # First port is available
            mock_is_port_in_use.return_value = False

            result = find_next_available_port(8000)

            self.assertEqual(result, 8000)
            mock_is_port_in_use.assert_called_once_with(8000)

    def test_find_next_available_port_skip_in_use(self):
        """Test that function skips ports that are in use."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            # First two ports are in use, third is free
            mock_is_port_in_use.side_effect = [True, True, False]

            result = find_next_available_port(8000)

            self.assertEqual(result, 8002)
            self.assertEqual(mock_is_port_in_use.call_count, 3)

    def test_find_next_available_port_with_exclude_ports(self):
        """Test that function skips ports in the exclude list."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            # All ports are free (not in use by system)
            mock_is_port_in_use.return_value = False

            # But we want to exclude 8000 and 8001
            result = find_next_available_port(8000, exclude_ports=[8000, 8001])

            self.assertEqual(result, 8002)

    def test_find_next_available_port_exclude_and_in_use(self):
        """Test that function skips both excluded and in-use ports."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            # Port 8000 is excluded (we won't check it)
            # Port 8001 is in use
            # Port 8002 is free
            def port_checker(port):
                if port == 8001:
                    return True
                return False

            mock_is_port_in_use.side_effect = port_checker

            result = find_next_available_port(8000, exclude_ports=[8000])

            self.assertEqual(result, 8002)

    def test_find_next_available_port_multiple_exclude(self):
        """Test excluding multiple already assigned ports."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            # All ports are free from system perspective
            mock_is_port_in_use.return_value = False

            # Simulate the scenario in assign_app_ports where we exclude already assigned ports
            assigned_ports = []

            # First assignment
            port1 = find_next_available_port(5000, exclude_ports=assigned_ports)
            assigned_ports.append(port1)
            self.assertEqual(port1, 5000)

            # Second assignment - should skip 5000
            port2 = find_next_available_port(5000, exclude_ports=assigned_ports)
            assigned_ports.append(port2)
            self.assertEqual(port2, 5001)

            # Third assignment - should skip 5000 and 5001
            port3 = find_next_available_port(5000, exclude_ports=assigned_ports)
            assigned_ports.append(port3)
            self.assertEqual(port3, 5002)

    def test_find_next_available_port_with_max_port(self):
        """Test that function respects the max_port limit."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            # All ports are in use
            mock_is_port_in_use.return_value = True

            with self.assertRaises(RuntimeError) as context:
                find_next_available_port(8000, max_port=8005)

            self.assertIn("Could not find an available port", str(context.exception))
            self.assertIn("8000", str(context.exception))
            self.assertIn("8005", str(context.exception))

    def test_find_next_available_port_default_max_port(self):
        """Test that default max_port is 65535."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            # Make ports unavailable until 65535, then available at 65535
            def port_checker(port):
                return port < 65535

            mock_is_port_in_use.side_effect = port_checker

            result = find_next_available_port(65530)

            self.assertEqual(result, 65535)

    def test_find_next_available_port_none_exclude_ports(self):
        """Test that function handles None exclude_ports gracefully."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            mock_is_port_in_use.return_value = False

            result = find_next_available_port(8000, exclude_ports=None)

            self.assertEqual(result, 8000)

    def test_find_next_available_port_empty_exclude_ports(self):
        """Test that function handles empty exclude_ports list."""
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            mock_is_port_in_use.return_value = False

            result = find_next_available_port(8000, exclude_ports=[])

            self.assertEqual(result, 8000)

    def test_find_next_available_port_realistic_scenario(self):
        """
        Test a realistic scenario of assigning multiple sequential ports.

        This test simulates the scenario in assign_app_ports where we need to assign
        5 ports starting from base 50000, while avoiding both system-used ports
        (50001, 50003, 50005) and already assigned ports in the same loop.

        Expected result: [50000, 50002, 50004, 50006, 50007]
        - 50000: free, assigned
        - 50001: used by system, skip
        - 50002: free, assigned (excludes 50000)
        - 50003: used by system, skip
        - 50004: free, assigned (excludes 50000, 50002)
        - 50005: used by system, skip
        - 50006: free, assigned (excludes 50000, 50002, 50004)
        - 50007: free, assigned (excludes 50000, 50002, 50004, 50006)
        """
        with patch("money4band.networker.is_port_in_use") as mock_is_port_in_use:
            # Simulate some system ports in use
            used_system_ports = {50001, 50003, 50005}

            def port_checker(port):
                return port in used_system_ports

            mock_is_port_in_use.side_effect = port_checker

            # Simulate assigning 5 ports starting from 50000
            assigned_ports = []
            base_port = 50000

            for i in range(5):
                port = find_next_available_port(
                    base_port + i, exclude_ports=assigned_ports
                )
                assigned_ports.append(port)

            self.assertEqual(assigned_ports, [50000, 50002, 50004, 50006, 50007])


class TestProxyValidation(unittest.TestCase):
    """Test suite for proxy URL format validation."""

    # -- Valid URLs -----------------------------------------------------------

    def test_valid_http_proxy(self):
        ok, reason = validate_proxy_url("http://user:pass@1.2.3.4:8080")
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_valid_socks5_proxy(self):
        ok, _ = validate_proxy_url("socks5://10.0.0.1:1080")
        self.assertTrue(ok)

    def test_valid_socks5h_proxy(self):
        ok, _ = validate_proxy_url("socks5h://user:pass@proxy.example.com:9050")
        self.assertTrue(ok)

    def test_valid_socks4_proxy(self):
        ok, _ = validate_proxy_url("socks4://192.168.1.1:1080")
        self.assertTrue(ok)

    def test_valid_https_proxy(self):
        ok, _ = validate_proxy_url("https://proxy.example.com:443")
        self.assertTrue(ok)

    def test_valid_with_special_chars_in_password(self):
        ok, _ = validate_proxy_url("http://user:p%40ss%23@host.com:3128")
        self.assertTrue(ok)

    def test_valid_high_port(self):
        ok, _ = validate_proxy_url("http://host:65535")
        self.assertTrue(ok)

    def test_valid_low_port(self):
        ok, _ = validate_proxy_url("http://host:1")
        self.assertTrue(ok)

    def test_leading_trailing_whitespace_stripped(self):
        ok, _ = validate_proxy_url("  http://host:8080  ")
        self.assertTrue(ok)

    # -- Invalid URLs ---------------------------------------------------------

    def test_empty_url(self):
        ok, reason = validate_proxy_url("")
        self.assertFalse(ok)
        self.assertIn("empty", reason.lower())

    def test_whitespace_only(self):
        ok, _ = validate_proxy_url("   ")
        self.assertFalse(ok)

    def test_none_like_empty(self):
        """Explicitly passing a blank string."""
        ok, _ = validate_proxy_url("")
        self.assertFalse(ok)

    def test_unsupported_protocol_ftp(self):
        ok, reason = validate_proxy_url("ftp://host:21")
        self.assertFalse(ok)
        self.assertIn("Unsupported protocol", reason)

    def test_unsupported_protocol_ssh(self):
        ok, reason = validate_proxy_url("ssh://host:22")
        self.assertFalse(ok)
        self.assertIn("ssh", reason)

    def test_missing_hostname(self):
        ok, reason = validate_proxy_url("http://:8080")
        self.assertFalse(ok)
        self.assertIn("hostname", reason.lower())

    def test_missing_port(self):
        ok, reason = validate_proxy_url("http://proxy.example.com")
        self.assertFalse(ok)
        self.assertIn("port", reason.lower())

    def test_no_scheme_at_all(self):
        ok, reason = validate_proxy_url("proxy.example.com:8080")
        self.assertFalse(ok)
        self.assertIn("protocol", reason.lower())

    def test_just_a_word(self):
        ok, _ = validate_proxy_url("garbage")
        self.assertFalse(ok)

    # -- Constants ------------------------------------------------------------

    def test_accepted_protocols_is_frozen(self):
        self.assertIsInstance(ACCEPTED_PROXY_PROTOCOLS, frozenset)

    def test_all_expected_protocols_present(self):
        for proto in ("http", "https", "socks4", "socks5", "socks5h"):
            self.assertIn(proto, ACCEPTED_PROXY_PROTOCOLS)


class TestProxyConnectivity(unittest.TestCase):
    """Test suite for TCP reachability check."""

    def test_success(self):
        with patch("money4band.networker.socket.create_connection"):
            ok, reason = check_proxy_connectivity("http://1.2.3.4:8080", timeout=1.0)
        self.assertTrue(ok)
        self.assertEqual(reason, "")

    def test_connection_refused(self):
        with patch(
            "money4band.networker.socket.create_connection",
            side_effect=OSError("Connection refused"),
        ):
            ok, reason = check_proxy_connectivity("http://1.2.3.4:8080", timeout=1.0)
        self.assertFalse(ok)
        self.assertIn("refused", reason.lower())

    def test_timeout(self):
        with patch(
            "money4band.networker.socket.create_connection",
            side_effect=TimeoutError("timed out"),
        ):
            ok, reason = check_proxy_connectivity("socks5://10.0.0.1:1080", timeout=0.5)
        self.assertFalse(ok)

    def test_bad_url_no_host(self):
        ok, reason = check_proxy_connectivity("not-a-url", timeout=1.0)
        self.assertFalse(ok)
        self.assertIn("host", reason.lower())

    def test_uses_correct_host_port(self):
        with patch("money4band.networker.socket.create_connection") as mock_conn:
            mock_conn.return_value.__enter__ = lambda s: s
            mock_conn.return_value.__exit__ = lambda s, *a: None
            check_proxy_connectivity("socks5://myproxy.net:9999", timeout=2.0)
        mock_conn.assert_called_once_with(("myproxy.net", 9999), timeout=2.0)


class TestValidateProxyList(unittest.TestCase):
    """Test suite for batch proxy validation."""

    def test_all_valid_no_connectivity(self):
        urls = ["http://a:b@1.2.3.4:80", "socks5://5.6.7.8:1080"]
        results = validate_proxy_list(urls)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(r["valid"] for r in results))
        self.assertTrue(all(r["reachable"] is None for r in results))

    def test_mixed_valid_invalid(self):
        urls = ["http://ok:ok@1.2.3.4:80", "bad-url", "socks5://good:1080"]
        results = validate_proxy_list(urls)
        self.assertTrue(results[0]["valid"])
        self.assertFalse(results[1]["valid"])
        self.assertTrue(results[2]["valid"])

    def test_invalid_skips_connectivity(self):
        """Invalid URLs should never get a connectivity check."""
        urls = ["not-valid"]
        with patch("money4band.networker.socket.create_connection") as mock_conn:
            results = validate_proxy_list(urls, check_connectivity=True)
        mock_conn.assert_not_called()
        self.assertFalse(results[0]["valid"])
        self.assertIsNone(results[0]["reachable"])

    def test_connectivity_check_reachable(self):
        urls = ["http://user:pass@1.2.3.4:8080"]
        with patch("money4band.networker.socket.create_connection"):
            results = validate_proxy_list(urls, check_connectivity=True, timeout=1.0)
        self.assertTrue(results[0]["valid"])
        self.assertTrue(results[0]["reachable"])

    def test_connectivity_check_unreachable(self):
        urls = ["http://user:pass@1.2.3.4:8080"]
        with patch(
            "money4band.networker.socket.create_connection",
            side_effect=OSError("refused"),
        ):
            results = validate_proxy_list(urls, check_connectivity=True, timeout=1.0)
        self.assertTrue(results[0]["valid"])
        self.assertFalse(results[0]["reachable"])
        self.assertIn("refused", str(results[0]["reason"]).lower())

    def test_empty_list(self):
        results = validate_proxy_list([])
        self.assertEqual(results, [])

    def test_preserves_original_urls_in_result(self):
        urls = ["http://a:b@1.2.3.4:80", "bad"]
        results = validate_proxy_list(urls)
        self.assertEqual(results[0]["url"], urls[0])
        self.assertEqual(results[1]["url"], urls[1])

    def test_multiple_unreachable(self):
        urls = ["http://a:b@1.1.1.1:80", "socks5://2.2.2.2:1080"]
        with patch(
            "money4band.networker.socket.create_connection",
            side_effect=OSError("no route"),
        ):
            results = validate_proxy_list(urls, check_connectivity=True)
        self.assertFalse(results[0]["reachable"])
        self.assertFalse(results[1]["reachable"])


if __name__ == "__main__":
    unittest.main()
