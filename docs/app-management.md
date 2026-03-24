# App Management

> Enable, disable, and extend the apps that earn for you.

---

## App Catalog

M4B tracks **35 passive-income apps** across three categories:

| Category | Description |
|----------|-------------|
| **Supported** | Active, tested apps included in setup |
| **Deprecated** | Previously supported apps removed for cause (shutdown, ToS issues, etc.) |
| **Candidate** | Apps under evaluation — not yet available in setup |

View the catalog:

```bash
m4b apps                         # full catalog
m4b apps --category supported    # filter by category
m4b apps honeygain               # detailed info for one app
```

### App Metadata

Each app entry in `config/app-config.json` includes:

- **Official name & publisher**
- **IP policy**: residential, datacenter, or universal
- **Payout method & minimum** (e.g., PayPal $5.00, crypto $0.20)
- **Device limits** per account
- **Install limit** (max instances in M4B)
- **Compose layer** assignment (residential / datacenter / universal)
- **Docker image** with tag
- **Health check** configuration
- **Earnings estimates** & confidence level
- **Warnings** (e.g., "Requires residential IP")

## Enabling / Disabling Apps

During `m4b setup`, you choose which apps to enable. To modify later:

1. Run `m4b setup` again — it preserves existing credentials.
2. Or edit `config/user-config.json` directly and run `m4b generate` to regenerate compose files.

## Auto-Claim Sidecars

Some apps (e.g., Honeygain) have optional **sidecar containers** that automatically claim daily rewards. These are configured alongside the main app container:

```yaml
# Example: honeygain-pot runs alongside honeygain
honeygain-pot:
  image: honeygain/honeygain-pot
  depends_on: [honeygain]
```

Sidecars are enabled automatically when you enable the parent app.

## Community App Plugins

You can add apps that aren't in the official catalog via the **App Wizard**:

```bash
m4b app add
```

The wizard prompts for:

1. **App name** (UPPERCASE convention)
2. **Docker image** (e.g., `publisher/app:latest`)
3. **Authentication type** (email, token, UUID, user ID, or manual)
4. **Compose layer** (residential / datacenter / universal)
5. **Optional flags** (sidecar, health check, etc.)

The plugin is validated against a JSON Schema and added to your local app-config.

### Validating Plugins

```bash
m4b app validate
```

## Referral Offers

Browse referral bonuses and passive-income offers:

```bash
m4b offers
m4b offers --category bandwidth
```

Offers are sourced from app metadata (single source of truth) and an optional `referral-offers.json`.

## Compose Layers

Apps are assigned to compose layers based on their IP policy:

| Layer | File | Apps |
|-------|------|------|
| residential | `compose.residential.yml` | Apps requiring residential IPs |
| datacenter | `compose.datacenter.yml` | Apps that work on datacenter IPs |
| universal | `compose.universal.yml` | Apps that work on any IP type |
| service | `compose.service.yml` | Auto-claim sidecars |
| proxy | `compose.proxy.yml` | VPN tunnel containers |
| base | `compose.yml` | Network + Watchtower |

In **monolithic mode** (default), all layers are merged into a single `docker-compose.yaml`.  
In **layered mode**, each layer is a separate file, composed via `docker compose -f ... -f ...`.
