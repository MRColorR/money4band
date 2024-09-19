import socket

def is_port_in_use(port):
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        return sock.connect_ex(('localhost', port)) == 0


def find_next_available_port(starting_port):
    """Find the next available port starting from the given port."""
    port = starting_port
    while is_port_in_use(port):
        port += 1
    return port
