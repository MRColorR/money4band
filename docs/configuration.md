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
| `system.compose_mode` | `monolithic` | `monolithic` or `layered` compose output |
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
`m4b-config.json`; no separate `app-config.json` file ships.
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

If you upgrade from a checkout that still has a standalone
`app-config.json`, the loader auto-folds it into `m4b-config.json` on
first run (one-time `app-config.json.v1.bak` backup). The legacy
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

## Compose Modes

### Monolithic (Default)

All services are written to a single `docker-compose.yaml`. Simple and compatible with all Docker Compose versions.

### Layered

Services are split into 6 separate compose files by IP-policy tier:

```
compose.yml                  # base (network + watchtower)
compose.residential.yml      # residential-IP apps
compose.datacenter.yml       # datacenter-OK apps
compose.universal.yml        # any-IP apps
compose.service.yml          # auto-claim sidecars
compose.proxy.yml            # VPN tunnel
```

Enable layered mode by editing `config/m4b-config.json`:
```jsonc
{
  "system": {
    "compose_mode": "layered"
  }
}
```

Layered mode is useful for advanced users who want to selectively start/stop app groups.

## Backup & Restore

```bash
m4b backup    # create encrypted backup → ~/.m4b/backups/
m4b restore   # pick from recent backups to restore
```

Backups are raw file copies — if the config is encrypted, the backup stays encrypted. Up to 5 backups are retained automatically.
