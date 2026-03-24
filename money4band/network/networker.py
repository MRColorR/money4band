from __future__ import annotations

import logging
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Accepted proxy protocols for tun2socks / SOCKS / HTTP tunnels.
ACCEPTED_PROXY_PROTOCOLS = frozenset({"http", "https", "socks4", "socks5", "socks5h"})


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("localhost", port)) == 0


def find_next_available_port(
    starting_port: int,
    exclude_ports: list[int] | None = None,
    max_port: int = 65535,
) -> int:
    """
    Find the next available port starting from the given port.

    Args:
        starting_port (int): The port number to start searching from
        exclude_ports (list[int], optional): List of ports to exclude from assignment (e.g., already assigned ports)
        max_port (int): Maximum port number to check (default: 65535, the maximum valid TCP/UDP port)

    Returns:
        int: The next available port number between starting_port and max_port (inclusive, range 1-65535)

    Raises:
        RuntimeError: If no available port is found between starting_port and max_port
    """
    exclude_ports = exclude_ports or []
    port = starting_port

    while port <= max_port:
        if not is_port_in_use(port) and port not in exclude_ports:
            return port
        port += 1

    raise RuntimeError(
        f"Could not find an available port between {starting_port} and {max_port}"
    )


# ---------------------------------------------------------------------------
# Proxy validation helpers
# ---------------------------------------------------------------------------


def validate_proxy_url(url: str) -> tuple[bool, str]:
    """Validate a proxy URL format.

    Expected format: ``protocol://[user:pass@]host:port``

    Returns:
        A ``(valid, reason)`` tuple.  *reason* is empty when valid.
    """
    if not url or not url.strip():
        return False, "Proxy URL is empty."

    try:
        parsed = urlparse(url.strip())
    except Exception as exc:
        return False, f"Failed to parse URL: {exc}"

    scheme = (parsed.scheme or "").lower()
    if scheme not in ACCEPTED_PROXY_PROTOCOLS:
        return False, (
            f"Unsupported protocol '{scheme}'. "
            f"Accepted: {', '.join(sorted(ACCEPTED_PROXY_PROTOCOLS))}"
        )

    if not parsed.hostname:
        return False, "Missing hostname in proxy URL."

    if not parsed.port:
        return False, "Missing port in proxy URL."

    if not 1 <= parsed.port <= 65535:
        return False, f"Port {parsed.port} outside valid range (1-65535)."

    return True, ""


def check_proxy_connectivity(
    url: str,
    timeout: float = 5.0,
) -> tuple[bool, str]:
    """Attempt a TCP connection to the proxy host:port.

    This only checks basic reachability — it does **not** authenticate or
    send traffic through the proxy.

    Returns:
        A ``(reachable, reason)`` tuple.
    """
    try:
        parsed = urlparse(url.strip())
        host = parsed.hostname
        port = parsed.port
        if not host or not port:
            return False, "Cannot extract host/port from URL."
    except Exception as exc:
        return False, f"URL parse error: {exc}"

    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, ""
    except OSError as exc:
        return False, f"Connection to {host}:{port} failed — {exc}"


def validate_proxy_list(
    proxy_urls: list[str],
    *,
    check_connectivity: bool = False,
    timeout: float = 5.0,
) -> list[dict[str, object]]:
    """Validate a list of proxy URLs.

    Returns a list of dicts with keys ``url``, ``valid``, ``reachable``
    (``None`` when *check_connectivity* is ``False``), and ``reason``.
    """
    results: list[dict[str, object]] = []
    for url in proxy_urls:
        ok, reason = validate_proxy_url(url)
        entry: dict[str, object] = {
            "url": url,
            "valid": ok,
            "reachable": None,
            "reason": reason,
        }
        if ok and check_connectivity:
            reachable, conn_reason = check_proxy_connectivity(url, timeout=timeout)
            entry["reachable"] = reachable
            if not reachable:
                entry["reason"] = conn_reason
        results.append(entry)
    return results
