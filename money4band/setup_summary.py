from __future__ import annotations

"""Generate a human-readable setup summary after the wizard completes."""

import logging
import os
from datetime import datetime, timezone
from typing import Any

from colorama import Fore, Style


logger = logging.getLogger(__name__)
SUMMARY_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "logs",
    "setup-summary.txt",
)


def generate_setup_summary(
    user_config: dict[str, Any],
    app_config: dict[str, Any],
) -> str:
    """Build and write ``logs/setup-summary.txt``, then print a brief overview.

    Returns the path to the written file.
    """
    lines: list[str] = []
    lines.append("=" * 60)
    lines.append("  M4B Setup Summary")
    lines.append(
        f"  Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    lines.append("=" * 60)

    # --- Device info ---
    device = user_config.get("device_info", {})
    lines.append("")
    lines.append("Device Information")
    lines.append(f"  Name:         {device.get('device_name', 'N/A')}")
    lines.append(f"  OS:           {device.get('os_type', 'N/A')}")
    lines.append(f"  Architecture: {device.get('detected_architecture', 'N/A')}")

    # --- Enabled apps ---
    apps = user_config.get("apps", {})
    enabled_apps = [name for name, cfg in apps.items() if cfg.get("enabled")]
    disabled_apps = [name for name, cfg in apps.items() if not cfg.get("enabled")]
    lines.append("")
    lines.append(f"Enabled Apps ({len(enabled_apps)})")
    for name in sorted(enabled_apps):
        lines.append(f"  + {name}")
    lines.append(f"Disabled Apps ({len(disabled_apps)})")
    for name in sorted(disabled_apps):
        lines.append(f"  - {name}")

    # --- Dashboard ---
    dash = user_config.get("m4b_dashboard", {})
    if dash.get("enabled"):
        ports = dash.get("ports", [8081])
        lines.append("")
        lines.append(f"Dashboard: http://localhost:{ports[0] if ports else 8081}")
    else:
        lines.append("")
        lines.append("Dashboard: disabled")

    # --- Watchtower ---
    wt = user_config.get("watchtower", {})
    lines.append(f"Watchtower auto-update: {'enabled' if wt.get('enabled') else 'disabled'}")

    # --- Notifications ---
    notif = user_config.get("notifications", {})
    lines.append(
        f"Notifications: {'enabled' if notif.get('enabled') else 'disabled'}"
    )

    # --- Proxy ---
    proxy = user_config.get("proxies", {})
    proxy_enabled = proxy.get("enabled", False)
    lines.append("")
    lines.append(f"Proxy: {'enabled' if proxy_enabled else 'disabled'}")
    if proxy_enabled:
        # Count multi-proxy instances
        instances_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "m4b-instances",
        )
        instance_count = 0
        if os.path.isdir(instances_dir):
            instance_count = sum(
                1
                for d in os.listdir(instances_dir)
                if os.path.isdir(os.path.join(instances_dir, d))
            )
        lines.append(f"  Multi-proxy instances: {instance_count}")

    # --- Resource estimate ---
    lines.append("")
    lines.append("Estimated Resource Usage")
    lines.append(f"  Active containers: ~{len(enabled_apps) + (2 if dash.get('enabled') else 1)}")
    lines.append("  (watchtower + dashboard + one per enabled app)")

    lines.append("")
    lines.append("=" * 60)
    lines.append("Run 'python main.py start' to launch the stack.")
    lines.append("=" * 60)

    content = "\n".join(lines) + "\n"

    # Write to file
    os.makedirs(os.path.dirname(SUMMARY_PATH), exist_ok=True)
    with open(SUMMARY_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info("Setup summary written to %s", SUMMARY_PATH)

    # Print abbreviated overview to console
    print(f"\n{Fore.GREEN}{'=' * 50}")
    print(f"  Setup Complete!")
    print(f"{'=' * 50}{Style.RESET_ALL}")
    print(f"  Enabled apps: {Fore.CYAN}{len(enabled_apps)}{Style.RESET_ALL}")
    if dash.get("enabled"):
        port = dash.get("ports", [8081])[0] if dash.get("ports") else 8081
        print(f"  Dashboard:    {Fore.CYAN}http://localhost:{port}{Style.RESET_ALL}")
    print(f"  Proxy:        {Fore.CYAN}{'enabled' if proxy_enabled else 'disabled'}{Style.RESET_ALL}")
    print(
        f"\n  Full summary saved to: {Fore.YELLOW}{SUMMARY_PATH}{Style.RESET_ALL}\n"
    )

    return SUMMARY_PATH
