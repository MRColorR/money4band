# Proxy & Multi-Proxy Setup

Route one stack through a proxy or give each instance its own proxy.

---

## Why Use Proxies?

Each proxy provides an exit IP for a stack. Check each provider's terms for
proxy use and device or IP limits before enabling that app in a proxied stack.

## Single Proxy

Configure a single proxy in the interactive setup or directly in your config:

1. Run `m4b setup` and select **Yes** when asked about proxy usage.
2. Enter your proxy URL (e.g., `socks5://user:pass@proxy-host:1080`).
3. M4B wraps your containers with a tunnel container that routes traffic through the proxy.

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
|-- proxy-1/    -> compose stack using proxy1
|-- proxy-2/    -> compose stack using proxy2
+-- proxy-3/    -> compose stack using proxy3
```

Each instance gets its own subnet (calculated automatically to avoid conflicts) and runs as an independent Docker Compose project.

### Managing Instances

From the proxy tools menu (`m4b proxy`):

- **Start all** / **Stop all** - Bulk operations across all instances
- **Update instances** - Regenerate from `proxies.txt`
- **Cleanup** - Remove all instance directories
- **Toggle install limits** - Enable/disable per-app instance limits

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

## Tips

- Start with a small number of proxies and verify each stack independently.
- Check container status in Money4Band and enrollment in the provider's dashboard.
