# Getting Started

> From zero to passive income in under five minutes.

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| OS | Windows 10+, macOS 12+, Linux (Debian/Ubuntu) | WSL2 supported on Windows |
| Docker | Docker Engine 20.10+ or Docker Desktop | `m4b setup` can install it for you |
| Python | 3.10+ | Only needed when running from source |

## Option A — Download the Binary (Recommended)

1. Go to **[Releases](https://github.com/MRColorR/money4band/releases)** and download the binary for your platform.
2. Run it:

```bash
# Linux / macOS
chmod +x m4b && ./m4b

# Windows
m4b.exe
```

3. The interactive menu guides you through setup.

## Option B — Run from Source

```bash
git clone https://github.com/MRColorR/money4band.git
cd money4band
pip install -r requirements.txt
python main.py
```

## First-Time Setup

When you launch M4B for the first time, choose **Setup Apps** from the menu (or run `m4b setup`):

1. **Docker check** — M4B verifies Docker is installed. If not, it offers to install it.
2. **App selection** — Pick the apps you want to run. Each app shows its IP policy (residential / datacenter / universal) and payout info.
3. **Credentials** — Enter the credentials required by each selected app (email, token, etc.). Credentials are encrypted with Fernet (AES-128-CBC) and stored in `config/user-config.json`.
4. **Generation** — M4B generates your `docker-compose.yaml` and `.env` file.
5. **Start** — Launch the stack with `m4b start` or choose **Start Stack** from the menu.

## Verifying Everything Works

```bash
# Check container status
m4b status

# View IP quality score (important for earnings)
m4b ip

# Open the web dashboard (optional)
m4b dashboard start
```

## Next Steps

- [CLI Reference](cli-reference.md) — all 23 subcommands
- [App Management](app-management.md) — enable / disable apps, community plugins
- [Proxy Setup](proxy-setup.md) — scale across multiple proxies
- [Dashboard & API](dashboard-api.md) — web UI for monitoring
- [Security](security.md) — how your credentials are protected
