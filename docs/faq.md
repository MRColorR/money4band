# FAQ & Troubleshooting

---

## General

### How much can I earn?

Earnings vary with provider demand, location, network eligibility, and usage.
Check each provider's dashboard for actual usage, balance, and payout status.

### Is this safe?

Money4Band runs apps in Docker and encrypts saved credentials. Each provider
defines how its app uses your connection and which networks it accepts.
Review the provider terms and [Money4Band security controls](security.md).

### Which apps should I run?

Start with the [app directory](APPS.md). Run `m4b apps` to check the catalog
in your installation and confirm the provider permits your network type.
See [App Management](app-management.md#app-catalog) for how to enable
candidates and install standalone apps.

### Can I run Money4Band on multiple devices?

Yes. Check each provider's device and IP limits before reusing an account
or sharing a connection across hosts. For multiple instances on one host,
see [Proxy Setup](proxy-setup.md) and use only apps that allow proxies.

### Do I need a powerful machine?

Requirements depend on the apps you enable. Check the
[platform requirements](getting-started.md#prerequisites) and use
[`m4b limit minimal`](cli-reference.md#limit-profile) if you need tighter CPU
and memory limits.

---

## Setup Issues

### The release asset won't extract

Run the platform executable directly. For a source archive, download
**Source code (zip)** from the release or use **Code > Download ZIP** on
GitHub. See [Getting Started](getting-started.md).

### "Permission denied" when running the binary

On Linux and macOS, set the executable bit with `chmod +x <filename>`.
If the error persists on a USB stick or network share, see the
[Linux launch instructions](getting-started.md#linux) for `noexec` mounts.

### macOS: "cannot be opened because the developer cannot be verified"

The release binary is unsigned. Follow the
[macOS launch instructions](getting-started.md#macos) for opening it.

### "cannot execute binary file: Exec format error"

Check the architecture with `uname -m` and select the corresponding
[release asset](getting-started.md#option-a---download-the-binary-recommended).

### Docker is not installed

See the [Docker prerequisites](getting-started.md#prerequisites) for your
platform. Start Docker before running the stack.

### "Permission denied" on Linux

If the message mentions the Docker socket, see
[Docker access on Linux](getting-started.md#linux).

### Setup asks for credentials I don't have

Create an account on the app's website first, then:
- **Email/password apps**: Use your login credentials.
- **Token apps**: Find the token in the app's dashboard/settings.
- **UUID apps**: M4B can auto-generate UUIDs.

---

## Runtime Issues

### Containers keep restarting

Check container status in the dashboard or with `m4b status`, then inspect logs using
`docker compose logs <service>` from the affected stack directory. Check for
rejected credentials, network eligibility errors, or port conflicts. Open
**Setup Apps** if you need to update credentials.

### Some apps show "unhealthy"

Health checks may fail if:
- The app's server is down (temporary - wait and retry)
- Your IP is blocked by that app
- The container needs time to initialize (give it 2-3 minutes)

### Low earnings

Check whether the container is running in the dashboard or with `m4b status`, then confirm the
device and traffic are visible in the provider's dashboard. Ask the provider
about payout delays or missing usage.

---

## Configuration Issues

### I lost my master encryption key

Recover the original key from a backup if possible. See
[Runtime Data Directory](configuration.md#runtime-data-directory) for the
key location. If the key is gone, saved credentials cannot be decrypted.
Choose **Reset user-config File**, then re-enter them through **Setup Apps**.
The CLI equivalents are `m4b reset` and `m4b setup`.

### How do I change the DNS?

See [DNS Configuration](configuration.md#dns-configuration) for the
presets, commands, and restart steps.

### How do I start only specific app tiers (e.g. only residential apps)?

Use [Docker Compose profiles](configuration.md#starting-selectively) to
start selected tiers or named services.

### How do I clean up old containers / networks?

Start with `m4b clean --dry-run`. See the
[`clean` reference](cli-reference.md#clean) for scope and what the
`--volumes` flag removes.

### How do I make my install portable (USB stick, multi-machine)?

See [Runtime Data Directory](configuration.md#runtime-data-directory)
for which files to keep with your install and how to migrate legacy data.
Some apps store their device identity separately. Check the
[provider setup and migration notes](app-management.md#provider-onboarding)
before moving an existing stack.

---

## Dashboard Issues

### Dashboard won't start

Open **M4B Dashboard and APIs** to check the dashboard, or use `m4b dashboard status`.
If port 8088 is busy, see
[Accessing the Dashboard](dashboard-api.md#accessing-the-dashboard) for the
configured port and how to find the one in use.

### Can I access the dashboard remotely?

Yes. Follow [Starting the Dashboard](dashboard-api.md#starting-the-dashboard)
and [API Authentication](dashboard-api.md#api-authentication) for web-exposed
mode. See [Security](security.md#rest-api-hardening-v50) before exposing it.

---

## Updates

### How do I update M4B?

Open **System Info → Check for updates** to check for and install an offered
stable release, or use `m4b update`. For
prereleases, manual binary replacement, and v4 migration, follow
[Upgrade an existing installation](getting-started.md#upgrade-an-existing-installation).

### How do I update app containers?

If enabled during setup, Watchtower updates eligible app images while the
stack runs. Money4Band itself is updated separately.
