"""Tests for money4band.apps.user_config_merger — bundle-completeness rule."""

from __future__ import annotations

import pytest

from money4band.apps.user_config_merger import apply_user_config_templates


@pytest.fixture
def catalog() -> dict:
    return {
        "app_config_version": 2.0,
        "supported": {
            "active": True,
            "entries": [
                {
                    "name": "HONEYGAIN",
                    "user_config_template": {
                        "enabled": False,
                        "email": "yourHONEYGAINMail",
                        "password": "yourHONEYGAINPw",
                        "service_enabled": False,
                    },
                },
                {
                    "name": "EARNAPP",
                    "user_config_template": {
                        "enabled": False,
                        "uuid": "sdk-node-yourUUID",
                    },
                },
            ],
        },
        "newcomers": {
            "active": False,
            "entries": [
                {
                    "name": "NEWAPP",
                    "user_config_template": {
                        "enabled": False,
                        "token": "yourNEWAPPToken",
                    },
                },
            ],
        },
        "deprecated": {"active": False, "entries": []},
    }


class TestApplyUserConfigTemplates:
    def test_empty_user_config_gets_all_slices(self, catalog):
        user_config: dict = {"apps": {}}
        added = apply_user_config_templates(user_config, catalog)
        assert added == 3
        assert set(user_config["apps"].keys()) == {"honeygain", "earnapp", "newapp"}
        assert user_config["apps"]["honeygain"]["email"] == "yourHONEYGAINMail"

    def test_existing_slice_is_not_overwritten(self, catalog):
        user_config = {
            "apps": {
                "honeygain": {
                    "enabled": True,
                    "email": "real@user.com",
                    "password": "realSecret",
                    "service_enabled": True,
                }
            }
        }
        apply_user_config_templates(user_config, catalog)
        # User values untouched
        assert user_config["apps"]["honeygain"]["email"] == "real@user.com"
        assert user_config["apps"]["honeygain"]["password"] == "realSecret"
        assert user_config["apps"]["honeygain"]["enabled"] is True
        assert user_config["apps"]["honeygain"]["service_enabled"] is True

    def test_missing_keys_filled_into_existing_slice(self, catalog):
        """When a new field is added to a bundle, old user-configs gain it."""
        user_config = {
            "apps": {
                "honeygain": {
                    "enabled": True,
                    "email": "real@user.com",
                    # password and service_enabled missing — must be filled
                }
            }
        }
        apply_user_config_templates(user_config, catalog)
        assert user_config["apps"]["honeygain"]["password"] == "yourHONEYGAINPw"
        assert user_config["apps"]["honeygain"]["service_enabled"] is False
        assert user_config["apps"]["honeygain"]["email"] == "real@user.com"

    def test_apps_section_created_when_missing(self, catalog):
        user_config: dict = {}
        apply_user_config_templates(user_config, catalog)
        assert "apps" in user_config
        assert "honeygain" in user_config["apps"]

    def test_apps_removed_from_catalog_keep_creds(self, catalog):
        """Orphan slices are preserved — credentials do not auto-disappear."""
        user_config = {
            "apps": {
                "honeygain": {"enabled": True, "email": "real@user.com"},
                "ghost_app": {"enabled": True, "token": "still-here"},
            }
        }
        apply_user_config_templates(user_config, catalog)
        assert "ghost_app" in user_config["apps"]
        assert user_config["apps"]["ghost_app"]["token"] == "still-here"

    def test_deep_copy_prevents_aliasing(self, catalog):
        """Mutating a user-config slice must not affect the catalog."""
        user_config: dict = {"apps": {}}
        apply_user_config_templates(user_config, catalog)
        user_config["apps"]["honeygain"]["email"] = "mutated@example.com"
        # Catalog template must still hold the placeholder.
        tpl = catalog["supported"]["entries"][0]["user_config_template"]
        assert tpl["email"] == "yourHONEYGAINMail"

    def test_entry_without_template_gets_enabled_stub(self, catalog):
        """Apps lacking user_config_template still receive a minimal slice."""
        catalog["supported"]["entries"].append({"name": "MINIMAL"})
        user_config: dict = {"apps": {}}
        apply_user_config_templates(user_config, catalog)
        assert user_config["apps"]["minimal"] == {"enabled": False}

    def test_non_dict_apps_section_is_reset(self, catalog):
        user_config: dict = {"apps": "corrupt"}
        apply_user_config_templates(user_config, catalog)
        assert isinstance(user_config["apps"], dict)
        assert "honeygain" in user_config["apps"]
