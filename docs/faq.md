# FAQ & Troubleshooting

---

## General

### How much can I earn?

Earnings depend on your **IP quality**, **location**, and **number of apps**. Residential IPs in tier-1 countries (US, UK, DE) earn the most. Typical range: **$5–$50/month** per IP with all compatible apps running.

### Is this safe?

M4B only runs official Docker images published by each app's developer. Your bandwidth is shared — not your personal data. M4B encrypts your credentials at rest and hardens containers with `no-new-privileges`.

### Which apps should I run?

Run `m4b apps` to see all supported apps. Start with the top earners (EarnApp, Honeygain, Pawns) and add more as you get comfortable.

### Do I need a powerful machine?

No. M4B runs lightweight Docker containers. A Raspberry Pi 4 or old laptop is sufficient. Use `m4b limit minimal` to reduce resource usage further.

---

## Setup Issues

### Docker is not installed

Run `m4b setup` — it offers to install Docker automatically. On Windows, you need WSL2 + Docker Desktop.

### "Permission denied" on Linux

Run with `sudo`, or add your user to the `docker` group:
```bash
sudo usermod -aG docker $USER
# Log out and back in
```

### Setup asks for credentials I don't have

Create an account on the app's website first, then:
- **Email/password apps**: Use your login credentials.
- **Token apps**: Find the token in the app's dashboard/settings.
- **UUID apps**: M4B can auto-generate UUIDs.

---

## Runtime Issues

### Containers keep restarting

Check logs:
```bash
docker compose logs <container-name>
```

Common causes:
- Invalid credentials (re-run `m4b setup`)
- IP blocked by the app (check `m4b ip`)
- Port conflict (check `m4b status`)

### Some apps show "unhealthy"

Health checks may fail if:
- The app's server is down (temporary — wait and retry)
- Your IP is blocked by that app
- The container needs time to initialize (give it 2-3 minutes)

### Low earnings

1. **Check IP quality**: `m4b ip` — datacenter or flagged IPs earn much less.
2. **Check app status**: `m4b status` — ensure containers are healthy.
3. **Add more apps**: `m4b apps` — not all apps may be enabled.
4. **Consider residential proxies**: See [Proxy Setup](proxy-setup.md).

---

## Configuration Issues

### I lost my master encryption key

If `~/.m4b/master.key` is lost, you cannot decrypt your saved credentials. Run `m4b reset` to start fresh and re-enter credentials via `m4b setup`.

### How do I change the DNS?

```bash
m4b dns list              # see available presets
m4b dns set cloudflare    # use a preset
m4b generate              # regenerate files with new DNS
m4b stack restart          # restart stack
```

Or use the **interactive menu** which shows the same presets.

### How do I switch between monolithic and layered compose?

Edit `config/m4b-config.json`:
```json
"compose_mode": "layered"
```
Then regenerate: `m4b generate`.

---

## Dashboard Issues

### Dashboard won't start

- Check if port 8088 is already in use: `m4b dashboard status`
- Try a different port in `config/user-config.json` → `dashboard.port`
- Ensure `fastapi` and `uvicorn` are installed (included in requirements)

### Can I access the dashboard remotely?

The dashboard binds to `localhost` by default. Exposing it remotely requires additional setup (reverse proxy, HTTPS) and enables API key authentication. **Not recommended** without proper security.

---

## Updates

### How do I update M4B?

```bash
m4b update
```

For binary installs: download the latest release from GitHub.

### How do I update app containers?

Watchtower runs alongside your stack and automatically pulls new container images. No action needed.
