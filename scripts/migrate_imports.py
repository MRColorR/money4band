#!/usr/bin/env python3
"""Migrate all imports after money4band package reorganization.

This script rewrites all `from money4band.X import Y` and `import money4band.X`
statements across the entire codebase (source + tests) to use the new subpackage
paths.
"""

import os
import re

# ── Import path mapping (old module path → new module path) ──────────────

IMPORT_MAP = {
    # apps/
    "money4band.app_configurator": "money4band.apps.configurator",
    "money4band.app_info": "money4band.apps.info",
    "money4band.app_schema": "money4band.apps.schema",
    "money4band.app_wizard": "money4band.apps.wizard",
    "money4band.fn_app_catalog": "money4band.apps.catalog",
    "money4band.fn_setupApps": "money4band.apps.setup",
    "money4band.offers": "money4band.apps.offers",
    "money4band.earnings_estimator": "money4band.apps.earnings",
    # core/
    "money4band.backup": "money4band.core.backup",
    "money4band.crypto": "money4band.core.crypto",
    "money4band.dumper": "money4band.core.dumper",
    "money4band.loader": "money4band.core.loader",
    "money4band.profiles": "money4band.core.profiles",
    "money4band.setup_progress": "money4band.core.progress",
    "money4band.fn_reset_config": "money4band.core.reset",
    "money4band.config_viewer": "money4band.core.viewer",
    # docker/
    "money4band.checker": "money4band.docker.checker",
    "money4band.compose_builder": "money4band.docker.compose_builder",
    "money4band.env_builder": "money4band.docker.env_builder",
    "money4band.generator": "money4band.docker.generator",
    "money4band.helper": "money4band.docker.helper",
    "money4band.image_security": "money4band.docker.image_security",
    "money4band.fn_install_docker": "money4band.docker.install",
    "money4band.monitor": "money4band.docker.monitor",
    "money4band.fn_startStack": "money4band.docker.start",
    "money4band.fn_stopStack": "money4band.docker.stop",
    "money4band.watchtower_setup": "money4band.docker.watchtower",
    # network/
    "money4band.http_client": "money4band.network.http_client",
    "money4band.ip_scorer": "money4band.network.ip_scorer",
    "money4band.multiproxy_setup": "money4band.network.multiproxy",
    "money4band.networker": "money4band.network.networker",
    "money4band.port_manager": "money4band.network.port_manager",
    "money4band.fn_multiproxy_tools": "money4band.network.proxy_tools",
    "money4band.downloader": "money4band.network.downloader",
    # system/
    "money4band.detector": "money4band.system.detector",
    "money4band.system_info": "money4band.system.info",
    "money4band.fn_resource_profiles": "money4band.system.resource_profiles",
    # ui/
    "money4band.banner": "money4band.ui.banner",
    "money4band.fn_bye": "money4band.ui.bye",
    "money4band.cls": "money4band.ui.cls",
    "money4band.notification_setup": "money4band.ui.notification_setup",
    "money4band.prompt_helper": "money4band.ui.prompt",
    "money4band.setup_summary": "money4band.ui.summary",
    # removed shim
    "money4band.fn_dashboard": "money4band.dashboard.menu",
}

# Sort by longest key first so longer paths match before shorter prefixes
SORTED_PAIRS = sorted(IMPORT_MAP.items(), key=lambda kv: -len(kv[0]))

# Directories to scan
SCAN_DIRS = [
    "money4band",
    "tests",
    "scripts",
]
SCAN_FILES = ["main.py"]

# Files to skip
SKIP_PATTERNS = {"__pycache__", ".pyc", "migrate_imports.py"}


def should_process(filepath: str) -> bool:
    """Return True if the file should be processed."""
    if not filepath.endswith(".py"):
        return False
    for skip in SKIP_PATTERNS:
        if skip in filepath:
            return False
    return True


def rewrite_file(filepath: str) -> int:
    """Rewrite imports in a single file. Returns count of replacements."""
    with open(filepath, encoding="utf-8") as f:
        content = f.read()

    original = content
    count = 0

    for old_path, new_path in SORTED_PAIRS:
        # Pattern 1: from money4band.X import Y
        # Pattern 2: import money4band.X
        # Pattern 3: @patch("money4band.X.something")
        # Pattern 4: "money4band.X" in string literals (for patches, mocks)

        # Replace in import statements
        old_escaped = re.escape(old_path)

        # Match: from <old_path> import ... OR import <old_path>
        # Also match inside string literals (for @patch decorators)
        pattern = re.compile(rf"(?<!\w){old_escaped}(?=[\s.,\"\'\)\]:]|$)", re.MULTILINE)

        new_content = pattern.sub(new_path, content)
        if new_content != content:
            replacements = len(pattern.findall(content))
            count += replacements
            content = new_content

    if content != original:
        with open(filepath, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    return count


def main():
    total_files = 0
    total_replacements = 0

    all_files = []

    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            continue
        for root, _dirs, files in os.walk(scan_dir):
            for fname in files:
                fpath = os.path.join(root, fname)
                if should_process(fpath):
                    all_files.append(fpath)

    for fpath in SCAN_FILES:
        if os.path.isfile(fpath) and should_process(fpath):
            all_files.append(fpath)

    for fpath in sorted(set(all_files)):
        count = rewrite_file(fpath)
        if count > 0:
            total_files += 1
            total_replacements += count
            print(f"  {fpath}: {count} replacements")

    print(f"\nTotal: {total_replacements} replacements in {total_files} files")


if __name__ == "__main__":
    main()
