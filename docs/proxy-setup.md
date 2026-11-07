# Proxy & Multi-Proxy Setup

Route one stack through a proxy or give each instance its own proxy.

---

## Why Use Proxies?

Each proxy provides an exit IP for a stack. Check each provider's terms for
proxy use and device or IP limits before enabling that app in a proxied stack.

## Single Proxy

Configure a single proxy in the interactive setup or directly in your config:

1. Open **Setup Apps** and select **Yes** when asked about proxy usage.
2. When setup asks for `proxies.txt`, provide a file containing one proxy URL
   such as `socks5://user:pass@proxy-host:1080`.
3. M4B wraps your containers with a tunnel container that routes traffic through the proxy.

The proxy tunnel is injected into the generated `docker-compose.yaml`
alongside the app containers, tagged with the `proxy` Docker Compose
profile so it activates only when proxying is enabled.

## Multi-Proxy Setup

Multi-proxy lets you create **N independent instances**, each routed through a different proxy.

### Setup

1. Open **Setup Apps** and enable proxy use.

2. Prepare `proxies.txt` when setup asks for it.

3. List one proxy URL per line:
   ```
   socks5://user:pass@proxy1:1080
   socks5://user:pass@proxy2:1080
   http://user:pass@proxy3:8080
   ```

4. Complete setup. M4B uses one proxy for the main stack and creates additional
   instance directories for the remaining proxies, each with its own:
   - `docker-compose.yaml`
   - `.env` file
   - Unique device name & UUID
   - Isolated Docker network subnet

### How It Works

The additional stacks live under `m4b_proxy_instances/`.

Each instance gets its own subnet (calculated automatically to avoid conflicts) and runs as an independent Docker Compose project.

### Managing Instances

From **Multiproxy Tools** (also opened by `m4b proxy`):

- **Update Proxies for Multiproxy Instances** updates existing instances from `proxies.txt`.
- **Toggle Install-Limit Enforcement** enables or disables per-app instance limits.

Use **Start apps stack** and **Stop apps stack** in the main menu to control
the stack and its proxy instances. The CLI equivalents are described under
[Stack Operations](cli-reference.md#stack-operations).

### Install Limits

The `enforce_install_limits` setting defaults to `true` in
`m4b-config.json`. Money4Band uses the limits recorded in its catalog.
Check each provider's current rules for your account and network.

## Supported Proxy Protocols

- `socks5://` - SOCKS5 proxy (recommended)
- `http://` - HTTP CONNECT proxy, TCP only
- `socks4://` - SOCKS4 proxy, TCP only

The bundled tunnel rejects `https://` and `socks5h://` proxy URLs. An
`http://` CONNECT proxy can still tunnel HTTPS connections to websites.
[Tunnel protocol support](https://github.com/xjasonlyu/tun2socks/wiki/Proxy-Models)

## Proxy Providers

Choose a provider for apps that support and permit proxy use. Referral links
support Money4Band through a commission on qualifying purchases.

| Provider | Description |
| --- | --- |
| [BirdProxies](https://birdproxies.com/@money4band) | Static ISP and residential proxies for dedicated connections in your multi-proxy setup.<br>Bonus code: `MONEY4BAND` - 10% off. |

## Tips

- Start with a small number of proxies and verify each stack independently.
- Check container status in Money4Band and enrollment in the provider's dashboard.
