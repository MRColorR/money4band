"""Promote newcomer apps to supported."""

import json
from pathlib import Path

CONFIG = Path("config/app-config.json")

PROMOTE_NAMES = {
    "SPIDE",
    "GAGANODE",
    "WIZARDGAIN",
    "ANTGAIN",
    "BEARSHARE",
    "URNETWORK",
    "TITAN",
}

# Docker Hub metadata gathered 2026-03-23
DOCKER_UPDATES = {
    "BEARSHARE": {
        "last_update": "2024-12",
        "image_official": True,
        "image_maintained": True,
    },
    "WIZARDGAIN": {
        "last_update": "2025-12",
        "image_official": True,
        "image_maintained": True,
    },
    "ANTGAIN": {
        "last_update": "2026-02",
        "image_official": True,
        "image_maintained": True,
    },
    "URNETWORK": {
        "last_update": "2026-03",
        "image_official": True,
        "image_maintained": True,
    },
    "SPIDE": {
        "last_update": "2024-10",
        "image_official": False,
        "image_maintained": True,
    },
    "GAGANODE": {
        "last_update": "2024-10",
        "image_official": False,
        "image_maintained": True,
    },
    "TITAN": {
        "last_update": "2024-12",
        "image_official": True,
        "image_maintained": True,
    },
}


def main():
    with open(CONFIG, encoding="utf-8") as f:
        config = json.load(f)

    to_promote = [
        a for a in config["newcomers"]["entries"] if a["name"] in PROMOTE_NAMES
    ]
    remaining = [
        a for a in config["newcomers"]["entries"] if a["name"] not in PROMOTE_NAMES
    ]

    for app in to_promote:
        name = app["name"]

        # Update Docker Hub metadata
        if name in DOCKER_UPDATES:
            app["app_details"]["docker"].update(DOCKER_UPDATES[name])

        # Mark as promoted
        app["app_details"]["recommendation"] = "promoted"
        app["app_details"]["recommendation_reasoning"] = (
            "Promoted to supported. Docker image verified on Docker Hub."
        )
        app["app_details"]["last_verified"] = "2026-03-23"

        # Add bearshare-pot sidecar (matches honeygain-pot / packetshare-pot pattern)
        if name == "BEARSHARE":
            app["service"] = {
                "name": "bearshare-pot",
                "description": "Auto-claims daily BearShare reward",
                "credentials_shared": True,
                "compose_config": {
                    "container_name": "${DEVICE_NAME}_bearshare-pot",
                    "hostname": "${DEVICE_NAME}_bearshare-pot",
                    "image": "ghcr.io/xterna/bearshare-pot:latest",
                    "environment": [
                        "EMAIL=${BEARSHARE_EMAIL}",
                        "PASSWORD=${BEARSHARE_PASSWORD}",
                    ],
                    "labels": [
                        "com.centurylinklabs.watchtower.enable=true",
                        "com.centurylinklabs.watchtower.scope=${M4B_WATCHTOWER_SCOPE}",
                    ],
                    "restart": "always",
                    "cpus": "${APP_CPU_LIMIT_LITTLE}",
                    "mem_reservation": "${APP_MEM_RESERV_LITTLE}",
                    "mem_limit": "${APP_MEM_LIMIT_LITTLE}",
                    "logging": {
                        "driver": "json-file",
                        "options": {"max-size": "10m", "max-file": "3"},
                    },
                },
            }

    # Move promoted ➜ supported, keep remainder in newcomers
    config["supported"]["entries"].extend(to_promote)
    config["newcomers"]["entries"] = remaining

    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    print(f"Promoted: {[a['name'] for a in to_promote]}")
    print(f"Supported: {len(config['supported']['entries'])} apps")
    print(f"Newcomers remaining: {len(config['newcomers']['entries'])}")
    print("Done.")


if __name__ == "__main__":
    main()
