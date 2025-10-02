import argparse
import importlib.util
import json
import logging
import os
from typing import Any


def load_json_config(config_path_or_dict: Any) -> dict[str, Any]:
    """
    Load JSON config variables from a file or dictionary.

    Arguments:
    config_path_or_dict -- the config file path or dictionary

    Returns:
    Dict[str, Any] -- The loaded configuration dictionary.

    Raises:
    FileNotFoundError -- If the config file is not found.
    JSONDecodeError -- If there is an error decoding the JSON file.
    ValueError -- If the config type is invalid.
    """
    if isinstance(config_path_or_dict, str):
        # If config is a string, assume it's a file path and load the JSON file
        try:
            with open(config_path_or_dict) as f:
                logging.debug(f"Loading config from file: {config_path_or_dict}")
                return json.load(f)
        except FileNotFoundError:
            logging.error(f"Config file {config_path_or_dict} not found.")
            raise
        except json.JSONDecodeError:
            logging.error(f"Error decoding JSON from {config_path_or_dict}")
            raise
        except Exception as e:
            logging.error(
                f"An unexpected error occurred when loading {config_path_or_dict}: {str(e)}"
            )
            raise
    elif isinstance(config_path_or_dict, dict):
        # If config is a dictionary, assume it's already loaded and return it directly
        logging.debug("Using provided config dictionary")
        return config_path_or_dict
    else:
        raise ValueError(
            "Invalid config type. Config must be a file path or a dictionary."
        )


def load_module_from_file(module_name: str, file_path: str):
    """
    Dynamically load a module from a Python file.

    Arguments:
    module_name -- the name to give to the loaded module
    file_path -- the path to the Python file

    Returns:
    Module -- The loaded module.

    Raises:
    Exception -- If there is an error loading the module.
    """
    try:
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logging.error(
            f"Failed to load module: {module_name} from {file_path}. Error: {str(e)}"
        )
        raise


def load_modules_from_directory(directory_path: str):
    """
    Dynamically load all modules in a directory.

    Arguments:
    directory_path -- the path to the directory

    Returns:
    Dict[str, Module] -- A dictionary of loaded modules.
    """
    modules = {}
    for filename in os.listdir(directory_path):
        if filename.endswith(".py") and filename != "__init__.py":
            path = os.path.join(directory_path, filename)
            module_name = filename[:-3]  # remove .py extension
            try:
                modules[module_name] = load_module_from_file(module_name, path)
                logging.info(f"Successfully loaded module: {module_name}")
            except Exception as e:
                logging.error(f"Failed to load module: {module_name}. Error: {str(e)}")
                raise
    return modules


def main(config_path_or_dict: Any, module_dir_path: str) -> None:
    """
    Main function to run the load module standalone.

    Arguments:
    config_path_or_dict -- the config file path or dictionary
    module_dir_path -- the directory containing the modules
    """
    try:
        config = load_json_config(config_path_or_dict)
        load_modules_from_directory(module_dir_path)
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise


if __name__ == "__main__":
    # Get the script absolute path and name
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_name = os.path.basename(__file__)

    # Parse command-line arguments
    parser = argparse.ArgumentParser(
        description=f"Run the {script_name} module standalone."
    )
    parser.add_argument(
        "--config-path",
        type=str,
        required=True,
        help="The config file path or JSON string",
    )
    parser.add_argument(
        "--module-dir-path",
        type=str,
        required=True,
        help="The directory containing the modules",
    )
    parser.add_argument(
        "--log-dir",
        default=os.path.join(script_dir, "logs"),
        help="Set the logging directory",
    )
    parser.add_argument(
        "--log-file", default=f"{script_name}.log", help="Set the logging file name"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Set the logging level",
    )
    args = parser.parse_args()

    # Set logging level based on command-line arguments
    log_level = getattr(logging, args.log_level.upper(), None)
    if not isinstance(log_level, int):
        raise ValueError(f"Invalid log level: {args.log_level}")

    # Start logging
    os.makedirs(args.log_dir, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.log_dir, args.log_file),
        format="%(asctime)s - [%(levelname)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=log_level,
    )

    logging.info(f"Starting {script_name} script...")

    try:
        # Load the app_config JSON file
        config_path = args.config_path
        module_dir_path = args.module_dir_path

        # Call the main function
        main(config_path_or_dict=config_path, module_dir_path=module_dir_path)

        logging.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logging.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"An unexpected error occurred: {str(e)}")
        raise
