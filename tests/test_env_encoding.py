"""Round-trip tests for .env value encoding.

Docker Compose interpolates ``$`` inside .env values and treats `` #``
as an inline comment, so credentials must be escaped on write and
un-escaped on read. Encode and decode MUST stay symmetric, otherwise M4B
disagrees with the running containers about what a value actually is.
"""

from __future__ import annotations

import pytest

from money4band.docker.env_builder import (
    build_env_lines,
    decode_env_value,
    format_env_value,
)
from money4band.docker.helper import read_env_var

_ROUND_TRIP_VALUES = [
    "simple",
    "Abc$123",
    "$$literal",
    "p@ss #1",
    "has spaces",
    'quote"inside',
    "back\\slash",
    "socks5://user:p$ss@1.2.3.4:1080",
    "trailing#hash",
    "a=b=c",
]


class TestFormatEnvValue:
    @pytest.mark.parametrize("raw", _ROUND_TRIP_VALUES)
    def test_round_trip(self, raw: str) -> None:
        encoded = format_env_value(raw)
        assert encoded is not None
        assert decode_env_value(encoded) == raw

    def test_dollar_is_escaped_for_compose(self) -> None:
        assert format_env_value("Abc$123") == "Abc$$123"

    def test_hash_and_space_are_quoted(self) -> None:
        encoded = format_env_value("p@ss #1")
        assert encoded.startswith('"') and encoded.endswith('"')

    def test_non_scalars_are_skipped(self) -> None:
        assert format_env_value({"stack_start": True}) is None
        assert format_env_value(["a"]) is None
        assert format_env_value(None) is None

    def test_multiline_rejected(self) -> None:
        assert format_env_value("line1\nline2") is None

    def test_scalars_survive(self) -> None:
        assert format_env_value(8080) == "8080"
        assert format_env_value(True) == "True"


class TestBuildEnvLinesEncoding:
    def _configs(self, password: str, notifications: dict) -> tuple[dict, dict, dict]:
        m4b = {"project": {}, "network": {}, "watchtower": {"scope": "money4band"}}
        app_cfg = {
            "supported": {
                "active": True,
                "entries": [
                    {
                        "name": "HONEYGAIN",
                        "flags": {"email": {}, "password": {}},
                        "compose_config": {"image": "x"},
                    }
                ],
            }
        }
        user = {
            "device_info": {},
            "resource_limits": {},
            "proxies": {},
            "notifications": notifications,
            "apps": {
                "honeygain": {
                    "enabled": True,
                    "email": "a@b.c",
                    "password": password,
                }
            },
        }
        return m4b, app_cfg, user

    def test_password_with_dollar_is_escaped(self) -> None:
        m4b, app_cfg, user = self._configs("Abc$123", {"enabled": False})
        lines = build_env_lines(m4b, app_cfg, user)
        assert "HONEYGAIN_PASSWORD=Abc$$123" in lines

    def test_nested_notifications_events_not_leaked(self) -> None:
        """The internal events map must never reach .env as a dict repr."""
        m4b, app_cfg, user = self._configs(
            "pw",
            {"enabled": True, "url": "https://hook", "events": {"stack_start": True}},
        )
        lines = build_env_lines(m4b, app_cfg, user)
        assert any(line.startswith("WATCHTOWER_NOTIFICATION_URL=") for line in lines)
        assert not any("_EVENTS=" in line for line in lines)
        assert not any("{" in line for line in lines)


class TestReadEnvVarRoundTrip:
    @pytest.mark.parametrize("raw", ["plain-name", "node$1", "my device", "a#b"])
    def test_written_value_reads_back_identical(self, tmp_path, raw: str) -> None:
        encoded = format_env_value(raw)
        env_file = tmp_path / ".env"
        env_file.write_text(f"DEVICE_NAME={encoded}\n", encoding="utf-8")
        assert read_env_var(str(env_file), "DEVICE_NAME") == raw

    def test_falls_back_to_env_meta(self, tmp_path) -> None:
        """The start flow wipes .env after compose-up; .env.meta persists."""
        (tmp_path / ".env.meta").write_text(
            "COMPOSE_PROJECT_NAME=money4band\n", encoding="utf-8"
        )
        env_file = tmp_path / ".env"
        assert read_env_var(str(env_file), "COMPOSE_PROJECT_NAME") == "money4band"
