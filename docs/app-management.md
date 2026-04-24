# App Management

> Enable, disable, and extend the apps that earn for you.

---

## App Catalog

M4B ships with **35 passive-income apps** split across three categories:

| Category | Count | Description |
|----------|-------|-------------|
| **Supported** | 21 | Active, tested apps included in setup (ToS-compliant, Docker images tracked) |
| **Newcomers** *(candidate)* | 8 | Apps under 6-month community evaluation — visible with `--category candidate` |
| **Deprecated** | 6 | Previously supported apps removed for cause (shutdown, ToS issues, unreliable earnings) |

> The internal category key for *Candidate* apps is `newcomers`; the CLI
> surface accepts `candidate` (user-facing) while the on-disk layout and
> API use `newcomers`.

View the catalog:

```bash
m4b apps                         # full catalog grouped by category
m4b apps --category supported    # only supported
m4b apps --category candidate    # only newcomers (candidates)
m4b apps --category deprecated   # only deprecated (with removal notes)
m4b apps honeygain               # detailed info card for one app
```

Interactively, the **App Catalog** screen also exposes a `m` shortcut to
**manage category status** — toggle `newcomers` / `deprecated` on or off
so they appear during `m4b setup`.

## On-Disk Layout (v2.0)

The catalog is **per-file**: one JSON bundle per app. The envelope is
**folded into `m4b-config.json`** under the `catalog` key — no standalone
`app-config.json` ships.

```
config/
├── m4b-config.json              ← project config + catalog envelope (under "catalog")
├── catalog/
│   ├── supported/
│   │   ├── HONEYGAIN.json       ← one CatalogEntry per file
│   │   ├── TRAFFMONETIZER.json
│   │   └── …
│   ├── newcomers/
│   ├── deprecated/
│   └── addons/                  ← sidecars with parent_id
├── apps.d/
│   └── <MYAPP>.json             ← hand-written community overlay (merged into newcomers)
├── offers.d/
│   └── <SLUG>.json              ← one external referral offer per file
└── user-config.json             ← your settings (encrypted at rest)
```

The envelope is tiny (lives under `m4b-config.json → catalog`):

```jsonc
// m4b-config.json (excerpt)
"catalog": {
  "app_config_version": 2.0,
  "catalog_sources": [
    {
      "type": "local",
      "path": "catalog",
      "default_source": "builtin",
      "enabled": true
    }
  ],
  "categories": {
    "supported":  {"active": true},
    "newcomers":  {"active": false},
    "deprecated": {"active": false}
  }
}
```

At load time the loader walks every declared `catalog_sources[]` entry,
reads the per-file bundles, and aggregates them back into the in-memory
shape used by the rest of the codebase. Adding, moving or removing an
app is a single-file change — no more merge conflicts on a 3600-line
monolith.

### Migration

If you open an older checkout, the loader auto-migrates on first run:

* Monolithic `app-config.json` is split into
  `config/catalog/<category>/<NAME>.json` per-file bundles.
* The resulting envelope is folded under `m4b-config.json → catalog`.
* The legacy `app-config.json` is renamed to `app-config.json.v1.bak`.
* Monolithic `referral-offers.json` is split into
  `config/offers.d/<SLUG>.json` and the original renamed to
  `referral-offers.json.v1.bak`.

You can also trigger migration explicitly:

```bash
python scripts/migrate_catalog_v1_to_v2.py        # defaults to config/m4b-config.json
python scripts/migrate_catalog_v1_to_v2.py -v     # verbose
```

The migration is idempotent: running it again on an already-folded
config is a no-op.

## Catalog Sources

Each entry in `catalog_sources[]` is handled by a concrete source class
in [`money4band/apps/sources.py`](../money4band/apps/sources.py). Two
source types ship today:

