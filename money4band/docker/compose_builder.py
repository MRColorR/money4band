from __future__ import annotations

"""Docker Compose file assembly - builds docker-compose.yaml from configuration.

Emits a single ``docker-compose.yaml``. Each service carries a
``profiles:`` array driven by its bundle's ``profile`` field, giving
selective startup via standard Docker Compose profile semantics
(``docker compose --profile residential up``).

Reserved profile names assigned by the generator (not valid as bundle
``profile`` values):

- ``monitoring`` - Watchtower service.
- ``proxy`` - tun2socks tunnel service (active when ``proxies.enabled``).

Sidecars (entries with ``parent_id``) inherit their parent app's profile
at generation time.
"""

import copy
import logging
import os
import re
import threading
import time
from typing import Any

import yaml

from money4band.core.dumper import write_json
from money4band.core.loader import (
    get_active_app_categories,
    get_category_entries,
    load_json_config,
    resolve_catalog_config,
)
from money4band.docker.checker import check_img_arch_support, get_compatible_tag
from money4band.docker.helper import show_spinner
from money4band.network import http_client

logger = logging.getLogger(__name__)

# Reserved profile names the generator assigns to optional services.
RESERVED_MONITORING_PROFILE = "monitoring"
RESERVED_PROXY_PROFILE = "proxy"


def get_compose_files(base_dir: str = ".") -> list[str]:
    """Return ``[docker-compose.yaml]`` if present, else ``[]``.

    List-return shape kept so callers can iterate and append ``-f`` flags
    without special-casing single vs multi-file output.
    """
    path = os.path.join(base_dir, "docker-compose.yaml")
    return [path] if os.path.isfile(path) else []


def substitute_port_placeholders(
    port_placeholders: list[str], actual_ports: list[int]
) -> list[str]:
    """
    Substitute port placeholders with actual port values.

    Args:
        port_placeholders (list[str]): List of port placeholders in format
            "${ENV_VAR}:container_port".
        actual_ports (list[int]): List of actual port numbers to use.

    Returns:
        list[str]: List of port mappings in format "host_port:container_port".

    Raises:
        ValueError: If actual_ports is empty.
    """
    if not actual_ports:
        raise ValueError("actual_ports cannot be empty")

    new_ports = []
    for idx, port_placeholder in enumerate(port_placeholders):
        # Extract env var name from placeholder
        match = re.match(r"\$\{([^}]+)\}:(\d+)", port_placeholder)
        if match:
            container_port = match.group(2)
            # Use indexed port if available, otherwise fallback to first port
            host_port = (
                actual_ports[idx % len(actual_ports)]
                if isinstance(actual_ports, list)
                else actual_ports
            )
            new_ports.append(f"{host_port}:{container_port}")
        else:
            # If not a placeholder, keep as is
            new_ports.append(port_placeholder)
    return new_ports


def split_image_ref(image: str) -> tuple[str, str]:
    """Split a Docker image reference into ``(name, tag)``.

    Handles images with no tag (defaults to ``latest``) and registry hosts
    that include a port, e.g. ``host:5000/repo/img``. A tag is only present
    when a ``:`` appears in the final path segment (after the last ``/``);
    otherwise any ``:`` belongs to a registry ``host:port``.
    """
    last_segment = image.rsplit("/", 1)[-1]
    if ":" in last_segment:
        name, tag = image.rsplit(":", 1)
        return name, tag
    return image, "latest"


