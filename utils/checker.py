import requests
import logging
import sys
import os
from typing import Dict, Optional

# Ensure the parent directory is in the sys.path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from utils.helper import ensure_service

# Store the Docker Hub base URL in a variable
DOCKERHUB_BASE_URL = "https://registry.hub.docker.com/v2/"

def fetch_docker_tags(image: str) -> Optional[Dict]:
    """
    Fetch the tags of a Docker image from Docker Hub.

    Args:
        image (str): The name of the Docker image.

    Returns:
        Optional[Dict]: A dictionary containing tag information if successful, None otherwise.
    """
    try:
        response = requests.get(f"{DOCKERHUB_BASE_URL}repositories/{image}/tags")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching Docker tags for {image}: {str(e)}")
        return None

def check_img_arch_support(image: str, tag: str, arch: str) -> bool:
    """
    Check if a Docker image tag supports the given architecture.

    Args:
        image (str): The name of the Docker image.
        tag (str): The specific tag of the Docker image.
        arch (str): The architecture to check for compatibility.

    Returns:
        bool: True if the architecture is supported, False otherwise.
    """
    tags_info = fetch_docker_tags(image)
    if tags_info is None:
        return False

    tag_info = next((t for t in tags_info.get('results', []) if t['name'] == tag), None)
    if not tag_info:
        logging.error(f"Tag {tag} not found for image {image}")
        return False

    return any(image_info['architecture'] == arch for image_info in tag_info['images'])

def get_compatible_tag(image: str, arch: str) -> Optional[str]:
    """
    Get a compatible tag for the given architecture if the default tag is not supported.
    If no compatible tag is found, ensure multi-arch emulation support with binfmt.

    Args:
        image (str): The name of the Docker image.
        arch (str): The architecture to check for compatibility.

    Returns:
        Optional[str]: The compatible tag name if found, None otherwise.
    """
    tags_info = fetch_docker_tags(image)
    if tags_info is None:
        return None

    compatible_tag = next(
        (t['name'] for t in tags_info.get('results', []) if any(image_info['architecture'] == arch for image_info in t['images'])),
        None
    )

    if compatible_tag:
        logging.info(f"Found compatible tag {compatible_tag} for {image} on {arch} architecture.")
    else:
        logging.info(f"No compatible tag found for {image} on {arch} architecture.")

        # Construct the path to the docker.binfmt.service file
        service_file_path = os.path.join(os.getcwd(), '.resources', '.files', 'docker.binfmt.service')
        
        # Ensure multi-arch emulation support with binfmt if no compatible tag is found
        ensure_service(service_name="docker.binfmt", service_file_path=service_file_path)
        
        # Log and inform the user that no compatible tag for the architecture was found
        logging.warning("No compatible tag found. The software will attempt to run the app using binfmt multi-arch emulation.")

    return compatible_tag
