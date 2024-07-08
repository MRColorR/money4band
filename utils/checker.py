import requests
import logging
from typing import Dict

# Store the Docker Hub base URL in a variable
DOCKERHUB_BASE_URL = "https://registry.hub.docker.com/v2/"

def fetch_docker_tags(image: str) -> Dict:
    """
    Fetch the tags of a Docker image from Docker Hub.
    """
    try:
        response = requests.get(f"{DOCKERHUB_BASE_URL}repositories/{image}/tags")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Error fetching Docker tags for {image}: {str(e)}")
        return {}

def check_img_arch_support(image: str, tag: str, arch: str) -> bool:
    """
    Check if a Docker image tag supports the given architecture.
    """
    tags_info = fetch_docker_tags(image)
    tag_info = next((t for t in tags_info.get('results', []) if t['name'] == tag), None)

    if not tag_info:
        logging.error(f"Tag {tag} not found for image {image}")
        return False

    return any(image_info['architecture'] == arch for image_info in tag_info['images'])

def get_compatible_tag(image: str, arch: str) -> str:
    """
    Get a compatible tag for the given architecture if the default tag is not supported.
    """
    tags_info = fetch_docker_tags(image)
    compatible_tag = next((t['name'] for t in tags_info.get('results', []) if any(image_info['architecture'] == arch for image_info in t['images'])), None)
    return compatible_tag if compatible_tag else ""
