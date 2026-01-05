import socket


def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(("localhost", port)) == 0


def find_next_available_port(starting_port, exclude_ports=None, max_port=65535):
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
