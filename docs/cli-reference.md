# CLI Reference

> All 23 subcommands available via `m4b <command>` (or `python main.py <command>`).

---

## General Usage

```
m4b [--version] [--verbose] [--dashboard true|false] <command> [options]
```

| Flag | Description |
|------|-------------|
| `--version` | Print version and exit |
| `--verbose` | Enable DEBUG-level console logging |
| `--dashboard true\|false` | Start / stop the web dashboard alongside any command |

When invoked **without** a subcommand, M4B opens the **interactive menu**.

---

## Setup & Configuration

### `setup`
Run the interactive setup wizard: Docker check → app selection → credentials → file generation.

```bash
m4b setup
```

### `config view`
Display the current configuration (credentials are redacted).

```bash
m4b config view
```

### `config edit`
Open the configuration in your default editor.

```bash
m4b config edit
```

### `reset`
Reset `user-config.json` to the factory template.

```bash
m4b reset
```

### `profile create <name>`
Save the current configuration as a named profile.

```bash
m4b profile create gaming-rig
```

### `profile switch <name>`
Load a previously saved profile.

```bash
m4b profile switch gaming-rig
```

### `profile delete <name>`
Delete a saved profile.

```bash
m4b profile delete gaming-rig
```

---

## Stack Operations

### `start`
Start the Docker Compose stack.

```bash
m4b start
```

### `stop`
Stop the Docker Compose stack.

```bash
m4b stop
```

### `status`
Show container status and health checks.

```bash
m4b status
```

### `generate`
Regenerate `docker-compose.yaml` and `.env` from current configuration.

```bash
m4b generate
```

---

## Apps

### `apps`
List all supported apps grouped by category.

```bash
m4b apps
m4b apps --category residential
```

### `apps <name>`
Show detailed information for a specific app.

```bash
m4b apps honeygain
```

### `app add`
Launch the community app plugin wizard.

```bash
m4b app add
```

### `app validate`
Validate a community app plugin JSON file.

```bash
m4b app validate
```

### `links`
Display app dashboard URLs and referral links.

```bash
m4b links
```

### `offers`
Browse referral and passive-income offers.

```bash
m4b offers
m4b offers --category bandwidth
```

---

## Network & Proxy

### `proxy`
Open the multi-proxy management menu.

```bash
m4b proxy
```

### `ip`
Run an IP quality analysis.

```bash
m4b ip
```

### `dns set <mode>`
Configure container DNS. Modes: `default`, `cloudflare`, `cloudflare-security`, `google`, `quad9`, `quad9-unfiltered`, `opendns`, `dns4eu`, `dns4eu-unfiltered`.

```bash
m4b dns set cloudflare
m4b dns set custom --servers 1.1.1.1 9.9.9.9
```

---

## System

### `info`
Display system information (OS, Docker, RAM, CPU, active profile, DNS, apps, proxy status).

```bash
m4b info
```

### `limit [profile]`
View or set the active resource limit profile. Profiles: `minimal`, `conservative`, `standard`, `performance`.

```bash
m4b limit              # show current
m4b limit conservative # switch profile
```

### `validate`
Run Docker image security checks on configured app images.

```bash
m4b validate
```

---

## Backup & Restore

### `backup`
Create an encrypted backup of `user-config.json`.

```bash
m4b backup
```

### `restore`
Restore from a previous backup.

```bash
m4b restore
```

---

## Dashboard

### `dashboard start`
Start the web dashboard (foreground).

```bash
m4b dashboard start
```

### `dashboard stop`
Stop a running background dashboard.

### `dashboard status`
Check whether the dashboard is running.

### `dashboard show-key`
Display the current API key.

### `dashboard regenerate-key`
Generate a new API key.

### `dashboard enable` / `dashboard disable`
Toggle dashboard auto-start.

---

## Notifications

### `notify test`
Send a test notification through the configured webhook.

```bash
m4b notify test
```

---

## Maintenance

### `update`
Check for M4B updates and apply if available.

```bash
m4b update
```