| Type | Implementation | Status |
|------|----------------|--------|
| `local` | `LocalSource` — reads per-file bundles under `path` (relative to the envelope file's parent). | Active |
| `remote` | `RemoteSource` — HTTPS fetch of an aggregated manifest, cached per-file on disk. | Active |

Sources are processed **in order**. The first source to claim a given
entry name (case-insensitive) wins — local/builtin bundles remain
authoritative over any remote fetch. Source failures are isolated: a
broken source is logged and skipped, never crashes the loader.

### Remote source behaviour

`RemoteSource` fetches a single aggregated `manifest.json` from the
configured `url` and rehydrates it into the local filesystem cache so
the on-disk layout mirrors a built-in catalog exactly:

```
<cache_path>/
├── .etag           # last server ETag (used for If-None-Match)
├── .fetched_at     # ISO-8601 UTC timestamp of last successful call
├── supported/<NAME>.json
├── newcomers/<NAME>.json
└── deprecated/<NAME>.json
```

- **Opt-in** — no remote source ships enabled by default. Users add an
  entry to `m4b-config.json → catalog.catalog_sources`.
- **Timeout** — defaults to `5.0` seconds; override via `timeout`.
- **ETag / 304** — the cached ETag is sent as `If-None-Match`; on 304
  the existing cache is reused untouched.
- **Offline fallback** — on network error, timeout, non-200 status, or
  invalid JSON, the cache is read as-is; no exception reaches the
  loader.
- **Atomic replace** — a successful 200 wipes the `supported/`,
  `newcomers/`, and `deprecated/` subdirs and writes fresh bundles
  (`.etag` and `.fetched_at` are preserved across refreshes).

Accepted manifest shapes (the server may emit any of these):

```jsonc
// 1. Category envelope
{ "supported": { "entries": [ {"name": "FOO", ...} ] }, "newcomers": {"entries": []} }

// 2. Bare category lists
{ "supported": [ {"name": "FOO", ...} ], "deprecated": [] }

// 3. Flat list with per-entry category
{ "entries": [ {"name": "FOO", "category": "supported", ...} ] }
```

Example envelope with a second (disabled by default) remote source:

```jsonc
{
  "app_config_version": 2.0,
  "catalog_sources": [
    { "type": "local",  "path": "catalog", "default_source": "builtin", "enabled": true },
    { "type": "remote",
      "url":  "https://raw.githubusercontent.com/MRColorR/money4band-community-catalog/main/manifest.json",
      "default_source": "community",
      "cache_path": "catalog/community",
      "enabled": false,
      "timeout": 5.0 }
  ],
  "categories": { "supported": {"active": true}, "newcomers": {"active": false}, "deprecated": {"active": false} }
}
```

## App Bundle Schema

Every bundle — whether shipped under `config/catalog/`, dropped into
`config/apps.d/`, or fetched from a remote catalog — follows the same
schema. The required fields are validated by
[`money4band/apps/schema.py::validate_app_entry()`](../money4band/apps/schema.py).

### Required fields

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | `^[A-Z][A-Z0-9_]+$` — uppercase, matches the filename stem |
| `compose_config` | object | Full Docker-Compose service definition (must include `image`) |
| `flags` | object | Credential keys prompted during setup (`email`, `password`, `apikey`, `uuid`, `userid`, `token`, `cid`, …) |
| `install_limit` | integer | Max instances per-machine / per-proxy (`-1` = unlimited) |
| `compose_layer` | string | One of `residential`, `datacenter`, `universal`, `service` |

### Optional fields

| Field | Type | Notes |
|-------|------|-------|
| `dashboard` | string | URL of the app's web dashboard (rendered by `m4b links`) |
| `referrals` | array | `[{url, contributor, added?, verified?, verified_by?[]}]` — referral pool (never a bare `link` string) |
| `additional_details` | string | Optional Markdown note — explains removal reason, ToS caveats, etc. |
| `app_details` | object | Rich metadata (publisher, IP policy, device limits, earnings, Docker status, `last_verified`). Used by `m4b apps <name>` and the dashboard |
| `user_config_template` | object | Default user-config slice (`{enabled: false, <cred_key>: "", service_enabled?: false}`) merged into `user-config.json → apps.<name_lower>` on reset / first enable |

> **Bundle completeness:** every bundle that declares credential `flags`
> MUST carry a matching `user_config_template`. The template is a
> non-destructive merge — existing user values are never overwritten.

### Minimal example

```jsonc
{
  "name": "MYAPP",
  "dashboard": "https://dashboard.myapp.example/",
  "compose_config": {
    "container_name": "${DEVICE_NAME}_myapp",
    "hostname": "${DEVICE_NAME}_myapp",
    "image": "myapp/myapp:latest",
    "environment": ["MYAPP_TOKEN=${MYAPP_TOKEN}"],
    "restart": "always"
  },
  "flags": { "token": {} },
  "install_limit": 1,
  "compose_layer": "universal",
  "referrals": [
    { "url": "https://myapp.example/ref/XYZ", "contributor": "MRColorR" }
  ],
  "user_config_template": {
    "enabled": false,
    "token": "yourMYAPPToken"
  }
}
```

## Enabling / Disabling Apps

During `m4b setup`, you choose which apps to enable. To modify later:

1. Run `m4b setup` again — existing credentials are preserved (the wizard
   only prompts for newly enabled apps).
2. Or edit `config/user-config.json` directly (flip `apps.<name>.enabled`)
   and run `m4b generate` to regenerate the compose files.
3. Or use the REST API / web dashboard (`PUT /api/apps/<name>`).

## Auto-Claim Sidecars (Addons)

Some apps can be paired with an optional **sidecar container** that
automatically claims daily rewards. Sidecars ship as standalone **addon
bundles** under `config/catalog/addons/<NAME>.json`, each referencing a
parent app via `parent_id`. The loader merges them in when the parent
is enabled AND the user opted in.

> **ToS note:** auto-claim sidecars for Honeygain and PacketShare are
> **not shipped in the core Money4Band catalog** because they bypass the
> daily reward flow the host service expects. They live in the opt-in
> [community catalog](https://github.com/MRColorR/money4band-community-catalog)
> alongside EarnApp. Enable that source from `m4b catalog add` if you
> want them.

### Addon bundle shape

```jsonc
{
  "name": "MYAPP_POT",
  "parent_id": "MYAPP",
  "description": "Auto-claims daily reward",
  "credentials_shared": true,
  "compose_layer": "service",
  "compose_config": {
    "container_name": "${DEVICE_NAME}_myapp-pot",
    "image": "ghcr.io/contrib/myapp-pot:latest",
    "environment": ["EMAIL=${MYAPP_EMAIL}", "PASSWORD=${MYAPP_PASSWORD}"],
    "restart": "always"
  }
}
```

**Enablement is opt-in.** During `m4b setup`, after you enter credentials
for a parent app that has a matching addon, the wizard asks:

```
MyApp has an auto-claim sidecar: MYAPP_POT
  Auto-claims daily reward  (currently OFF)
Enable MYAPP_POT for MyApp? (y/n)
```

Your choice is stored as `apps.<name_lower>.service_enabled` in
`user-config.json`. Toggle it later by re-running `m4b setup`, editing
the JSON directly (then `m4b generate`), or via the web dashboard.

> **Layered compose:** addons are written into `compose.service.yml`
> (layered mode) or merged into `docker-compose.yaml` (monolithic mode —
> the default).

## Community App Plugins

You can add apps that aren't in the shipped catalog via the **App
Wizard**:

```bash
m4b app add
```

The wizard prompts for:

1. **Name** — uppercase identifier (`^[A-Z][A-Z0-9_]+$`)
2. **Docker image** — e.g. `publisher/app:latest`
3. **Authentication type** — email, token, UUID, user ID, API key, or manual
4. **Compose layer** — `residential` / `datacenter` / `universal` / `service`
5. **Install limit** — max instances per machine (`-1` = unlimited)
6. **Sidecar?** — optional auto-claim container
7. **Health check?** — optional `healthcheck` block

The generated bundle is written to `config/apps.d/<NAME>.json`, validated
against the schema, and merged into the `newcomers` category on next
load.

### Validating Plugins

After hand-editing a file under `config/apps.d/`, validate it:

```bash
m4b app validate
```

Invalid files are logged with the exact schema error and skipped at load
time — they never crash the loader.

## Referral Offers

Browse referral bonuses and passive-income offers:

```bash
m4b offers
m4b offers --category bandwidth   # bandwidth | compute | survey | other
```

Offers come from two sources:

* Every bundle's `referrals[]` pool (single source of truth).
* An optional `config/referral-offers.json` for hand-curated promos.

When multiple referral URLs exist for an app, M4B applies a **sticky
per-user pick** (stored under
`user-config.json → settings.picked_referrals`) so the same URL is
offered across runs.

## Compose Layers

Apps are assigned to compose layers based on their IP policy:

| Layer | File (layered mode) | Contents |
|-------|---------------------|----------|
| base | `compose.yml` | Network + Watchtower |
| residential | `compose.residential.yml` | Apps requiring residential IPs |
| datacenter | `compose.datacenter.yml` | Apps that work on datacenter IPs |
| universal | `compose.universal.yml` | Apps that work on any IP type |
| service | `compose.service.yml` | Auto-claim sidecars |
| proxy | `compose.proxy.yml` | VPN / SOCKS tunnel containers |

In **monolithic mode** (default, `m4b-config.json → system.compose_mode: "monolithic"`)
all layers are merged into a single `docker-compose.yaml`. In **layered
mode** each layer is a separate file composed via
`docker compose -f ... -f ...`.

## Promoting Candidates to Supported

Maintainers move a newcomer into `supported` with:

```bash
python scripts/promote_apps.py <NAME>
```

The script reads `config/catalog/newcomers/<NAME>.json`, stamps
`app_details.docker`, `recommendation`, `last_verified`, adds any
`*_SIDECAR` services if applicable, and calls
`catalog_store.move_entry()` to relocate the bundle to
`config/catalog/supported/<NAME>.json`. The move is atomic and a single
file change — no envelope edits required.
