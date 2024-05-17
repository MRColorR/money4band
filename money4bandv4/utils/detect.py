import logging
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