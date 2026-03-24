# Package Structure — Module Inventory

> Complete map of every module in the `money4band` package.

---

## `apps/` — App Management

| Module | Purpose |
|--------|---------|
| `catalog.py` | Display app catalog grouped by category (active / deprecated / candidate) |
| `configurator.py` | Collect per-app credentials during setup |
| `earnings.py` | Bandwidth & earnings estimation |
| `info.py` | CLI `m4b apps [name]` — list apps or show detail |
| `offers.py` | Referral & passive-income offers directory |
| `schema.py` | JSON Schema validation for community app plugins |
| `setup.py` | Interactive setup wizard — full app onboarding flow |
| `wizard.py` | CLI `m4b app add` — community app plugin wizard |

## `core/` — Configuration & Data

| Module | Purpose |
|--------|---------|
| `backup.py` | Create / restore / cleanup encrypted config backups (`~/.m4b/backups/`) |
| `crypto.py` | Fernet AES-128-CBC encryption for credentials at rest |
| `dumper.py` | Pretty-print data structures for debugging |
| `loader.py` | Config file I/O — load / save / merge JSON configs |
| `profiles.py` | Named configuration profiles (create / switch / delete) |
| `progress.py` | Terminal progress indicators |
| `reset.py` | Reset `user-config.json` to factory template |
| `viewer.py` | CLI `m4b config view` / `m4b config edit` |

## `docker/` — Docker Operations

| Module | Purpose |
|--------|---------|
| `checker.py` | Verify Docker is installed and running |
| `compose_builder.py` | Assemble layered Docker Compose files (6 layers) |
| `env_builder.py` | Generate `.env` file from configuration |
| `generator.py` | Regenerate compose + `.env` + UUID device names |
| `helper.py` | Docker install instructions & guides |
| `image_security.py` | Docker image security scanning & validation |
| `install.py` | Automated Docker installation |
| `monitor.py` | Container health monitoring (`m4b status`) |
| `start.py` | Start Docker Compose stack(s) |
| `stop.py` | Stop Docker Compose stack(s) |
| `watchtower.py` | Watchtower auto-updater configuration |

## `network/` — Networking & Proxy

| Module | Purpose |
|--------|---------|
| `downloader.py` | HTTP file downloads with retry-backoff |
| `http_client.py` | Shared HTTP session with timeout/retry defaults |
| `ip_scorer.py` | IP quality scoring via external APIs |
| `multiproxy.py` | Multi-proxy instance management (subnet calc, directory lifecycle) |
| `networker.py` | Network utilities — IP lookup, gateway detection |
| `port_manager.py` | Port allocation & conflict detection |
| `proxy_tools.py` | Interactive proxy management menu |

## `system/` — System Detection

| Module | Purpose |
|--------|---------|
| `detector.py` | OS, architecture, platform detection; WSL awareness |
| `info.py` | System information display (`m4b info`) |
| `resource_profiles.py` | CPU / RAM resource limit profiles (4 tiers) |

## `ui/` — User Interface

| Module | Purpose |
|--------|---------|
| `banner.py` | ASCII art banner & version display |
| `bye.py` | Farewell messages on exit |
| `cls.py` | Cross-platform terminal clear |
| `notification_setup.py` | Interactive notification webhook setup |
| `prompt.py` | Styled input prompts & validators |
| `summary.py` | Configuration summary display |

## `api/` — REST API (FastAPI)

| Module | Purpose |
|--------|---------|
| `server.py` | FastAPI app, CORS, Bearer auth, SSE events, static mount |
| `_deps.py` | Shared request dependencies |
| `schemas.py` | Pydantic request / response models |
| `router_*.py` | 13 endpoint routers (stack, config, apps, system, monitor, backups, profiles, earnings, ip, offers, notifications, update, security) |

## `dashboard/` — Web Dashboard

| Module | Purpose |
|--------|---------|
| `cli.py` | CLI dispatcher for `m4b dashboard <action>` |
| `menu.py` | Interactive dashboard sub-menu (8 items) |
| `setup.py` | Dashboard setup wizard, PID management, background spawn |

## Root Modules

| Module | Purpose |
|--------|---------|
| `notifier.py` | Fire-and-forget webhook notifications via Shoutrrr |
| `services.py` | UI-agnostic service layer (bridges CLI / Menu / API) |
| `structured_logging.py` | JSON structured log formatter |
| `updater.py` | Self-update mechanism (version check + apply) |
| `readme_generator.py` | Auto-generate `README.md` app table from config |
