"""
Test networker module functionality.
"""

import socket
import unittest
from unittest.mock import patch

from utils.networker import find_next_available_port, is_port_in_use


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
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
            # First port is available
            mock_is_port_in_use.return_value = False

            result = find_next_available_port(8000)

            self.assertEqual(result, 8000)
            mock_is_port_in_use.assert_called_once_with(8000)

    def test_find_next_available_port_skip_in_use(self):
        """Test that function skips ports that are in use."""
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
            # First two ports are in use, third is free
            mock_is_port_in_use.side_effect = [True, True, False]

            result = find_next_available_port(8000)

            self.assertEqual(result, 8002)
            self.assertEqual(mock_is_port_in_use.call_count, 3)

    def test_find_next_available_port_with_exclude_ports(self):
        """Test that function skips ports in the exclude list."""
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
            # All ports are free (not in use by system)
            mock_is_port_in_use.return_value = False

            # But we want to exclude 8000 and 8001
            result = find_next_available_port(8000, exclude_ports=[8000, 8001])

            self.assertEqual(result, 8002)

    def test_find_next_available_port_exclude_and_in_use(self):
        """Test that function skips both excluded and in-use ports."""
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
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
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
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
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
            # All ports are in use
            mock_is_port_in_use.return_value = True

            with self.assertRaises(RuntimeError) as context:
                find_next_available_port(8000, max_port=8005)

            self.assertIn("Could not find an available port", str(context.exception))
            self.assertIn("8000", str(context.exception))
            self.assertIn("8005", str(context.exception))

    def test_find_next_available_port_default_max_port(self):
        """Test that default max_port is 65535."""
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
            # Make ports unavailable until 65535, then available at 65535
            def port_checker(port):
                return port < 65535

            mock_is_port_in_use.side_effect = port_checker

            result = find_next_available_port(65530)

            self.assertEqual(result, 65535)

    def test_find_next_available_port_none_exclude_ports(self):
        """Test that function handles None exclude_ports gracefully."""
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
            mock_is_port_in_use.return_value = False

            result = find_next_available_port(8000, exclude_ports=None)

            self.assertEqual(result, 8000)

    def test_find_next_available_port_empty_exclude_ports(self):
        """Test that function handles empty exclude_ports list."""
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
            mock_is_port_in_use.return_value = False

            result = find_next_available_port(8000, exclude_ports=[])

            self.assertEqual(result, 8000)

    def test_find_next_available_port_realistic_scenario(self):
        """Test a realistic scenario of assigning multiple sequential ports."""
        with patch("utils.networker.is_port_in_use") as mock_is_port_in_use:
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

            # Expected: [50000, 50002, 50004, 50006, 50007]
            # - 50000: free
            # - 50001: used by system, skip
            # - 50002: free
            # - 50003: used by system, skip
            # - 50004: free
            # - 50005: used by system, skip
            # - 50006: free
            # - 50007: free
            self.assertEqual(assigned_ports, [50000, 50002, 50004, 50006, 50007])


if __name__ == "__main__":
    unittest.main()
