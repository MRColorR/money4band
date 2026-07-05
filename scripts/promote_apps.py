"""Promote newcomer apps to supported (per-file catalog layout)."""

from __future__ import annotations

import json
from pathlib import Path

from money4band.core.catalog_store import catalog_root, move_entry

CONFIG = Path("config/m4b-config.json")

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

BEARSHARE_ADDON = {
    "name": "BEARSHARE_POT",
    "parent_id": "BEARSHARE",
    "description": "Auto-claims daily BearShare reward",
    "credentials_shared": True,
    "profile": "service",
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


def _candidates() -> list[Path]:
    root = catalog_root(CONFIG)
    newcomers = root / "newcomers"
    return sorted(p for p in newcomers.glob("*.json") if p.stem in PROMOTE_NAMES)


def main() -> None:
    promoted: list[str] = []
    for src in _candidates():
        name = src.stem
        with open(src, encoding="utf-8") as f:
            entry = json.load(f)

        entry.setdefault("app_details", {}).setdefault("docker", {})
        if name in DOCKER_UPDATES:
            entry["app_details"]["docker"].update(DOCKER_UPDATES[name])
        entry["app_details"]["recommendation"] = "promoted"
        entry["app_details"]["recommendation_reasoning"] = (
            "Promoted to supported. Docker image verified on Docker Hub."
        )
        entry["app_details"]["last_verified"] = "2026-03-23"

        if name == "BEARSHARE":
            addon_path = catalog_root(CONFIG) / "addons" / "BEARSHARE_POT.json"
            addon_path.parent.mkdir(parents=True, exist_ok=True)
            addon_path.write_text(
                json.dumps(BEARSHARE_ADDON, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

        # Move per-file bundle: newcomers/ -> supported/
        move_entry(CONFIG, name, "newcomers", "supported", updates=entry)
        promoted.append(name)

    print(f"Promoted: {promoted}")
    print("Done.")


if __name__ == "__main__":
    main()
