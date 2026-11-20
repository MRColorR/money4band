"""Credential prompts must make app cancellation explicit and transactional."""

import re

import pytest

from money4band.apps.configurator import _configure_apps
from money4band.ui.prompt import (
    SkipAppError,
    ask_email,
    ask_string,
    ask_uuid,
    wait_for_enter,
)


@pytest.fixture(autouse=True)
def no_setup_message_delay(monkeypatch):
    monkeypatch.setattr("money4band.apps.configurator.time.sleep", lambda _: None)


@pytest.mark.parametrize(
    ("reader", "value"),
    [
        (ask_string, "n-prefix-key"),
        (ask_email, "name@example.com"),
        (ask_uuid, "a" * 32),
    ],
)
def test_credential_prompt_has_one_colon(reader, value, monkeypatch):
    prompts = []

    def read(message):
        prompts.append(message)
        return value

    monkeypatch.setattr("builtins.input", read)
    kwargs = {"length": 32} if reader is ask_uuid else {}
    assert reader("Credential:", show_default=False, **kwargs) == value
    plain = re.sub(r"\x1b\[[0-9;]*m", "", prompts[0])
    assert plain == "Credential: "


@pytest.mark.parametrize("reader", [ask_string, ask_email, ask_uuid])
def test_explicit_skip_cancels_each_credential_type(reader, monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "/skip")
    kwargs = {"length": 32} if reader is ask_uuid else {}
    with pytest.raises(SkipAppError):
        reader("Credential", allow_skip=True, **kwargs)


def test_no_is_not_a_secret_cancellation_command(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "n-prefix-key")
    assert ask_string("API key", allow_skip=True) == "n-prefix-key"


def test_existing_secret_is_masked_and_enter_preserves_it(monkeypatch):
    prompts = []

    def read(message):
        prompts.append(message)
        return ""

    monkeypatch.setattr("builtins.input", read)
    saved = "fixture-secret-value"
    assert (
        ask_string("Password", default=saved, show_default=False, allow_skip=True)
        == saved
    )
    assert saved not in prompts[0]
    assert "********; Enter to keep" in prompts[0]


