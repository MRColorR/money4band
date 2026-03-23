from __future__ import annotations

"""IP quality scoring — batch analysis of the real IP and proxy IPs.

Uses the ip-api.com free batch endpoint (max 100 IPs, 15 req/min)
and optional Spamhaus ZEN blacklist checking via Cloudflare DoH.
"""

import json
import logging
import re
from typing import Any
from urllib.parse import urlparse

from colorama import Fore, Style

from money4band.http_client import get_session


logger = logging.getLogger(__name__)
# ---------------------------------------------------------------------------
# IP providers (multi-fallback)
# ---------------------------------------------------------------------------
_IP_PROVIDERS = [
    "https://api.ipify.org",
    "https://ifconfig.me/ip",
    "https://icanhazip.com",
]

_IP_API_BATCH_URL = "http://ip-api.com/batch"
_IP_API_FIELDS = "status,query,country,city,isp,org,proxy,hosting,mobile"

_CLOUDFLARE_DOH = "https://1.1.1.1/dns-query"

# Regex to validate an IPv4 address.
_IPV4_RE = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

# Suspicious ISP keywords that increase fraud score.
_SUSPICIOUS_ISP_KEYWORDS = frozenset({
    "ovh", "hetzner", "digitalocean", "linode", "vultr", "aws", "amazon",
    "google cloud", "azure", "contabo", "scaleway", "oracle",
})


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------

def get_public_ip(timeout: int = 5) -> str | None:
    """Return the machine's public IPv4 address, trying multiple providers."""
    session = get_session()
    for url in _IP_PROVIDERS:
        try:
            resp = session.get(url, timeout=timeout)
            ip = resp.text.strip()
            if _IPV4_RE.match(ip):
                return ip
        except Exception:
            logger.debug("IP provider %s failed", url)
    logger.warning("Could not determine public IP from any provider")
    return None


def parse_proxy_file(path: str) -> list[str]:
    """Read *path* and return non-empty, non-comment lines."""
    try:
        with open(path) as fh:
            return [
                line.strip()
                for line in fh
                if line.strip() and not line.strip().startswith("#")
            ]
    except FileNotFoundError:
        logger.warning("Proxy file not found: %s", path)
        return []


def extract_proxy_ip(proxy_url: str) -> str:
    """Extract the bare host/IP from a proxy URL like ``socks5://user:pass@1.2.3.4:1080``."""
    parsed = urlparse(proxy_url if "://" in proxy_url else f"http://{proxy_url}")
    return parsed.hostname or proxy_url


def test_proxy_connectivity(proxy_url: str, timeout: int = 10) -> str | None:
    """Connect through *proxy_url* and return the exit IP, or ``None`` on failure."""
    session = get_session()
    try:
        resp = session.get(
            "https://api.ipify.org",
            proxies={"http": proxy_url, "https": proxy_url},
            timeout=timeout,
        )
        ip = resp.text.strip()
        if _IPV4_RE.match(ip):
            return ip
    except Exception as exc:
        logger.debug("Proxy connectivity test failed for %s: %s", proxy_url, exc)
    return None


