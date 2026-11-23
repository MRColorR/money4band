from __future__ import annotations

import pytest

from money4band.api._deps import normalize_referrals
from money4band.api.schemas import ReferralOut
from money4band.apps.catalog import _display_catalog
from money4band.apps.configurator import _configure_apps
from money4band.apps.info import show_app_detail
from money4band.apps.links import app_link_text, app_referral_code
from money4band.apps.schema import Referral
from money4band.readme_generator import generate_apps_md_table, generate_readme_table
from scripts.update_tables import documentation_entry


@pytest.mark.parametrize(
    "referral_url", [None, "unavailable", "https://provider.test/"]
)
def test_manual_code_survives_website_fallback_and_all_text_views(
    referral_url, capsys, monkeypatch
):
    entry = {
        "name": "EXAMPLE",
        "referrals": [{"url": referral_url, "code": "MYCODE", "contributor": "owner"}],
        "app_details": {"official_url": "https://provider.test/"},
        "flags": {},
        "compose_config": {},
    }
    config = {"supported": {"active": True, "entries": [entry]}}
    assert app_link_text(entry) == "https://provider.test/ (code: MYCODE)"
    for table in (generate_readme_table(config), generate_apps_md_table(config)):
        assert "[**EXAMPLE**](https://provider.test/) (code: `MYCODE`)" in table
        assert "unavailable" not in table
    assert documentation_entry(entry)["referrals"][0]["code"] == "MYCODE"
    _display_catalog(config)
    assert "(code: MYCODE)" in capsys.readouterr().out
    assert show_app_detail(config, "example")
    output = capsys.readouterr().out
    assert "Referral code:" in output and "MYCODE" in output
    answers = iter(["y", ""])
    monkeypatch.setattr("builtins.input", lambda _: next(answers))
    monkeypatch.setattr("money4band.apps.configurator.cls", lambda: None)
    _configure_apps({"apps": {"example": {"enabled": False}}}, [entry], {})
    assert "https://provider.test/ (code: MYCODE)" in capsys.readouterr().out


def test_manual_code_is_preserved_by_typed_models_and_api():
    referral = {"url": "https://provider.test/", "code": "MYCODE"}
    assert Referral.from_raw(referral).code == "MYCODE"
    result = ReferralOut.model_validate(normalize_referrals([referral])[0])
    assert result.model_dump()["code"] == "MYCODE"


def test_explicit_manual_code_takes_precedence_over_url_parameter():
    entry = {"referrals": [{"url": "https://provider.test/?code=OLD", "code": "NEW"}]}
    assert app_referral_code(entry) == "NEW"