def test_continue_prompt_does_not_silently_consume_no(monkeypatch, capsys):
    replies = iter(["n", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    wait_for_enter("Press Enter", allow_skip=True)
    assert "Press Enter to continue" in capsys.readouterr().out


@pytest.mark.parametrize("skip_at", ["continue", "credential"])
def test_skip_preserves_current_app_and_next_app_collects_credentials(
    skip_at, monkeypatch
):
    prior = {"enabled": False, "apikey": "previous-key"}
    user = {"apps": {"netyield": prior.copy(), "nextapp": {"enabled": False}}}
    apps = [
        {"name": "NETYIELD", "flags": {"apikey": {}}, "compose_config": {}},
        {"name": "NEXTAPP", "flags": {"email": {}}, "compose_config": {}},
    ]
    replies = ["y"] + ([""] if skip_at == "credential" else [])
    replies += ["/skip", "y", "", "next@example.com"]
    answers = iter(replies)
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("money4band.apps.configurator.cls", lambda: None)
    _configure_apps(user, apps, {})
    assert user["apps"]["netyield"] == prior
    assert user["apps"]["nextapp"]["enabled"] is True
    assert user["apps"]["nextapp"]["email"] == "next@example.com"


def test_skip_confirmation_uses_configured_reading_delay(monkeypatch):
    delays = []
    monkeypatch.setattr("money4band.apps.configurator.time.sleep", delays.append)
    answers = iter(["y", "/skip"])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("money4band.apps.configurator.cls", lambda: None)
    user = {"apps": {"example": {"enabled": False}}}
    _configure_apps(
        user,
        [{"name": "EXAMPLE", "flags": {}, "compose_config": {}}],
        {"system": {"sleep_time": 2.5}},
    )
    assert delays == [2.5]


def test_ctrl_c_with_auto_dashboard_skips_app_without_stopping_dashboard(monkeypatch):
    import atexit
    import os
    import signal

    import money4band.dashboard.setup as dashboard

    handlers = {}
    cleanup = []
    killed = []
    removed = []
    monkeypatch.setattr(dashboard, "_CLEANUP_REGISTERED", False)
    monkeypatch.setattr(signal, "signal", lambda sig, fn: handlers.update({sig: fn}))
    monkeypatch.setattr(atexit, "register", cleanup.append)
    monkeypatch.setattr(dashboard, "read_dashboard_owner", lambda _: "auto")
    monkeypatch.setattr(dashboard, "read_dashboard_pid", lambda _: 49173)
    monkeypatch.setattr(dashboard, "remove_dashboard_pid", removed.append)
    monkeypatch.setattr(os, "kill", lambda pid, sig: killed.append((pid, sig)))
    dashboard._register_auto_dashboard_cleanup("test-config", 49173)

    answers = iter(["y", "", None, "y", "", "next@example.com"])

    def read(_message):
        value = next(answers)
        if value is None:
            handlers[signal.SIGINT](signal.SIGINT, None)
        return value

    monkeypatch.setattr("builtins.input", read)
    monkeypatch.setattr("money4band.apps.configurator.cls", lambda: None)
    user = {"apps": {"netyield": {"enabled": False}, "nextapp": {"enabled": False}}}
    apps = [
        {"name": "NETYIELD", "flags": {"apikey": {}}, "compose_config": {}},
        {"name": "NEXTAPP", "flags": {"email": {}}, "compose_config": {}},
    ]
    _configure_apps(user, apps, {})
    assert user["apps"]["netyield"] == {"enabled": False}
    assert user["apps"]["nextapp"]["email"] == "next@example.com"
    assert killed == removed == []
    cleanup[0]()
    assert killed == [(49173, signal.SIGTERM)]
    assert removed == ["test-config"]


@pytest.mark.parametrize("existing", ["yourSPIDEMachineID", "a" * 32])
def test_machine_id_setup_persists_valid_identity_on_enter(existing, monkeypatch):
    from money4band.docker.generator import validate_uuid

    user = {"apps": {"spide": {"enabled": False, "machine_id": existing}}}
    app = {
        "name": "SPIDE",
        "flags": {"machine_id": {"length": 32}},
        "compose_config": {},
    }
    replies = iter(["y", "", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(replies))
    monkeypatch.setattr("money4band.apps.configurator.cls", lambda: None)
    _configure_apps(user, [app], {})
    identity = user["apps"]["spide"]["machine_id"]
    assert validate_uuid(identity, 32)
    if existing == "a" * 32:
        assert identity == existing


def test_builtin_catalog_has_no_silently_ignored_setup_flags():
    import json
    from pathlib import Path

    from money4band.apps.configurator import flag_function_mapper

    root = Path(__file__).resolve().parents[1] / "config/catalog"
    for category in ("supported", "newcomers"):
        for path in (root / category).glob("*.json"):
            entry = json.loads(path.read_text(encoding="utf-8"))
            assert set(entry.get("flags", {})) <= flag_function_mapper.keys(), path.name


def test_new_proxy_instances_do_not_reuse_spide_machine_identity():
    import copy

    from money4band.network.multiproxy import regenerate_uuids_for_apps

    original = {"apps": {"spide": {"enabled": True, "machine_id": "a" * 32}}}
    catalog = {
        "supported": {
            "active": True,
            "entries": [{"name": "SPIDE", "flags": {"machine_id": {"length": 32}}}],
        }
    }
    identities = {original["apps"]["spide"]["machine_id"]}
    for _ in range(2):
        instance = copy.deepcopy(original)
        regenerate_uuids_for_apps(instance, catalog)
        identities.add(instance["apps"]["spide"]["machine_id"])
    assert len(identities) == 3
    assert original["apps"]["spide"]["machine_id"] == "a" * 32