def score_ips(ips: list[str]) -> list[dict[str, Any]]:
    """Batch-query ip-api.com for up to 100 IPs. Returns the API response list."""
    if not ips:
        return []
    payload = [{"query": ip, "fields": _IP_API_FIELDS} for ip in ips[:100]]
    session = get_session()
    try:
        resp = session.post(
            _IP_API_BATCH_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.error("ip-api.com batch request failed: %s", exc)
        return []


def check_blacklist(ip: str) -> bool:
    """Check *ip* against Spamhaus ZEN via Cloudflare DNS-over-HTTPS.

    Returns ``True`` if blacklisted (any ``127.0.0.x`` response).
    """
    reversed_ip = ".".join(ip.split(".")[::-1])
    qname = f"{reversed_ip}.zen.spamhaus.org"
    session = get_session()
    try:
        resp = session.get(
            _CLOUDFLARE_DOH,
            params={"name": qname, "type": "A"},
            headers={"Accept": "application/dns-json"},
            timeout=5,
        )
        data = resp.json()
        for answer in data.get("Answer", []):
            if answer.get("data", "").startswith("127.0.0."):
                return True
    except Exception as exc:
        logger.debug("Blacklist check failed for %s: %s", ip, exc)
    return False


def calculate_fraud_score(
    entry: dict[str, Any],
    blacklisted: bool = False,
) -> int:
    """Compute a composite fraud score (0–100) from ip-api fields + blacklist."""
    score = 0
    if entry.get("proxy"):
        score += 40
    if entry.get("hosting"):
        score += 30
    if entry.get("mobile"):
        score += 10
    if blacklisted:
        score += 30
    isp = (entry.get("isp") or "").lower()
    if any(kw in isp for kw in _SUSPICIOUS_ISP_KEYWORDS):
        score += 15
    return min(score, 100)


def get_score_rating(score: int) -> str:
    """Return a human-readable rating label for a fraud score."""
    if score <= 20:
        return f"{Fore.GREEN}Excellent{Style.RESET_ALL}"
    if score <= 40:
        return f"{Fore.GREEN}Good{Style.RESET_ALL}"
    if score <= 60:
        return f"{Fore.YELLOW}Medium{Style.RESET_ALL}"
    if score <= 80:
        return f"{Fore.RED}High{Style.RESET_ALL}"
    return f"{Fore.RED}Critical{Style.RESET_ALL}"


def format_isp_type(entry: dict[str, Any]) -> str:
    """Classify the ISP type from ip-api boolean flags."""
    if entry.get("proxy"):
        return "Proxy/VPN"
    if entry.get("hosting"):
        return "Datacenter"
    if entry.get("mobile"):
        return "Mobile"
    return "Residential"


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_ip_table(results: list[dict[str, Any]]) -> None:
    """Print a formatted table of IP analysis results."""
    if not results:
        print(f"{Fore.YELLOW}No IP results to display.{Style.RESET_ALL}")
        return

    # Header
    print(
        f"\n  {'#':<4} {'IP Address':<17} {'Score':<8} {'Rating':<20} "
        f"{'Type':<14} {'Location':<25} {'Blacklist'}"
    )
    print(f"  {'-'*4} {'-'*17} {'-'*8} {'-'*12} {'-'*14} {'-'*25} {'-'*9}")

    for i, r in enumerate(results, 1):
        ip = r.get("query", "?")
        score = r.get("_fraud_score", 0)
        rating = get_score_rating(score)
        isp_type = format_isp_type(r)
        location = f"{r.get('city', '?')}, {r.get('country', '?')}"
        bl = r.get("_blacklisted", False)
        bl_str = f"{Fore.RED}YES{Style.RESET_ALL}" if bl else f"{Fore.GREEN}no{Style.RESET_ALL}"

        label = "REAL" if i == 1 and not r.get("_is_proxy") else f"P{i - 1}" if r.get("_is_proxy") else str(i)
        print(
            f"  {label:<4} {ip:<17} {score:<8} {rating:<20} "
            f"{isp_type:<14} {location:<25} {bl_str}"
        )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def analyse_ips(proxy_file: str | None = None) -> list[dict[str, Any]]:
    """Run the full IP analysis: real IP + all proxies.

    When *proxy_file* is ``None`` (the default) only the real public IP
    is scored.  Pass an explicit path to include proxy IPs.

    Returns the enriched results list.
    """
    results: list[dict] = []

    # 1. Get real public IP
    print(f"{Fore.CYAN}Detecting public IP...{Style.RESET_ALL}")
    real_ip = get_public_ip()
    if not real_ip:
        print(f"{Fore.RED}Could not determine public IP.{Style.RESET_ALL}")
        return results

    all_ips = [real_ip]
    proxy_ip_map: dict[str, str] = {}  # exit_ip → proxy_url

    # 2. Test proxy connectivity (only when a proxy file was provided)
    proxies = parse_proxy_file(proxy_file) if proxy_file else []
    if proxies:
        print(
            f"{Fore.CYAN}Testing {len(proxies)} proxies...{Style.RESET_ALL}"
        )
        for proxy_url in proxies:
            exit_ip = test_proxy_connectivity(proxy_url)
            if exit_ip and exit_ip not in all_ips:
                all_ips.append(exit_ip)
                proxy_ip_map[exit_ip] = proxy_url
            elif exit_ip is None:
                print(
                    f"  {Fore.YELLOW}FAIL: {extract_proxy_ip(proxy_url)}{Style.RESET_ALL}"
                )

    # 3. Batch IP scoring
    print(f"{Fore.CYAN}Scoring {len(all_ips)} IP(s) via ip-api.com...{Style.RESET_ALL}")
    api_results = score_ips(all_ips)

    # 4. Blacklist check + fraud score
    for entry in api_results:
        ip = entry.get("query", "")
        bl = check_blacklist(ip) if entry.get("status") == "success" else False
        entry["_blacklisted"] = bl
        entry["_fraud_score"] = calculate_fraud_score(entry, bl)
        entry["_is_proxy"] = ip in proxy_ip_map

    # 5. Display
    display_ip_table(api_results)

    # Average score for working proxies
    proxy_scores = [e["_fraud_score"] for e in api_results if e.get("_is_proxy")]
    if proxy_scores:
        avg = sum(proxy_scores) / len(proxy_scores)
        print(
            f"\n  Average proxy fraud score: {avg:.0f}/100 "
            f"({get_score_rating(int(avg))})"
        )

    return api_results
