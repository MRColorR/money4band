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
