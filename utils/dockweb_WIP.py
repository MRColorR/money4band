from typing import Any, Dict


def enable_dockweb_if_needed(user_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enable DockWeb if any of the associated apps is enabled and disable the associated apps.

    Args:
        user_config (dict): The user configuration dictionary.

    Returns:
        Dict[str, Any]: The updated user configuration dictionary.
    """
    dockweb_enabled = False
    associated_apps = ["grass", "gradient", "dawn", "teno"]

    for app_name in associated_apps:
        if user_config["apps"].get(app_name, {}).get("enabled", False):
            dockweb_enabled = True
            user_config["apps"][app_name]["enabled"] = False

    if dockweb_enabled:
        user_config["apps"]["dockweb"]["enabled"] = True
    else:
        user_config["apps"]["dockweb"]["enabled"] = False

    return user_config
