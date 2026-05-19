"""Tests for utils.offers — referral & passive income directory."""

from __future__ import annotations

import json

from money4band.apps.offers import display_offers, load_all_offers, load_external_offers


class TestLoadExternalOffers:
    def test_loads_valid_file(self, tmp_path):
        data = {
            "offers": [
                {
                    "name": "VPN Deal",
                    "url": "https://vpn.example.com",
                    "bonus": "x",
                    "category": "vpn",
                }
            ]
        }
        path = tmp_path / "offers.json"
        path.write_text(json.dumps(data))
        result = load_external_offers(str(path))
        assert len(result) == 1
        assert result[0]["name"] == "VPN Deal"

    def test_missing_file(self):
        assert load_external_offers("/nonexistent/file.json") == []

    def test_invalid_json(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("not json")
        assert load_external_offers(str(path)) == []


class TestLoadAllOffers:
    def _write_app_config(self, tmp_path):
        cfg = {
            "supported": {
                "active": True,
                "entries": [
                    {
                        "name": "TESTAPP",
                        "referrals": [
                            {
                                "url": "https://testapp.com/ref",
                                "contributor": "MRColorR",
                            }
                        ],
                        "compose_config": {"image": "x"},
                        "flags": {},
                        "install_limit": -1,
                        "profile": "residential",
                        "app_details": {
                            "official_name": "TestApp",
                            "earnings": {
                                "model": "per-GB",
                                "payout_methods": ["PayPal"],
                            },
                            "ip_policy": {"residential": True, "datacenter": False},
                        },
                    }
                ],
            }
        }
        p = tmp_path / "app-config.json"
        p.write_text(json.dumps(cfg))
        return str(p)

    def _write_ext_offers(self, tmp_path):
        data = {
            "offers": [
                {"name": "ExtVPN", "url": "https://vpn.example.com", "category": "vpn"}
            ]
        }
        p = tmp_path / "offers.json"
        p.write_text(json.dumps(data))
        return str(p)

    def test_merges_app_and_external(self, tmp_path):
        app_path = self._write_app_config(tmp_path)
        ext_path = self._write_ext_offers(tmp_path)
        result = load_all_offers(app_path, ext_path)
        names = [o["name"] for o in result]
        assert "TestApp" in names
        assert "ExtVPN" in names
        # App offers first
        assert names.index("TestApp") < names.index("ExtVPN")

    def test_app_offers_have_m4b_flag(self, tmp_path):
        app_path = self._write_app_config(tmp_path)
        ext_path = self._write_ext_offers(tmp_path)
        result = load_all_offers(app_path, ext_path)
        app_offer = next(o for o in result if o["name"] == "TestApp")
        assert app_offer["m4b_app"] is True
        ext_offer = next(o for o in result if o["name"] == "ExtVPN")
        assert ext_offer.get("m4b_app") is not True

    def test_skips_deprecated_apps(self, tmp_path):
        cfg = {
            "supported": {"active": True, "entries": []},
            "deprecated": {
                "active": False,
                "entries": [
                    {
                        "name": "OLDAPP",
                        "referrals": [
                            {"url": "https://old.com", "contributor": "MRColorR"}
                        ],
                        "compose_config": {"image": "x"},
                        "flags": {},
                        "install_limit": -1,
                        "profile": "residential",
                    }
                ],
            },
        }
        p = tmp_path / "app-config.json"
        p.write_text(json.dumps(cfg))
        ext_path = self._write_ext_offers(tmp_path)
        result = load_all_offers(str(p), ext_path)
        names = [o["name"] for o in result]
        assert "OLDAPP" not in names

    def test_missing_app_config(self, tmp_path):
        ext_path = self._write_ext_offers(tmp_path)
        result = load_all_offers("/nonexistent/config.json", ext_path)
        assert len(result) == 1
        assert result[0]["name"] == "ExtVPN"


class TestDisplayOffers:
    def _write_files(self, tmp_path):
        cfg = {
            "supported": {
                "active": True,
                "entries": [
                    {
                        "name": "MYAPP",
                        "referrals": [
                            {"url": "https://myapp.com/ref", "contributor": "MRColorR"}
                        ],
                        "compose_config": {"image": "x"},
                        "flags": {},
                        "install_limit": -1,
                        "profile": "universal",
                        "app_details": {"official_name": "MyApp"},
                    }
                ],
            }
        }
        app_path = tmp_path / "app-config.json"
        app_path.write_text(json.dumps(cfg))

        ext = {
            "offers": [
                {
                    "name": "ExtDeal",
                    "url": "https://ext.example.com",
                    "category": "affiliate",
                },
            ]
        }
        ext_path = tmp_path / "offers.json"
        ext_path.write_text(json.dumps(ext))
        return str(app_path), str(ext_path)

    def test_displays_merged(self, tmp_path, capsys):
        app_path, ext_path = self._write_files(tmp_path)
        display_offers(ext_path, app_config_path=app_path)
        out = capsys.readouterr().out
        assert "MyApp" in out
        assert "ExtDeal" in out
        assert "2 offer(s)" in out

    def test_category_filter(self, tmp_path, capsys):
        app_path, ext_path = self._write_files(tmp_path)
        display_offers(ext_path, category_filter="affiliate", app_config_path=app_path)
        out = capsys.readouterr().out
        assert "ExtDeal" in out
        assert "MyApp" not in out

    def test_empty_offers(self, tmp_path, capsys):
        empty = tmp_path / "empty.json"
        empty.write_text(json.dumps({"offers": []}))
        display_offers(str(empty))
        out = capsys.readouterr().out
        assert "No referral offers" in out

    def test_no_match_category(self, tmp_path, capsys):
        app_path, ext_path = self._write_files(tmp_path)
        display_offers(ext_path, category_filter="survey", app_config_path=app_path)
        out = capsys.readouterr().out
        assert "No offers in category" in out
