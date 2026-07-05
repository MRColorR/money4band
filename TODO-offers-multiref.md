# TODO: multiple referral links for offers

Offers (`config/offers.d/*.json`) currently support a single `url` field, so
they do **not** support multiple referral links like apps do.

Apps store a `referrals[]` array in their catalog bundles and pick among them
via `pick_referral_url` / `get_picked_referrals` (see
`money4band/apps/offers.py` and `money4band/api/router_apps.py`).

To bring offers to parity:

- Change the offer schema from a single `url` to a `referrals[]` array.
- Reuse the apps' picker logic (`pick_referral_url` / `get_picked_referrals`)
  and the same contributor-pool selection used for app referrals, so offer
  links rotate/weight the same way.
- Migrate existing `offers.d/*.json` (`url` -> `referrals: [{ "url": ... }]`)
  and update `offers_store.py` read/write + the offers view rendering.
- No need to keep Keep backward compatibility for a single `url` during migration.
