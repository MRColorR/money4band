import os
import argparse
import logging
import json
import platform
from typing import Dict, Any

# Ensure the parent directory is in the sys.path
import sys
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

# Import the module from the parent directory
from utils.loader import load_json_config

def detect_os(m4b_config_path_or_dict: Any) -> Dict[str, str]:
    """
    Detect the operating system and return its type.

    Arguments:
    m4b_config_path_or_dict -- the path to the m4b config file or the config dictionary

    Returns:
    Dict[str, str] -- A dictionary containing the detected OS type.

    Raises:
    Exception -- If an error occurs during OS detection.
    """
    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)

        logging.debug("Detecting OS type")
        os_map = m4b_config.get("system", {}).get("os_map", {})
        os_type = platform.system().lower()
        os_type = os_map.get(os_type, "unknown")
        logging.info(f"OS type detected: {os_type}")
        return {"os_type": os_type}
    except Exception as e:
        logging.error(f"An error occurred while detecting OS: {str(e)}")
        raise

def detect_architecture(m4b_config_path_or_dict: Any) -> Dict[str, str]:
    """
    Detect the system architecture and return its type.

    Arguments:
    m4b_config_path_or_dict -- the path to the m4b config file or the config dictionary

    Returns:
    Dict[str, str] -- A dictionary containing the detected architecture and Docker architecture.

    Raises:
    Exception -- If an error occurs during architecture detection.
    """
    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)

        logging.debug("Detecting system architecture")
        arch_map = m4b_config.get("system", {}).get("arch_map", {})
        arch = platform.machine().lower()
        dkarch = arch_map.get(arch, "unknown")
        logging.info(f"System architecture detected: {arch}, Docker architecture has been set to {dkarch}")
        return {"arch": arch, "dkarch": dkarch}
    except Exception as e:
        logging.error(f"An error occurred while detecting architecture: {str(e)}")
        raise

def main(m4b_config_path_or_dict: Any) -> None:
    """
    Main function to run the detect module standalone.

    Arguments:
    m4b_config_path_or_dict -- the path to the m4b config file or the config dictionary
    """
    try:
        logging.info("Testing detect module function")
        print(detect_os(m4b_config_path_or_dict))
        print(detect_architecture(m4b_config_path_or_dict))
        logging.info("Detect module test complete")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise

if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description=f"Run the {script_name} module standalone.")
    parser.add_argument('--m4b-config-path-or-dict', type=str, required=True, help='The m4b config file path or JSON string')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default=f"{script_name}.log", help='Set the logging file name')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], default='INFO', help='Set the logging level')
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f'Invalid log level: {args.log_level}')

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format='%(asctime)s - [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        level=log_level
    )

    logging.info(f"Starting {script_name} script...")

    try:
        # Call the main function
        main(args.m4b_config_path_or_dict)
        logging.info(f"{script_name} script completed successfully")
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        print(f"An unexpected error occurred: {str(e)}")
