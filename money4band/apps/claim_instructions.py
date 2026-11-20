"""Local post-setup instructions for each stack's provider devices."""

from __future__ import annotations

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from money4band.core.loader import get_active_app_categories, get_category_entries

logger = logging.getLogger(__name__)


def write_claim_instructions(
    app_config: dict[str, Any],
    user_config: dict[str, Any],
    directory: str | Path,
    services: dict[str, Any],
) -> list[Path]:
    """Write only onboarding details, never account credentials."""
    device = user_config.get("device_info", {}).get("device_name", "")
    written: list[Path] = []
    for category in get_active_app_categories(app_config):
        for app in get_category_entries(app_config, category):
            name = app["name"].lower()
            if name not in services or not re.fullmatch(r"[a-z0-9_]+", name):
                continue
            config = user_config.get("apps", {}).get(name, {})
            flags = app.get("flags", {})
            manual = flags.get("manual", {})
            instructions = manual.get("instructions") or flags.get(
                "machine_id", {}
            ).get("claimURLBase")
            uuid_flags = flags.get("uuid", {})
            claim_base = uuid_flags.get("claimURLBase")
            if not instructions and not claim_base:
                continue
            container = (
                services[name]
                .get("container_name", "")
                .replace("${DEVICE_NAME}", device)
            )
            lines = [app["name"], f"Device: {device}", f"Container: {container}"]
            if app.get("dashboard"):
                lines.append(f"Dashboard: {app['dashboard']}")
            for field, label in (("uuid", "Device ID"), ("machine_id", "Machine ID")):
                if config.get(field):
                    lines.append(f"{label}: {config[field]}")
            if manual.get("device_key_from_logs"):
                lines.append("Device Key: available after startup")
            ports = config.get("ports", [])
            if isinstance(ports, list) and ports:
                lines.append(f"Local WebUI: http://localhost:{ports[0]}")
            lines.append("")
            if claim_base and config.get("uuid"):
                uuid = str(config["uuid"])
                prefix = uuid_flags.get("prefix", "")
                if prefix and uuid.startswith(prefix):
                    uuid = uuid[len(prefix) :]
                lines.extend([f"{claim_base}{uuid}", ""])
            if instructions:
                lines.append(str(instructions))
            if manual.get("device_key_from_logs"):
                lines.extend(["", f"Device Key logs: docker logs {container}"])
            path = Path(directory) / f"claim_instructions_{name}.txt"
            try:
                path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            except OSError as exc:
                logger.warning("Cannot save setup instructions to %s: %s", path, exc)
                continue
            written.append(path)
            print(f"Setup instructions saved: {path}")
    return written


def refresh_claim_keys(directory: str | Path, *, use_sudo: bool = False) -> None:
    """Fill device keys after startup when logs match the saved machine identity."""
    for path in Path(directory).glob("claim_instructions_*.txt"):
        try:
            text = path.read_text(encoding="utf-8")
            if not re.search(r"^Device Key:", text, re.MULTILINE):
                continue
            container = re.search(
                r"^Container: ([a-zA-Z0-9][a-zA-Z0-9_.-]*)$", text, re.MULTILINE
            )
            identity = re.search(r"^Machine ID: ([0-9a-fA-F]{32})$", text, re.MULTILINE)
            if not container or not identity:
                continue
            command = (["sudo"] if use_sudo else []) + [
                "docker",
                "logs",
                "--tail",
                "100",
                container[1],
            ]
            for attempt in range(3):
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5,
                    check=False,
                )
                logs = (result.stdout + "\n" + result.stderr)[-20000:]
                machines = re.findall(r"Machine ID:\s*([0-9a-fA-F]{32})", logs)
                keys = re.findall(r"Device Key:\s*([0-9a-fA-F]{64})", logs)
                if (
                    result.returncode == 0
                    and machines
                    and machines[-1] == identity[1]
                    and keys
                ):
                    text = re.sub(
                        r"^Device Key:.*$",
                        f"Device Key: {keys[-1]}",
                        text,
                        flags=re.MULTILINE,
                    )
                    path.write_text(text, encoding="utf-8")
                    print(f"Device Key saved: {path}")
                    break
                if attempt < 2:
                    time.sleep(0.5)
        except (OSError, UnicodeError, subprocess.TimeoutExpired) as exc:
            logger.warning("Cannot refresh device key in %s: %s", path, exc)
