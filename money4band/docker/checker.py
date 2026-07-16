from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from money4band.docker.helper import ensure_service
from money4band.network import http_client
from money4band.network.http_client import get_client

logger = logging.getLogger(__name__)

DOCKERHUB_BASE_URL = "https://registry.hub.docker.com/v2/"
GHCR_BASE_URL = "https://ghcr.io/v2/"

# Short-lived per-process memo: one compose assembly asks for the same
# image's tags up to 3 times (arch check + compatible-tag x2), each behind
# a retry/backoff transport.
_TAGS_CACHE_TTL = 600.0  # seconds
_tags_cache: dict[str, tuple[float, dict | None]] = {}


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
    cached = _tags_cache.get(image)
    if cached is not None and time.monotonic() - cached[0] < _TAGS_CACHE_TTL:
        return cached[1]

    client = get_client()
    timeout = http_client.REQUEST_TIMEOUT
    try:
        if image.startswith("ghcr.io/"):
            ghcr_image = image.replace("ghcr.io/", "")
            url = f"{GHCR_BASE_URL}{ghcr_image}/tags/list"
            response = client.get(url, timeout=timeout)
            response.raise_for_status()
            tags = response.json().get("tags", [])
            result = {"results": [{"name": tag, "images": []} for tag in tags]}
            _tags_cache[image] = (time.monotonic(), result)
            return result
        else:
            url = f"{DOCKERHUB_BASE_URL}repositories/{image}/tags"
            response = client.get(url, timeout=timeout)
            response.raise_for_status()
            payload: dict[Any, Any] = response.json()
            _tags_cache[image] = (time.monotonic(), payload)
            return payload
    except httpx.ConnectError:
        logger.error(
            "Cannot reach registry for %s - network may be down. "
            "Retries exhausted after %s attempts.",
            image,
            http_client.MAX_RETRIES,
        )
        return None
    except httpx.TimeoutException:
        logger.error("Registry request timed out for %s after %ss.", image, timeout)
        return None
    except httpx.HTTPError as e:
        logger.error("Error fetching Docker tags for %s: %s", image, e)
        return None


def _parse_platform(docker_platform: str) -> tuple[str, str | None]:
    """Split ``linux/arm/v7`` into ``('arm', 'v7')``; no variant -> None."""
    parts = docker_platform.split("/")
    arch = parts[1] if len(parts) > 1 else parts[0]
    variant = parts[2] if len(parts) > 2 else None
    return arch, variant


def _image_matches(image_info: dict, arch: str, variant: str | None) -> bool:
    """Match a registry manifest entry against (arch, variant).

    ``arm/v6`` and ``arm/v7`` are NOT interchangeable: matching on
    architecture alone approved v7-only images on armv6 hosts, and the
    pinned ``platform:`` then failed at pull time.
    """
    if image_info.get("architecture") != arch:
        return False
    if variant is None:
        return True
    manifest_variant = image_info.get("variant") or None
    return manifest_variant == variant


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
        # Log-only: this runs inside the compose-assembly loop behind a
        # spinner - a print + 4s sleep per GHCR image added ~20s dead time
        # to every stack generation without changing the outcome.
        logger.warning(
            "Skipping arch check for GHCR image %s (requires GH PAT). "
            "Falling back to default platform for emulation.",
            image,
        )
        return None
    arch, variant = _parse_platform(docker_platform)
    tags_info = fetch_docker_tags(image)
    if tags_info is None:
        logger.warning(
            "Cannot reach registry for %s - skipping arch check. "
            "Docker will attempt to pull at stack start.",
            image,
        )
        return None

    tag_info = next((t for t in tags_info.get("results", []) if t["name"] == tag), None)
    if not tag_info:
        logger.error("Tag %s not found for image %s", tag, image)
        return False

    return any(
        _image_matches(image_info, arch, variant) for image_info in tag_info["images"]
    )


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
    arch, variant = _parse_platform(docker_platform)
    tags_info = fetch_docker_tags(image)
    if tags_info is None:
        return None

    compatible_tag = next(
        (
            t["name"]
            for t in tags_info.get("results", [])
            if any(
                _image_matches(image_info, arch, variant) for image_info in t["images"]
            )
        ),
        None,
    )

    if not compatible_tag:
        from money4band.resources import get_path

        service_file_path = str(get_path("files", "docker.binfmt.service"))
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
