# Catalog availability review, 2026-11-19

Community reports dated 2026-11-15 identified four unavailable domains. The
review distinguishes an outdated URL from an unavailable signup service.

| App | Evidence checked | Catalog decision |
| --- | --- | --- |
| ByteBenefit | `bytebenefit.com` redirects through `/lander` to a GoDaddy domain-sale URL. [bytebenefit.io](https://bytebenefit.io/) and its linked account dashboard are available. | Correct the URL in OpenPassiveHub; retain external-only status. No Docker integration or payout claim is added. |
| URnetwork | The old catalog URL does not provide the current app. The [official site](https://ur.io/), [web app](https://ur.io/app) and [documentation](https://ur.io/docs) are available. `bringyour/community-provider:g4-latest` publishes Linux amd64 and arm64 manifests. | Retain the built-in entry and correct its website, dashboard and non-referral link. |
| Adnade | [HugeDomains lists adnade.com for sale](https://www.hugedomains.com/domain_profile.cfm?d=adnade.com). No verified replacement for the cataloged bandwidth-sharing service was found. The similarly named adnade.net advertises a different advertising service. | Move the OpenPassiveHub entry to deprecated and remove the obsolete signup link. |
| GaGaNode | `gaganode.com/lander` serves GoDaddy domain-parking HTML. `dashboard.gaganode.com` returns NXDOMAIN using both Cloudflare (1.1.1.1) and Google (8.8.8.8) DNS. [Historical documentation](https://docs.gaganode.com/running/) remains indexed and was reachable during part of the review. | Move the community entry to deprecated and remove the obsolete signup link. |

These checks establish website and catalog availability as observed on the
review date. They do not establish authenticated enrollment, traffic, payouts,
or a permanent shutdown. Archived entries can be reconsidered when a working
service and verified official replacement are available.

The entry files in each source repository remain authoritative. Their manifests
are rebuilt with `scripts/build_manifest.py`; Money4Band then refreshes its
documentation snapshot and both app tables with `scripts/update_tables.py --refresh`.
