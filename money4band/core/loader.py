from __future__ import annotations

import argparse
import importlib.util
import json
import logging
import os
import sys
import types
from typing import TYPE_CHECKING, Any

from money4band.core.crypto import decrypt_to_dict, is_encrypted

if TYPE_CHECKING:
    from money4band.apps.schema import CatalogEntry

logger = logging.getLogger(__name__)


def load_json_config(config_path_or_dict: Any) -> dict[str, Any]:
    """
    Load JSON config variables from a file or dictionary.

    If the file is encrypted (M4B_ENCRYPTED: prefix), it is decrypted
    transparently before parsing.

    Arguments:
    config_path_or_dict -- the config file path or dictionary

    Returns:
    Dict[str, Any] -- The loaded configuration dictionary.

    Raises:
    FileNotFoundError -- If the config file is not found.
    JSONDecodeError -- If there is an error decoding the JSON file.
    ValueError -- If the config type is invalid or decryption fails.
    """
    if isinstance(config_path_or_dict, str):
        # If config is a string, assume it's a file path and load the JSON file
        try:
            with open(config_path_or_dict, encoding="utf-8") as f:
                logger.debug("Loading config from file: %s", config_path_or_dict)
                content = f.read()

            if is_encrypted(content):
                logger.debug("Decrypting encrypted config: %s", config_path_or_dict)
                return decrypt_to_dict(content)

            return json.loads(content)
        except FileNotFoundError:
            logger.error("Config file %s not found.", config_path_or_dict)
            raise
        except json.JSONDecodeError:
            logger.error("Error decoding JSON from %s", config_path_or_dict)
            raise
        except Exception as e:
            logger.error(
                "An unexpected error occurred when loading %s: %s",
                config_path_or_dict,
                e,
            )
            raise
    elif isinstance(config_path_or_dict, dict):
        # If config is a dictionary, assume it's already loaded and return it directly
        logger.debug("Using provided config dictionary")
        return config_path_or_dict
    else:
        raise ValueError(
            "Invalid config type. Config must be a file path or a dictionary."
        )


def get_all_app_categories(app_config: dict[str, Any]) -> list[str]:
    """Return *all* category keys that carry an ``entries`` list."""
    return [
        key
        for key, val in app_config.items()
        if isinstance(val, dict) and "entries" in val
    ]


def load_app_config_with_overlays(
    config_path: str, apps_d_dir: str | None = None
) -> dict[str, Any]:
    """Load app-config.json and merge community apps from ``apps.d/``.

    If *apps_d_dir* is ``None``, it defaults to ``config/apps.d/`` relative
    to the config file directory.
    """
    config = load_json_config(config_path)

    if apps_d_dir is None:
        apps_d_dir = os.path.join(os.path.dirname(config_path), "apps.d")

    if os.path.isdir(apps_d_dir):
        from money4band.apps.schema import merge_community_apps

        config = merge_community_apps(config, apps_d_dir)

    return config


def is_category_active(app_config: dict[str, Any], category: str) -> bool:
    """Return whether *category* is marked active."""
    cat = app_config.get(category)
    if isinstance(cat, dict):
        return cat.get("active", False)
    return False


def get_active_app_categories(app_config: dict[str, Any]) -> list[str]:
    """Return the list of active app category keys from *app_config*.

    Each category is a dict with ``"active": true/false`` and
    ``"entries": [...]``.  Only categories marked active are returned.
    """
    return [
        key
        for key, val in app_config.items()
        if isinstance(val, dict) and val.get("active", False) and "entries" in val
    ]


def get_category_entries(
    app_config: dict[str, Any], category: str
) -> list[dict[str, Any]]:
    """Return the entries list for *category*, or ``[]`` if missing."""
    cat = app_config.get(category)
    if isinstance(cat, dict):
        return cat.get("entries", [])
    # Legacy fallback: category value is already a list
    if isinstance(cat, list):
        return cat
    return []


def get_install_limit(app_entry: dict[str, Any]) -> int:
    """Return the install_limit for an app entry (-1 = unlimited)."""
    return app_entry.get("install_limit", -1)


def load_catalog_entries(
    app_config: dict[str, Any],
    *,
    categories: list[str] | None = None,
) -> list[CatalogEntry]:
    """Return typed :class:`CatalogEntry` objects for *app_config*.

    Phase-8.1 additive helper.  Existing consumers that use
    :func:`get_category_entries` keep working unchanged — this function
    simply wraps the same dicts in dataclasses.

    Arguments:
    app_config -- previously loaded app-config (post-overlay merge).
    categories -- explicit list of category keys to include.  When
        ``None`` (default), every category that carries an ``entries``
        list is included regardless of its ``active`` flag — callers that
        want only active ones should filter the result on ``.category``
        after calling :func:`get_active_app_categories`.
    """
    from money4band.apps.schema import SOURCE_BUILTIN, CatalogEntry

    if categories is None:
        categories = get_all_app_categories(app_config)

    out: list[CatalogEntry] = []
    for cat_key in categories:
        for raw in get_category_entries(app_config, cat_key):
            if not isinstance(raw, dict):
                continue
            try:
                out.append(
                    CatalogEntry.from_raw(raw, source=SOURCE_BUILTIN, category=cat_key)
                )
            except (TypeError, ValueError) as exc:
                logger.warning("Skipping invalid catalog entry in %s: %s", cat_key, exc)
    return out


def load_module_from_file(module_name: str, file_path: str) -> types.ModuleType:
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
        # Register in sys.modules before exec so @dataclass and other
        # metaclass introspection can find the module at import time.
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    except Exception as e:
        logger.error(
            f"Failed to load module: {module_name} from {file_path}. Error: {str(e)}"
        )
        raise


def load_modules_from_directory(directory_path: str) -> dict[str, types.ModuleType]:
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
                logger.info(f"Successfully loaded module: {module_name}")
            except Exception as e:
                logger.error(f"Failed to load module: {module_name}. Error: {str(e)}")
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
        load_json_config(config_path_or_dict)
        load_modules_from_directory(module_dir_path)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
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

    logger.info(f"Starting {script_name} script...")

    try:
        # Load the app_config JSON file
        config_path = args.config_path
        module_dir_path = args.module_dir_path

        # Call the main function
        main(config_path_or_dict=config_path, module_dir_path=module_dir_path)

        logger.info(f"{script_name} script completed successfully")
    except FileNotFoundError as e:
        logger.error(f"File not found: {str(e)}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        raise
