from __future__ import annotations

import logging
import os
import sys
import time

import requests

from money4band import http_client
from money4band.helper import ensure_service
from money4band.http_client import get_session

logger = logging.getLogger(__name__)

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

DOCKERHUB_BASE_URL = "https://registry.hub.docker.com/v2/"
GHCR_BASE_URL = "https://ghcr.io/v2/"


def fetch_docker_tags(image: str) -> dict | None:
    """
    Fetch the tags of a Docker image from Docker Hub or GHCR.

    Uses retry-with-backoff for transient network/server errors
    and a connection timeout to avoid hanging on unresponsive registries.

    Args:
        image (str): The name of the Docker image.

    Returns:
        dict | None: Tag information if successful, None otherwise.
    """
    session = get_session()
    timeout = http_client.REQUEST_TIMEOUT
    try:
        if image.startswith("ghcr.io/"):
            ghcr_image = image.replace("ghcr.io/", "")
            url = f"{GHCR_BASE_URL}{ghcr_image}/tags/list"
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            tags = response.json().get("tags", [])
            return {"results": [{"name": tag, "images": []} for tag in tags]}
        else:
            url = f"{DOCKERHUB_BASE_URL}repositories/{image}/tags"
            response = session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
    except requests.ConnectionError:
        logger.error(
            "Cannot reach registry for %s — network may be down. "
            "Retries exhausted after %s attempts.",
            image,
            http_client.MAX_RETRIES,
        )
        return None
    except requests.Timeout:
        logger.error("Registry request timed out for %s after %ss.", image, timeout)
        return None
    except requests.RequestException as e:
        logger.error("Error fetching Docker tags for %s: %s", image, e)
        return None


def check_img_arch_support(image: str, tag: str, docker_platform: str) -> bool | None:
    """
    Check if a Docker image tag supports the given docker platform.

    Args:
        image (str): The name of the Docker image.
        tag (str): The specific tag of the Docker image.
        docker_platform (str): The docker platform to check
            (e.g., 'linux/arm64').

    Returns:
        bool | None: True if the architecture is supported, False if not supported,
                     None if we cannot determine compatibility (e.g., GHCR images
                     without PAT, or registry unreachable).
    """
    if image.startswith("ghcr.io/"):
        logger.warning(
            "Skipping arch check for GHCR image %s (requires GH PAT). "
            "Falling back to default platform for emulation.",
            image,
        )
        print(
            f"\n[WARNING] Cannot check arch for GHCR image {image} "
            f"(requires GH PAT). Falling back to linux/amd64 for emulation."
        )
        time.sleep(4)
        return None
    arch = docker_platform.split("/")[1]
    tags_info = fetch_docker_tags(image)
    if tags_info is None:
        logger.warning(
            "Cannot reach registry for %s — skipping arch check. "
            "Docker will attempt to pull at stack start.",
            image,
        )
        return None

    tag_info = next((t for t in tags_info.get("results", []) if t["name"] == tag), None)
    if not tag_info:
        logger.error("Tag %s not found for image %s", tag, image)
        return False

    return any(image_info["architecture"] == arch for image_info in tag_info["images"])


def get_compatible_tag(image: str, docker_platform: str) -> str | None:
    """
    Get a compatible tag for the given architecture if the default tag is not supported.
    If no compatible tag is found, ensure multi-arch emulation support with binfmt.

    Args:
        image (str): The name of the Docker image.
        arch (str): The architecture to check for compatibility.

    Returns:
        Optional[str]: The compatible tag name if found, None otherwise.
    """
    arch = docker_platform.split("/")[1]
    tags_info = fetch_docker_tags(image)
    if tags_info is None:
        return None

    compatible_tag = next(
        (
            t["name"]
            for t in tags_info.get("results", [])
            if any(image_info["architecture"] == arch for image_info in t["images"])
        ),
        None,
    )

    if not compatible_tag:
        service_file_path = os.path.join(
            os.getcwd(), ".resources", ".files", "docker.binfmt.service"
        )
        ensure_service(
            service_name="docker.binfmt", service_file_path=service_file_path
        )
        logger.warning(
            "No compatible tag found for %s on %s. "
            "Will attempt binfmt multi-arch emulation.",
            image,
            docker_platform,
        )
    else:
        logger.info(
            "Found compatible tag %s for %s on %s",
            compatible_tag,
            image,
            docker_platform,
        )

    return compatible_tag
