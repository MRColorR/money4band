"""Tests for IP quality scoring (utils/ip_scorer.py)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from money4band.ip_scorer import (
    calculate_fraud_score,
    extract_proxy_ip,
    format_isp_type,
    get_public_ip,
    get_score_rating,
    parse_proxy_file,
    score_ips,
)


class TestGetPublicIp:

    @patch("money4band.ip_scorer.get_session")
    def test_returns_ip_from_first_provider(self, mock_sess):
        resp = MagicMock()
        resp.text = "1.2.3.4"
        mock_sess.return_value.get.return_value = resp
        assert get_public_ip() == "1.2.3.4"

    @patch("money4band.ip_scorer.get_session")
    def test_returns_none_when_all_fail(self, mock_sess):
        mock_sess.return_value.get.side_effect = Exception("fail")
        assert get_public_ip() is None

    @patch("money4band.ip_scorer.get_session")
    def test_skips_non_ip_response(self, mock_sess):
        bad = MagicMock()
        bad.text = "<html>not an ip</html>"
        good = MagicMock()
        good.text = "5.6.7.8"
        mock_sess.return_value.get.side_effect = [bad, good]
        assert get_public_ip() == "5.6.7.8"


class TestParseProxyFile:

    def test_reads_lines_skips_comments(self, tmp_path):
        f = tmp_path / "proxies.txt"
        f.write_text("# comment\nsocks5://1.2.3.4:1080\n\nhttp://5.6.7.8:8080\n")
        result = parse_proxy_file(str(f))
        assert result == ["socks5://1.2.3.4:1080", "http://5.6.7.8:8080"]

    def test_returns_empty_on_missing_file(self, tmp_path):
        assert parse_proxy_file(str(tmp_path / "nope.txt")) == []


class TestExtractProxyIp:

    def test_socks5_with_auth(self):
        assert extract_proxy_ip("socks5://user:pass@1.2.3.4:1080") == "1.2.3.4"

    def test_http_no_auth(self):
        assert extract_proxy_ip("http://10.0.0.1:8080") == "10.0.0.1"

    def test_bare_ip_port(self):
        assert extract_proxy_ip("192.168.1.1:3128") == "192.168.1.1"


class TestScoreIps:

    def test_empty_list(self):
        assert score_ips([]) == []

    @patch("money4band.ip_scorer.get_session")
    def test_batch_request(self, mock_sess):
        resp = MagicMock()
        resp.json.return_value = [
            {"status": "success", "query": "1.2.3.4", "proxy": False, "hosting": False}
        ]
        resp.raise_for_status = MagicMock()
        mock_sess.return_value.post.return_value = resp
        result = score_ips(["1.2.3.4"])
        assert len(result) == 1
        assert result[0]["query"] == "1.2.3.4"

    @patch("money4band.ip_scorer.get_session")
    def test_returns_empty_on_error(self, mock_sess):
        mock_sess.return_value.post.side_effect = Exception("timeout")
        assert score_ips(["1.2.3.4"]) == []


class TestCalculateFraudScore:

    def test_clean_residential(self):
        entry = {"proxy": False, "hosting": False, "mobile": False, "isp": "Comcast"}
        assert calculate_fraud_score(entry) == 0

    def test_proxy_flag(self):
        entry = {"proxy": True, "hosting": False, "mobile": False, "isp": "Comcast"}
        assert calculate_fraud_score(entry) == 40

    def test_datacenter_plus_blacklist(self):
        entry = {"proxy": False, "hosting": True, "mobile": False, "isp": "OVH SAS"}
        # hosting=30 + blacklisted=30 + suspicious_isp=15 = 75
        assert calculate_fraud_score(entry, blacklisted=True) == 75

    def test_caps_at_100(self):
        entry = {"proxy": True, "hosting": True, "mobile": True, "isp": "OVH"}
        # 40+30+10+15 = 95, + blacklisted 30 = 125 → capped 100
        assert calculate_fraud_score(entry, blacklisted=True) == 100


class TestGetScoreRating:

    @pytest.mark.parametrize(
        "score,expected_word",
        [
            (0, "Excellent"),
            (20, "Excellent"),
            (21, "Good"),
            (40, "Good"),
            (41, "Medium"),
            (60, "Medium"),
            (61, "High"),
            (80, "High"),
            (81, "Critical"),
            (100, "Critical"),
        ],
    )
    def test_rating_thresholds(self, score, expected_word):
        assert expected_word in get_score_rating(score)


class TestFormatIspType:

    def test_proxy(self):
        assert format_isp_type({"proxy": True, "hosting": False, "mobile": False}) == "Proxy/VPN"

    def test_datacenter(self):
        assert format_isp_type({"proxy": False, "hosting": True, "mobile": False}) == "Datacenter"

    def test_mobile(self):
        assert format_isp_type({"proxy": False, "hosting": False, "mobile": True}) == "Mobile"

    def test_residential(self):
        assert format_isp_type({"proxy": False, "hosting": False, "mobile": False}) == "Residential"
