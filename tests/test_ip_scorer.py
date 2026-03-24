"""Tests for IP quality scoring (utils/ip_scorer.py)."""

from unittest.mock import MagicMock, patch

import pytest

from money4band.network.ip_scorer import (
    calculate_fraud_score,
    extract_proxy_ip,
    format_isp_type,
    get_public_ip,
    get_score_rating,
    parse_proxy_file,
    score_ips,
)


class TestGetPublicIp:
    @patch("money4band.network.ip_scorer.get_session")
    def test_returns_ip_from_first_provider(self, mock_sess):
        resp = MagicMock()
        resp.text = "1.2.3.4"
        mock_sess.return_value.get.return_value = resp
        assert get_public_ip() == "1.2.3.4"

    @patch("money4band.network.ip_scorer.get_session")
    def test_returns_none_when_all_fail(self, mock_sess):
        mock_sess.return_value.get.side_effect = Exception("fail")
        assert get_public_ip() is None

    @patch("money4band.network.ip_scorer.get_session")
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

    @patch("money4band.network.ip_scorer.get_session")
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

    @patch("money4band.network.ip_scorer.get_session")
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
        assert (
            format_isp_type({"proxy": True, "hosting": False, "mobile": False})
            == "Proxy/VPN"
        )

    def test_datacenter(self):
        assert (
            format_isp_type({"proxy": False, "hosting": True, "mobile": False})
            == "Datacenter"
        )

    def test_mobile(self):
        assert (
            format_isp_type({"proxy": False, "hosting": False, "mobile": True})
            == "Mobile"
        )

    def test_residential(self):
        assert (
            format_isp_type({"proxy": False, "hosting": False, "mobile": False})
            == "Residential"
        )


class TestCheckBlacklist:
    """DNS-over-HTTPS Spamhaus query via mocked HTTP session."""

    @patch("money4band.network.ip_scorer.get_session")
    def test_blacklisted_ip(self, mock_sess):
        resp = MagicMock()
        resp.json.return_value = {"Answer": [{"data": "127.0.0.2"}]}
        mock_sess.return_value.get.return_value = resp
        from money4band.network.ip_scorer import check_blacklist

        assert check_blacklist("1.2.3.4") is True

    @patch("money4band.network.ip_scorer.get_session")
    def test_clean_ip(self, mock_sess):
        resp = MagicMock()
        resp.json.return_value = {}
        mock_sess.return_value.get.return_value = resp
        from money4band.network.ip_scorer import check_blacklist

        assert check_blacklist("8.8.8.8") is False

    @patch("money4band.network.ip_scorer.get_session")
    def test_exception_returns_false(self, mock_sess):
        mock_sess.return_value.get.side_effect = ConnectionError("timeout")
        from money4band.network.ip_scorer import check_blacklist

        assert check_blacklist("1.2.3.4") is False


class TestTestProxyConnectivity:
    """Connectivity test via mocked HTTP session through proxy."""

    @patch("money4band.network.ip_scorer.get_session")
    def test_returns_ip_on_success(self, mock_sess):
        resp = MagicMock()
        resp.text = "  203.0.113.5  "
        mock_sess.return_value.get.return_value = resp
        from money4band.network.ip_scorer import test_proxy_connectivity

        assert test_proxy_connectivity("socks5://1.2.3.4:1080") == "203.0.113.5"

    @patch("money4band.network.ip_scorer.get_session")
    def test_returns_none_on_failure(self, mock_sess):
        mock_sess.return_value.get.side_effect = ConnectionError
        from money4band.network.ip_scorer import test_proxy_connectivity

        assert test_proxy_connectivity("http://bad:8080") is None

    @patch("money4band.network.ip_scorer.get_session")
    def test_rejects_non_ip_response(self, mock_sess):
        resp = MagicMock()
        resp.text = "not-an-ip"
        mock_sess.return_value.get.return_value = resp
        from money4band.network.ip_scorer import test_proxy_connectivity

        assert test_proxy_connectivity("http://proxy:8080") is None


class TestDisplayIpTable:
    """Table display handles empty and populated result lists."""

    def test_empty_results(self, capsys):
        from money4band.network.ip_scorer import display_ip_table

        display_ip_table([])
        assert "No IP results" in capsys.readouterr().out

    def test_displays_rows_with_score_and_rating(self, capsys):
        from money4band.network.ip_scorer import display_ip_table

        results = [
            {
                "query": "1.2.3.4",
                "status": "success",
                "_fraud_score": 15,
                "_blacklisted": False,
                "_is_proxy": False,
                "proxy": False,
                "hosting": False,
                "mobile": False,
                "city": "NYC",
                "country": "US",
            },
            {
                "query": "5.6.7.8",
                "status": "success",
                "_fraud_score": 75,
                "_blacklisted": True,
                "_is_proxy": True,
                "proxy": True,
                "hosting": False,
                "mobile": False,
                "city": "London",
                "country": "UK",
            },
        ]
        display_ip_table(results)
        out = capsys.readouterr().out
        # Row 1: real IP with Excellent rating (score 15 < 21)
        assert "1.2.3.4" in out
        assert "NYC" in out
        assert "Excellent" in out
        assert "REAL" in out
        # Row 2: proxy IP with High rating (score 75, 61-80) and blacklisted
        assert "5.6.7.8" in out
        assert "London" in out
        assert "High" in out
        assert "YES" in out  # blacklist flag


class TestAnalyseIps:
    """Full analysis orchestrator with mocked network."""

    @patch("money4band.network.ip_scorer.check_blacklist", return_value=False)
    @patch("money4band.network.ip_scorer.score_ips")
    @patch("money4band.network.ip_scorer.get_public_ip", return_value="1.2.3.4")
    @patch("money4band.network.ip_scorer.display_ip_table")
    def test_real_ip_only(self, _display, mock_pub, mock_score, _bl):
        mock_score.return_value = [
            {
                "query": "1.2.3.4",
                "status": "success",
                "proxy": False,
                "hosting": False,
                "mobile": False,
            }
        ]
        from money4band.network.ip_scorer import analyse_ips

        results = analyse_ips()
        assert len(results) == 1
        assert results[0]["query"] == "1.2.3.4"

    @patch("money4band.network.ip_scorer.get_public_ip", return_value=None)
    def test_no_public_ip_returns_empty(self, _pub):
        from money4band.network.ip_scorer import analyse_ips

        assert analyse_ips() == []

    @patch("money4band.network.ip_scorer.check_blacklist", return_value=False)
    @patch("money4band.network.ip_scorer.score_ips")
    @patch("money4band.network.ip_scorer.test_proxy_connectivity", return_value="5.6.7.8")
    @patch("money4band.network.ip_scorer.parse_proxy_file", return_value=["http://proxy:8080"])
    @patch("money4band.network.ip_scorer.get_public_ip", return_value="1.2.3.4")
    @patch("money4band.network.ip_scorer.display_ip_table")
    def test_with_proxy_file(self, _display, _pub, _parse, _test, mock_score, _bl):
        mock_score.return_value = [
            {
                "query": "1.2.3.4",
                "status": "success",
                "proxy": False,
                "hosting": False,
                "mobile": False,
            },
            {
                "query": "5.6.7.8",
                "status": "success",
                "proxy": True,
                "hosting": False,
                "mobile": False,
            },
        ]
        from money4band.network.ip_scorer import analyse_ips

        results = analyse_ips(proxy_file="proxies.txt")
        assert len(results) == 2
