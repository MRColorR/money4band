"""User setup output must stay local while shipped defaults remain versioned."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from money4band.apps.remote_cache import replace_entries
from money4band.apps.wizard import run_app_wizard
from money4band.core import progress
from money4band.core.profiles import create_profile


def test_generated_user_data_stays_out_of_git(tmp_path, monkeypatch):
    git = shutil.which("git")
    if git is None:
        pytest.skip("Git is required to verify repository ignore rules")
    root = Path(__file__).resolve().parents[1]
    shutil.copyfile(root / ".gitignore", tmp_path / ".gitignore")

    def run_git(*args):
        return subprocess.check_output(  # noqa: S603 - fixed Git commands in a temporary repo
            [git, "-C", str(tmp_path), *args], text=True
        ).strip()

    run_git("init", "--quiet")
    config = tmp_path / "config"
    config.mkdir()
    shipped = [
        "config/m4b-config.json",
        "config/catalog/supported/EXAMPLE.json",
        "config/catalog/newcomers/EXAMPLE.json",
        "config/catalog/deprecated/EXAMPLE.json",
        "config/catalog/addons/EXAMPLE.json",
        "config/apps.d/README.md",
        "template/user-config.json",
    ]
    for name in shipped:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    run_git("add", "--", ".gitignore", *shipped)

    user = config / "user-config.json"
    user.write_text('{"device_name": "test-device"}', encoding="utf-8")
    (tmp_path / ".env").write_text("DEVICE_NAME=test-device", encoding="utf-8")
    create_profile("home", str(config), str(tmp_path), str(user))
    monkeypatch.setattr(progress, "PROGRESS_FILE", str(config / ".setup_progress.json"))
    progress.save_progress([1])

    answers = iter(["LOCALAPP", "example/client:latest", "2", "1", "-1", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    assert run_app_wizard(str(config / "apps.d")) is not None
    for source in ("community", "openpassivehub", "custom-source"):
        replace_entries(
            config / "catalog" / source,
            {"supported": [{"name": "REMOTEAPP"}]},
        )

    assert run_git("ls-files", "--others", "--exclude-standard") == ""
    assert set(run_git("ls-files").splitlines()) == {".gitignore", *shipped}
