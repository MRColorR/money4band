# CLI Reference

> All 23 subcommands available via `m4b <command>` (or `python main.py <command>`).

---

## General Usage

```
m4b [--log-level LEVEL] [--dashboard true|false] <command> [options]
```

| Flag | Description |
|------|-------------|
| `--log-level LEVEL` | Set console log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) |
| `--dashboard true\|false` | Start / stop the web dashboard alongside any command |
| `--config-dir PATH` | Override the default config directory |
| `--log-dir PATH` | Override the default log directory |
| `--log-file NAME` | Override the log file name |

When invoked **without** a subcommand, M4B opens the **interactive menu**.

---

## Setup & Configuration

### `setup`
Run the interactive setup wizard: Docker check -> app selection -> credentials -> file generation.

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

### `config migrate-data-dir`
Copy the legacy `~/.m4b/{master.key, session.salt, backups/}` runtime state
into `<install>/.m4b/` so the install dir is fully self-contained (portable
between machines, immune to multi-install collisions). Idempotent -
re-running after a successful copy reports every entry as identical.

```bash
m4b config migrate-data-dir                 # copy only; legacy kept
m4b config migrate-data-dir --remove-source # wipes legacy after byte-verify
m4b config migrate-data-dir --force         # overwrites a divergent target
```

See [Configuration -> Runtime Data Directory](configuration.md#runtime-data-directory)
for the 3-tier resolver (`$M4B_DATA_DIR` -> `<install>/.m4b/` -> `~/.m4b/`).

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

### `stack start`
Start the Docker Compose stack.

```bash
m4b stack start
```

### `stack stop`
Stop the Docker Compose stack.

```bash
m4b stack stop
```

### `stack restart`
Stop then start the Docker Compose stack.

```bash
m4b stack restart
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

### `clean`
Prune orphan resources scoped to this M4B project - stopped containers and
unused networks tagged with `com.docker.compose.project=<this project>`.
Other Docker Compose projects on the same host are never touched.

```bash
m4b clean                  # containers + networks (with confirm)
m4b clean --dry-run        # preview without removing anything
m4b clean --volumes        # ALSO remove project volumes (DESTRUCTIVE)
m4b clean --yes            # skip confirmation prompt
```

`--volumes` wipes per-app persistent state (e.g. mystnode keystore). Use
only after backing up anything you need.

---

## Apps

### `apps`
List all apps grouped by category.

```bash
m4b apps                           # all categories
m4b apps --category supported      # supported (default, always active)
m4b apps --category candidate      # newcomers (candidates, opt-in)
m4b apps --category deprecated     # deprecated (removed for cause)
```

### `apps <name>`
Show the detailed info card (publisher, IP policy, device limits,
earnings estimate, referrals, last-verified date) for a specific app.

```bash
m4b apps honeygain
```

### `app add`
Launch the community app plugin wizard. Writes a new per-file bundle to
`config/apps.d/<NAME>.json` which is merged into the `newcomers`
category on next load.

```bash
m4b app add
```

### `app validate`
Validate every JSON file under `config/apps.d/` against the app schema.
Reports the exact error per file and exits non-zero if any file fails.

```bash
m4b app validate
```

### `links`
Display app dashboard URLs and referral links.

```bash
m4b links
```

## Catalog

Manage catalog sources and category activation. Every subcommand maps 1:1 to the
`/api/catalog/*` REST endpoints and to the `c Catalog sources` shortcut inside
the interactive App Catalog screen, so the three surfaces stay in sync.

### `catalog list`
List every declared catalog source with its type, enabled state, default source
tag, and target (path for local, URL for remote).

### `catalog status`
Print the same list enriched with cache metadata (resolved path, cached-entry
count, last `fetched_at` age for remote sources) plus the active/inactive flag
for each category.

### `catalog add <name> --type {local,remote}`
Register a new source. Required flags per type:

- `--url URL` (remote)
- `--path PATH` (local, relative to `m4b-config.json`)

Optional:

- `--default-source NAME` - tag entries with this provenance (defaults to
  `community` for remote, `builtin` for local)
- `--cache-path PATH`, `--timeout SECONDS` - remote-only
- `--disabled` - register the source disabled

Duplicate names are rejected.

### `catalog remove <name>`
Delete the source declaration. Cache directories are left on disk.

### `catalog enable <name>` / `catalog disable <name>`
Flip the `enabled` flag without touching anything else.

### `catalog refresh [name]`
Force-refresh every enabled remote source (or just `<name>`) by deleting the
stored ETag and re-downloading. Local sources are skipped.

### `catalog category list`
Show `active` status for `supported`, `newcomers`, and `deprecated`.

### `catalog category enable <name>` / `catalog category disable <name>`
Toggle one category on or off - inactive categories are hidden from the app
catalog, stack generation, and all surfaces.

**Examples:**

```bash
m4b catalog list
m4b catalog status
m4b catalog add community --type remote --url https://example.com/manifest.json --disabled
m4b catalog enable community
m4b catalog refresh community
m4b catalog category disable newcomers
m4b catalog remove community
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
Configure container DNS. Mode can be `default` (host DNS), `custom` (with `--servers`), or any preset name.

```bash
m4b dns set cloudflare                       # use Cloudflare preset
m4b dns set google                           # use Google preset
m4b dns set default                          # use host DNS
m4b dns set custom --servers 1.1.1.1,8.8.8.8  # inject custom servers (comma-separated)
```

### `dns list`
List all available DNS presets with their server addresses.

```bash
m4b dns list
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

```bash
m4b dashboard stop
```

### `dashboard status`
Check whether the dashboard is running.

```bash
m4b dashboard status
```

### `dashboard show-key`
Display the current API key.

```bash
m4b dashboard show-key
```

### `dashboard regenerate-key`
Generate a new API key (invalidates the old one).

```bash
m4b dashboard regenerate-key
```

### `dashboard restart`
Restart the background dashboard.

```bash
m4b dashboard restart
m4b dashboard restart --host 0.0.0.0 --port 9000
```

### `dashboard enable` / `dashboard disable`
Toggle dashboard auto-start on M4B launch.

```bash
m4b dashboard enable
m4b dashboard disable
```

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
