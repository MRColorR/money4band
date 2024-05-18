import os
import argparse
import logging
import json
import importlib.util
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

if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description=f"Run the {script_name} module standalone.")
    parser.add_argument('--config-path', type=str, required=True, help='The config file path')
    parser.add_argument('--module-dir-path', type=str, required=True, help='The directory containing the modules')
    parser.add_argument('--log-dir', default=os.path.join(script_dir, 'logs'), help='Set the logging directory')
    parser.add_argument('--log-file', default=f"{script_name}.log", help='Set the logging file name')
    args = parser.parse_args()

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(filename=os.path.join(args.log_dir, args.log_file),  format='%(asctime)s - [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S', level="DEBUG")

    # Test the function
    msg = f"Testing {script_name} function"
    print(msg)
    logging.info(msg)

    load_json_config(args.config_path)
    load_modules_from_directory(args.module_dir_path)
    
    msg = f"{script_name} test complete"
    print(msg)
    logging.info(msg)
