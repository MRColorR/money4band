# Configuration

> How M4B stores, secures, and manages your settings.

---

## Config Files

| File | Location | Purpose |
|------|----------|---------|
| `m4b-config.json` | `config/` | Project settings — ports, DNS presets, menu, word lists, compose mode **and** catalog envelope under `catalog` key (`app_config_version`, `catalog_sources[]`, per-category `active` flags — see [App Management](app-management.md#on-disk-layout-v20)) |
| `catalog/` | `config/` | Per-file app bundles under `supported/` / `newcomers/` / `deprecated/` (one JSON file per app) |
| `apps.d/` | `config/` | Hand-written community overlays merged into `newcomers` at load time |
| `offers.d/` | `config/` | Per-file external referral offers (one JSON file per offer) |
| `user-config.json` | `config/` | **Your settings** — credentials, proxy config, preferences (encrypted at rest) |

> The catalog envelope (folded under `m4b-config.json → catalog`) + `catalog/` + `apps.d/` are aggregated
> in-memory at load time via the pluggable catalog-source interface in
> [`money4band/apps/sources.py`](../money4band/apps/sources.py). See the
> [Catalog Sources](app-management.md#catalog-sources) section for the
> source model and ordering rules.

### user-config.json

This is the only file you need to care about. It stores:

- App credentials (encrypted at rest)
- Enabled/disabled app selections
- Proxy configuration
- Dashboard settings
- Notification webhook URL

A factory template exists at `template/user-config.json`. Reset anytime with:

```bash
m4b reset
```

### m4b-config.json

Project-level settings you can tune:

| Key | Default | Description |
|-----|---------|-------------|
| `ports.default_port_base` | `50000` | Starting port for app port allocation |
| `ports.port_offset_per_app` | `1000` | Port stride between apps |
| `ports.port_offset_per_instance` | `3` | Port stride between multi-proxy instances |
| `system.dns.available_modes` | list | Selectable DNS presets exposed by `m4b dns` |
| `system.registry_request_timeout` | `15` | Seconds before giving up on a Docker-registry probe |
| `system.registry_max_retries` | `3` | Docker-registry retry attempts |

> **Note:** User-mutable settings (`resource_profile`, `dns_mode`, `dns_servers`,
> `enforce_install_limits`, `setup_completed`, `picked_referrals`) live in
> `user-config.json` under the `settings` section. See
> [`template/user-config.json`](../template/user-config.json) for defaults.

### Catalog envelope (folded into `m4b-config.json`)

The catalog envelope lives under the `catalog` key of
`m4b-config.json`; no separate standalone catalog file ships.
The envelope itself is intentionally small:

```jsonc
// m4b-config.json (excerpt)
{
  "project": { "project_version": "5.0.0" },
  "catalog": {
    "app_config_version": 2.0,
    "catalog_sources": [
      { "type": "local", "path": "catalog", "default_source": "builtin", "enabled": true }
    ],
    "categories": {
      "supported":  { "active": true  },
      "newcomers":  { "active": false },
      "deprecated": { "active": false }
    }
  }
}
```

Per-app bundles live under `config/catalog/<category>/<NAME>.json` — one
file per app. See [App Management → On-Disk Layout](app-management.md#on-disk-layout-v20)
for the full schema and the source-plugin model.

If you upgrade from a checkout that still has a standalone legacy
catalog file, the loader auto-folds it into `m4b-config.json` on
first run (one-time `.v1.bak` backup). The legacy
monolithic `referral-offers.json` is likewise auto-split into
`config/offers.d/<SLUG>.json` per-file bundles. You can also run the
migration by hand: `python scripts/migrate_catalog_v1_to_v2.py`.

## Configuration Profiles

Save and switch between named configurations:

```bash
m4b profile create work-pc     # save current config
m4b profile create gaming-rig  # save another

m4b profile switch work-pc     # restore "work-pc" config
m4b profile delete gaming-rig  # remove a profile
```

Profiles are stored at `config/profiles/{name}/` and include both `user-config.json` and `.env`.

## Resource Limit Profiles

Control how much CPU and memory containers are allowed to use:

| Profile | CPU Limit | Memory Limit | Use Case |
|---------|-----------|--------------|----------|
| `minimal` | 20% | 10% | Background, shared machine |
| `conservative` | 40% | 25% | Light usage alongside other work |
| `standard` | 60% | 40% | **Default** — balanced |
| `performance` | 85% | 65% | Dedicated earning machine |

```bash
m4b limit                # view current profile
m4b limit conservative   # switch profile
```

## DNS Configuration

Configure which DNS servers your containers use:

```bash
m4b dns                                      # show current DNS config
m4b dns list                                 # list available presets
m4b dns set cloudflare                       # use Cloudflare 1.1.1.1
m4b dns set google                           # use Google 8.8.8.8
m4b dns set quad9                            # use Quad9 9.9.9.9 (malware blocking)
m4b dns set default                          # use host DNS
m4b dns set custom --servers 1.1.1.1,8.8.8.8  # inject custom servers (comma-separated)
```

Available presets: `default`, `cloudflare`, `cloudflare-security`, `google`, `quad9`, `quad9-unfiltered`, `opendns`, `dns4eu`, `dns4eu-unfiltered`, `custom`.

The same presets are available through the **interactive menu** and the **REST API** (`PUT /api/system/dns`).

## Docker Compose Profiles

M4B generates a single `docker-compose.yaml` per project. Each service
carries a `profiles:` array of one entry, driven by the app bundle's
`profile` field. This gives selective startup via standard Docker Compose
semantics — bring up only the apps you want with `--profile <name>`.

### Reserved profiles

| Profile | Used by | Notes |
|---------|---------|-------|
| `residential` | Apps that need a residential IP (Honeygain, Bitping, …) | Tagged via bundle `profile: "residential"` |
| `datacenter` | Apps tolerating datacenter IPs (Repocket, Mystnode, …) | Tagged via bundle `profile: "datacenter"` |
| `universal` | Apps accepting any IP (TraffMonetizer, …) | Tagged via bundle `profile: "universal"` |
| `service` | Sidecars and helper services | Apps that ship as helper containers; addons inherit their parent's profile |
| `monitoring` | Watchtower | Auto-update service for app images |
| `proxy` | tun2socks tunnel | Activated only when `proxies.enabled` is true in user-config |

### Starting selectively

`m4b stack start` auto-discovers profiles in use from your enabled apps
and activates the right set — you never need to pass `--profile` by hand.

Power users can drop to raw Docker Compose for surgical control:

```bash
# Only residential-IP apps
docker compose --profile residential --env-file .env up -d

# Residential apps + Watchtower
docker compose --profile residential --profile monitoring --env-file .env up -d

# Single named service
docker compose --env-file .env up -d honeygain bitping
```

Compose v2.20+ is recommended (`include:` directive support, modern
profile semantics). v1.28+ is the minimum (profile selection support).

### Sidecar profile inheritance

Auto-claim sidecar containers (the "pots") **inherit their parent app's
profile** at generation time. Starting `--profile residential` brings up
Honeygain AND its `honeygain-pot` together — no separate flag needed,
no orphan-pot edge cases.

## Backup & Restore

```bash
m4b backup    # create encrypted backup → <data-dir>/backups/
m4b restore   # pick from recent backups to restore
```

Backups are raw file copies — if the config is encrypted, the backup stays encrypted. Up to 5 backups are retained automatically. The `<data-dir>` location is resolved by the rules in the next section.

## Runtime Data Directory

The master encryption key, session salt, and config backups live in a runtime
data directory. M4B resolves the location with a 3-tier precedence:

1. **`$M4B_DATA_DIR`** — environment variable, highest priority. Use this for
   custom layouts (e.g. shared volumes, container deployments).
2. **`<install>/.m4b/`** — portable default. The install dir is the directory
   containing the executable (frozen binary) or the repo root (source checkout).
   Used automatically when the install dir is writable and no legacy `~/.m4b`
   exists, or whenever the portable dir is already populated.
3. **`~/.m4b/`** — legacy fallback for users upgrading from older M4B builds,
   and for system-installed binaries on read-only paths.

Why portable: a PyInstaller binary on a USB stick, or a git clone moved between
machines, carries its key + salt + backups with it. Multiple installs on one
machine stay isolated.

### Migrating from `~/.m4b/` to the portable dir

If your install already wrote to `~/.m4b/`, copy the runtime state into the
install dir:

```bash
m4b config migrate-data-dir                 # copy only; keeps the source
m4b config migrate-data-dir --remove-source # copy then wipe the legacy dir
m4b config migrate-data-dir --force         # overwrite differing target files
```

The command is idempotent — re-running it with the same source and target after
a successful copy reports every entry as "already identical" and does nothing.
It refuses to overwrite a divergent target without `--force`.
