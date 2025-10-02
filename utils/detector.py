import logging
import os
import platform

# Ensure the parent directory is in the sys.path
import sys
from typing import Any

import psutil

from utils.dumper import write_json
from utils.loader import load_json_config

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Import the module from the parent directory


def detect_os(m4b_config_path_or_dict: Any) -> dict[str, str]:
    """
    Detect the operating system based on the system's platform and map it according to the m4b configuration.

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b config file or the config dictionary.

    Returns:
        Dict[str, str]: A dictionary containing the detected OS type.

    Raises:
        Exception: If an error occurs during OS detection or if the OS is not recognized.
    """
    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)

        logging.debug("Detecting OS type")
        os_map = m4b_config.get("system", {}).get("os_map", {})

        # Get the OS type from the platform module and convert it to lowercase
        detected_os = platform.system().lower()
        logging.info(f"Detected OS: {detected_os}")

        # Map the detected OS using the os_map from the config
        mapped_os = os_map.get(detected_os, "unknown")

        if mapped_os == "unknown":
            raise ValueError(
                f"OS type '{detected_os}' is not recognized in the provided os_map."
            )

        logging.info(f"Mapped OS: {mapped_os}")
        return {"os_type": mapped_os}

    except KeyError as e:
        logging.error(f"KeyError in configuration: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An error occurred while detecting OS: {str(e)}")
        raise


def detect_architecture(m4b_config_path_or_dict: Any) -> dict[str, str]:
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
        logging.info(
            f"System architecture detected: {arch}, Docker architecture has been set to {dkarch}"
        )
        return {"arch": arch, "dkarch": dkarch}
    except Exception as e:
        logging.error(f"An error occurred while detecting architecture: {str(e)}")
        raise


def get_system_memory_and_cores():
    logging.debug("Retrieving system memory and cores")
    total_memory = psutil.virtual_memory().total / (1024**2)
    cores = psutil.cpu_count(logical=False)
    logging.debug(f"Total RAM: {total_memory:.2f} MB, CPU cores: {cores}")
    return total_memory, cores


def calculate_resource_limits(user_config_path_or_dict: Any) -> None:
    logging.debug("Determining resource limits")
    user_config = load_json_config(user_config_path_or_dict)
    total_memory, cores = get_system_memory_and_cores()
    memory_cap = user_config.get("resource_limits", {}).get("ram_cap_mb_default")
    if memory_cap > total_memory:
        logging.debug(
            f"Memory cap {memory_cap} MB is greater than total system memory {total_memory} MB. Using total memory as cap."
        )
        memory_cap = total_memory

    resource_limits = {}
    resource_limits["app_mem_reserv_little"] = f"{int(max(memory_cap * 0.2, 64))}m"
    resource_limits["app_mem_limit_little"] = f"{int(max(memory_cap * 0.4, 128))}m"
    resource_limits["app_mem_reserv_medium"] = f"{int(max(memory_cap * 0.4, 128))}m"
    resource_limits["app_mem_limit_medium"] = f"{int(max(memory_cap * 0.6, 256))}m"
    resource_limits["app_mem_reserv_big"] = f"{int(max(memory_cap * 0.6, 256))}m"
    resource_limits["app_mem_limit_big"] = f"{int(max(memory_cap * 0.8, 512))}m"
    resource_limits["app_mem_reserv_huge"] = f"{int(max(memory_cap * 0.8, 512))}m"
    resource_limits["app_mem_limit_huge"] = f"{int(max(memory_cap, 1024))}m"

    resource_limits["app_cpu_limit_little"] = round(max(cores * 0.2, 0.8), 1)
    resource_limits["app_cpu_limit_medium"] = round(max(cores * 0.4, 1.0), 1)
    resource_limits["app_cpu_limit_big"] = round(max(cores * 0.6, 1.0), 1)
    resource_limits["app_cpu_limit_huge"] = round(max(cores * 0.8, 1.0), 1)

    user_config.get("resource_limits", {}).update(resource_limits)
    write_json(user_config, user_config_path_or_dict)
    logging.debug("Resource limits updated")
