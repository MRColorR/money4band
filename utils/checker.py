import logging
import os
import sys
import time
from typing import Dict, Optional

import requests

from utils.helper import ensure_service

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Store the Docker Hub base URL in a variable
DOCKERHUB_BASE_URL = "https://registry.hub.docker.com/v2/"

# Store the GitHub Container Registry base URL in a variable
GHCR_BASE_URL = "https://ghcr.io/v2/"


def fetch_docker_tags(image: str) -> Optional[Dict]:
    """
    Fetch the tags of a Docker image from Docker Hub.

    Args:
        image (str): The name of the Docker image.

    Returns:
        Optional[Dict]: A dictionary containing tag information if successful, None otherwise.
    """
    try:
        # Detect GHCR images (ghcr.io/owner/image)
        if image.startswith("ghcr.io/"):
            # Remove 'ghcr.io/' prefix for API
            ghcr_image = image.replace("ghcr.io/", "")
            url = f"{GHCR_BASE_URL}{ghcr_image}/tags/list"
            response = requests.get(url)
            response.raise_for_status()
            # GHCR returns tags in 'tags' key, but does not provide architecture info
            tags = response.json().get("tags", [])
            # Return a Docker Hub-like structure for compatibility
            return {"results": [{"name": tag, "images": []} for tag in tags]}
        else:
            # Docker Hub image (owner/image or library/image)
            url = f"{DOCKERHUB_BASE_URL}repositories/{image}/tags"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching Docker tags for {image}: {str(e)}")
        return None


def check_img_arch_support(image: str, tag: str, docker_platform: str) -> bool:
    """
    Check if a Docker image tag supports the given docker platform.

    Args:
        image (str): The name of the Docker image.
        tag (str): The specific tag of the Docker image.
        arch (str): The architecture to check for compatibility.

    Returns:
        bool: True if the architecture is supported, False otherwise.
    """
    if image.startswith("ghcr.io/"):
        logging.warning(
            f"Skipping architecture/tag compatibility check for GHCR image: {image}. (As it would require a GH PAT). Using provided tag '{tag}' as compatible."
        )
        print(
            f"\n[WARNING] Cannot check architecture/tag for GHCR image {image}. (As it would require a GH PAT). Using provided tag '{tag}'."
        )
        time.sleep(4)
        return True
    arch = docker_platform.split("/")[1]
    tags_info = fetch_docker_tags(image)
    if tags_info is None:
        return False

    tag_info = next((t for t in tags_info.get("results", []) if t["name"] == tag), None)
    if not tag_info:
        logging.error(f"Tag {tag} not found for image {image}")
        return False

    return any(image_info["architecture"] == arch for image_info in tag_info["images"])


def get_compatible_tag(image: str, docker_platform: str) -> Optional[str]:
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
        # Construct the path to the docker.binfmt.service file
        service_file_path = os.path.join(
            os.getcwd(), ".resources", ".files", "docker.binfmt.service"
        )

        # Ensure multi-arch emulation support with binfmt if no compatible tag is found
        ensure_service(
            service_name="docker.binfmt", service_file_path=service_file_path
        )

        # Log and inform the user that no compatible tag for the architecture was found
        logging.warning(
            f"No compatible tag found for {image} on platform {docker_platform}. The software will attempt to run the app using binfmt multi-arch emulation."
        )
    else:
        logging.info(
            f"Found compatible tag {compatible_tag} for {image} on platform {docker_platform}"
        )

    return compatible_tag
