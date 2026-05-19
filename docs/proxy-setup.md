# Proxy & Multi-Proxy Setup

> Scale your earnings across multiple IP addresses.

---

## Why Use Proxies?

Many bandwidth-sharing apps limit earnings per IP address. By routing containers through different proxies, you can run multiple instances — each appearing to come from a unique IP. M4B supports both single-proxy and multi-proxy configurations.

## Single Proxy

Configure a single proxy in the interactive setup or directly in your config:

1. Run `m4b setup` and select **Yes** when asked about proxy usage.
2. Enter your proxy URL (e.g., `socks5://user:pass@proxy-host:1080`).
3. M4B wraps your containers with a VPN tunnel container that routes traffic through the proxy.

The proxy tunnel is injected into the generated `docker-compose.yaml`
alongside the app containers, tagged with the `proxy` Docker Compose
profile so it activates only when proxying is enabled.

## Multi-Proxy Setup

Multi-proxy lets you create **N independent instances**, each routed through a different proxy.

### Setup

1. Open the proxy tools menu:
   ```bash
   m4b proxy
   ```

2. Choose **Update multi-proxy instances**.

3. Provide a `proxies.txt` file with one proxy URL per line:
   ```
   socks5://user:pass@proxy1:1080
   socks5://user:pass@proxy2:1080
   http://user:pass@proxy3:8080
   ```

4. M4B creates a separate directory for each proxy instance, each with its own:
   - `docker-compose.yaml`
   - `.env` file
   - Unique device name & UUID
   - Isolated Docker network subnet

### How It Works

```
instances/
├── proxy-1/    → compose stack using proxy1
├── proxy-2/    → compose stack using proxy2
└── proxy-3/    → compose stack using proxy3
```

Each instance gets its own subnet (calculated automatically to avoid conflicts) and runs as an independent Docker Compose project.

### Managing Instances

From the proxy tools menu (`m4b proxy`):

- **Start all** / **Stop all** — Bulk operations across all instances
- **Update instances** — Regenerate from `proxies.txt`
- **Cleanup** — Remove all instance directories
- **Toggle install limits** — Enable/disable per-app instance limits

### Install Limits

By default, `enforce_install_limits` is `true` in `m4b-config.json`. This respects each app's documented device/IP limits to avoid account bans. You can toggle this from the proxy menu, but doing so is at your own risk.

## Supported Proxy Protocols

- `socks5://` — SOCKS5 proxy (recommended)
- `http://` — HTTP proxy
- `https://` — HTTPS proxy

## Tips

- **IP quality matters.** Run `m4b ip` to check your IP score before investing in proxies. Residential IPs earn significantly more than datacenter IPs.
- **Start small.** Test with 2-3 proxies before scaling up.
- **Monitor earnings.** Not all apps support datacenter IPs. Check the app catalog (`m4b apps`) for each app's IP policy.
