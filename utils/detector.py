import os
import argparse
import logging
import json
import platform
import logging
from typing import Dict, Any

# Ensure the parent directory is in the sys.path
import sys

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the module from the parent directory
from utils.loader import load_json_config

def detect_os(m4b_config_path_or_dict: Any) -> Dict[str, str]:
    """
    Detect the operating system and return its type.

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b config file or the config dictionary.

    Returns:
        Dict[str, str]: A dictionary containing the detected OS type.

    Raises:
        Exception: If an error occurs during OS detection.
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

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b config file or the config dictionary.

    Returns:
        Dict[str, str]: A dictionary containing the detected architecture and Docker architecture.

    Raises:
        Exception: If an error occurs during architecture detection.
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

