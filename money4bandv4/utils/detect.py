import os
import argparse
import logging
import json
import platform
from typing import Dict

def detect_os(os_map: Dict[str, str]) -> Dict[str, str]:
    """
    Detect the operating system and return its type.

    Arguments:
    os_map -- a dictionary mapping operating system names to their types
    """
    try:
        logging.debug("Detecting OS type")
        os_type = platform.system().lower()
        os_type = os_map.get(os_type, "unknown")
        logging.info(f"OS type detected: {os_type}")
        return {"os_type": os_type}
    except Exception as e:
        logging.error(f"An error occurred while detecting OS: {str(e)}")
        raise

def detect_architecture(arch_map: Dict[str, str]) -> Dict[str, str]:
    """
    Detect the system architecture and return its type.

    Arguments:
    arch_map -- a dictionary mapping system architectures to their types
    """
    try:
        logging.debug("Detecting system architecture")
        arch = platform.machine().lower()
        dkarch = arch_map.get(arch, "unknown")
        logging.info(f"System architecture detected: {arch}, Docker architecture has been set to {dkarch}")
        return {"arch": arch, "dkarch": dkarch}
    except Exception as e:
        logging.error(f"An error occurred while detecting architecture: {str(e)}")
        raise

if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description=f"Run the {script_name} module standalone.")
    parser.add_argument('--os-map', type=str, required=True, help='Path to os_map JSON file')
    parser.add_argument('--arch-map', type=str, required=True, help='Path to arch_map JSON file')

    args = parser.parse_args()

    # Start logging
    logging.basicConfig(filename=f"{script_name}.log",  format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level="DEBUG")

    # Test the function
    msg = f"Testing {script_name} function"
    print(msg)
    logging.info(msg)
    logging.info("Loading os_map JSON fie")
    with open(args.os_map, 'r') as f:
        os_map = json.load(f)
        logging.info("os_map JSON file loaded successfully")
    logging.info("Loading arch_map JSON file")
    with open(args.arch_map, 'r') as f:
        arch_map = json.load(f)
        logging.info("arch_map JSON file loaded successfully")

    print(detect_os(os_map))
    print(detect_architecture(arch_map))
    logging.info(f"{script_name} test complete")
