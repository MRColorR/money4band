"""Tests for the frozen-build bundled-data seeding in main.py.

Onefile builds carry config/ and template/ inside the executable and
seed them next to the binary on first run. User state must NEVER come
out of that bundle: user-config.json is encrypted with the *building*
machine's master.key, so shipping it makes every fresh install fail to
decrypt and leaks the builder's data.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import main as m4b_main


class TestSeedBundledDir:
    def _bundle(self, tmp_path):
        bundle = tmp_path / "bundle"
        (bundle / "config").mkdir(parents=True)
        (bundle / "config" / "m4b-config.json").write_text("{}", encoding="utf-8")
        (bundle / "config" / "catalog").mkdir()
        (bundle / "config" / "catalog" / "APP.json").write_text("{}", encoding="utf-8")
        (bundle / "config" / "user-config.json").write_text(
            "M4B_ENCRYPTED:gAAAAAsecret", encoding="utf-8"
        )
        (bundle / "config" / ".dashboard.pid").write_text("123", encoding="utf-8")
        return bundle

    def test_seeds_config_without_user_state(self, tmp_path):
        bundle = self._bundle(tmp_path)
        dest = tmp_path / "dest_config"
        with patch.object(sys, "_MEIPASS", str(bundle), create=True):
            m4b_main._seed_bundled_dir(
                str(dest), "config", ignore=m4b_main._NEVER_SEED_INTO_CONFIG
            )

        assert (dest / "m4b-config.json").is_file()
        assert (dest / "catalog" / "APP.json").is_file()
        # The builder's encrypted credentials must not be shipped/seeded.
        assert not (dest / "user-config.json").exists()
        assert not (dest / ".dashboard.pid").exists()

    def test_never_overwrites_existing_config(self, tmp_path):
        bundle = self._bundle(tmp_path)
        dest = tmp_path / "dest_config"
        dest.mkdir()
        (dest / "m4b-config.json").write_text('{"mine": true}', encoding="utf-8")
        with patch.object(sys, "_MEIPASS", str(bundle), create=True):
            m4b_main._seed_bundled_dir(
                str(dest), "config", ignore=m4b_main._NEVER_SEED_INTO_CONFIG
            )
        assert (dest / "m4b-config.json").read_text(
            encoding="utf-8"
        ) == '{"mine": true}'

    def test_noop_when_not_frozen(self, tmp_path):
        dest = tmp_path / "dest_config"
        # No sys._MEIPASS -> running from source, nothing to seed.
        with patch.object(sys, "_MEIPASS", None, create=True):
            m4b_main._seed_bundled_dir(str(dest), "config")
        assert not dest.exists()


class TestEnsureConfigDir:
    def test_seeds_custom_config_dir(self, tmp_path):
        bundle = tmp_path / "bundle"
        (bundle / "config").mkdir(parents=True)
        (bundle / "config" / "m4b-config.json").write_text("{}", encoding="utf-8")

        import argparse

        custom = tmp_path / "custom_cfg"
        args = argparse.Namespace(config_dir=str(custom))
        with patch.object(sys, "_MEIPASS", str(bundle), create=True):
            m4b_main._ensure_config_dir(args)
        assert (custom / "m4b-config.json").is_file()

    def test_existing_dir_left_alone(self, tmp_path):
        import argparse

        custom = tmp_path / "custom_cfg"
        custom.mkdir()
        args = argparse.Namespace(config_dir=str(custom))
        with patch.object(sys, "_MEIPASS", str(tmp_path), create=True):
            m4b_main._ensure_config_dir(args)
        assert list(custom.iterdir()) == []


class TestTemplateSeeding:
    """template/ is read-only reference data the app resets FROM."""

    def _bundle(self, tmp_path, marker: str = "v1"):
        bundle = tmp_path / "bundle"
        tpl = bundle / "template"
        tpl.mkdir(parents=True, exist_ok=True)
        # The template's user-config.json is the legitimate placeholder
        # skeleton - the config/ user-state filter must NOT drop it.
        (tpl / "user-config.json").write_text(
            f'{{"settings": {{"setup_completed": false}}, "v": "{marker}"}}',
            encoding="utf-8",
        )
        return bundle

    def test_template_user_config_is_seeded(self, tmp_path):
        bundle = self._bundle(tmp_path)
        dest = tmp_path / "template"
        with patch.object(sys, "_MEIPASS", str(bundle), create=True):
            m4b_main._seed_bundled_dir(str(dest), "template", refresh=True)
        assert (dest / "user-config.json").is_file()

    def test_template_refreshes_after_update(self, tmp_path):
        """A self-update replaces only the exe; templates must not stay pinned."""
        dest = tmp_path / "template"
        dest.mkdir()
        (dest / "user-config.json").write_text('{"v": "old"}', encoding="utf-8")

        bundle = self._bundle(tmp_path, marker="v2")
        with patch.object(sys, "_MEIPASS", str(bundle), create=True):
            m4b_main._seed_bundled_dir(str(dest), "template", refresh=True)
        assert '"v2"' in (dest / "user-config.json").read_text(encoding="utf-8")


class TestFrozenResourceRoot:
    """get_path must point inside <_MEIPASS>/money4band/resources when frozen.

    The build bundles the package via --add-data "money4band;money4band",
    so resources are NOT at the bundle root. A wrong root silently skips
    the web-frontend mount (dashboard served 404 on /) and breaks the
    QEMU binfmt service-file lookup in release binaries.
    """

    def _reload_resources(self):
        import importlib

        import money4band.resources as res

        return importlib.reload(res)

    def test_frozen_root_includes_package_prefix(self, tmp_path):
        www = tmp_path / "money4band" / "resources" / "www"
        www.mkdir(parents=True)
        (www / "index.html").write_text("<html></html>", encoding="utf-8")

        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", str(tmp_path), create=True),
        ):
            res = self._reload_resources()
            assert res.get_path("www").is_dir()
            assert (res.get_path("www") / "index.html").is_file()
        # Restore the dev-mode root for the rest of the suite.
        self._reload_resources()

    def test_dev_root_resolves_real_www(self):
        res = self._reload_resources()
        assert res.get_path("www", "index.html").is_file()
        assert res.get_path("files", "docker.binfmt.service").is_file()
