"""Tests for utils.app_wizard — interactive app-add wizard."""

from __future__ import annotations

import json
from unittest import mock

from money4band.apps.wizard import run_app_wizard


class TestAppWizard:
    """Test the wizard with mocked input()."""

    def _mock_inputs(self, *responses):
        """Return a side_effect callable for builtins.input."""
        it = iter(responses)
        return lambda prompt="": next(it)

    def test_wizard_creates_file(self, tmp_path):
        inputs = self._mock_inputs(
            "TESTAPP",  # name
            "test/image:latest",  # image
            "1",  # auth type: email+password
            "1",  # layer: residential
            "-1",  # install limit
            "",  # dashboard (skip)
            "",  # link (skip)
        )
        with mock.patch("builtins.input", side_effect=inputs):
            result = run_app_wizard(str(tmp_path))

        assert result is not None
        assert result["name"] == "TESTAPP"
        assert result["compose_config"]["image"] == "test/image:latest"
        assert "email" in result["flags"]
        assert "password" in result["flags"]
        assert result["compose_layer"] == "residential"
        assert result["install_limit"] == -1

        # File should exist
        filepath = tmp_path / "TESTAPP.json"
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert data["name"] == "TESTAPP"

    def test_wizard_uuid_auth(self, tmp_path):
        inputs = self._mock_inputs(
            "UUIDAPP",
            "pub/uuid:v1",
            "3",  # UUID auth
            "64",  # UUID length
            "2",  # universal layer
            "5",  # install limit
            "https://dash.example.com",
            "",
        )
        with mock.patch("builtins.input", side_effect=inputs):
            result = run_app_wizard(str(tmp_path))

        assert result["flags"]["uuid"]["length"] == 64
        assert result["compose_layer"] == "universal"
        assert result["install_limit"] == 5
        assert result["dashboard"] == "https://dash.example.com"

    def test_wizard_manual_auth(self, tmp_path):
        inputs = self._mock_inputs(
            "MANUALAPP",
            "pub/manual:latest",
            "5",  # manual auth
            "3",  # datacenter layer
            "-1",
            "",
            "",
        )
        with mock.patch("builtins.input", side_effect=inputs):
            result = run_app_wizard(str(tmp_path))

        assert result["flags"].get("manual_onboard") is True

    def test_wizard_cancel_no_name(self, tmp_path):
        inputs = self._mock_inputs("")  # empty name → cancel
        with mock.patch("builtins.input", side_effect=inputs):
            result = run_app_wizard(str(tmp_path))
        assert result is None

    def test_wizard_cancel_no_image(self, tmp_path):
        inputs = self._mock_inputs("APP", "")  # empty image → cancel
        with mock.patch("builtins.input", side_effect=inputs):
            result = run_app_wizard(str(tmp_path))
        assert result is None

    def test_wizard_overwrite_declined(self, tmp_path):
        # Pre-create the file
        (tmp_path / "EXISTING.json").write_text("{}")
        inputs = self._mock_inputs(
            "EXISTING",
            "img:latest",
            "2",  # token auth
            "1",  # residential
            "-1",
            "",
            "",
            "n",  # decline overwrite
        )
        with mock.patch("builtins.input", side_effect=inputs):
            result = run_app_wizard(str(tmp_path))
        assert result is None

    def test_wizard_overwrite_accepted(self, tmp_path):
        (tmp_path / "OVERME.json").write_text("{}")
        inputs = self._mock_inputs(
            "OVERME",
            "img:latest",
            "2",
            "2",  # universal
            "-1",
            "",
            "",
            "y",  # accept overwrite
        )
        with mock.patch("builtins.input", side_effect=inputs):
            result = run_app_wizard(str(tmp_path))
        assert result is not None
        assert result["name"] == "OVERME"