def assemble_docker_compose(
    m4b_config_path_or_dict: Any,
    app_config_path_or_dict: Any,
    user_config_path_or_dict: Any,
    compose_output_path: str = str(os.path.join(os.getcwd(), "docker-compose.yaml")),
    is_main_instance: bool = False,
) -> list[str]:
    """
    Assemble a single Docker Compose file from the catalog + user config.

    Every service gets a ``profiles:`` array of one entry derived from its
    bundle's ``profile`` field (apps), inherited from the parent (addons),
    or assigned by the generator (Watchtower -> ``monitoring``,
    tun2socks -> ``proxy``).

    Args:
        m4b_config_path_or_dict (Any): The path to the m4b configuration file or the config dictionary.
        app_config_path_or_dict (Any): The path to the app configuration file or the config dictionary.
        user_config_path_or_dict (Any): The path to the user configuration file or the config dictionary.
        compose_output_path (str, optional): The path to save the assembled docker-compose.yaml file. Defaults to './docker-compose.yaml'.
        is_main_instance (bool, optional): Whether this is the main instance. Defaults to False.

    Returns:
        list[str]: Single-element list with the path to the generated compose file.
    """
    event = threading.Event()
    spinner_thread = threading.Thread(
        target=show_spinner, args=("Assembling Docker Compose file...", event)
    )
    spinner_thread.start()

    try:
        m4b_config = load_json_config(m4b_config_path_or_dict)
        app_config = resolve_catalog_config(app_config_path_or_dict)
        user_config = load_json_config(user_config_path_or_dict)

        http_client.configure(m4b_config)

        default_docker_platform = m4b_config["system"].get(
            "default_docker_platform", "linux/amd64"
        )
        proxy_enabled = user_config["proxies"].get("enabled", False)

        services = {}
        service_profiles: dict[str, str] = {}
        disabled_apps_due_to_incompatibility = []
        apps_categories = get_active_app_categories(app_config)

        proxy_ports = []
        app_ports_transferred = {}

        for category in apps_categories:
            for app in get_category_entries(app_config, category):
                app_name = app["name"].lower()
                user_app_config = user_config["apps"].get(app_name, {})
                if user_app_config.get("enabled"):
                    # Copy the app's compose configuration to avoid modifying the original
                    app_compose_config = app["compose_config"].copy()
                    # Substitute port placeholders with actual values
                    if "ports" in app_compose_config and "ports" in user_app_config:
                        app_compose_config["ports"] = substitute_port_placeholders(
                            app_compose_config["ports"], user_app_config["ports"]
                        )
                    image = app_compose_config["image"]
                    image_name, image_tag = split_image_ref(image)
                    docker_platform = user_app_config.get(
                        "docker_platform", default_docker_platform
                    )

                    arch_support = check_img_arch_support(
                        image_name, image_tag, docker_platform
                    )

                    if arch_support is None:
                        # Cannot determine compatibility (e.g., GHCR images without PAT)
                        # Fallback to default platform (linux/amd64) for safety - emulation will be used if needed
                        app_compose_config["platform"] = default_docker_platform
                        logger.info(
                            f"Cannot verify architecture support for {image_name}. "
                            f"Falling back to default platform {default_docker_platform} for emulation compatibility."
                        )
                    elif not arch_support:
                        compatible_tag = get_compatible_tag(image_name, docker_platform)
                        if compatible_tag:
                            app_compose_config["image"] = (
                                f"{image_name}:{compatible_tag}"
                            )
                            # Add platform also on all already compatible images tags
                            app_compose_config["platform"] = docker_platform
                            logger.info(
                                f"Updated {app_name} to compatible tag: {compatible_tag}"
                            )
                        else:
                            logger.warning(
                                f"No compatible tag found for {image_name} with architecture {docker_platform}. Searching for a suitable tag for default emulation architecture {default_docker_platform}."
                            )
                            # find a compatibile tag with default docker platform
                            compatible_tag = get_compatible_tag(
                                image_name, default_docker_platform
                            )
                            if compatible_tag:
                                app_compose_config["image"] = (
                                    f"{image_name}:{compatible_tag}"
                                )
                                # Add platform to the compose configuration to force image pull for emulation
                                app_compose_config["platform"] = default_docker_platform
                                logger.warning(
                                    f"Compatible tag found to run {image_name} with emulation on {default_docker_platform} architecture. Using binfmt emulation for {app_name} with image {image_name}:{image_tag}"
                                )
                            else:
                                error_msg = (
                                    f"No compatible tag found for {image_name} either with "
                                    f"specified architecture {docker_platform} or with default "
                                    f"architecture {default_docker_platform}."
                                )
                                logger.error(error_msg)
                                logger.error(
                                    f"Please check the image tag and architecture compatibility "
                                    f"on the registry. Disabling {app_name}..."
                                )
                                user_app_config["enabled"] = False
                                user_config["apps"][app_name] = user_app_config
                                write_json(user_config, user_config_path_or_dict)
                                logger.info(
                                    f"{app_name} has been disabled in user-config.json due to lack of compatible image tag."
                                )
                                disabled_apps_due_to_incompatibility.append(app_name)
                                continue  # Do not add the app to the compose file
                    elif arch_support:
                        # Add platform only when we've confirmed the image supports it
                        app_compose_config["platform"] = docker_platform

                    if proxy_enabled:
                        app_proxy_compose = app.get("compose_config_proxy", {})

                        # If using proxy's network, we can't publish ports directly
                        if app_proxy_compose.get("network_mode", "").startswith(
                            "service:"
                        ):
                            # If the app has ports and will use proxy, collect them for the proxy service
                            if "ports" in app_compose_config:
                                logger.info(
                                    f"Moving ports from {app_name} to proxy service as it's using proxy network"
                                )

                                # Track which app's ports are being transferred to proxy
                                app_ports_transferred[app_name] = True

                                # Check if 'ports' is a list or a single value
                                if isinstance(app_compose_config["ports"], list):
                                    for port_mapping in app_compose_config["ports"]:
                                        # Only add if the port mapping contains a variable that's defined
                                        if "${" in str(port_mapping) and "}" in str(
                                            port_mapping
                                        ):
                                            # Check if this app is enabled (we already know it is at this point)
                                            # and if it has the port defined in user_config
                                            if user_app_config.get("ports"):
                                                proxy_ports.append(port_mapping)
                                                logger.info(
                                                    f"Added port mapping {port_mapping} to proxy from {app_name}"
                                                )
                                        else:
                                            # For static port mappings
                                            proxy_ports.append(port_mapping)
                                            logger.info(
                                                f"Added static port mapping {port_mapping} to proxy from {app_name}"
                                            )
                                else:
                                    # For single port value
                                    port_mapping = app_compose_config["ports"]
                                    if "${" in str(port_mapping) and "}" in str(
                                        port_mapping
                                    ):
                                        # Check if this app is enabled and has the port defined
                                        if user_app_config.get("ports"):
                                            proxy_ports.append(port_mapping)
                                            logger.info(
                                                f"Added port mapping {port_mapping} to proxy from {app_name}"
                                            )
                                    else:
                                        # For static port mapping
                                        proxy_ports.append(port_mapping)
                                        logger.info(
                                            f"Added static port mapping {port_mapping} to proxy from {app_name}"
                                        )

                                # Remove ports from the app config since they're now handled by the proxy
                                del app_compose_config["ports"]

                        # Apply all other proxy-specific configurations
                        for key, value in app_proxy_compose.items():
                            app_compose_config[key] = value
                            if app_compose_config[key] is None:
                                del app_compose_config[key]

                        # Apps sharing the proxy network must wait for the
                        # tunnel to be healthy before starting.
                        if app_compose_config.get("network_mode", "").startswith(
                            "service:"
                        ):
                            app_compose_config["depends_on"] = {
                                "proxy": {"condition": "service_healthy"}
                            }

                    services[app_name] = app_compose_config
                    app_profile = app.get("profile", "datacenter")
                    service_profiles[app_name] = app_profile

                    # Sidecars inherit the parent's profile so they activate
                    # together under ``--profile <tier>``.
                    from money4band.apps.addons import get_addons_for

                    addons_for_app = get_addons_for(app_name, app_config)
                    if addons_for_app and user_app_config.get("service_enabled", False):
                        for addon in addons_for_app:
                            # Addon IDs are UPPER_SNAKE; compose service
                            # names are kebab-case (HONEYGAIN_POT -> honeygain-pot).
                            sidecar_name = addon["name"].lower().replace("_", "-")
                            sidecar_config = copy.deepcopy(addon["compose_config"])
                            # Apply same platform as the parent app
                            if "platform" in app_compose_config:
                                sidecar_config["platform"] = app_compose_config[
                                    "platform"
                                ]
                            services[sidecar_name] = sidecar_config
                            service_profiles[sidecar_name] = app_profile
                            logger.info(
                                "Added auto-claim sidecar '%s' for %s "
                                "(inherited profile=%s)",
                                sidecar_name,
                                app_name,
                                app_profile,
                            )

        # Add common services only if this is the main instance
        compose_config_common = user_config.get("compose_config_common", {})
        if is_main_instance:
            watchtower_enabled = user_config.get("watchtower", {}).get("enabled", True)
            if watchtower_enabled:
                # KI-024: proxy_disabled uses ROLLING_RESTART=true, proxy_enabled
                # uses false.  This is intentional: in proxy mode all app containers
                # depend on tun2socks' network stack (network_mode: service:proxy).
                # Rolling-restarting tun2socks would silently break every app's
                # connectivity, so we force a clean stop-all/start-all cycle instead.
                watchtower_service_key = (
                    "proxy_enabled" if proxy_enabled else "proxy_disabled"
                )
                watchtower_service = copy.deepcopy(
                    compose_config_common["watchtower_service"][watchtower_service_key]
                )
                # Enforce scoping env vars at generation time so older user-config
                # files (missing WATCHTOWER_SCOPE / WATCHTOWER_LABEL_ENABLE) still
                # produce a correctly scoped Watchtower service.
                wt_env: list = watchtower_service.setdefault("environment", [])
                required_env = {
                    "WATCHTOWER_SCOPE": "WATCHTOWER_SCOPE=${M4B_WATCHTOWER_SCOPE}",
                    "WATCHTOWER_LABEL_ENABLE": "WATCHTOWER_LABEL_ENABLE=${M4B_WATCHTOWER_LABELS}",
                }
                existing_keys = {e.split("=")[0] for e in wt_env if isinstance(e, str)}
                for key, entry in required_env.items():
                    if key not in existing_keys:
                        wt_env.append(entry)
                        logger.info(f"Enforced missing Watchtower env var: {entry}")
                # Enforce scope label so the service is self-managed within scope.
                wt_labels: list = watchtower_service.setdefault("labels", [])
                scope_label = (
                    "com.centurylinklabs.watchtower.scope=${M4B_WATCHTOWER_SCOPE}"
                )
                if scope_label not in wt_labels:
                    wt_labels.append(scope_label)
                    logger.info("Enforced missing Watchtower scope label")
                # KI-032: Strip notification env var when notifications disabled
                # to prevent Docker Compose WARN spam about unset variables.
                notifications_enabled = user_config.get("notifications", {}).get(
                    "enabled", False
                )
                if not notifications_enabled:
                    wt_env[:] = [
                        e
                        for e in wt_env
                        if not e.startswith("WATCHTOWER_NOTIFICATION_")
                    ]
                # Watchtower only reads config, never writes - safe to lock filesystem
                watchtower_service.setdefault("read_only", True)
                watchtower_service["profiles"] = [RESERVED_MONITORING_PROFILE]
                services["watchtower"] = watchtower_service
                service_profiles["watchtower"] = RESERVED_MONITORING_PROFILE

        if proxy_enabled:
            # Get the base proxy service configuration
            proxy_service = compose_config_common["proxy_service"].copy()

            # Add collected ports from apps to the proxy service
            if proxy_ports:
                # If 'ports' key not in the proxy service, create it
                if "ports" not in proxy_service:
                    proxy_service["ports"] = []
                elif not isinstance(proxy_service["ports"], list):
                    # If it's not a list, convert it to one
                    proxy_service["ports"] = [proxy_service["ports"]]

                # Add required ports from enabled apps
                for port_mapping in proxy_ports:
                    if port_mapping not in proxy_service["ports"]:
                        proxy_service["ports"].append(port_mapping)

                logger.info(
                    f"Added {len(proxy_ports)} port mappings to the proxy service from apps using its network"
                )

            proxy_service["healthcheck"] = {
                "test": [
                    "CMD-SHELL",
                    "ip link show tun0 2>/dev/null | grep -q UP || exit 1",
                ],
                "interval": "30s",
                "timeout": "5s",
                "retries": 3,
                "start_period": "30s",
            }
            proxy_service["profiles"] = [RESERVED_PROXY_PROFILE]
            services["proxy"] = proxy_service
            service_profiles["proxy"] = RESERVED_PROXY_PROFILE

        # Define network configuration using config json and environment variables
        # This is a hybrid solution to remember that it could be possible to ditch the env file and generate all compose file parts from config json
        network_config = {
            "networks": {
                "default": {
                    "driver": compose_config_common["network"]["driver"],
                    "ipam": {
                        "config": [
                            {
                                "subnet": f"{compose_config_common['network']['subnet']}/{compose_config_common['network']['netmask']}"
                            }
                        ]
                    },
                }
            }
        }

        # Harden non-privileged services: prevent setuid/setgid escalation.
        for svc_config in services.values():
            if not svc_config.get("privileged", False):
                svc_config.setdefault("security_opt", ["no-new-privileges:true"])

        # Centralised DNS: custom servers replace per-service DNS; default
        # mode strips leftover per-service entries so Docker uses the host.
        dns_cfg = user_config.get("settings", {})
        if dns_cfg.get("dns_mode") == "custom":
            dns_servers = dns_cfg.get("dns_servers", [])
            if dns_servers:
                for svc_config in services.values():
                    svc_config["dns"] = list(dns_servers)
        else:
            for svc_config in services.values():
                svc_config.pop("dns", None)

        # Apply ``profiles:`` to every service. Watchtower and tun2socks
        # already carry their reserved profile from the blocks
        # above (we don't overwrite if profiles is already set).
        for svc_name, svc_config in services.items():
            if "profiles" not in svc_config:
                assigned = service_profiles.get(svc_name)
                if assigned:
                    svc_config["profiles"] = [assigned]

        generated_files: list[str] = []
        compose_dict = {"services": services}
        compose_dict.update(network_config)
        output_dir = os.path.dirname(compose_output_path) or "."
        # Strip any leftover layered compose files from prior runs.
        for stale_layer in (
            "compose.yml",
            "compose.residential.yml",
            "compose.datacenter.yml",
            "compose.universal.yml",
            "compose.service.yml",
            "compose.proxy.yml",
        ):
            stale = os.path.join(output_dir, stale_layer)
            if os.path.isfile(stale):
                os.remove(stale)
                logger.info("Removed legacy layered compose file: %s", stale_layer)
        with open(compose_output_path, "w") as f:
            yaml.dump(compose_dict, f, sort_keys=False, default_flow_style=False)
        generated_files.append(compose_output_path)

        logger.info(f"Docker Compose file(s) assembled: {generated_files}")
        if disabled_apps_due_to_incompatibility:
            # disable the apps and save updated config

            # inform the user
            print(
                "\nThe following apps were disabled due to image tag/architecture incompatibility with this device:"
            )
            for app in disabled_apps_due_to_incompatibility:
                print(f"- {app}")
            time.sleep(2 * m4b_config.get("system", {}).get("sleep_time", 2))
    except Exception as e:
        logger.error(f"Error during Docker Compose assembly: {e}")
        raise
    finally:
        event.set()
        spinner_thread.join()
    return generated_files
