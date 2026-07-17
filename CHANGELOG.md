# Changelog

All notable changes to this project are documented in this file.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [5.0.0]

Major rewrite: config-driven CLI + optional web dashboard, replacing the
older shell/menu-only workflow.

### Added

- CLI + guided setup wizard (`m4b` subcommands alongside the interactive menu).
- Encrypted-at-rest credential storage (tokens, passwords, API keys).
- Multi-proxy scaling: multiple IPs/instances under one configuration.
- Web dashboard with a Bearer-token-authenticated API.
- Auto-claim sidecars for daily-reward apps.
- Resource limit profiles (CPU/RAM presets per app).
- IP quality scoring before deployment.
- Encrypted backup & restore.
- Webhook notifications (Discord, Telegram, and anywhere Shoutrrr reaches).
- Self-update (`m4b update`).
- Per-file catalog layout with a pluggable `CatalogSource` interface,
  remote/community sources, and user-owned catalog overrides.

### Removed

- The referral-offers subsystem (`m4b offers`, `config/offers.d/`, the
  `/api/offers` endpoint): every shipped offer was an unconfigured
  placeholder. May return in a later release with real referral links.
  App referral links are unaffected (`m4b links`).

### Fixed (release review wave)

- **Stack start actually starts the earning apps.** Every generated
  service is gated behind a Docker Compose tier profile, but both the
  menu and the dashboard API resolved profiles from the raw (folded)
  m4b-config and activated none of them - `compose up` started only
  watchtower (menu) or nothing at all (dashboard). Profile resolution
  now aggregates the catalog everywhere, `stop` covers the full profile
  universe, and the compose/.env builders reject the raw folded shape.
- **Self-update from binaries works end-to-end.** The updater requested
  asset names the release workflow never published (guaranteed 404).
  Releases are now single-file binaries named `Money4Band-<os>-<arch>`
  with a generated `checksums.sha256`; a contract test keeps the updater
  and the workflow in sync. The update-check cache moved from the
  world-writable temp dir to the per-user data dir and is validated
  before being trusted.
- **Dashboard starts on released binaries.** The background spawn used
  `python -c`, which a frozen executable cannot interpret - the
  dashboard died instantly on every packaged build. Frozen builds now
  relaunch themselves via an internal `dashboard serve` entrypoint.
- **Web login over LAN.** The session cookie was marked `Secure` when
  the server was bound to `0.0.0.0`, but the dashboard is plain HTTP -
  browsers dropped the cookie and login looped forever.
- **Credentials survive `.env` generation.** Values are now escaped for
  Docker Compose interpolation (`$` -> `$$`, quoting for `#`/spaces);
  a password like `Abc$123` was silently mangled before. Non-scalar
  config (the notifications events map) no longer leaks into `.env`.
- **Second start after secure `.env` deletion.** The start flow wipes
  `.env` after `compose up`; the next start now regenerates it (main
  stack and proxy instances) instead of refusing or silently skipping
  instances while reporting success. Dashboard-URL generation gained the
  same `.env.meta` fallback.
- Re-setup can no longer assign the same host port to two apps
  (previously only live-bound ports were excluded, so collisions
  appeared with the stack stopped).
- `arm/v6` vs `arm/v7` image variants are no longer treated as
  interchangeable when pinning platform-compatible tags.
- Regenerating files from the menu produced an app-less compose/.env
  (same folded-catalog bug) and restarted the stack without profile
  flags; both paths now go through the canonical helpers.
- Proxy-mode port mappings no longer leak back into the persisted
  user-config template (shallow-copy bug), and a missing compatible
  image tag disables just that app instead of crashing the whole
  assembly on ARM hosts.
- Catalog-overrides writes are atomic and encryption-preserving (a crash
  mid-write could truncate the credentials file).
- `m4b info` now refreshes the detected OS/architecture instead of
  showing the template placeholder (Linux/amd64) on fresh installs.
- Performance: bulk `docker inspect` for health polling, shared HTTP
  client with connection pooling, remote-catalog fetches honor a 1h
  min-refresh window, config decrypt/reload only after menu actions,
  registry tag fetches memoized, dropped a flat 4s sleep per GHCR image.

### Fixed (release-prep pass)

- Replaced `datetime.UTC` with `datetime.timezone.utc` in
  `money4band/apps/remote_cache.py` - `datetime.UTC` requires Python 3.11+
  while the project targets 3.10, which is also in the CI test matrix.
- Removed a duplicated `_security_headers` middleware registration in
  `money4band/api/server.py` (merge artifact - both copies were running
  on every request).
- Guarded `importlib.util.spec_from_file_location()` returning `None` in
  `money4band/core/loader.py` instead of failing with an unguarded
  `AttributeError` deeper in the call.
- Tightened self-update binary permissions from `0o755` to `0o700`
  (bandit B103 - only the current user ever runs it).
- Satisfied the mypy CI gate (`mypy --ignore-missing-imports money4band/
  main.py`), which was red with 64 errors, via explicit annotations at
  the boundary where `json.loads()` / `response.json()` / `dict.get()`
  returns crossed into typed function signatures.
- Normalized all shipped source, docs, and config text to pure ASCII.

## [Unreleased]

Nothing yet.
