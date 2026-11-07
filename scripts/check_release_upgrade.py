"""Verify catalog seeding through a packaged executable's startup path."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory


def main() -> None:
    executable = Path(sys.argv[1]).resolve(strict=True)
    root = Path(__file__).resolve().parent.parent
    bundled_entry = root / "config/catalog/newcomers/NETYIELD.json"
    current_config = json.loads(
        (root / "config/m4b-config.json").read_text(encoding="utf-8")
    )
    with TemporaryDirectory(prefix="m4b-release-upgrade-") as directory:
        for scenario in ("fresh", "existing", "moved"):
            installation = Path(directory) / scenario
            installation.mkdir()
            binary = installation / executable.name
            shutil.copy2(executable, binary)
            config = installation / "config"
            credentials = config / "user-config.json"
            previous_entry = config / "catalog/supported/NETYIELD.json"
            if scenario != "fresh":
                config.mkdir()
                old_config = deepcopy(current_config)
                old_config["project"]["project_version"] = "5.0.6"
                (config / "m4b-config.json").write_text(
                    json.dumps(old_config), encoding="utf-8"
                )
                credentials.write_text(
                    '{"test_marker": "preserve-me"}', encoding="utf-8"
                )
            if scenario == "moved":
                previous_entry.parent.mkdir(parents=True)
                entry = json.loads(bundled_entry.read_text(encoding="utf-8"))
                entry["test_marker"] = "preserve-entry-edit"
                previous_entry.write_text(json.dumps(entry), encoding="utf-8")

            subprocess.run(
                [str(binary), "--help"],
                cwd=installation,
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            target = config / "catalog/newcomers/NETYIELD.json"
            entry = json.loads(target.read_text(encoding="utf-8"))
            if entry.get("name") != "NETYIELD":
                raise RuntimeError(f"{scenario}: NetYield missing from the catalog")
            if scenario != "fresh" and json.loads(
                credentials.read_text(encoding="utf-8")
            ) != {"test_marker": "preserve-me"}:
                raise RuntimeError(f"{scenario}: existing user configuration changed")
            if scenario == "moved" and (
                previous_entry.exists()
                or entry.get("test_marker") != "preserve-entry-edit"
            ):
                raise RuntimeError(
                    "Category migration failed to preserve the existing entry"
                )
            print(f"Packaged startup verified for {scenario} installation")


if __name__ == "__main__":
    main()
