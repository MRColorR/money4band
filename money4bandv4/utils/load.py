import os
import json
import importlib.util
import logging
from typing import Dict, Any



def load_json_config(config_file_path: str) -> Dict[str, Any]:
    """
    Load JSON config variables from a file.

    Arguments:
    config_file_path -- the path to the config file
    """
    try:
        with open(config_file_path, 'r') as f:
            logging.debug(f"Loading config from {config_file_path}")
            config = json.load(f)
        logging.info(f"Successfully loaded config from {config_file_path}")
        return config
    except FileNotFoundError:
        logging.error(f"Config file {config_file_path} not found.")
        raise
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON from {config_file_path}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred when loading {config_file_path}: {str(e)}")
        raise


def load_module_from_file(module_name: str, file_path: str):
    """
    Dynamically load a module from a Python file.

    Arguments:
    module_name -- the name to give to the loaded module
    file_path -- the path to the Python file
    """
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_modules_from_directory(directory_path: str):
    """
    Dynamically load all modules in a directory.

    Arguments:
    directory_path -- the path to the directory
    """
    modules = {}
    for filename in os.listdir(directory_path):
        if filename.endswith('.py') and filename != '__init__.py':
            path = os.path.join(directory_path, filename)
            module_name = filename[:-3]  # remove .py extension
            try:
                modules[module_name] = load_module_from_file(module_name, path)
                logging.info(f'Successfully loaded module: {module_name}')
            except Exception as e:
                logging.error(f'Failed to load module: {module_name}. Error: {str(e)}')
    return modules