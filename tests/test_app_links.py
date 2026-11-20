from __future__ import annotations

import pytest

from money4band.apps.catalog import _display_catalog
from money4band.apps.links import primary_app_link


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        (
            {
                "referrals": [{"url": "https://provider.test/?ref=code"}],
                "app_details": {"official_url": "https://provider.test/"},
            },
            "https://provider.test/?ref=code",
        ),
        (
            {"app_details": {"official_url": "https://provider.test/"}},
            "https://provider.test/",
        ),
        (
            {
                "referrals": [{"url": ""}],
                "app_details": {"official_url": "undocumented"},
                "dashboard": "https://provider.test/dashboard",
            },
            "https://provider.test/dashboard",
        ),
        (
            {
                "referrals": [None],
                "app_details": {"official_url": "https://provider.test/"},
            },
            "https://provider.test/",
        ),
        ({"app_details": {"official_url": "javascript:alert(1)"}}, ""),
    ],
)
def test_public_link_priority_and_catalog_fallback(entry, expected, capsys):
    assert primary_app_link(entry) == expected
    _display_catalog(
        {"deprecated": {"active": False, "entries": [{"name": "EXAMPLE", **entry}]}}
    )
    output = capsys.readouterr().out
    if expected:
        assert expected in output
    assert "javascript:" not in output
