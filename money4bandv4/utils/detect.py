import os
import argparse
import logging
import json
import platform
from typing import Dict, Any

def detect_os(m4b_config_path: str) -> Dict[str, str]:
    """
    Detect the operating system and return its type.

    Arguments:
    m4b_config_path -- the path to the m4b config file
    """
    try:
        logging.debug("Loading m4b_config JSON file")
        with open(m4b_config_path, 'r') as f:
            m4b_config = json.load(f)
        logging.info("m4b_config JSON file loaded successfully")

        logging.debug("Detecting OS type")
        os_map = m4b_config.get("system").get("os_map")
        os_type = platform.system().lower()
        os_type = os_map.get(os_type, "unknown")
        logging.info(f"OS type detected: {os_type}")
        return {"os_type": os_type}
    except Exception as e:
        logging.error(f"An error occurred while detecting OS: {str(e)}")
        raise

def detect_architecture(m4b_config_path: str) -> Dict[str, str]:
    """
    Detect the system architecture and return its type.

    Arguments:
    m4b_config_path -- the path to the m4b config file
    """
    try:
        logging.debug("Loading m4b_config JSON file")
        with open(m4b_config_path, 'r') as f:
            m4b_config = json.load(f)
        logging.info("m4b_config JSON file loaded successfully")

        logging.debug("Detecting system architecture")
        arch_map = m4b_config.get("system").get("arch_map")
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
    parser.add_argument('--m4b-config-path', type=str, required=True, help='The m4b config file path')
    args = parser.parse_args()

    # Start logging
    logging.basicConfig(filename=f"{script_name}.log",  format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level="DEBUG")

    # Test the function
    msg = f"Testing {script_name} function"
    print(msg)
    logging.info(msg)

    print(detect_os(args.m4b_config_path))
    print(detect_architecture(args.m4b_config_path))
    logging.info(f"{script_name} test complete")
