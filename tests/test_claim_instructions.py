from __future__ import annotations

import subprocess

from money4band.apps.claim_instructions import (
    refresh_claim_keys,
    write_claim_instructions,
)


def _catalog():
    return {
        "supported": {
            "active": True,
            "entries": [
                {
                    "name": "SPIDE",
                    "dashboard": "https://spide.network/network.html",
                    "flags": {
                        "manual": {
                            "instructions": "Register the Device Key in the dashboard.",
                            "device_key_from_logs": True,
                        }
                    },
                }
            ],
        }
    }


def test_instructions_match_each_instance_without_account_credentials(
    tmp_path, monkeypatch
):
    machine = "a" * 32
    key = "b" * 64
    monkeypatch.setattr(
        "money4band.apps.claim_instructions.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, f"Machine ID: {machine}", f"Device Key: {key}"
        ),
    )
    for device in ("main", "proxy-1"):
        folder = tmp_path / device
        folder.mkdir()
        user = {
            "device_info": {"device_name": device},
            "apps": {
                "spide": {
                    "machine_id": machine,
                    "password": "private-password",
                    "apikey": "private-key",
                }
            },
        }
        paths = write_claim_instructions(
            _catalog(),
            user,
            folder,
            {"spide": {"container_name": "${DEVICE_NAME}_spide"}},
        )
        refresh_claim_keys(folder)
        text = paths[0].read_text()
        assert f"Device: {device}" in text
        assert f"Container: {device}_spide" in text
        assert f"Machine ID: {machine}" in text
        assert f"Device Key: {key}" in text
        assert "https://spide.network/network.html" in text
        assert "private-password" not in text and "private-key" not in text


def test_old_container_key_cannot_replace_new_machine_identity(tmp_path, monkeypatch):
    monkeypatch.setattr("money4band.apps.claim_instructions.time.sleep", lambda _: None)
    monkeypatch.setattr(
        "money4band.apps.claim_instructions.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, "Machine ID: " + "a" * 32, "Device Key: " + "b" * 64
        ),
    )
    user = {
        "device_info": {"device_name": "new"},
        "apps": {"spide": {"machine_id": "c" * 32}},
    }
    paths = write_claim_instructions(
        _catalog(), user, tmp_path, {"spide": {"container_name": "new_spide"}}
    )
    refresh_claim_keys(tmp_path)
    assert "Device Key: available after startup" in paths[0].read_text()
    assert "b" * 64 not in paths[0].read_text()


def test_uuid_claim_preserves_prefix_contract_and_excludes_absent_services(tmp_path):
    app = {
        "name": "APP",
        "flags": {
            "uuid": {"prefix": "sdk-", "claimURLBase": "https://claim.test/sdk-"}
        },
    }
    catalog = {"supported": {"active": True, "entries": [app]}}
    user = {"apps": {"app": {"uuid": "sdk-abcd"}}}
    assert write_claim_instructions(catalog, user, tmp_path, {}) == []
    paths = write_claim_instructions(
        catalog, user, tmp_path, {"app": {"container_name": "device_app"}}
    )
    assert "https://claim.test/sdk-abcd" in paths[0].read_text()
    assert "sdk-sdk-" not in paths[0].read_text()


def test_device_key_can_arrive_after_first_log_read(tmp_path, monkeypatch):
    machine, key = "a" * 32, "b" * 64
    responses = iter(
        [
            subprocess.CompletedProcess([], 0, "", ""),
            subprocess.CompletedProcess(
                [], 0, f"Machine ID: {machine}", f"Device Key: {key}"
            ),
        ]
    )
    monkeypatch.setattr(
        "money4band.apps.claim_instructions.subprocess.run",
        lambda *args, **kwargs: next(responses),
    )
    monkeypatch.setattr("money4band.apps.claim_instructions.time.sleep", lambda _: None)
    user = {
        "device_info": {"device_name": "main"},
        "apps": {"spide": {"machine_id": machine}},
    }
    paths = write_claim_instructions(
        _catalog(), user, tmp_path, {"spide": {"container_name": "main_spide"}}
    )
    refresh_claim_keys(tmp_path)
    assert f"Device Key: {key}" in paths[0].read_text()
