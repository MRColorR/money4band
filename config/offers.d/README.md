# External Referral Offers

Each file in this folder is **one offer bundle** - an external referral
for a VPN / proxy / affiliate / crypto-exchange / survey service that
M4B does not run as a Docker app.

## File naming

`<SLUG>.json` where `SLUG` is the uppercase kebab-case form of the
offer name (e.g. `NORDVPN.json`, `MULLVAD-VPN.json`).

## Schema

```jsonc
{
  "name": "NordVPN",
  "url": "https://...",          // null until a referral link is configured
  "bonus": "Up to 73% off + 3 months free",
  "category": "vpn",            // vpn | proxy | affiliate | crypto-exchange | survey | other
  "notes": "Optional note / status"
}
```

App referrals (Honeygain, EarnApp, ...) are **not** stored here - they
live in the catalog bundles at `config/catalog/<category>/<NAME>.json`,
which is the single source of truth.

## CLI

```bash
m4b offers                       # list everything
m4b offers --category vpn        # filter
```
